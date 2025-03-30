from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from datetime import datetime, date
import calendar
from pony.orm import db_session, select, commit

from app.auth.oauth2 import get_current_user
from app.models import entities
from app.models import schemas

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# API-Endpunkte
@router.post("/", response_model=schemas.AvailabilityResponse)
async def create_availability(
        availability: schemas.AvailabilityCreate,
        current_user=Depends(get_current_user)
):
    with db_session:
        user = entities.User.get(username=current_user["username"])
        if not user:
            raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")

        new_availability = entities.Availability(
            name=availability.name,
            start_time=availability.start_time,
            end_time=availability.end_time,
            user=user
        )
        commit()

        # Daten für die Antwort vorbereiten
        return schemas.AvailabilityResponse(
            id=new_availability.id,
            name=new_availability.name,
            start_time=new_availability.start_time,
            end_time=new_availability.end_time,
            user_id=user.username
        )


@router.get("/", response_model=List[schemas.AvailabilityResponse])
async def get_availabilities(
        current_user=Depends(get_current_user),
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
):
    with db_session:
        query = select(a for a in entities.Availability if a.user.username == current_user["username"])

        if start_date:
            # Konvertiere date zu datetime für Vergleich
            start_datetime = datetime.combine(start_date, datetime.min.time())
            query = query.filter(lambda a: a.start_time >= start_datetime)

        if end_date:
            # Konvertiere date zu datetime für Vergleich
            end_datetime = datetime.combine(end_date, datetime.max.time())
            query = query.filter(lambda a: a.end_time <= end_datetime)

        availabilities = list(query)

        # Daten für die Antwort vorbereiten
        return [
            schemas.AvailabilityResponse(
                id=a.id,
                name=a.name,
                start_time=a.start_time,
                end_time=a.end_time,
                user_id=a.user.username
            ) for a in availabilities
        ]


@router.get("/{availability_id}", response_model=schemas.AvailabilityResponse)
async def get_availability(
        availability_id: int,
        current_user=Depends(get_current_user)
):
    with db_session:
        availability = entities.Availability.get(id=availability_id)

        if not availability or availability.user.username != current_user["username"]:
            raise HTTPException(status_code=404, detail="Verfügbarkeit nicht gefunden")

        return schemas.AvailabilityResponse(
            id=availability.id,
            name=availability.name,
            start_time=availability.start_time,
            end_time=availability.end_time,
            user_id=availability.user.username
        )


@router.delete("/{availability_id}")
async def delete_availability(
        availability_id: int,
        current_user=Depends(get_current_user)
):
    with db_session:
        availability = entities.Availability.get(id=availability_id)

        if not availability or availability.user.username != current_user["username"]:
            raise HTTPException(status_code=404, detail="Verfügbarkeit nicht gefunden")

        availability.delete()
        commit()

        return {"message": "Verfügbarkeit gelöscht"}


# HTMX-Endpunkte für die Weboberfläche
@router.get("/summary-htmx")
async def get_availability_summary_htmx(
        request: Request,
        current_user=Depends(get_current_user)
):
    """Liefert eine HTML-Zusammenfassung der Verfügbarkeiten für HTMX"""
    try:
        now = datetime.now()

        with db_session:
            # Get username from the user dict
            username = current_user.get("username")
            if not username:
                return templates.TemplateResponse(
                    "partials/error.html",
                    {"request": request, "message": "Benutzerdaten konnten nicht geladen werden"}
                )

            # Perform the query
            query = select(a for a in entities.Availability if a.user.username == username)
            availabilities = list(query)

            # Convert to dicts to avoid any PonyORM-related serialization issues
            availability_dicts = []
            upcoming_dicts = []
            upcoming_count = 0

            for a in availabilities:
                a_dict = {
                    "id": a.id,
                    "name": a.name,
                    "start_time": a.start_time,
                    "end_time": a.end_time,
                    "user_id": a.user.username
                }
                availability_dicts.append(a_dict)

                if a.start_time > now:
                    upcoming_count += 1
                    upcoming_dicts.append(a_dict)

            # Sort upcoming and limit to 3
            upcoming_dicts = sorted(upcoming_dicts, key=lambda x: x["start_time"])[:3]

            return templates.TemplateResponse(
                "partials/availability_summary.html",
                {
                    "request": request,
                    "total_count": len(availability_dicts),
                    "upcoming_count": upcoming_count,
                    "upcoming": upcoming_dicts
                }
            )

    except Exception as e:
        return templates.TemplateResponse(
            "partials/error.html",
            {"request": request, "message": f"Fehler beim Laden der Verfügbarkeiten: {str(e)}"}
        )


@router.post("/add-htmx")
async def add_availability_htmx(
        request: Request,
        current_user=Depends(get_current_user),
        name: str = None,
        start_date: str = None,
        start_time: str = None,
        end_date: str = None,
        end_time: str = None
):
    """HTMX-Endpunkt zum Hinzufügen einer Verfügbarkeit"""
    if not all([name, start_date, start_time, end_date, end_time]):
        return templates.TemplateResponse(
            "partials/error.html",
            {"request": request, "message": "Alle Felder müssen ausgefüllt sein"}
        )

    try:
        start_datetime = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
        end_datetime = datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %H:%M")
    except ValueError:
        return templates.TemplateResponse(
            "partials/error.html",
            {"request": request, "message": "Ungültiges Datum oder Uhrzeit"}
        )

    if end_datetime <= start_datetime:
        return templates.TemplateResponse(
            "partials/error.html",
            {"request": request, "message": "Die Endzeit muss nach der Startzeit liegen"}
        )

    # Verfügbarkeit erstellen
    with db_session:
        user = entities.User.get(username=current_user["username"])

        new_availability = entities.Availability(
            name=name,
            start_time=start_datetime,
            end_time=end_datetime,
            user=user
        )
        commit()

    # Aktualisierte Kalenderansicht zurückgeben
    return await get_calendar(
        request=request,
        current_user=current_user,
        year=start_datetime.year,
        month=start_datetime.month
    )


@router.delete("/delete-htmx/{availability_id}")
async def delete_availability_htmx(
        request: Request,
        availability_id: int,
        current_user=Depends(get_current_user)
):
    """HTMX-Endpunkt zum Löschen einer Verfügbarkeit"""
    try:
        year, month = None, None

        # Verfügbarkeit finden um Monat und Jahr zu bestimmen
        with db_session:
            availability = entities.Availability.get(id=availability_id)

            if not availability or availability.user.username != current_user["username"]:
                return templates.TemplateResponse(
                    "partials/error.html",
                    {"request": request, "message": "Verfügbarkeit nicht gefunden"}
                )

            month = availability.start_time.month
            year = availability.start_time.year

            # Löschen
            availability.delete()
            commit()

        # Aktualisierte Kalenderansicht zurückgeben
        return await get_calendar(
            request=request,
            current_user=current_user,
            year=year,
            month=month
        )
    except Exception as e:
        return templates.TemplateResponse(
            "partials/error.html",
            {"request": request, "message": f"Fehler beim Löschen: {str(e)}"}
        )