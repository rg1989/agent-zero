// app.js — crud-app template script

document.addEventListener("DOMContentLoaded", () => {

  // ── Delete confirmation ────────────────────────────────────────────────────
  // Any submit button with data-confirm="..." will trigger a confirmation dialog.
  // If the user cancels, the form submission is prevented.
  document.querySelectorAll("[data-confirm]").forEach((btn) => {
    const form = btn.closest("form");
    if (!form) return;
    form.addEventListener("submit", (e) => {
      const message = btn.dataset.confirm || "Are you sure?";
      if (!confirm(message)) {
        e.preventDefault();
      }
    });
  });

  // ── Flash message auto-dismiss ─────────────────────────────────────────────
  // Flash notifications fade out after 5 seconds.
  document.querySelectorAll(".flash").forEach((flash) => {
    // Manual close button
    const closeBtn = flash.querySelector(".flash-close");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => dismissFlash(flash));
    }
    // Auto-dismiss after 5s
    setTimeout(() => dismissFlash(flash), 5000);
  });

});


// ── Helpers ───────────────────────────────────────────────────────────────────

function dismissFlash(el) {
  if (!el || el.classList.contains("flash-hiding")) return;
  el.classList.add("flash-hiding");
  el.style.transition = "opacity 0.4s ease";
  el.style.opacity    = "0";
  setTimeout(() => el.remove(), 400);
}

/** Fetch JSON from a relative API path */
async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

/** Format a number with thousands separator */
function fmt(n, decimals = 0) {
  return Number(n).toLocaleString(undefined, { maximumFractionDigits: decimals });
}
