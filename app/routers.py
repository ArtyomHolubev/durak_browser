from fastapi import FastAPI, WebSocket

from .game_service import create_game, websocket_handler
from .schemas import CreateGameRequest


def register_routes(app: FastAPI) -> None:
    @app.post("/api/games")
    async def create_game_endpoint(req: CreateGameRequest):
        return await create_game(req)

    @app.websocket("/ws/{game_id}")
    async def websocket_endpoint(websocket: WebSocket, game_id: str):
        await websocket_handler(websocket, game_id)
