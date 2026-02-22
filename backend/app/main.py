"""
FIRE — Ticket Distribution Service
Main FastAPI application
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.api import upload, tickets, managers, distribution

# ── Logging Configuration ─────────────────────────────
# Show NLP/distribution processing logs in terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
# Set app-level loggers to DEBUG for detailed output
logging.getLogger("app").setLevel(logging.DEBUG)
logging.getLogger("nlp_module").setLevel(logging.DEBUG)


# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FIRE — Ticket Distribution Service",
    description="Автоматическая обработка и распределение обращений клиентов",
    version="1.0.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router)
app.include_router(tickets.router)
app.include_router(managers.router)
app.include_router(distribution.router)


@app.get("/")
def root():
    return {"service": "FIRE", "status": "running"}


@app.get("/api/health")
def health():
    return {"status": "ok"}
