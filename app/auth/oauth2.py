from fastapi import Depends, HTTPException, status, Request, Cookie
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from pony.orm import db_session
import bcrypt
import os

from app.models.entities import User

# OAuth2 Konfiguration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2 Schema ohne tokenUrl für Cookie-basierte Auth
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=False)


# Token erstellen
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Passwort hashen
def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode(), salt)
    return hashed_password.decode()


# Passwort verifizieren
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


# Benutzer über Token validieren
async def get_current_user(
        request: Request,
        token: Optional[str] = Depends(oauth2_scheme),
        access_token: Optional[str] = Cookie(None)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Ungültige Anmeldeinformationen",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Token aus Cookie extrahieren falls keins über den Header kam
    if access_token and not token:
        if access_token.startswith("Bearer "):
            token = access_token[7:]
        else:
            token = access_token

    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Benutzer aus Datenbank abrufen
    with db_session:
        user = User.get(username=username)
        if user is None:
            raise credentials_exception
        return user.to_dict()