import { state } from "./state.js";
import elements, { getCardAsset, formatCard, PLACEHOLDER_CARD } from "./dom.js";

const RANK_ORDER = ["6", "7", "8", "9", "10", "J", "Q", "K", "A"];
const SUIT_ORDER = ["C", "D", "H", "S"];
const RANK_INDEX = RANK_ORDER.reduce((acc, rank, idx) => {
  acc[rank] = idx;
  return acc;
}, {});
const SUIT_INDEX = SUIT_ORDER.reduce((acc, suit, idx) => {
  acc[suit] = idx;
  return acc;
}, {});

const CARD_RENDER_OPTIONS = { rotationStep: 4 };
let toastTimer = null;
let callbacks = {
  onPlayAttack: null,
  onPlayDefense: null,
};

function cardWeight(card, trumpSuit) {
  const rankScore = RANK_INDEX[card.rank] ?? 0;
  const suitScore = SUIT_INDEX[card.suit] ?? 0;
  const base = rankScore + suitScore / 10;
  if (trumpSuit && card.suit === trumpSuit) {
    return 100 + base;
  }
  return base;
}

function sortHandCards(hand, trumpSuit) {
  return [...hand].sort((a, b) => {
    const diff = cardWeight(a, trumpSuit) - cardWeight(b, trumpSuit);
    if (diff !== 0) return diff;
    return (a.rank + a.suit).localeCompare(b.rank + b.suit);
  });
}

function registerCallbacks(newCallbacks) {
  callbacks = { ...callbacks, ...newCallbacks };
}

function showToast(message) {
  if (!elements.toast) return;
  elements.toast.textContent = message;
  elements.toast.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    elements.toast.classList.add("hidden");
  }, 2500);
}

function toggleEntryVisibility(joined) {
  if (!elements.entrySection) return;
  const showWaiting = state.inviteMode || state.waitingOnly;
  if (joined) {
    elements.entrySection.classList.add("hidden");
    document.body.classList.add("game-mode");
    if (showWaiting) {
      elements.waitingScreen?.classList.remove("hidden");
      elements.inviteInfo?.classList.add("compact");
    } else {
      elements.waitingScreen?.classList.add("hidden");
      elements.inviteInfo?.classList.remove("compact");
    }
  } else {
    document.body.classList.remove("game-mode");
    if (showWaiting) {
      elements.entrySection.classList.add("hidden");
      elements.waitingScreen?.classList.remove("hidden");
      elements.inviteInfo?.classList.add("compact");
    } else {
      elements.entrySection.classList.remove("hidden");
      elements.waitingScreen?.classList.add("hidden");
      elements.inviteInfo?.classList.remove("compact");
    }
  }
}

function activateInviteMode(gameId) {
  state.inviteMode = true;
  state.waitingOnly = true;
  state.inviteGameId = gameId;
  elements.entrySection?.classList.add("hidden");
  elements.waitingScreen?.classList.remove("hidden");
  elements.inviteInfo?.classList.add("compact");
}

function deactivateInviteMode() {
  state.inviteMode = false;
  state.waitingOnly = false;
  state.inviteGameId = null;
  elements.waitingScreen?.classList.add("hidden");
  elements.entrySection?.classList.remove("hidden");
  elements.inviteInfo?.classList.remove("compact");
}

function exitWaitingState() {
  state.inviteMode = false;
  state.waitingOnly = false;
  state.inviteGameId = null;
  elements.waitingScreen?.classList.add("hidden");
  elements.inviteInfo?.classList.remove("compact");
}

function requestInviteName() {
  const response = window.prompt("Введите ваше имя, чтобы присоединиться к игре");
  return response ? response.trim() : "";
}

function updateInviteLink(gameId) {
  if (!elements.inviteLinkInput || !gameId) return;
  const url = new URL(window.location.href);
  url.searchParams.set("game", gameId);
  elements.inviteLinkInput.value = url.toString();
}

