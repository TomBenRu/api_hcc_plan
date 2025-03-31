from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from datetime import datetime, date
import calendar
from app.auth.oauth2 import get_current_user
from app.services.availability_service import AvailabilityService
from app.models import schemas

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# API-Endpunkte
@router.post("/", response_model=schemas.AvailabilityResponse)
async def create_availability(
    availability: schemas.AvailabilityCreate,
    current_user=Depends(get_current_user)
):
    """Erstellt eine neue Verfügbarkeit"""
    try:
        return AvailabilityService.create_availability(
            username=current_user["username"],
            availability_data=availability
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[schemas.AvailabilityResponse])
async def get_availabilities(
    current_user=Depends(get_current_user),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """Holt alle Verfügbarkeiten eines Benutzers"""
    return AvailabilityService.get_availabilities(
        username=current_user["username"],
        start_date=start_date,
        end_date=end_date
    )


@router.get("/by_id", response_model=schemas.AvailabilityResponse)
async def get_availability(
    availability_id: int,
    current_user=Depends(get_current_user)
):
    """Holt eine spezifische Verfügbarkeit"""
    availability = AvailabilityService.get_availability_by_id(
        availability_id=availability_id,
        username=current_user["username"]
    )
    if not availability:
        raise HTTPException(status_code=404, detail="Verfügbarkeit nicht gefunden")
    return availability


@router.delete("/by_id")
async def delete_availability(
    availability_id: int,
    current_user=Depends(get_current_user)
):
    """Löscht eine Verfügbarkeit"""
    if not AvailabilityService.delete_availability(
        availability_id=availability_id,
        username=current_user["username"]
    ):
        raise HTTPException(status_code=404, detail="Verfügbarkeit nicht gefunden")
    return {"message": "Verfügbarkeit gelöscht"}


@router.get("/page")
async def availability_page(request: Request, current_user=Depends(get_current_user)):
    # Get current month and year for the calendar
    now = datetime.now()
    current_month = now.month
    current_year = now.year

    # Import calendar to get month name
    import calendar
    month_name = calendar.month_name[current_month]

    return templates.TemplateResponse("availability.html", {
        "request": request,
        "user": current_user,
        "current_month": current_month,
        "current_year": current_year,
        "month_name": month_name
    })


@router.get("/calendar", response_class=HTMLResponse, name="get_calendar")
async def get_calendar(
    request: Request,
    current_user=Depends(get_current_user),
    year: Optional[int] = None,
    month: Optional[int] = None
):
    """Liefert eine Kalenderansicht für HTMX"""
    try:
        now = datetime.now()
        year = year or now.year
        month = month or now.month

        if not (1 <= month <= 12 and 1900 <= year <= 2100):
            return templates.TemplateResponse(
                "partials/error.html",
                {"request": request, "message": "Ungültiges Datum"},
                status_code=400
            )

        # Verfügbarkeiten für den Monat laden
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)

        availabilities = AvailabilityService.get_availabilities(
            username=current_user["username"],
            start_date=start_date,
            end_date=end_date
        )

        return templates.TemplateResponse(
            "partials/calendar.html",
            {
                "request": request,
                "calendar": calendar.monthcalendar(year, month),
                "current_year": year,
                "current_month": month,
                "month_name": calendar.month_name[month],
                "availabilities": [a.model_dump() for a in availabilities]
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "partials/error.html",
            {"request": request, "message": f"Fehler beim Laden des Kalenders: {str(e)}"},
            status_code=500
        )


@router.post("/add-availability-htmx")
async def add_availability_htmx(
    request: Request,
    current_user=Depends(get_current_user)
):
    """HTMX-Endpunkt zum Hinzufügen einer Verfügbarkeit"""
    try:
        form_data = await request.form()

        # Validiere Form-Daten
        try:
            start_datetime = datetime.strptime(
                f"{form_data['start_date']} {form_data['start_time']}",
                "%Y-%m-%d %H:%M"
            )
            end_datetime = datetime.strptime(
                f"{form_data['end_date']} {form_data['end_time']}",
                "%Y-%m-%d %H:%M"
            )
        except (KeyError, ValueError):
            return templates.TemplateResponse(
                "partials/error.html",
                {"request": request, "message": "Ungültiges Datum oder Uhrzeit"}
            )

        # Erstelle Availability
        availability_data = schemas.AvailabilityCreate(
            name=form_data["name"],
            start_time=start_datetime,
            end_time=end_datetime
        )

        availability = AvailabilityService.create_availability(
            username=current_user["username"],
            availability_data=availability_data
        )
        print(f"Debug - Created availability: {availability}")  # Debug-Ausgabe

        # Aktualisierte Kalenderansicht zurückgeben
        return await get_calendar(
            request=request,
            current_user=current_user,
            year=start_datetime.year,
            month=start_datetime.month
        )
    except ValueError as e:
        return templates.TemplateResponse(
            "partials/error.html",
            {"request": request, "message": str(e)}
        )
    except Exception as e:
        return templates.TemplateResponse(
            "partials/error.html",
            {"request": request, "message": f"Fehler beim Erstellen: {str(e)}"},
            status_code=500
        )


@router.delete("/delete-availability-htmx/{availability_id}")
async def delete_availability_htmx(
    request: Request,
    availability_id: int,
    current_user=Depends(get_current_user)
):
    """HTMX-Endpunkt zum Löschen einer Verfügbarkeit"""
    try:
        # Verfügbarkeit finden um Monat und Jahr zu bestimmen
        availability = AvailabilityService.get_availability_by_id(
            availability_id=availability_id,
            username=current_user["username"]
        )
        if not availability:
            return templates.TemplateResponse(
                "partials/error.html",
                {"request": request, "message": "Verfügbarkeit nicht gefunden"}
            )

        # Speichere Datum für Kalenderaktualisierung
        year = availability.start_time.year
        month = availability.start_time.month

        # Löschen
        AvailabilityService.delete_availability(
            availability_id=availability_id,
            username=current_user["username"]
        )

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


# HTMX-Endpunkte für die Weboberfläche
@router.get("/summary-htmx")
async def get_availability_summary_htmx(
    request: Request,
    current_user=Depends(get_current_user)
):
    """Liefert eine HTML-Zusammenfassung der Verfügbarkeiten für HTMX"""
    try:
        username = current_user["username"]
        availabilities = AvailabilityService.get_availabilities(username=username)
        upcoming = AvailabilityService.get_upcoming_availabilities(username=username)

        return templates.TemplateResponse(
            "partials/availability_summary.html",
            {
                "request": request,
                "total_count": len(availabilities),
                "upcoming_count": len([a for a in availabilities if a.start_time > datetime.now()]),
                "upcoming": [a.model_dump() for a in upcoming]
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "partials/error.html",
            {"request": request, "message": f"Fehler beim Laden der Verfügbarkeiten: {str(e)}"},
            status_code=500
        )
