import { apiFetch, requireAuth } from "./api.js";
import { showToast } from "./toast.js";
import { mountSidebar } from "./sidebar.js";

await requireAuth();
mountSidebar("dashboard");

let business = null;

async function loadBusiness() {
  const response = await apiFetch("/api/businesses/me");
  if (response.status === 404) {
    document.getElementById("no-business-card").style.display = "block";
    return null;
  }
  return await response.json();
}

document.getElementById("business-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = document.getElementById("business-name").value;
  await apiFetch("/api/businesses", { method: "POST", body: JSON.stringify({ name }) });
  window.location.reload();
});

function statusBadge(status) {
  return `<span class="badge status-${status}">${status.replace("_", " ")}</span>`;
}

function isOverdue(invoice) {
  return !["paid", "written_off"].includes(invoice.status) && new Date(invoice.due_date) < new Date();
}

async function loadDashboard() {
  const [invoicesRes, clientsRes, approvalsRes] = await Promise.all([
    apiFetch(`/api/invoices?business_id=${business.id}`),
    apiFetch(`/api/clients?business_id=${business.id}`),
    apiFetch(`/api/approvals/pending?business_id=${business.id}`),
  ]);
  const invoices = await invoicesRes.json();
  const clients = await clientsRes.json();
  const approvals = await approvalsRes.json();

  const clientNameById = Object.fromEntries(clients.map((c) => [c.id, c.name]));

  document.getElementById("stat-overdue").textContent = invoices.filter(isOverdue).length;
  document.getElementById("stat-approvals").textContent = approvals.length;
  document.getElementById("stat-total").textContent = invoices.length;
  document.getElementById("stat-clients").textContent = clients.length;

  const invoicesBody = document.getElementById("invoices-body");
  invoicesBody.innerHTML = invoices.length
    ? invoices.map((inv) => `
        <tr class="clickable" onclick="window.location.href='/invoice?id=${inv.id}'">
          <td>${clientNameById[inv.client_id] || "—"}</td>
          <td>${inv.currency} ${inv.amount}</td>
          <td>${inv.due_date}</td>
          <td>${statusBadge(isOverdue(inv) ? "overdue" : inv.status)}</td>
        </tr>`).join("")
    : `<tr class="empty-row"><td colspan="4">No invoices yet — create one to get started.</td></tr>`;

  const approvalsBody = document.getElementById("approvals-body");
  approvalsBody.innerHTML = approvals.length
    ? approvals.map((a) => `
        <tr>
          <td>${a.agent_name}</td>
          <td>${a.action_type}</td>
          <td>${(a.confidence * 100).toFixed(0)}%</td>
          <td class="btn-row">
            <button data-id="${a.id}" data-approved="true" class="success approve-btn">Approve</button>
            <button data-id="${a.id}" data-approved="false" class="danger reject-btn">Reject</button>
          </td>
        </tr>`).join("")
    : `<tr class="empty-row"><td colspan="4">Nothing awaiting review</td></tr>`;

  document.querySelectorAll(".approve-btn, .reject-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const actionId = btn.dataset.id;
      const approved = btn.dataset.approved;
      await apiFetch(`/api/approvals/${actionId}/decide?approved=${approved}`, { method: "POST" });
      showToast(approved === "true" ? "Approved" : "Rejected");
      loadDashboard();
    });
  });
}

document.getElementById("run-reminders-btn").addEventListener("click", async () => {
  const response = await apiFetch(`/api/escalation/run?business_id=${business.id}`, { method: "POST" });
  const data = await response.json();
  showToast(`Sent ${data.reminders_sent.length} reminder(s) (simulated)`);
});

document.getElementById("new-invoice-btn").addEventListener("click", () => {
  window.location.href = "/invoice";
});

business = await loadBusiness();
if (business) {
  document.getElementById("dashboard-content").style.display = "block";
  document.getElementById("business-name-header").textContent = business.name;
  await loadDashboard();
}