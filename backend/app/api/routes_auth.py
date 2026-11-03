import hmac
import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy.orm import Session

from app.auth.db import get_db
from app.auth.dependencies import get_current_user
from app.auth.mailer import send_otp_email
from app.auth.models import EmailOTP, User
from app.auth.security import (
    DUMMY_HASH,
    create_access_token,
    generate_otp,
    hash_otp,
    hash_password,
    verify_password,
)
from app.config import settings
from app.rate_limit import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

OTP_MAX_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 60


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name is required")
        return v


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(pattern=r"^\d{6}$")


class EmailRequest(BaseModel):
    email: EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str


class LoginResponse(BaseModel):
    user: UserOut


def _aware(dt: datetime) -> datetime:
    # SQLite returns naive datetimes even for timezone=True columns.
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _set_session_cookie(response: Response, user: User) -> None:
    response.set_cookie(
        "access_token",
        create_access_token(user.id, user.email),
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )


def _issue_otp(db: Session, email: str, name: str, password_hash: str) -> None:
    now = datetime.now(UTC)
    row = db.query(EmailOTP).filter(EmailOTP.email == email).first()
    if row:
        wait = (
            RESEND_COOLDOWN_SECONDS - (now - _aware(row.last_sent_at)).total_seconds()
        )
        if wait > 0:
            raise HTTPException(
                429, f"Please wait {int(wait) + 1}s before requesting another code."
            )
    else:
        row = EmailOTP(email=email)
        db.add(row)

    otp = generate_otp()
    row.name = name
    row.password_hash = password_hash
    row.code_hash = hash_otp(email, otp)
    row.attempts = 0
    row.expires_at = now + timedelta(minutes=settings.otp_expire_minutes)
    row.last_sent_at = now
    db.commit()

    try:
        send_otp_email(email, name, otp)
    except Exception as exc:
        logger.exception("Could not send OTP email")
        db.delete(row)  # don't make the user wait out the cooldown for a failed send
        db.commit()
        raise HTTPException(
            502, "Could not send the verification email. Please try again."
        ) from exc


@router.post("/register")
@limiter.limit("5/minute")
def register(request: Request, req: RegisterRequest, db: Session = Depends(get_db)):
    email = str(req.email).lower()
    existing = db.query(User).filter(User.email == email).first()
    if existing and existing.password_hash:
        raise HTTPException(
            409, "An account with this email already exists. Please sign in."
        )
    _issue_otp(db, email, req.name, hash_password(req.password))
    return {"status": "otp_sent", "email": email}


@router.post("/resend-otp")
@limiter.limit("5/minute")
def resend_otp(request: Request, req: EmailRequest, db: Session = Depends(get_db)):
    email = str(req.email).lower()
    row = db.query(EmailOTP).filter(EmailOTP.email == email).first()
    if not row:
        raise HTTPException(
            404, "No pending signup for this email. Please sign up again."
        )
    _issue_otp(db, email, row.name, row.password_hash)
    return {"status": "otp_sent", "email": email}


@router.post("/verify-otp", response_model=LoginResponse)
@limiter.limit("10/minute")
def verify_otp(
    request: Request,
    req: VerifyOtpRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    email = str(req.email).lower()
    row = db.query(EmailOTP).filter(EmailOTP.email == email).first()
    if not row:
        raise HTTPException(
            400, "No pending signup for this email. Please sign up again."
        )
    if datetime.now(UTC) > _aware(row.expires_at):
        raise HTTPException(400, "This code has expired. Please request a new one.")
    if row.attempts >= OTP_MAX_ATTEMPTS:
        raise HTTPException(
            429, "Too many incorrect attempts. Please request a new code."
        )
    if not hmac.compare_digest(row.code_hash, hash_otp(email, req.otp)):
        row.attempts += 1
        db.commit()
        raise HTTPException(400, "Incorrect code. Please try again.")

    user = db.query(User).filter(User.email == email).first()
    if user and user.password_hash:
        db.delete(row)
        db.commit()
        raise HTTPException(
            409, "An account with this email already exists. Please sign in."
        )
    if (
        user
    ):  # old Google-only account: the verified email proves ownership, so claim it
        user.name = row.name
        user.password_hash = row.password_hash
    else:
        user = User(email=email, name=row.name, password_hash=row.password_hash)
        db.add(user)
    db.delete(row)
    db.commit()
    db.refresh(user)

    _set_session_cookie(response, user)
    return LoginResponse(user=UserOut.model_validate(user))


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
def login(
    request: Request,
    req: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    email = str(req.email).lower()
    user = db.query(User).filter(User.email == email).first()
    stored = user.password_hash if user and user.password_hash else DUMMY_HASH
    password_ok = verify_password(req.password, stored)
    if not (user and user.password_hash and password_ok):
        raise HTTPException(401, "Incorrect email or password.")

    _set_session_cookie(response, user)
    return LoginResponse(user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"status": "logged out"}
