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

const invoices = await loadInvoices();
await loadDisputes(invoices);