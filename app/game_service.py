from __future__ import annotations

import secrets
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, WebSocket, WebSocketDisconnect

from .cards import MAX_ATTACKS, RANK_VALUE, beats, build_deck, generate_game_id
from .models import (
    GameState,
    PlayerState,
    cleanup_finished_players,
    ensure_current_roles,
    next_active_index,
    recalc_attack_limit,
    refill_hands,
)
from .schemas import CreateGameRequest
from .storage import games


def lowest_trump_player(players: List[PlayerState], trump_suit: str) -> int:
    best_index = 0
    best_value: Optional[int] = None
    for idx, player in enumerate(players):
        for card in player.hand:
            if card["suit"] == trump_suit:
                value = RANK_VALUE[card["rank"]]
                if best_value is None or value < best_value:
                    best_value = value
                    best_index = idx
    return best_index


def ranks_on_table(game: GameState) -> set[str]:
    ranks: set[str] = set()
    for slot in game.table:
        ranks.add(slot["attack"]["rank"])
        if slot["defense"]:
            ranks.add(slot["defense"]["rank"])
    return ranks


def serialize_game_for_player(game: GameState, player_id: str) -> Dict[str, Any]:
    player = game.find_player(player_id)
    you_cards = player.hand if player else []
    serialized_players = []
    for pl in game.players:
        entry = {
            "id": pl.id,
            "name": pl.name,
            "hand": you_cards if pl.id == player_id else [],
            "handSize": len(pl.hand),
            "isHost": pl.id == game.host_id,
            "isOut": pl.is_out,
            "connected": pl.connected,
        }
        serialized_players.append(entry)
    payload = {
        "id": game.id,
        "phase": game.phase,
        "maxPlayers": game.max_players,
        "players": serialized_players,
        "deckCount": len(game.deck),
        "discardCount": len(game.discard),
        "trumpCard": game.trump_card,
        "table": game.table,
        "status": game.status_message,
        "attackerId": game.players[game.attacker_index].id
        if game.attacker_index is not None
        else None,
        "defenderId": game.players[game.defender_index].id
        if game.defender_index is not None
        else None,
        "allowThrowIns": game.allow_throw_ins,
        "loserId": game.loser_id,
    }
    payload["availableActions"] = build_available_actions(game, player_id)
    return payload


def build_available_actions(game: GameState, player_id: str) -> Dict[str, Any]:
    actions: Dict[str, Any] = {
        "canStart": False,
        "canAttack": False,
        "canThrow": False,
        "canPass": False,
        "canDefend": False,
        "canTake": False,
    }
    player = game.find_player(player_id)
    if not player or player.is_out:
        return actions
    if game.phase == "lobby" and player.id == game.host_id:
        actions["canStart"] = len(game.players) >= 2
        return actions
    if game.phase != "playing" or game.attacker_index is None or game.defender_index is None:
        return actions
    attacker = game.players[game.attacker_index]
    defender = game.players[game.defender_index]
    pending_defense = any(slot["defense"] is None for slot in game.table)
    max_attacks = max(1, game.attack_limit or MAX_ATTACKS)
    if player.id != defender.id and not player.hand:
        return actions
    if player.id == attacker.id and len(game.table) < max_attacks:
        if not game.table:
            actions["canAttack"] = True
        else:
            ranks = ranks_on_table(game)
            if ranks:
                available = any(card["rank"] in ranks for card in player.hand)
                actions["canThrow"] = available
    elif (
        player.id != defender.id
        and game.allow_throw_ins
        and len(game.table) < max_attacks
    ):
        ranks = ranks_on_table(game)
        if ranks:
            can_throw = any(card["rank"] in ranks for card in player.hand)
            actions["canThrow"] = can_throw
    if player.id != defender.id:
        actions["canPass"] = bool(game.table) and not pending_defense
    if player.id == defender.id:
        actions["canDefend"] = pending_defense
        actions["canTake"] = bool(game.table)
    return actions


async def broadcast_state(game: GameState) -> None:
    for player in game.players:
        if not player.websocket:
            continue
        try:
            await player.websocket.send_json(
                {"type": "game_state", "game": serialize_game_for_player(game, player.id)}
            )
        except Exception:
            player.connected = False


async def create_game(req: CreateGameRequest) -> Dict[str, str]:
    game_id = generate_game_id()
    games[game_id] = GameState(game_id, req.maxPlayers)
    return {"gameId": game_id}


def find_game(game_id: str) -> GameState:
    game = games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Игра не найдена")
    return game


