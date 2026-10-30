from ..models.core import AuditLog, User


def audit(db, user: User, action: str, target="", detail: dict | None = None) -> None:
    db.add(AuditLog(org_id=user.org_id, user_id=user.id, action=action, target=str(target), detail=detail))
