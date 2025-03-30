#!/usr/bin/env python
"""
Skript zum Initialisieren der Datenbank mit Testdaten
"""
import os
import sys
from datetime import datetime, timedelta

# Füge das Hauptverzeichnis zum Pfad hinzu
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pony.orm import db_session, commit
from app.database import db
from app.models.entities import User, Availability
from app.auth.oauth2 import get_password_hash


# Testbenutzer erstellen
@db_session
def create_test_user(username, email, full_name, password):
    # Prüfen, ob Benutzer bereits existiert
    if User.get(username=username):
        print(f"Benutzer {username} existiert bereits")
        return

    # Benutzer erstellen
    hashed_password = get_password_hash(password)
    user = User(
        username=username,
        email=email,
        full_name=full_name,
        hashed_password=hashed_password
    )
    commit()
    print(f"Testbenutzer {username} wurde erstellt")
    return user


# Verfügbarkeiten für einen Benutzer erstellen
@db_session
def create_test_availabilities(username):
    user = User.get(username=username)
    if not user:
        print(f"Benutzer {username} nicht gefunden")
        return

    # Aktuelles Datum
    now = datetime.now()
    current_month_start = datetime(now.year, now.month, 1)

    # Beispiel-Verfügbarkeiten für den aktuellen Monat
    availabilities = [
        {
            "name": "Urlaub",
            "start_time": current_month_start + timedelta(days=5, hours=9),
            "end_time": current_month_start + timedelta(days=5, hours=17)
        },
        {
            "name": "Arzttermin",
            "start_time": current_month_start + timedelta(days=12, hours=14),
            "end_time": current_month_start + timedelta(days=12, hours=16)
        },
        {
            "name": "Fortbildung",
            "start_time": current_month_start + timedelta(days=18, hours=9),
            "end_time": current_month_start + timedelta(days=19, hours=17)
        }
    ]

    for avail in availabilities:
        Availability(
            name=avail["name"],
            start_time=avail["start_time"],
            end_time=avail["end_time"],
            user=user
        )
    commit()
    print(f"{len(availabilities)} Verfügbarkeiten für {username} erstellt")


if __name__ == "__main__":
    # Testdaten erstellen
    create_test_user("testuser", "test@example.com", "Test Benutzer", "password123")
    create_test_availabilities("testuser")

    print("Datenbank wurde mit Testdaten initialisiert")