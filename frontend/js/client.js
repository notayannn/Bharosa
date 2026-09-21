import { apiFetch, requireAuth, supabase } from "./api.js";
import { mountSidebar } from "./sidebar.js";

await requireAuth();
mountSidebar("clients");

const params = new URLSearchParams(window.location.search);
const clientId = params.get("id");

const { data: client } = await supabase.from("clients").select("*").eq("id", clientId).single();

document.getElementById("client-name-header").textContent = client.name;
document.getElementById("client-contact-sub").textContent =
  client.contact_channels?.primary ? `Contact: ${client.contact_channels.primary}` : "No contact info on file";

  setupContactEdit();

document.getElementById("new-invoice-btn").addEventListener("click", () => {
  window.location.href = `/invoice?client_id=${clientId}`;
});

function statusBadge(status) {
  return `<span class="badge status-${status}">${status.replace("_", " ")}</span>`;
}

function disputeBadge(status) {
  return `<span class="badge dispute-${status}">${status.replace("_", " ")}</span>`;
}

async function loadInvoices() {
  const { data: invoices } = await supabase
    .from("invoices")
    .select("*")
    .eq("client_id", clientId)
    .order("issue_date", { ascending: false });

  const body = document.getElementById("invoices-body");
  body.innerHTML = invoices?.length
    ? invoices.map((inv) => `
        <tr class="clickable" onclick="window.location.href='/invoice?id=${inv.id}'">
          <td>${inv.currency} ${inv.amount}</td>
          <td>${inv.issue_date}</td>
          <td>${inv.due_date}</td>
          <td>${statusBadge(inv.status)}</td>
        </tr>`).join("")
    : `<tr class="empty-row"><td colspan="4">No invoices for this client yet.</td></tr>`;

  return invoices || [];
}

async function loadDisputes(invoices) {
  const invoiceIds = invoices.map((inv) => inv.id);
  const list = document.getElementById("disputes-list");

  if (!invoiceIds.length) {
    list.innerHTML = "<p class='subhead'>No invoices, so no disputes yet.</p>";
    return;
  }

  const { data: disputes } = await supabase.from("disputes").select("*").in("invoice_id", invoiceIds);

  list.innerHTML = disputes?.length
    ? disputes.map((d) => `
        <div class="ledger-entry">
          <span>${d.claim_text}${d.claim_amount ? ` — Rs. ${d.claim_amount}` : ""}</span>
          ${disputeBadge(d.status)}
        </div>`).join("")
    : "<p class='subhead'>No disputes recorded for this client.</p>";
}

function setupContactEdit() {
  const displayEl = document.getElementById("client-title-display");
  const formEl = document.getElementById("contact-edit-form");
  const inputEl = document.getElementById("contact-edit-input");
  const subEl = document.getElementById("client-contact-sub");

  document.getElementById("edit-contact-btn").addEventListener("click", () => {
    inputEl.value = client.contact_channels?.primary || "";
    formEl.style.display = "flex";
    inputEl.focus();
  });

  document.getElementById("contact-cancel-btn").addEventListener("click", () => {
    formEl.style.display = "none";
  });

  formEl.addEventListener("submit", async (e) => {
    e.preventDefault();
    const value = inputEl.value.trim();
    if (!value) return;

    const response = await apiFetch(`/api/clients/${clientId}`, {
      method: "PATCH",
      body: JSON.stringify({ contact_channels: { primary: value } }),
    });
    const updated = await response.json();
    client.contact_channels = updated.contact_channels;
    subEl.textContent = `Contact: ${value}`;
    formEl.style.display = "none";
  });
}

async function loadRiskIndicator(invoices) {
  const badge = document.getElementById("risk-badge");
  const paidInvoices = invoices.filter((inv) => inv.status === "paid");

  if (!paidInvoices.length) {
    badge.innerHTML = `<span class="risk-badge risk-new">New client</span>`;
    return;
  }

  const invoiceIds = paidInvoices.map((inv) => inv.id);
  const { data: paymentEntries } = await supabase
    .from("ledger_entries")
    .select("*")
    .in("invoice_id", invoiceIds)
    .eq("entry_type", "payment_received");

  const dueDateByInvoice = Object.fromEntries(paidInvoices.map((inv) => [inv.id, inv.due_date]));
  let lateCount = 0;

  (paymentEntries || []).forEach((entry) => {
    const dueDate = dueDateByInvoice[entry.invoice_id];
    if (dueDate && new Date(entry.created_at) > new Date(dueDate)) lateCount++;
  });

  const total = (paymentEntries || []).length || 1;
  const lateRatio = lateCount / total;

  if (lateRatio === 0) {
    badge.innerHTML = `<span class="risk-badge risk-good">Reliable payer</span>`;
  } else if (lateRatio <= 0.4) {
    badge.innerHTML = `<span class="risk-badge risk-watch">Occasionally late</span>`;
  } else {
    badge.innerHTML = `<span class="risk-badge risk-poor">Frequently late</span>`;
  }
}

const invoices = await loadInvoices();
await loadDisputes(invoices);
await loadRiskIndicator(invoices);