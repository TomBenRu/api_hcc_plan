import calendar

from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn
import os

from pony.orm import db_session, select

# PonyORM und Datenmodelle importieren
from app.database import init_database
from app.models import entities
from app.models.entities import User, Availability

from app.auth.oauth2 import get_current_user
from app.api import availability, users
from app.auth import routes as auth_routes

# Debug-Modus
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")

# Datenbank initialisieren
init_database(debug=DEBUG)

app = FastAPI(title="HCC Einsatzplanung")

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Statische Dateien einrichten
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates einrichten
templates = Jinja2Templates(directory="app/templates")

# Globale Template-Kontexte
from datetime import datetime
@app.middleware("http")
async def add_global_template_context(request: Request, call_next):
    # Fügt globale Variablen zu allen Templates hinzu
    request.state.current_year = datetime.now().year
    response = await call_next(request)
    return response

# API Routen einbinden
app.include_router(auth_routes.router, prefix="/auth", tags=["auth"])
app.include_router(availability.router, prefix="/api/availability", tags=["availability"])
app.include_router(users.router, prefix="/api/users", tags=["users"])

# Web-Routen
@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/dashboard")
async def dashboard(request: Request, current_user=Depends(get_current_user)):
    # Get availability summary data
    with db_session:
        now = datetime.now()
        user = entities.User.get(username=current_user["username"])

        if user:
            availabilities = list(select(a for a in entities.Availability if a.user == user))
            upcoming = [a for a in availabilities if a.start_time > now]

            availability_summary = {
                "total_count": len(availabilities),
                "upcoming_count": len(upcoming)
            }
        else:
            availability_summary = {
                "total_count": 0,
                "upcoming_count": 0
            }

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": current_user,
        "availability_summary": availability_summary
    })


@app.get("/availability")
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


@app.get("/calendar", response_class=HTMLResponse, name="get_calendar")
async def get_calendar(
    request: Request, current_user=Depends(get_current_user), year: str = None, month: str = None
):

    """Liefert eine Kalenderansicht für HTMX"""
    try:
        now = datetime.now()

        # Convert string parameters to integers with proper error handling
        try:
            year_int = int(year) if year is not None else now.year
            month_int = int(month) if month is not None else now.month
        except ValueError:
            return templates.TemplateResponse(
                "partials/error.html",
                {"request": request, "message": "Ungültiges Format für Jahr oder Monat"},
                status_code=400
            )

        # Validierung
        if not (1 <= month_int <= 12):
            return templates.TemplateResponse(
                "partials/error.html",
                {"request": request, "message": "Ungültiger Monat"},
                status_code=400
            )
        if not (1900 <= year_int <= 2100):
            return templates.TemplateResponse(
                "partials/error.html",
                {"request": request, "message": "Ungültiges Jahr"},
                status_code=400
            )

        # Kalenderdaten vorbereiten
        cal = calendar.monthcalendar(year_int, month_int)
        month_name = calendar.month_name[month_int]

        # Verfügbarkeiten laden
        with db_session:
            month_start = datetime(year_int, month_int, 1)
            month_end = datetime(year_int, month_int + 1, 1) if month_int < 12 else datetime(year_int + 1, 1, 1)

            availabilities = select(a for a in entities.Availability
                                    if a.user.username == current_user["username"]
                                    and a.start_time >= month_start
                                    and a.start_time < month_end)[:]

            availability_list = [{
                'id': a.id,
                'name': a.name,
                'start_time': a.start_time,
                'end_time': a.end_time
            } for a in availabilities]

        return templates.TemplateResponse(
            "partials/calendar.html",
            {
                "request": request,
                "calendar": cal,
                "current_year": year_int,
                "current_month": month_int,
                "month_name": month_name,
                "availabilities": availability_list
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "partials/error.html",
            {
                "request": request,
                "message": f"Fehler beim Laden des Kalenders: {str(e)}"
            },
            status_code=500
        )

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)