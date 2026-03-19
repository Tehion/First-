import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, engine
from app.routers import activities, emails, leads, pipeline, reminders
from app.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Mini CRM",
    description="A mini CRM for lead management, pipeline tracking, reminders, and email campaigns.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(leads.router)
app.include_router(pipeline.router)
app.include_router(activities.router)
app.include_router(reminders.router)
app.include_router(emails.router)


@app.get("/")
def root():
    return {"message": "Mini CRM API", "docs": "/docs"}
