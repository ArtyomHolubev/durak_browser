const state = {
  socket: null,
  playerId: null,
  playerName: "",
  gameId: null,
  inviteMode: false,
  inviteGameId: null,
  waitingOnly: false,
  game: null,
};

const PLAYER_KEY = (gameId) => `durak-player-${gameId}`;
const NAME_KEY = (gameId) => `durak-name-${gameId}`;

function getStoredPlayerId(gameId) {
  if (!gameId) return null;
  return localStorage.getItem(PLAYER_KEY(gameId));
}

function storePlayerId(gameId, playerId) {
  if (!gameId || !playerId) return;
  localStorage.setItem(PLAYER_KEY(gameId), playerId);
}

function getStoredPlayerName(gameId) {
  if (!gameId) return "";
  return localStorage.getItem(NAME_KEY(gameId)) || "";
}

function storePlayerName(gameId, name) {
  if (!gameId || !name) return;
  localStorage.setItem(NAME_KEY(gameId), name);
}

export {
  state,
  getStoredPlayerId,
  storePlayerId,
  getStoredPlayerName,
  storePlayerName,
};
