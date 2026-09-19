import { apiFetch, requireAuth, downloadDocument } from "./api.js";
import { showToast } from "./toast.js";
import { mountSidebar } from "./sidebar.js";

await requireAuth();
mountSidebar("clients");

let business = null;

const modal = document.getElementById("client-modal");
document.getElementById("new-client-btn").addEventListener("click", () => modal.classList.add("open"));
document.getElementById("client-cancel").addEventListener("click", () => modal.classList.remove("open"));

document.getElementById("client-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = document.getElementById("client-name").value;
  const contact = document.getElementById("client-contact").value;
  await apiFetch("/api/clients", {
    method: "POST",
    body: JSON.stringify({
      business_id: business.id,
      name,
      contact_channels: contact ? { primary: contact } : {},
    }),
  });
  modal.classList.remove("open");
  showToast("Client created");
  loadClients();
});

async function loadClients() {
  const [clientsRes, invoicesRes] = await Promise.all([
    apiFetch(`/api/clients?business_id=${business.id}`),
    apiFetch(`/api/invoices?business_id=${business.id}`),
  ]);
  const clients = await clientsRes.json();
  const invoices = await invoicesRes.json();

  const openCountByClient = {};
  for (const inv of invoices) {
    if (!["paid", "written_off"].includes(inv.status)) {
      openCountByClient[inv.client_id] = (openCountByClient[inv.client_id] || 0) + 1;
    }
  }

  const body = document.getElementById("clients-body");
  body.innerHTML = clients.length
    ? clients.map((c) => `
        <tr class="clickable" onclick="window.location.href='/client?id=${c.id}'">
          <td>${c.name}</td>
          <td>${c.contact_channels?.primary || "—"}</td>
          <td>${openCountByClient[c.id] || 0}</td>
          <td><button class="secondary statement-btn" data-client-id="${c.id}" onclick="event.stopPropagation()">Statement</button></td>
        </tr>`).join("")
    : `<tr class="empty-row"><td colspan="4">No clients yet — add one to get started.</td></tr>`;

  document.querySelectorAll(".statement-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try {
        await downloadDocument(`/api/documents/statement/${btn.dataset.clientId}`);
      } catch (e) {
        showToast(e.message);
      }
    });
  });
}

business = await (await apiFetch("/api/businesses/me")).json();
await loadClients();