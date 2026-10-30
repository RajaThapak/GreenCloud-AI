import re
from math import ceil

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...collectors.config import REGIONS
from ...execution import states as S
from ...models.core import AuditLog, User, Workload
from ...models.execution import ExecutionRun
from ..audit import audit
from ..deps import get_cloud, get_db, make_manager
from ..errors import ApiError
from ..helpers import detail, org_settings
from ..schemas_v2 import AdvanceIn, AuditOut, AwsVerifyIn, CreateUserIn, SettingsIn, SettingsOut, UserOut, WorkloadDetail
from ..security import current_user, hash_password, require_admin

router = APIRouter(tags=["admin"])
ARN = re.compile(r"^arn:aws:iam::\d{12}:role/[\w+=,.@\-/]+$")


def _user_out(user: User) -> UserOut:
    return UserOut(id=user.id, email=user.email, role=user.role, org_id=user.org_id)


def _settings_out(value) -> SettingsOut:
    return SettingsOut(
        budget=value.budget, default_mode=value.default_mode, regions=value.regions or [],
        aws_connected=value.aws_connected, aws_role_arn=value.aws_role_arn, aws_external_id=value.aws_external_id,
    )


@router.get("/settings", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db), user: User = Depends(current_user)):
    value = org_settings(db, user.org_id)
    db.commit()
    return _settings_out(value)


@router.put("/settings", response_model=SettingsOut)
def put_settings(body: SettingsIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    unknown = [region for region in body.regions if region not in REGIONS]
    if unknown:
        raise ApiError(422, f"Unknown region(s): {', '.join(unknown)}.", "bad_region")
    value = org_settings(db, admin.org_id)
    value.budget, value.default_mode, value.regions = body.budget, body.default_mode, body.regions
    audit(db, admin, "settings.update", admin.org_id)
    db.commit()
    return _settings_out(value)


@router.post("/settings/aws/verify", response_model=SettingsOut)
def verify_aws(body: AwsVerifyIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    role_arn = body.role_arn.strip()
    if not ARN.match(role_arn):
        raise ApiError(422, "Enter a valid role ARN.", "bad_arn")
    value = org_settings(db, admin.org_id)
    value.aws_role_arn, value.aws_connected = role_arn, True
    audit(db, admin, "aws.connect", role_arn)
    db.commit()
    return _settings_out(value)


@router.get("/admin/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return [_user_out(user) for user in db.scalars(select(User).where(User.org_id == admin.org_id).order_by(User.id))]


@router.post("/admin/users", response_model=UserOut, status_code=201)
def create_user(body: CreateUserIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    email = body.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        raise ApiError(409, "An account with this email already exists.", "email_taken")
    user = User(email=email, password_hash=hash_password(body.password), role=body.role, org_id=admin.org_id)
    db.add(user)
    db.flush()
    audit(db, admin, "user.create", email, {"role": body.role})
    db.commit()
    return _user_out(user)


@router.get("/admin/audit", response_model=list[AuditOut])
def audit_log(limit: int = 50, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    emails = {user.id: user.email for user in db.scalars(select(User).where(User.org_id == admin.org_id))}
    rows = db.scalars(
        select(AuditLog).where(AuditLog.org_id == admin.org_id).order_by(AuditLog.id.desc()).limit(min(max(limit, 1), 200))
    )
    return [
        {"id": row.id, "user_email": emails.get(row.user_id), "action": row.action, "target": row.target,
         "detail": row.detail, "created_at": row.created_at}
        for row in rows
    ]


@router.post("/dev/advance")
def dev_advance(body: AdvanceIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    cloud = get_cloud()
    manager = make_manager(db, cloud)
    ids = list(db.scalars(
        select(ExecutionRun.id).join(Workload, Workload.run_id == ExecutionRun.id)
        .where(Workload.org_id == admin.org_id, ExecutionRun.status.in_(S.ACTIVE))
    ))
    left = body.hours
    for _ in range(ceil(body.hours / 0.25)):
        step = min(0.25, left)
        cloud.advance(step)
        left -= step
        for run_id in ids:
            manager.tick(run_id)
    db.commit()
    return {"simulated_time": cloud.now.isoformat() + "Z", "runs_checked": len(ids)}


@router.post("/dev/interrupt/{workload_id}", response_model=WorkloadDetail)
def dev_interrupt(workload_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    workload = db.get(Workload, workload_id)
    if workload is None or workload.org_id != admin.org_id or not workload.run_id:
        raise ApiError(404, "No running workload with that id.", "not_found")
    cloud = get_cloud()
    manager = make_manager(db, cloud)
    run = db.get(ExecutionRun, workload.run_id)
    attempt = manager._active(run)
    if attempt is None or attempt.purchase != "Spot":
        raise ApiError(409, "Only a running Spot instance can be interrupted.", "not_interruptible")
    cloud.interrupt_in(attempt.instance_id, 0)
    cloud.advance(0)
    manager.tick(workload.run_id)
    db.commit()
    return detail(db, workload)