function renderApp() {
  if (!state.game) return;
  const inLobby = state.game.phase === "lobby";
  if (!inLobby && state.waitingOnly) {
    exitWaitingState();
  }
  toggleEntryVisibility(Boolean(state.playerId));
  const { game } = state;
  if (inLobby) {
    elements.lobbySection?.classList.remove("hidden");
    if (elements.roomCodeLabel) elements.roomCodeLabel.textContent = game.id;
    if (elements.lobbyStatus) {
      elements.lobbyStatus.textContent = `Ожидаем игроков: ${game.players.length}/${game.maxPlayers}`;
    }
    renderPlayers(game);
    if (elements.startButton) {
      const me = game.players.find((p) => p.id === state.playerId);
      const activePlayers = game.players.filter((p) => !p.isOut);
      const canStart = Boolean(me?.isHost) && activePlayers.length >= 2;
      elements.startButton.classList.toggle("hidden", !canStart);
    }
  } else {
    elements.lobbySection?.classList.add("hidden");
    elements.entrySection?.classList.add("hidden");
    elements.waitingScreen?.classList.add("hidden");
    elements.inviteInfo?.classList.add("compact");
  }

  if (game.phase === "playing" || game.phase === "ended") {
    elements.gameSection?.classList.remove("hidden");
    renderGameBoard(game);
  } else {
    elements.gameSection?.classList.add("hidden");
    if (state.inviteMode && state.playerId) {
      elements.lobbySection?.classList.add("hidden");
      elements.waitingScreen?.classList.remove("hidden");
    }
  }
}

function renderPlayers(game) {
  if (!elements.playersList) return;
  elements.playersList.innerHTML = "";
  game.players.forEach((player) => {
    const li = document.createElement("li");
    const spanName = document.createElement("span");
    spanName.textContent = `${player.name}${
      player.id === state.playerId ? " (вы)" : ""
    }`;
    li.appendChild(spanName);
    const detail = document.createElement("span");
    detail.className = "tag";
    if (player.isOut) {
      detail.textContent = "Вышел";
    } else if (!player.connected) {
      detail.textContent = "Отключен";
    } else {
      detail.textContent = `${player.handSize} карт`;
    }
    li.appendChild(detail);
    elements.playersList.appendChild(li);
  });
}

function renderGameBoard(game) {
  if (elements.gameStatus) elements.gameStatus.textContent = game.status;
  if (elements.deckInfo) {
    elements.deckInfo.textContent = `Сброс: ${game.discardCount}`;
  }
  const actions = game.availableActions || {};
  if (elements.passButton) elements.passButton.disabled = !actions.canPass;
  if (elements.takeButton) elements.takeButton.disabled = !actions.canTake;
  renderDeck(game);
  renderTable(game.table);
  renderHand(game);
  renderPlayerBadges(game);
}

function renderDeck(game) {
  const count = game.deckCount || 0;
  if (elements.deckCount) {
    elements.deckCount.textContent = String(count);
  }
  if (elements.deckStack) {
    elements.deckStack.innerHTML = "";
    elements.deckStack.classList.toggle("empty", count === 0);
  }
  if (elements.trumpCardVisual) {
    elements.trumpCardVisual.innerHTML = "";
    if (game.trumpCard) {
      const img = document.createElement("img");
      img.src = getCardAsset(game.trumpCard);
      img.alt = `Козырь ${formatCard(game.trumpCard)}`;
      elements.trumpCardVisual.classList.remove("hidden");
      elements.trumpCardVisual.appendChild(img);
      elements.trumpLabel?.classList.remove("hidden");
    } else {
      elements.trumpCardVisual.classList.add("hidden");
      elements.trumpLabel?.classList.add("hidden");
    }
  }
}

