import elements from "./dom.js";
import { state, getStoredPlayerName } from "./state.js";
import {
  activateInviteMode,
  deactivateInviteMode,
  registerCallbacks,
  renderApp,
  requestInviteName,
  showToast,
  updateInviteLink,
  hideDefenseModal,
} from "./ui.js";
import { connectToGame, sendAction } from "./network.js";

registerCallbacks({
  onPlayAttack: (card) => sendAction("play_attack", { card }),
  onPlayDefense: (card, attackIndex) =>
    sendAction("play_defense", { card, attackIndex }),
});

elements.surrenderButton?.addEventListener("click", () => sendAction("surrender"));

elements.createForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const name = elements.createNameInput.value.trim();
  const count = Number(elements.createCountInput.value);
  if (!name) {
    showToast("Введите имя для создания игры.");
    return;
  }
  if (Number.isNaN(count) || count < 2 || count > 6) {
    showToast("Количество игроков от 2 до 6.");
    return;
  }
  try {
    const response = await fetch("/api/games", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ maxPlayers: count }),
    });
    if (!response.ok) {
      throw new Error("Ошибка создания комнаты.");
    }
    const data = await response.json();
    elements.joinCodeInput.value = data.gameId;
    updateInviteLink(data.gameId);
    connectToGame(data.gameId, name);
    showToast("Комната создана — делитесь ссылкой!");
  } catch (error) {
    showToast("Не удалось создать комнату.");
    console.error(error);
  }
});

elements.joinForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  const code = elements.joinCodeInput.value.trim().toUpperCase();
  const name = elements.joinNameInput.value.trim();
  if (!code || code.length !== 6) {
    showToast("Введите код из приглашения (6 символов).");
    return;
  }
  if (!name) {
    showToast("Введите имя.");
    return;
  }
  updateInviteLink(code);
  connectToGame(code, name);
});

elements.startButton?.addEventListener("click", () => {
  sendAction("start_game");
});

elements.passButton?.addEventListener("click", () => {
  sendAction("pass_attack");
});

elements.takeButton?.addEventListener("click", () => {
  sendAction("take_cards");
});

elements.closeModalBtn?.addEventListener("click", (event) => {
  event.preventDefault();
  hideDefenseModal();
});

if (elements.waitingScreen) {
  elements.waitingScreen.addEventListener("click", (event) => {
    if (!state.inviteMode || state.playerId) return;
    if (event.target === elements.waitingExitBtn) return;
    const gameId =
      state.inviteGameId || elements.joinCodeInput.value.trim().toUpperCase();
    if (!gameId) return;
    requestNameAndJoin(gameId);
  });
}

elements.waitingExitBtn?.addEventListener("click", (event) => {
  event.stopPropagation();
  deactivateInviteMode();
});

elements.rematchBtn?.addEventListener("click", (event) => {
  event.preventDefault();
  sendAction("request_rematch");
});

elements.exitRematchBtn?.addEventListener("click", (event) => {
  event.preventDefault();
  sendAction("cancel_rematch");
});

elements.chatForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  const value = elements.chatInput?.value.trim();
  if (!value) {
    return;
  }
  sendAction("send_chat", { message: value });
  if (elements.chatInput) {
    elements.chatInput.value = "";
  }
});

elements.copyLinkButton?.addEventListener("click", async () => {
  if (!elements.inviteLinkInput?.value) return;
  const originalText = elements.copyLinkButton.textContent;
  const notifyCopied = () => {
    elements.copyLinkButton.textContent = "Скопировано";
    setTimeout(() => {
      elements.copyLinkButton.textContent = originalText;
    }, 1500);
    showToast("Ссылка скопирована.");
  };
  try {
    await navigator.clipboard.writeText(elements.inviteLinkInput.value);
    notifyCopied();
  } catch (err) {
    elements.inviteLinkInput.select();
    document.execCommand("copy");
    notifyCopied();
  }
});

function requestNameAndJoin(gameId) {
  if (!gameId) return false;
  const name = requestInviteName();
  if (!name) {
    showToast("Имя обязательно для входа.");
    return false;
  }
  updateInviteLink(gameId);
  connectToGame(gameId, name);
  return true;
}

const params = new URLSearchParams(window.location.search);
const presetCode = params.get("game");
if (presetCode) {
  const normalized = presetCode.toUpperCase();
  elements.joinCodeInput.value = normalized;
  updateInviteLink(normalized);
  activateInviteMode(normalized);
  const storedName = getStoredPlayerName(normalized);
  if (storedName) {
    connectToGame(normalized, storedName);
  } else {
    showToast("Введите имя, чтобы присоединиться.");
    requestNameAndJoin(normalized);
  }
}

renderApp();

