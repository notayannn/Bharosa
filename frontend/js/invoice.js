import { apiFetch, requireAuth, supabase, downloadDocument, API_BASE_URL } from "./api.js";
import { showToast, showPlaceholder } from "./toast.js";
import { mountSidebar } from "./sidebar.js";

await requireAuth();
mountSidebar("clients");

const params = new URLSearchParams(window.location.search);
const invoiceId = params.get("id");
const presetClientId = params.get("client_id");

let business = null;

document.getElementById("pay-jazzcash-btn").addEventListener("click", () => showPlaceholder("JazzCash"));
document.getElementById("pay-easypaisa-btn").addEventListener("click", () => showPlaceholder("EasyPaisa"));
document.getElementById("whatsapp-btn").addEventListener("click", () => showPlaceholder("WhatsApp reminders"));

business = await (await apiFetch("/api/businesses/me")).json();

if (invoiceId) {
  await renderDetailMode();
} else {
  await renderCreateMode();
}

async function renderCreateMode() {
  document.getElementById("create-mode").style.display = "block";

  const clients = await (await apiFetch(`/api/clients?business_id=${business.id}`)).json();
  const select = document.getElementById("invoice-client");
  select.innerHTML = clients.map((c) => `<option value="${c.id}">${c.name}</option>`).join("");
  if (presetClientId) select.value = presetClientId;

  const today = new Date().toISOString().split("T")[0];
  document.getElementById("invoice-issue-date").value = today;

  document.getElementById("create-invoice-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const response = await apiFetch("/api/invoices", {
      method: "POST",
      body: JSON.stringify({
        business_id: business.id,
        client_id: select.value,
        amount: parseFloat(document.getElementById("invoice-amount").value),
        issue_date: document.getElementById("invoice-issue-date").value,
        due_date: document.getElementById("invoice-due-date").value,
      }),
    });
    const invoice = await response.json();
    window.location.href = `/invoice?id=${invoice.id}`;
  });
}

async function renderDetailMode() {
  document.getElementById("detail-mode").style.display = "block";

  const { data: invoice } = await supabase.from("invoices").select("*").eq("id", invoiceId).single();
  const { data: client } = await supabase.from("clients").select("*").eq("id", invoice.client_id).single();

  document.getElementById("invoice-title").textContent = `${invoice.currency} ${invoice.amount} — ${client.name}`;
  document.getElementById("invoice-subhead").textContent = `Due ${invoice.due_date} · ${invoice.status}`;

  await loadLedger();
  await loadDisputes();

  document.getElementById("download-invoice-btn").addEventListener("click", async () => {
    try {
      await downloadDocument(`/api/documents/invoice/${invoiceId}`);
    } catch (e) {
      showToast(e.message);
    }
  });

  if (invoice.status === "paid") {
    const receiptBtn = document.getElementById("download-receipt-btn");
    receiptBtn.style.display = "inline-block";
    receiptBtn.addEventListener("click", async () => {
      try {
        await downloadDocument(`/api/documents/receipt/${invoiceId}`);
      } catch (e) {
        showToast(e.message);
      }
    });
  }

  document.getElementById("upload-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById("slip-file");
    const formData = new FormData();
    formData.append("business_id", business.id);
    formData.append("client_id", invoice.client_id);
    formData.append("file", fileInput.files[0]);

    const { data } = await supabase.auth.getSession();
        const response = await fetch(`${API_BASE_URL}/api/payments/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${data.session.access_token}` },
      body: formData,
    });
    const result = await response.json();

    const resultEl = document.getElementById("upload-result");
    if (result.reconciliation?.requires_owner_review) {
      resultEl.textContent = "Uploaded — ambiguous match, sent to your approval queue on the dashboard.";
    } else {
      resultEl.textContent = `Uploaded and matched automatically (${(result.reconciliation.confidence * 100).toFixed(0)}% confidence).`;
    }
    showToast("Slip processed");
    await loadLedger();
  });

  const disputeModal = document.getElementById("dispute-modal");
  document.getElementById("raise-dispute-btn").addEventListener("click", () => disputeModal.classList.add("open"));
  document.getElementById("dispute-cancel").addEventListener("click", () => disputeModal.classList.remove("open"));

  document.getElementById("dispute-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    await apiFetch("/api/disputes", {
      method: "POST",
      body: JSON.stringify({
        business_id: business.id,
        invoice_id: invoiceId,
        raised_by: document.getElementById("dispute-raised-by").value,
        claim_text: document.getElementById("dispute-details").value,
        claim_amount: document.getElementById("dispute-amount").value
          ? parseFloat(document.getElementById("dispute-amount").value)
          : null,
      }),
    });
    disputeModal.classList.remove("open");
    showToast("Dispute logged");
    await loadDisputes();
  });
}

async function loadLedger() {
  const { data: entries } = await supabase
    .from("ledger_entries")
    .select("*")
    .eq("invoice_id", invoiceId)
    .order("created_at");

  const list = document.getElementById("ledger-list");
  list.innerHTML = entries?.length
    ? entries.map((e) => `
        <div class="ledger-entry">
          <span>${e.entry_type.replace("_", " ")} ${e.amount ? `— ${e.amount}` : ""}</span>
          <span class="actor">${e.actor}${e.agent_name ? ` (${e.agent_name})` : ""}</span>
        </div>`).join("")
    : "<p class='subhead'>No ledger entries yet.</p>";
}

async function loadDisputes() {
  const { data: disputes } = await supabase.from("disputes").select("*").eq("invoice_id", invoiceId);
  const list = document.getElementById("disputes-list");

  list.innerHTML = disputes?.length
    ? disputes.map((d) => `
        <div class="ledger-entry">
          <span>${d.claim_text}${d.claim_amount ? ` — Rs. ${d.claim_amount}` : ""}</span>
          <span class="badge dispute-${d.status}">${d.status.replace("_", " ")}</span>
        </div>`).join("")
    : "<p class='subhead'>No disputes on this invoice.</p>";
}