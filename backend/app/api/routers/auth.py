from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models.core import Organization, User
from ..audit import audit
from ..deps import get_db
from ..errors import ApiError
from ..schemas_v2 import LoginIn, RegisterIn, TokenOut, UserOut
from ..security import current_user, hash_password, make_token, verify_password

router = APIRouter(tags=["auth"])


def _out(user: User) -> UserOut:
    return UserOut(id=user.id, email=user.email, role=user.role, org_id=user.org_id)


def _token(user: User) -> TokenOut:
    return TokenOut(access_token=make_token(user), user=_out(user))


@router.post("/auth/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        raise ApiError(409, "An account with this email already exists.", "email_taken")
    org = Organization(name=body.org_name or f"{email}'s team")
    db.add(org)
    db.flush()
    user = User(email=email, password_hash=hash_password(body.password), role="Admin", org_id=org.id)
    db.add(user)
    db.flush()
    audit(db, user, "user.register", user.email)
    db.commit()
    return _token(user)


@router.post("/auth/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise ApiError(401, "Wrong email or password.", "bad_credentials")
    audit(db, user, "user.login", user.email)
    db.commit()
    return _token(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return _out(user)