async def handle_start_game(game: GameState, player: PlayerState) -> None:
    if player.id != game.host_id:
        raise ValueError("Только создатель может начать игру.")
    if len(game.players) < 2:
        raise ValueError("Нужно минимум два игрока.")
    if game.phase != "lobby":
        raise ValueError("Игра уже началась.")
    game.phase = "playing"
    game.deck = build_deck()
    game.trump_card = game.deck[-1]
    for _ in range(6):
        for pl in game.players:
            pl.hand.append(game.deck.pop())
    lowest_idx = lowest_trump_player(game.players, game.trump_card["suit"])
    game.attacker_index = lowest_idx
    game.defender_index = next_active_index(game, lowest_idx)
    if game.defender_index is None:
        game.defender_index = 0
    recalc_attack_limit(game)
    game.table = []
    game.status_message = f"Атакует {game.players[game.attacker_index].name}"
    game.allow_throw_ins = False
    game.attack_passed.clear()


async def handle_join_lobby(
    websocket: WebSocket, game: GameState, payload: Dict[str, Any]
) -> PlayerState:
    name = payload.get("playerName", "").strip()[:20]
    if not name:
        raise ValueError("Введите имя игрока.")
    requested_id = payload.get("playerId")
    async with game.lock:
        if game.phase != "lobby" and not requested_id:
            raise ValueError("Игра уже началась.")
        player = None
        if requested_id:
            player = game.find_player(requested_id)
        if player:
            player.websocket = websocket
            player.connected = True
            player.name = name or player.name
        else:
            if game.phase != "lobby":
                raise ValueError("Игра уже началась.")
            if len(game.players) >= game.max_players:
                raise ValueError("Комната заполнена.")
            player_id = secrets.token_hex(4)
            player = PlayerState(player_id, name, websocket)
            game.players.append(player)
            if not game.host_id:
                game.host_id = player_id
    await websocket.send_json(
        {"type": "joined", "playerId": player.id, "gameId": game.id}
    )
    await broadcast_state(game)
    return player


def validate_attack_card(
    game: GameState, player: PlayerState, card: Dict[str, str]
) -> None:
    if game.attacker_index is None or game.defender_index is None:
        raise ValueError("Сейчас нельзя атаковать.")
    max_attacks = max(1, game.attack_limit or MAX_ATTACKS)
    if len(game.table) >= max_attacks:
        raise ValueError("Нельзя подкидывать больше карт.")
    idx = player.card_index(card)
    if idx == -1:
        raise ValueError("У вас нет такой карты.")
    if not game.table:
        if player.id != game.players[game.attacker_index].id:
            raise ValueError("Первым ходит назначенный атакующий.")
        return
    ranks = ranks_on_table(game)
    if card["rank"] not in ranks:
        raise ValueError("Можно подкидывать только имеющиеся ранги.")
    if player.id != game.players[game.attacker_index].id and not game.allow_throw_ins:
        raise ValueError("Ждите пока защитник побьёт первую карту.")


def validate_defense_card(
    game: GameState, player: PlayerState, attack_index: int, card: Dict[str, str]
) -> None:
    if game.defender_index is None:
        raise ValueError("Нет защитника.")
    if player.id != game.players[game.defender_index].id:
        raise ValueError("Сейчас ход защиты у другого игрока.")
    if attack_index < 0 or attack_index >= len(game.table):
        raise ValueError("Нет такой карты на столе.")
    slot = game.table[attack_index]
    if slot["defense"]:
        raise ValueError("Эта карта уже побита.")
    idx = player.card_index(card)
    if idx == -1:
        raise ValueError("У вас нет этой карты.")
    trump_suit = game.trump_card["suit"] if game.trump_card else ""
    if not beats(card, slot["attack"], trump_suit):
        raise ValueError("Карта не бьёт атаку.")


def remove_card_from_hand(player: PlayerState, card: Dict[str, str]) -> Dict[str, str]:
    idx = player.card_index(card)
    if idx == -1:
        raise ValueError("Карта не найдена.")
    return player.hand.pop(idx)


def finish_successful_round(game: GameState) -> None:
    for slot in game.table:
        game.discard.append(slot["attack"])
        if slot["defense"]:
            game.discard.append(slot["defense"])
    game.table.clear()
    game.attack_passed.clear()
    game.allow_throw_ins = False
    if game.attacker_index is None or game.defender_index is None:
        return
    game.status_message = (
        f"{game.players[game.defender_index].name} отбился и теперь атакует."
    )
    game.attacker_index = game.defender_index
    game.defender_index = next_active_index(game, game.attacker_index)
    if game.defender_index is None:
        game.defender_index = game.attacker_index
    refill_hands(game, game.attacker_index)
    cleanup_finished_players(game)
    ensure_current_roles(game)
    recalc_attack_limit(game)
    check_for_game_end(game)


