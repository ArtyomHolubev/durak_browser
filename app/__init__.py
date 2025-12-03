from __future__ import annotations

import mimetypes

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routers import register_routes

# Гарантируем корректный MIME-тип для JS/CSS (особенно важно для ES-модулей)
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")


def create_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_headers=["*"],
        allow_methods=["*"],
    )
    register_routes(app)
    app.mount("/", StaticFiles(directory="public", html=True), name="static")
    return app
