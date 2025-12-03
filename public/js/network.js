import {
  state,
  getStoredPlayerId,
  storePlayerId,
  getStoredPlayerName,
  storePlayerName,
} from "./state.js";
import { showToast, renderApp, toggleEntryVisibility } from "./ui.js";

function normalizeName(name) {
  return name ? name.trim() : "";
}

function connectToGame(gameId, name) {
  if (!gameId) return;
  const normalized = normalizeName(name) || getStoredPlayerName(gameId);
  if (normalized) {
    state.playerName = normalized;
    storePlayerName(gameId, normalized);
  }
  state.gameId = gameId;
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const wsUrl = `${protocol}://${window.location.host}/ws/${gameId}`;
  if (state.socket) {
    state.socket.close();
  }
  const socket = new WebSocket(wsUrl);
  state.socket = socket;
  socket.onopen = () => {
    socket.send(
      JSON.stringify({
        action: "join",
        playerName: state.playerName || getStoredPlayerName(gameId),
        playerId: getStoredPlayerId(gameId),
      })
    );
  };
  socket.onmessage = ({ data }) => {
    const payload = JSON.parse(data);
    if (payload.type === "joined") {
      state.playerId = payload.playerId;
      storePlayerId(payload.gameId, payload.playerId);
      storePlayerName(payload.gameId, state.playerName);
      toggleEntryVisibility(true);
      const nextUrl = new URL(window.location.href);
      nextUrl.searchParams.set("game", payload.gameId);
      window.history.replaceState({}, "", nextUrl.toString());
    } else if (payload.type === "game_state") {
      state.game = payload.game;
      renderApp();
    } else if (payload.type === "error") {
      showToast(payload.message);
    }
  };
  socket.onclose = () => {
    showToast("Соединение закрыто.");
  };
}

function sendAction(action, payload = {}) {
  if (!state.socket || state.socket.readyState !== WebSocket.OPEN) {
    showToast("Нет соединения с сервером.");
    return;
  }
  state.socket.send(JSON.stringify({ action, ...payload }));
}

export { connectToGame, sendAction };
