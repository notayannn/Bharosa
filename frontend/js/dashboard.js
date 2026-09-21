import { apiFetch, requireAuth, supabase } from "./api.js";
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

document.getElementById("qa-new-invoice").addEventListener("click", () => window.location.href = "/invoice");
document.getElementById("qa-new-client").addEventListener("click", () => window.location.href = "/clients");
document.getElementById("qa-ask-ai").addEventListener("click", () => window.location.href = "/chat");

function statusBadge(status) {
  return `<span class="badge status-${status}">${status.replace("_", " ")}</span>`;
}

function isOverdue(invoice) {
  return !["paid", "written_off"].includes(invoice.status) && new Date(invoice.due_date) < new Date();
}

function formatCurrency(amount, currency) {
  return `${currency} ${Number(amount).toLocaleString()}`;
}

function renderStatusChart(invoices) {
  const counts = { issued: 0, paid: 0, overdue: 0, disputed: 0, written_off: 0 };
  invoices.forEach((inv) => {
    if (isOverdue(inv)) counts.overdue++;
    else if (counts[inv.status] !== undefined) counts[inv.status]++;
  });

  const ctx = document.getElementById("status-chart");
  const styles = getComputedStyle(document.documentElement);
  const inkMuted = styles.getPropertyValue("--ink-muted").trim();
  const border = styles.getPropertyValue("--border").trim();

  if (window._statusChart) window._statusChart.destroy();

  window._statusChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Issued", "Paid", "Overdue", "Disputed", "Written off"],
      datasets: [{
        data: [counts.issued, counts.paid, counts.overdue, counts.disputed, counts.written_off],
        backgroundColor: ["#e0b93f", "#34c77f", "#e5534b", "#e5534b", "#8b968e"],
        borderRadius: 6,
        maxBarThickness: 48,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: inkMuted }, grid: { display: false } },
        y: { beginAtZero: true, ticks: { color: inkMuted, precision: 0 }, grid: { color: border } },
      },
    },
  });
}

function setupTitleEdit() {
  const displayEl = document.getElementById("title-display");
  const formEl = document.getElementById("title-edit-form");
  const inputEl = document.getElementById("title-edit-input");
  const headerEl = document.getElementById("business-name-header");

  document.getElementById("edit-title-btn").addEventListener("click", () => {
    inputEl.value = business.name;
    displayEl.style.display = "none";
    formEl.style.display = "flex";
    inputEl.focus();
  });

  document.getElementById("title-cancel-btn").addEventListener("click", () => {
    formEl.style.display = "none";
    displayEl.style.display = "flex";
  });

  formEl.addEventListener("submit", async (e) => {
    e.preventDefault();
    const newName = inputEl.value.trim();
    if (!newName) return;

    const response = await apiFetch("/api/businesses/me", {
      method: "PATCH",
      body: JSON.stringify({ name: newName }),
    });
    const updated = await response.json();
    business.name = updated.name;
    headerEl.textContent = updated.name;
    formEl.style.display = "none";
    displayEl.style.display = "flex";
    showToast("Business name updated");
  });
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

  const paidInvoices = invoices.filter((inv) => inv.status === "paid");
  const totalCollected = paidInvoices.reduce((sum, inv) => sum + Number(inv.amount), 0);
  const currency = invoices[0]?.currency || "PKR";

  document.getElementById("stat-overdue").textContent = invoices.filter(isOverdue).length;
  document.getElementById("stat-approvals").textContent = approvals.length;
  document.getElementById("stat-total").textContent = invoices.length;
  document.getElementById("stat-clients").textContent = clients.length;
  document.getElementById("stat-revenue").textContent = formatCurrency(totalCollected, currency);

  renderStatusChart(invoices);

  const invoicesBody = document.getElementById("invoices-body");
  invoicesBody.innerHTML = invoices.length
    ? invoices.map((inv) => `
        <tr class="clickable" onclick="window.location.href='/invoice?id=${inv.id}'">
          <td>${clientNameById[inv.client_id] || "—"}</td>
          <td>${formatCurrency(inv.amount, inv.currency)}</td>
          <td>${inv.due_date}</td>
          <td>${statusBadge(isOverdue(inv) ? "overdue" : inv.status)}</td>
        </tr>`).join("")
    : `<tr class="empty-row"><td colspan="4">No invoices yet — create one to get started.</td></tr>`;

  const approvalsList = document.getElementById("approvals-list");
  approvalsList.innerHTML = approvals.length
    ? approvals.map((a) => `
        <div class="ledger-entry" style="flex-direction:column; align-items:stretch; gap:0.5rem;">
          <div style="display:flex; justify-content:space-between;">
            <span>${a.agent_name} · ${a.action_type}</span>
            <span class="actor">${(a.confidence * 100).toFixed(0)}%</span>
          </div>
          <div class="btn-row">
            <button data-id="${a.id}" data-approved="true" class="success approve-btn" style="flex:1;">Approve</button>
            <button data-id="${a.id}" data-approved="false" class="danger reject-btn" style="flex:1;">Reject</button>
          </div>
        </div>`).join("")
    : "<p class='subhead'>Nothing awaiting review.</p>";

  document.querySelectorAll(".approve-btn, .reject-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const actionId = btn.dataset.id;
      const approved = btn.dataset.approved;
      await apiFetch(`/api/approvals/${actionId}/decide?approved=${approved}`, { method: "POST" });
      showToast(approved === "true" ? "Approved" : "Rejected");
      loadDashboard();
    });
  });

  await loadRecentActivity(invoices, clientNameById);
}

