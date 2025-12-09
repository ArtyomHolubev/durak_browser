from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import WebSocket

from .cards import MAX_ATTACKS


class PlayerState:
    def __init__(self, player_id: str, name: str, websocket: WebSocket):
        self.id = player_id
        self.name = name
        self.websocket = websocket
        self.hand: List[Dict[str, str]] = []
        self.connected = True
        self.is_out = False

    def card_index(self, card: Dict[str, str]) -> int:
        for idx, owned in enumerate(self.hand):
            if owned["rank"] == card["rank"] and owned["suit"] == card["suit"]:
                return idx
        return -1


class GameState:
    def __init__(self, game_id: str, max_players: int):
        self.id = game_id
        self.max_players = max_players
        self.players: List[PlayerState] = []
        self.host_id: Optional[str] = None
        self.phase: str = "lobby"
        self.deck: List[Dict[str, str]] = []
        self.discard: List[Dict[str, str]] = []
        self.trump_card: Optional[Dict[str, str]] = None
        self.attacker_index: Optional[int] = None
        self.defender_index: Optional[int] = None
        self.table: List[Dict[str, Any]] = []
        self.status_message: str = "Создайте игру и пригласите друзей."
        self.allow_throw_ins: bool = False
        self.attack_passed: set[str] = set()
        self.lock = asyncio.Lock()
        self.history: List[str] = []
        self.loser_id: Optional[str] = None
        self.attack_limit: int = MAX_ATTACKS
        self.rematch_votes: set[str] = set()
        self.winner_id: Optional[str] = None
        self.chat_messages: List[Dict[str, str]] = []

    def find_player(self, player_id: str) -> Optional[PlayerState]:
        for player in self.players:
            if player.id == player_id:
                return player
        return None


def next_active_index(game: GameState, current: int) -> Optional[int]:
    if not game.players:
        return None
    total = len(game.players)
    for step in range(1, total + 1):
        idx = (current + step) % total
        candidate = game.players[idx]
        if not candidate.is_out:
            return idx
    return None


def refill_hands(game: GameState, start_index: Optional[int]) -> None:
    if start_index is None or not game.deck:
        return
    player_count = len(game.players)
    order = []
    idx = start_index
    visited = 0
    while visited < player_count:
        if not game.players[idx].is_out:
            order.append(idx)
        idx = (idx + 1) % player_count
        visited += 1
    for pos in order:
        player = game.players[pos]
        while len(player.hand) < 6 and game.deck:
            player.hand.append(game.deck.pop())


def cleanup_finished_players(game: GameState) -> None:
    if game.deck:
        return
    for player in game.players:
        if not player.is_out and not player.hand:
            player.is_out = True


def ensure_current_roles(game: GameState) -> None:
    if not game.players:
        game.attacker_index = None
        game.defender_index = None
        return
    if game.attacker_index is not None:
        if game.players[game.attacker_index].is_out:
            next_idx = next_active_index(game, game.attacker_index)
            game.attacker_index = next_idx
    if game.attacker_index is None:
        return
    if game.defender_index is not None:
        if game.players[game.defender_index].is_out or game.defender_index == game.attacker_index:
            game.defender_index = next_active_index(game, game.attacker_index)


def recalc_attack_limit(game: GameState) -> None:
    if game.defender_index is None:
        game.attack_limit = MAX_ATTACKS
        return
    defender = game.players[game.defender_index]
    game.attack_limit = min(MAX_ATTACKS, max(1, len(defender.hand)))
