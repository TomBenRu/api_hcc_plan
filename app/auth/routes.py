from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from datetime import timedelta
from pony.orm import db_session, commit
import os

from app.auth.oauth2 import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, verify_password
from app.models import entities, schemas

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# OAuth2 Token-Route
@router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    with db_session:
        user = entities.User.get(username=form_data.username)
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Ungültiger Benutzername oder Passwort",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}


# HTMX-freundliche Login-Route
@router.post("/login-htmx")
async def login_htmx(request: Request, response: Response):
    form_data = await request.form()
    username = form_data.get("username")
    password = form_data.get("password")
    print(f'{username=}, {password=}, {request.form=}, {response=}', flush=True)
    if not username or not password:
        return templates.TemplateResponse(
            "partials/login_error.html",
            {"request": request, "message": "Bitte füllen Sie alle Felder aus"}
        )

    with db_session:
        user = entities.User.get(username=username)
        if not user or not verify_password(password, user.hashed_password):
            return templates.TemplateResponse(
                "partials/login_error.html",
                {"request": request, "message": "Ungültiger Benutzername oder Passwort"}
            )

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )

        # Cookie setzen
        response.set_cookie(
            key="access_token",
            value=f"Bearer {access_token}",
            httponly=True,
            max_age=1800,
            samesite="lax"
        )

        # JavaScript-Weiterleitung zurückgeben
        return templates.TemplateResponse(
            "partials/login_success.html",
            {"request": request, "redirect_url": "/dashboard", "message": "Anmeldung erfolgreich"}
        )


@router.get("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"redirect_url": "/login"}


# Hilfsfunktion zum Erstellen eines Test-Benutzers (nur für Entwicklung)
@router.post("/create-test-user")
async def create_test_user(user: schemas.UserCreate):
    """Erstellt einen Testbenutzer für Entwicklungszwecke"""
    if os.getenv("ENVIRONMENT", "development") != "development":
        raise HTTPException(status_code=403, detail="Diese Funktion ist nur in der Entwicklungsumgebung verfügbar")

    from app.auth.oauth2 import get_password_hash

    with db_session:
        # Prüfen, ob Benutzer bereits existiert
        if entities.User.get(username=user.username) or entities.User.get(email=user.email):
            raise HTTPException(status_code=400, detail="Benutzername oder E-Mail existiert bereits")

        # Benutzer erstellen
        hashed_password = get_password_hash(user.password)
        user = entities.User(
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            hashed_password=hashed_password
        )
        commit()

        return {"message": f"Testbenutzer {user.username} wurde erstellt"}