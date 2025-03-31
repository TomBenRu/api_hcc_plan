from datetime import datetime

from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from pony.orm import db_session, select

from app.auth.oauth2 import get_current_user
from app.models import entities

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
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