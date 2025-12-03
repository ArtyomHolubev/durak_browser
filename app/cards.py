from __future__ import annotations

import random
import secrets
import string
from typing import Dict, List

SUITS = ["C", "D", "H", "S"]
RANKS = ["6", "7", "8", "9", "10", "J", "Q", "K", "A"]
RANK_VALUE = {rank: idx for idx, rank in enumerate(RANKS)}
MAX_ATTACKS = 6


def generate_game_id() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))


def build_deck() -> List[Dict[str, str]]:
    deck = [{"suit": suit, "rank": rank} for suit in SUITS for rank in RANKS]
    random.shuffle(deck)
    return deck


def beats(defense: Dict[str, str], attack: Dict[str, str], trump_suit: str) -> bool:
    if defense["suit"] == attack["suit"]:
        return RANK_VALUE[defense["rank"]] > RANK_VALUE[attack["rank"]]
    if defense["suit"] == trump_suit and attack["suit"] != trump_suit:
        return True
    return False