async function loadWhatsappPanel() {
  const panel = document.getElementById("whatsapp-panel");
  const statusRes = await apiFetch("/api/whatsapp/status");
  const status = await statusRes.json();

  if (status.connected) {
    panel.innerHTML = `<p class="subhead">✅ Connected and ready to send.</p>`;
    return;
  }

  const qrRes = await apiFetch("/api/whatsapp/qr");
  const qr = await qrRes.json();

  if (qr.status === "needs_scan") {
    panel.innerHTML = `
      <p class="subhead">Scan with WhatsApp → Settings → Linked Devices</p>
      <img src="data:image/png;base64,${qr.qr_base64}" style="width:100%; border-radius:8px;" />
    `;
  } else {
    panel.innerHTML = `<p class="subhead">Couldn't load QR code — check backend logs.</p>`;
  }
}

function setupWhatsappCollapse() {
  const header = document.getElementById("whatsapp-toggle");
  const body = document.getElementById("whatsapp-panel-wrap");
  header.addEventListener("click", () => {
    header.classList.toggle("open");
    body.classList.toggle("open");
  });
}

async function loadRecentActivity(invoices, clientNameById) {
  const activityList = document.getElementById("activity-list");
  const invoiceIds = invoices.map((inv) => inv.id);

  if (!invoiceIds.length) {
    activityList.innerHTML = "<p class='subhead'>No activity yet.</p>";
    return;
  }

  const invoiceClientById = Object.fromEntries(invoices.map((inv) => [inv.id, clientNameById[inv.client_id] || "—"]));

  const { data: entries } = await supabase
    .from("ledger_entries")
    .select("*")
    .in("invoice_id", invoiceIds)
    .order("created_at", { ascending: false })
    .limit(6);

  activityList.innerHTML = entries?.length
    ? entries.map((e) => `
        <div class="ledger-entry">
          <span>${e.entry_type.replace("_", " ")}${e.amount ? ` — ${e.amount}` : ""} · ${invoiceClientById[e.invoice_id] || "—"}</span>
          <span class="actor">${e.actor}${e.agent_name ? ` (${e.agent_name})` : ""}</span>
        </div>`).join("")
    : "<p class='subhead'>No activity yet.</p>";
}

document.getElementById("run-reminders-btn").addEventListener("click", async () => {
  const response = await apiFetch(`/api/escalation/run?business_id=${business.id}`, { method: "POST" });
  const data = await response.json();
  showToast(`Sent ${data.reminders_sent.length} reminder(s) (simulated)`);
});

business = await loadBusiness();
if (business) {
  document.getElementById("dashboard-content").style.display = "block";
  document.getElementById("business-name-header").textContent = business.name;
  setupTitleEdit();
  setupWhatsappCollapse();
  await loadDashboard();
  await loadWhatsappPanel();
}