import { apiFetch, requireAuth } from "./api.js";
import { mountSidebar } from "./sidebar.js";

await requireAuth();
mountSidebar("chat");

const business = await (await apiFetch("/api/businesses/me")).json();
const storageKey = `bharosa-chat-history:${business.id}`;

const scrollEl = document.getElementById("chat-scroll");
const input = document.getElementById("chat-input");
const sendBtn = document.getElementById("chat-send");

function loadHistory() {
  try {
    return JSON.parse(localStorage.getItem(storageKey) || "[]");
  } catch {
    return [];
  }
}

function saveHistory(history) {
  localStorage.setItem(storageKey, JSON.stringify(history));
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function render(history) {
  if (!history.length) {
    scrollEl.innerHTML = `<div class="chat-empty">Ask about your invoices, clients, or ledger.</div>`;
    return;
  }

  scrollEl.innerHTML = history.map((msg) => `
    <div class="chat-bubble-row ${msg.role}">
      <div class="chat-bubble ${msg.thinking ? "thinking" : ""}">${escapeHtml(msg.text)}</div>
    </div>
  `).join("");

  scrollEl.scrollTop = scrollEl.scrollHeight;
}

let history = loadHistory();
render(history);

async function send() {
  const question = input.value.trim();
  if (!question) return;
  input.value = "";
  sendBtn.disabled = true;

  history.push({ role: "user", text: question });
  history.push({ role: "bot", text: "Thinking…", thinking: true });
  render(history);

  const response = await apiFetch("/api/chatbot/ask", {
    method: "POST",
    body: JSON.stringify({ business_id: business.id, question }),
  });
  const data = await response.json();

  history[history.length - 1] = { role: "bot", text: data.answer };
  saveHistory(history);
  render(history);
  sendBtn.disabled = false;
  input.focus();
}

sendBtn.addEventListener("click", send);
input.addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });

document.getElementById("clear-history-btn").addEventListener("click", () => {
  history = [];
  saveHistory(history);
  render(history);
});