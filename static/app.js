"use strict";

const codeElement = document.getElementById("totp-code");
const countdownElement = document.getElementById("countdown");
const progressBar = document.getElementById("progress-bar");
const copyButton = document.getElementById("copy-code");
const copyLabel = document.getElementById("copy-label");
const statusMessage = document.getElementById("status-message");
const messages = {
  newCodeIn: document.body.dataset.newCodeIn || "New code in",
  second: document.body.dataset.second || "second",
  seconds: document.body.dataset.seconds || "seconds",
  refreshing: document.body.dataset.refreshing || "Refreshing",
  tapToCopy: document.body.dataset.tapToCopy || "Tap to copy",
  unableToRetrieve:
    document.body.dataset.unableToRetrieve || "Unable to retrieve the code.",
  connectionError: document.body.dataset.connectionError || "Connection error.",
  copied: document.body.dataset.copied || "Copied",
  copyFailed:
    document.body.dataset.copyFailed || "Copy failed. Select the code manually.",
};

let currentCode = "";
let currentRemaining = 0;
let currentPeriod = 30;
let lastFetchAt = 0;
let fetchInFlight = false;

function formatCode(code) {
  if (code.length === 6) return `${code.slice(0, 3)} ${code.slice(3)}`;
  if (code.length === 8) return `${code.slice(0, 4)} ${code.slice(4)}`;
  return code;
}

function renderCountdown() {
  if (!currentCode) return;
  const elapsed = Math.floor((Date.now() - lastFetchAt) / 1000);
  const remaining = Math.max(0, currentRemaining - elapsed);
  const ratio = Math.max(0, Math.min(1, remaining / currentPeriod));
  progressBar.style.width = `${ratio * 100}%`;
  const unit = remaining === 1 ? messages.second : messages.seconds;
  countdownElement.textContent = `${messages.newCodeIn} ${remaining} ${unit}`;

  if (remaining <= 0) {
    currentCode = "";
    codeElement.textContent = "••• •••";
    copyLabel.textContent = messages.refreshing;
    fetchCode();
    return;
  }
  if (remaining <= 1) fetchCode();
}

async function fetchCode() {
  if (fetchInFlight) return;
  fetchInFlight = true;
  try {
    const response = await fetch("/api/code", {
      method: "GET",
      cache: "no-store",
      credentials: "same-origin",
      headers: { "Accept": "application/json" },
    });
    const data = await response.json();

    if (response.status === 401 || response.status === 403) {
      window.location.assign("/");
      return;
    }
    if (!response.ok) {
      throw new Error(data.error || messages.unableToRetrieve);
    }

    currentCode = String(data.code || "");
    currentRemaining = Number(data.remaining || 0);
    currentPeriod = Number(data.period || 30);
    lastFetchAt = Date.now();
    codeElement.textContent = formatCode(currentCode);
    copyLabel.textContent = messages.tapToCopy;
    statusMessage.textContent = "";
    renderCountdown();
  } catch (error) {
    statusMessage.textContent = error.message || messages.connectionError;
  } finally {
    fetchInFlight = false;
  }
}

copyButton?.addEventListener("click", async () => {
  if (!currentCode) return;
  try {
    await navigator.clipboard.writeText(currentCode);
    copyLabel.textContent = messages.copied;
    window.setTimeout(() => {
      copyLabel.textContent = messages.tapToCopy;
    }, 1400);
  } catch {
    statusMessage.textContent = messages.copyFailed;
  }
});

if (codeElement) {
  fetchCode();
  window.setInterval(renderCountdown, 250);
  window.setInterval(fetchCode, 5000);
}
