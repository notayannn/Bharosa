import { supabase } from "./api.js";
import { showToast } from "./toast.js";

const PAGES = [
  { href: "/dashboard", label: "Dashboard", key: "dashboard", icon: "▦" },
  { href: "/clients", label: "Clients", key: "clients", icon: "◉" },
  { href: "/chat", label: "AI Chat Assistant", key: "chat", icon: "◈" },
];

export function mountSidebar(activeKey) {
  const root = document.getElementById("sidebar-root");
  if (!root) return;

  const collapsed = localStorage.getItem("bharosa-sidebar-collapsed") === "true";

  root.innerHTML = `
    <aside class="sidebar ${collapsed ? "collapsed" : ""}" id="sidebar">
      <div class="sidebar-top">
        <button class="sidebar-toggle" id="sidebar-toggle" aria-label="Toggle sidebar">☰</button>
        <h1 class="sidebar-heading">Bharosa</h1>
      </div>
      <nav>
        ${PAGES.map(p => `
          <a href="${p.href}" class="${p.key === activeKey ? "active" : ""}" title="${p.label}">
            <span class="nav-icon">${p.icon}</span><span class="nav-label">${p.label}</span>
          </a>`).join("")}
      </nav>
      <div class="sidebar-bottom">
        <a href="#" id="settings-link" title="Settings">
          <span class="nav-icon">⚙</span><span class="nav-label">Settings</span>
        </a>
        <a href="#" id="logout-link" title="Log out">
          <span class="nav-icon">↪</span><span class="nav-label">Log out</span>
        </a>
      </div>
    </aside>
  `;

  document.getElementById("sidebar-toggle").addEventListener("click", () => {
    const sidebar = document.getElementById("sidebar");
    const isCollapsed = sidebar.classList.toggle("collapsed");
    localStorage.setItem("bharosa-sidebar-collapsed", isCollapsed);
  });

  document.getElementById("settings-link").addEventListener("click", (e) => {
    e.preventDefault();
    showToast("Settings page isn't built yet.");
  });

  document.getElementById("logout-link").addEventListener("click", async (e) => {
    e.preventDefault();
    await supabase.auth.signOut();
    window.location.href = "/";
  });
}