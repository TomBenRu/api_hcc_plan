#!/usr/bin/env python
"""
Hauptskript zum Starten der Anwendung
"""
import os
import uvicorn

if __name__ == "__main__":
    # Debug-Modus
    debug = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")

    # Port
    port = int(os.getenv("PORT", 8000))

    # Anwendung starten
    uvicorn.run("app.main:app", reload=debug)