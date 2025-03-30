from pony.orm import Database
import os

# Datenbank-Konfiguration
db = Database()

def init_database(debug=True):
    """Initialisiert die Datenbankverbindung"""
    if not db.provider:  # Nur binden wenn noch nicht gebunden
        db_path = os.getenv("DB_PATH", "hcc_plan_db.sqlite")
        
        if debug:
            # SQLite für die Entwicklung
            db.bind(provider='sqlite', filename=db_path, create_db=True)
        else:
            # Produktionseinstellungen
            db_params = {
                'provider': 'postgres',
                'user': os.getenv("DB_USER", "postgres"),
                'password': os.getenv("DB_PASSWORD", ""),
                'host': os.getenv("DB_HOST", "localhost"),
                'database': os.getenv("DB_NAME", "hcc_plan_db")
            }
            db.bind(**db_params)

        # Datenbankschema generieren
        db.generate_mapping(create_tables=True)