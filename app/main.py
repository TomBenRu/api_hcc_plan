from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

# PonyORM und Datenmodelle importieren
from app.database import init_database
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
async def dashboard(request: Request, current_user = Depends(get_current_user)):
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": current_user
    })

@app.get("/availability")
async def availability_page(request: Request, current_user = Depends(get_current_user)):
    return templates.TemplateResponse("availability.html", {
        "request": request,
        "user": current_user
    })

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)