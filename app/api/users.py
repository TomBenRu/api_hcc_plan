from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.templating import Jinja2Templates
from typing import List
from pony.orm import db_session, select

from app.auth.oauth2 import get_current_user, get_password_hash
from app.models import schemas
from app.models import entities

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# API-Endpunkte
@router.get("/me", response_model=schemas.UserResponse)
async def get_current_user_info(current_user=Depends(get_current_user)):
    """Gibt Informationen über den aktuellen Benutzer zurück"""
    return schemas.UserResponse(**current_user)


@router.put("/me", response_model=schemas.UserResponse)
async def update_user_info(
        user_update: schemas.UserUpdate,
        current_user=Depends(get_current_user)
):
    """Aktualisiert Informationen über den aktuellen Benutzer"""
    with db_session:
        user = entities.User.get(username=current_user["username"])
        if not user:
            raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")

        if user_update.email is not None:
            # Prüfen, ob E-Mail bereits vergeben ist
            existing_user = entities.User.get(email=user_update.email)
            if existing_user and existing_user.username != user.username:
                raise HTTPException(status_code=400, detail="Diese E-Mail wird bereits verwendet")
            user.email = user_update.email

        if user_update.full_name is not None:
            user.full_name = user_update.full_name

        if user_update.password is not None and user_update.password.strip():
            user.hashed_password = get_password_hash(user_update.password)

        # Aktualisierte Benutzerinformationen zurückgeben
        return schemas.UserResponse(
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active
        )


# Admin-Endpunkte (erfordern spezielle Berechtigung in einer echten Anwendung)
@router.get("/", response_model=List[schemas.UserResponse])
async def get_all_users(current_user=Depends(get_current_user)):
    """Gibt eine Liste aller Benutzer zurück (nur für Administratoren)"""
    # Hier sollte eine Berechtigungsprüfung erfolgen
    with db_session:
        users = select(u for u in entities.User)
        return [
            schemas.UserResponse(
                username=u.username,
                email=u.email,
                full_name=u.full_name,
                is_active=u.is_active
            ) for u in users
        ]


@router.post("/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_create: schemas.UserCreate, current_user=Depends(get_current_user)):
    """Erstellt einen neuen Benutzer (nur für Administratoren)"""
    # Hier sollte eine Berechtigungsprüfung erfolgen
    with db_session:
        # Prüfen, ob Benutzername oder E-Mail bereits vergeben sind
        if entities.User.get(username=user_create.username):
            raise HTTPException(status_code=400, detail="Dieser Benutzername wird bereits verwendet")

        if entities.User.get(email=user_create.email):
            raise HTTPException(status_code=400, detail="Diese E-Mail wird bereits verwendet")

        # Benutzer erstellen
        hashed_password = get_password_hash(user_create.password)
        user = entities.User(
            username=user_create.username,
            email=user_create.email,
            full_name=user_create.full_name,
            hashed_password=hashed_password
        )

        # Neuen Benutzer zurückgeben
        return schemas.UserResponse(
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active
        )


@router.get("/{username}", response_model=schemas.UserResponse)
async def get_user(username: str, current_user=Depends(get_current_user)):
    """Gibt Informationen über einen bestimmten Benutzer zurück"""
    # Hier sollte eine Berechtigungsprüfung erfolgen oder nur eigene Daten erlauben
    with db_session:
        user = entities.User.get(username=username)
        if not user:
            raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")

        return schemas.UserResponse(
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active
        )


@router.delete("/{username}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(username: str, current_user=Depends(get_current_user)):
    """Löscht einen Benutzer (nur für Administratoren)"""
    # Hier sollte eine Berechtigungsprüfung erfolgen
    with db_session:
        user = entities.User.get(username=username)
        if not user:
            raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")

        # Benutzer nicht löschen, wenn es der aktuelle Benutzer ist
        if user.username == current_user["username"]:
            raise HTTPException(status_code=400, detail="Sie können Ihren eigenen Benutzer nicht löschen")

        user.delete()