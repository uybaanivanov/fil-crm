import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db import apply_migrations
from backend.routes import users as users_routes
from backend.routes import apartments as apartments_routes
from backend.routes import clients as clients_routes
from backend.routes import bookings as bookings_routes
from backend.routes import dashboard as dashboard_routes
from backend.routes import reports as reports_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    apply_migrations()
    yield


app = FastAPI(title="fil-crm", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.environ.get("DEBUG"):
    from backend.routes import dev_auth as dev_auth_routes

    app.include_router(dev_auth_routes.router)

app.include_router(users_routes.router)
app.include_router(apartments_routes.router)
app.include_router(clients_routes.router)
app.include_router(bookings_routes.router)
app.include_router(dashboard_routes.router)
app.include_router(reports_routes.router)


@app.get("/health")
def health():
    return {"ok": True}