def defender_take_cards(game: GameState) -> None:
    if game.defender_index is None or not game.table:
        raise ValueError("Нечего брать.")
    defender = game.players[game.defender_index]
    for slot in game.table:
        defender.hand.append(slot["attack"])
        if slot["defense"]:
            defender.hand.append(slot["defense"])
    game.table.clear()
    game.attack_passed.clear()
    game.allow_throw_ins = False
    prev_attacker = game.attacker_index if game.attacker_index is not None else 0
    attacker_name = game.players[prev_attacker].name if game.players else "Атакующий"
    game.status_message = (
        f"{defender.name} взял карты. Атакует {attacker_name}."
    )
    refill_hands(game, prev_attacker)
    cleanup_finished_players(game)
    game.defender_index = next_active_index(game, prev_attacker)
    ensure_current_roles(game)
    recalc_attack_limit(game)
    check_for_game_end(game)


def handle_attack_pass(game: GameState, player: PlayerState) -> None:
    if not game.table:
        raise ValueError("Нельзя пасовать до первой атаки.")
    if game.defender_index is None:
        raise ValueError("Нет защитника.")
    if player.id == game.players[game.defender_index].id:
        raise ValueError("Защитник не пасует.")
    if any(slot["defense"] is None for slot in game.table):
        raise ValueError("Сначала дождитесь защиты карт.")
    game.attack_passed.add(player.id)
    alive_attackers = [
        pl.id
        for idx, pl in enumerate(game.players)
        if idx != game.defender_index and not pl.is_out and pl.hand
    ]
    pending = any(slot["defense"] is None for slot in game.table)
    if not pending and all(attacker in game.attack_passed for attacker in alive_attackers):
        finish_successful_round(game)


def check_for_game_end(game: GameState) -> None:
    remaining = [pl for pl in game.players if not pl.is_out]
    if len(remaining) <= 1 and game.phase == "playing":
        game.phase = "ended"
        if remaining:
            loser = remaining[0]
            game.loser_id = loser.id
            game.status_message = f"{loser.name} остался в дураках."
        else:
            game.status_message = "Игра завершена."


async def process_action(
    action: str, data: Dict[str, Any], game: GameState, player: PlayerState
) -> None:
    if action == "start_game":
        async with game.lock:
            await handle_start_game(game, player)
        await broadcast_state(game)
        return
    if game.phase != "playing":
        raise ValueError("Игра ещё не началась.")
    async with game.lock:
        if action == "play_attack":
            card = data.get("card")
            if not isinstance(card, dict):
                raise ValueError("Укажите карту.")
            validate_attack_card(game, player, card)
            removed = remove_card_from_hand(player, card)
            is_first_card = not game.table
            game.table.append({"attack": removed, "defense": None, "attackerId": player.id})
            game.attack_passed.clear()
            if is_first_card:
                game.allow_throw_ins = False
            if game.allow_throw_ins is False and len(game.table) == 1:
                game.status_message = f"{game.players[game.defender_index].name} должен отбиться."
        elif action == "play_defense":
            card = data.get("card")
            attack_index = data.get("attackIndex")
            if not isinstance(card, dict) or attack_index is None:
                raise ValueError("Нужны карта и номер атаки.")
            validate_defense_card(game, player, int(attack_index), card)
            removed = remove_card_from_hand(player, card)
            game.table[int(attack_index)]["defense"] = removed
            if not game.allow_throw_ins:
                game.allow_throw_ins = True
            if all(slot["defense"] for slot in game.table):
                game.status_message = "Атакующие решают подкидывать или пасовать."
        elif action == "pass_attack":
            handle_attack_pass(game, player)
        elif action == "take_cards":
            defender_take_cards(game)
        else:
            raise ValueError("Неизвестное действие.")
        await broadcast_state(game)


async def websocket_handler(websocket: WebSocket, game_id: str) -> None:
    game = games.get(game_id)
    if not game:
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "Игра не найдена."})
        await websocket.close()
        return
    await websocket.accept()
    player: Optional[PlayerState] = None
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            if action == "join":
                player = await handle_join_lobby(websocket, game, data)
            elif not player:
                await websocket.send_json({"type": "error", "message": "Сначала присоединитесь."})
            else:
                try:
                    await process_action(action, data, game, player)
                except ValueError as exc:
                    await websocket.send_json({"type": "error", "message": str(exc)})
    except WebSocketDisconnect:
        if player:
            player.connected = False
            player.websocket = None
            await broadcast_state(game)
