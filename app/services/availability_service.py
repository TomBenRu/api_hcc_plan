
from datetime import datetime, date
from typing import List, Optional
from pony.orm import db_session, select, commit, flush

from app.models import entities
from app.models import schemas


class AvailabilityService:
    @staticmethod
    @db_session
    def create_availability(
        username: str,
        availability_data: schemas.AvailabilityCreate
    ) -> schemas.AvailabilityResponse:
        """Erstellt eine neue Verfügbarkeit für einen Benutzer"""
        user = entities.User.get(username=username)
        if not user:
            raise ValueError("Benutzer nicht gefunden")
            
        if availability_data.start_time >= availability_data.end_time:
            raise ValueError("Startzeit muss vor Endzeit liegen")

        # Prüfen auf Überschneidungen
        overlapping = select(a for a in entities.Availability
                            if a.user == user and (
                                (availability_data.start_time >= a.start_time and
                                 availability_data.end_time <= a.end_time) or
                                (availability_data.start_time <= a.start_time and
                                 availability_data.end_time >= a.end_time) or
                                (availability_data.start_time >= a.start_time and
                                 availability_data.start_time < a.end_time) or
                                (availability_data.end_time > a.start_time and
                                 availability_data.end_time <= a.end_time)
                            ))
        
        if overlapping:
            raise ValueError("Zeitraum überschneidet sich mit existierender Verfügbarkeit")

        availability = entities.Availability(
            name=availability_data.name,
            start_time=availability_data.start_time,
            end_time=availability_data.end_time,
            user=user
        )

        # Flush durchführen, damit die ID generiert wird
        flush()

        return schemas.AvailabilityResponse.model_validate(availability)

    @staticmethod
    @db_session
    def get_availabilities(
        username: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[schemas.AvailabilityResponse]:
        """Holt Verfügbarkeiten eines Benutzers mit optionaler Datumsbegrenzung"""
        query = select(a for a in entities.Availability if a.user.username == username)

        if start_date:
            start_datetime = datetime.combine(start_date, datetime.min.time())
            query = query.filter(lambda a: a.start_time >= start_datetime)

        if end_date:
            end_datetime = datetime.combine(end_date, datetime.max.time())
            query = query.filter(lambda a: a.end_time <= end_datetime)

        return [schemas.AvailabilityResponse.model_validate(a) for a in query]


    @staticmethod
    @db_session
    def delete_availability(availability_id: int, username: str) -> bool:
        """Löscht eine Verfügbarkeit, wenn sie dem Benutzer gehört"""
        availability = entities.Availability.get(id=availability_id)
        
        if not availability or availability.user.username != username:
            return False
            
        availability.delete()
        return True

    @staticmethod
    @db_session
    def get_upcoming_availabilities(username: str, limit: int = 3) -> List[schemas.AvailabilityResponse]:
        """Holt die nächsten Verfügbarkeiten eines Benutzers"""
        now = datetime.now()
        query = select(a for a in entities.Availability
                       if a.user.username == username and a.start_time > now)
        return [schemas.AvailabilityResponse.model_validate(a)
                for a in query.order_by(entities.Availability.start_time)][:limit]

    @staticmethod
    @db_session
    def check_availability_conflict(
        username: str,
        start_time: datetime,
        end_time: datetime,
        exclude_id: Optional[int] = None
    ) -> bool:
        """Prüft ob sich ein Zeitraum mit existierenden Verfügbarkeiten überschneidet"""
        user = entities.User.get(username=username)
        if not user:
            return False

        query = select(a for a in entities.Availability
                      if a.user == user and (
                           # Fall 1: Neue Zeit liegt komplett innerhalb einer existierenden Zeit
                           (start_time >= a.start_time and end_time <= a.end_time) or
                           # Fall 2: Neue Zeit umschließt eine existierende Zeit
                           (start_time <= a.start_time and end_time >= a.end_time) or
                           # Fall 3: Neue Startzeit liegt in existierender Zeit
                           (start_time >= a.start_time and start_time < a.end_time) or
                           # Fall 4: Neue Endzeit liegt in existierender Zeit
                           (end_time > a.start_time and end_time <= a.end_time)
                       )
                       )
        
        if exclude_id:
            query = query.filter(lambda a: a.id != exclude_id)

        return bool(query)

    @staticmethod
    @db_session
    def get_availability_by_id(availability_id: int, username: str) -> Optional[schemas.AvailabilityResponse]:
        """Holt eine spezifische Verfügbarkeit eines Benutzers"""
        availability = entities.Availability.get(id=availability_id)

        if not availability or availability.user.username != username:
            return None

        return schemas.AvailabilityResponse.model_validate(availability)
