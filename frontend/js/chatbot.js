import { apiFetch } from "./api.js";

export function mountChatbot(getBusinessId) {
  const toggle = document.createElement("div");
  toggle.className = "chat-toggle";
  toggle.textContent = "💬";
  document.body.appendChild(toggle);

  const panel = document.createElement("div");
  panel.className = "chat-panel";
  panel.innerHTML = `
    <div class="chat-panel-header">Ask Bharosa</div>
    <div class="chat-messages" id="chat-messages">
      <div class="chat-msg bot">Ask me about overdue invoices, a client's ledger, or anything else in your account.</div>
    </div>
    <div class="chat-input-row">
      <input type="text" id="chat-input" placeholder="e.g. which clients are overdue?" />
      <button id="chat-send">Send</button>
    </div>
  `;
  document.body.appendChild(panel);

  toggle.addEventListener("click", () => panel.classList.toggle("open"));

  const messages = panel.querySelector("#chat-messages");
  const input = panel.querySelector("#chat-input");
  const sendBtn = panel.querySelector("#chat-send");

  async function send() {
    const question = input.value.trim();
    if (!question) return;
    addMessage(question, "user");
    input.value = "";
    sendBtn.disabled = true;

    const businessId = await getBusinessId();
    const response = await apiFetch("/api/chatbot/ask", {
      method: "POST",
      body: JSON.stringify({ business_id: businessId, question }),
    });
    const data = await response.json();
    addMessage(data.answer, "bot");
    sendBtn.disabled = false;
  }

  function addMessage(text, who) {
    const el = document.createElement("div");
    el.className = `chat-msg ${who}`;
    el.textContent = text;
    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
  }

  sendBtn.addEventListener("click", send);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });
}