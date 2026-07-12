"use strict";

const codeElement = document.getElementById("totp-code");
const countdownElement = document.getElementById("countdown");
const progressBar = document.getElementById("progress-bar");
const copyButton = document.getElementById("copy-code");
const copyLabel = document.getElementById("copy-label");
const statusMessage = document.getElementById("status-message");

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
  countdownElement.textContent = remaining === 1
    ? "New code in 1 second"
    : `New code in ${remaining} seconds`;

  if (remaining <= 1) fetchCode();
}

async function fetchCode() {
  if (fetchInFlight) return;
  fetchInFlight = true;
  try {
    const response = await fetch("/api/code", {
      method: "GET",
      cache: "no-store",
      headers: { "Accept": "application/json" },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Unable to retrieve the code.");

    currentCode = String(data.code || "");
    currentRemaining = Number(data.remaining || 0);
    currentPeriod = Number(data.period || 30);
    lastFetchAt = Date.now();
    codeElement.textContent = formatCode(currentCode);
    statusMessage.textContent = "";
    renderCountdown();
  } catch (error) {
    statusMessage.textContent = error.message || "Connection error.";
  } finally {
    fetchInFlight = false;
  }
}

copyButton.addEventListener("click", async () => {
  if (!currentCode) return;
  try {
    await navigator.clipboard.writeText(currentCode);
    copyLabel.textContent = "Copied";
    window.setTimeout(() => { copyLabel.textContent = "Tap to copy"; }, 1400);
  } catch {
    statusMessage.textContent = "Copy failed. Select the code manually.";
  }
});

fetchCode();
window.setInterval(renderCountdown, 250);
window.setInterval(fetchCode, 5000);