function renderTable(table) {
  if (!elements.tableEl) return;
  elements.tableEl.innerHTML = "";
  if (!table.length) {
    elements.tableEl.textContent = "Стол пуст.";
    elements.tableEl.style.color = "#111";
    return;
  }
  elements.tableEl.style.color = "";
  table.forEach((slot, index) => {
    const cell = document.createElement("div");
    cell.className = "slot";
    cell.appendChild(createTableCard(slot.attack));
    if (slot.defense) {
      cell.appendChild(createTableCard(slot.defense));
    } else {
      const label = document.createElement("small");
      label.textContent = `Слот #${index + 1}`;
      cell.appendChild(label);
    }
    elements.tableEl.appendChild(cell);
  });
}

function renderHand(game) {
  if (!elements.handContainer) return;
  const me = game.players.find((p) => p.id === state.playerId);
  elements.handContainer.innerHTML = "";
  if (!me) return;
  const sortedHand = sortHandCards(me.hand, game.trumpCard?.suit);
  const total = sortedHand.length;
  const center = (total - 1) / 2;
  sortedHand.forEach((card, index) => {
    const btn = document.createElement("button");
    btn.className = "hand-card";
    const angle = (index - center) * CARD_RENDER_OPTIONS.rotationStep;
    btn.style.transform = `rotate(${angle}deg)`;
    btn.style.zIndex = index + 1;
    const img = document.createElement("img");
    img.src = getCardAsset(card);
    img.alt = formatCard(card);
    btn.appendChild(img);
    btn.addEventListener("click", () => handleCardClick(card));
    elements.handContainer.appendChild(btn);
  });
}

function renderPlayerBadges(game) {
  if (!elements.playersInline) return;
  elements.playersInline.innerHTML = "";
  game.players.forEach((player) => {
    const badge = document.createElement("div");
    badge.className = "player-chip";
    if (player.id === game.attackerId) badge.classList.add("attacker");
    if (player.id === game.defenderId) badge.classList.add("defender");
    badge.textContent = `${player.name} (${player.handSize})`;
    if (player.id === game.loserId) badge.textContent += " • дурак";
    elements.playersInline.appendChild(badge);
  });
}

function handleCardClick(card) {
  const game = state.game;
  if (!game || !state.socket) return;
  const actions = game.availableActions || {};
  const isDefender = game.defenderId === state.playerId;
  if (isDefender && actions.canDefend) {
    openDefenseModal(card);
    return;
  }
  if ((actions.canAttack || actions.canThrow) && callbacks.onPlayAttack) {
    callbacks.onPlayAttack(card);
  } else {
    showToast("Сейчас нельзя ходить этой картой.");
  }
}

function openDefenseModal(card) {
  if (!elements.defenseModal || !elements.defenseOptions) return;
  const pending = state.game.table
    .map((slot, idx) => (slot.defense ? null : { index: idx, card: slot.attack }))
    .filter(Boolean);
  if (!pending.length) {
    showToast("Нечего отбивать.");
    return;
  }
  elements.defenseOptions.innerHTML = "";
  pending.forEach((option) => {
    const btn = document.createElement("button");
    btn.textContent = `Отбить ${formatCard(option.card)}`;
    btn.classList.add("primary");
    btn.addEventListener("click", () => {
      if (callbacks.onPlayDefense) {
        callbacks.onPlayDefense(card, option.index);
      }
      hideDefenseModal();
    });
    elements.defenseOptions.appendChild(btn);
  });
  elements.defenseModal.classList.remove("hidden");
}

function hideDefenseModal() {
  if (!elements.defenseModal || !elements.defenseOptions) return;
  elements.defenseModal.classList.add("hidden");
  elements.defenseOptions.innerHTML = "";
}

function createTableCard(card) {
  const wrapper = document.createElement("div");
  wrapper.className = "card-on-table";
  const img = document.createElement("img");
  img.src = getCardAsset(card);
  img.alt = formatCard(card);
  wrapper.appendChild(img);
  return wrapper;
}

export {
  activateInviteMode,
  deactivateInviteMode,
  exitWaitingState,
  registerCallbacks,
  renderApp,
  requestInviteName,
  showToast,
  toggleEntryVisibility,
  updateInviteLink,
  hideDefenseModal,
};
