from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import auth, models, schemas
from app.config import Settings, get_settings
from app.db import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=schemas.TokenOut)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> schemas.TokenOut:
    user = db.query(models.User).filter_by(username=form_data.username).first()
    # Deliberately identical error for "no such user" and "wrong password" — a
    # different message for each would let an attacker enumerate valid usernames.
    if user is None or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    token = auth.create_access_token(user, settings)
    return schemas.TokenOut(access_token=token, token_type="bearer", username=user.username, role=user.role)


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(auth.get_current_user)) -> models.User:
    return current_user
