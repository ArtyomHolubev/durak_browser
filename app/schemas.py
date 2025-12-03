from pydantic import BaseModel, Field


class CreateGameRequest(BaseModel):
    maxPlayers: int = Field(ge=2, le=6)
