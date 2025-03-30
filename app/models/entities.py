from pony.orm import Required, Optional, Set, PrimaryKey
from datetime import datetime
from app.database import db


class User(db.Entity):
    """Benutzer-Entität (Freiberuflicher Mitarbeiter)"""

    username = Required(str, unique=True)
    email = Required(str, unique=True)
    full_name = Required(str)
    hashed_password = Required(str)
    is_active = Required(bool, default=True)
    created_at = Required(datetime, default=lambda: datetime.now())

    # Beziehungen
    availabilities = Set('Availability')
    skills = Set('Skill')
    assignments = Set('Assignment')

    def to_dict(self):
        return {
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Availability(db.Entity):
    """Verfügbarkeits-Entität (Freie Tageszeiten / Sperrtermine)"""

    name = Required(str)  # Bezeichnung für die Verfügbarkeit/Sperrzeit
    start_time = Required(datetime)
    end_time = Required(datetime)
    created_at = Required(datetime, default=lambda: datetime.now())

    # Beziehungen
    user = Required(User)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "user_id": self.user.username,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Skill(db.Entity):
    """Fähigkeiten-Entität"""

    name = Required(str, unique=True)
    description = Optional(str)

    # Beziehungen
    users = Set(User)
    required_for = Set('Project')

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description
        }


class Location(db.Entity):
    """Einsatzort-Entität"""

    name = Required(str)
    address = Required(str)
    city = Required(str)
    postal_code = Required(str)
    country = Required(str, default="Deutschland")

    # Beziehungen
    projects = Set('Project')

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "address": self.address,
            "city": self.city,
            "postal_code": self.postal_code,
            "country": self.country
        }


class Project(db.Entity):
    """Projekt-Entität"""

    name = Required(str)
    description = Optional(str)
    start_date = Required(datetime)
    end_date = Required(datetime)

    # Beziehungen
    location = Required(Location)
    required_skills = Set(Skill)
    assignments = Set('Assignment')

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "location_id": self.location.id
        }


class Assignment(db.Entity):
    """Einsatzplan-Entität (Zuordnung von Mitarbeitern zu Projekten)"""

    start_date = Required(datetime)
    end_date = Required(datetime)
    status = Required(str, default="geplant")  # geplant, bestätigt, abgeschlossen, storniert
    notes = Optional(str)
    created_at = Required(datetime, default=lambda: datetime.now())

    # Beziehungen
    user = Required(User)
    project = Required(Project)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user.username,
            "project_id": self.project.id,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }