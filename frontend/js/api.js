// Supabase client loaded via CDN (ESM build) — no npm install needed.
// This works because this file is loaded as a <script type="module">,
// which lets the browser natively handle the `import` statement below.
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

export const supabase = createClient(
  window.__ENV__.SUPABASE_URL,
  window.__ENV__.SUPABASE_PUBLISHABLE_KEY
);

export const API_BASE_URL = window.__ENV__.API_BASE_URL;

/**
 * Fetch wrapper that automatically attaches the current user's Supabase
 * JWT to every backend API call. Every page's JS imports and uses this
 * instead of raw fetch(), so no page has to manually handle auth headers.
 */
export async function apiFetch(path, options = {}) {
  const { data } = await supabase.auth.getSession();
  const token = data?.session?.access_token;

  if (!token) {
    // No valid session — bounce to login rather than let the API call
    // fail with a confusing 401 deep inside some page's logic.
    window.location.href = "/";
    return;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...options.headers,
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (response.status === 401) {
    window.location.href = "/";
    return;
  }

  return response;
}

/**
 * Call at the top of every protected page (dashboard, clients, invoice)
 * to redirect unauthenticated visitors back to login before anything
 * else on the page runs.
 */
export async function requireAuth() {
  const { data } = await supabase.auth.getSession();
  if (!data?.session) {
    window.location.href = "/";
  }
  return data?.session;
}

export async function downloadDocument(path) {
  const response = await apiFetch(path);
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to generate document");
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  window.open(url, "_blank");
}