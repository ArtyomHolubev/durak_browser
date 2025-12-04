const elements = {
  entrySection: document.getElementById("entry-section"),
  waitingScreen: document.getElementById("waiting-screen"),
  waitingExitBtn: document.getElementById("waiting-exit"),
  createForm: document.getElementById("create-form"),
  joinForm: document.getElementById("join-form"),
  joinCodeInput: document.getElementById("join-code"),
  joinNameInput: document.getElementById("join-name"),
  createNameInput: document.getElementById("create-name"),
  createCountInput: document.getElementById("create-count"),
  lobbySection: document.getElementById("lobby"),
  gameSection: document.getElementById("game"),
  playersList: document.getElementById("players"),
  roomCodeLabel: document.getElementById("room-code"),
  lobbyStatus: document.getElementById("lobby-status"),
  inviteLinkInput: document.getElementById("invite-link"),
  copyLinkButton: document.getElementById("copy-link"),
  inviteInfo: document.querySelector(".invite-info"),
  trumpLabel: document.getElementById("trump-label"),
  startButton: document.getElementById("start-game"),
  tableEl: document.getElementById("table"),
  handContainer: document.getElementById("hand-cards"),
  passButton: document.getElementById("pass-btn"),
  takeButton: document.getElementById("take-btn"),
  toast: document.getElementById("toast"),
  playersInline: document.getElementById("players-inline"),
  deckInfo: document.getElementById("deck-info"),
  deckStack: document.getElementById("deck-stack"),
  trumpCardVisual: document.getElementById("trump-card-visual"),
  deckCount: document.getElementById("deck-count"),
  gameStatus: document.getElementById("game-status"),
  defenseModal: document.getElementById("defense-modal"),
  defenseOptions: document.getElementById("defense-options"),
  modalCardName: document.getElementById("modal-card-name"),
  closeModalBtn: document.getElementById("close-modal"),
  winnerModal: document.getElementById("winner-modal"),
  winnerMessage: document.getElementById("winner-message"),
  rematchBtn: document.getElementById("rematch-btn"),
  exitRematchBtn: document.getElementById("exit-rematch-btn"),
  animationLayer: document.getElementById("animation-layer"),
};

const SUIT_SYMBOL = {
  C: "♣",
  D: "♦",
  H: "♥",
  S: "♠",
};

function formatCard(card) {
  if (!card) return "";
  return `${card.rank}${SUIT_SYMBOL[card.suit] ?? card.suit}`;
}

function getCardAsset(card) {
  return `cards/${card.rank}${card.suit}.svg`;
}

export default elements;
export { SUIT_SYMBOL, formatCard, getCardAsset };
