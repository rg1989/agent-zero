// app.js — starter script for flask-basic template
// Replace / extend with your own logic.

document.addEventListener("DOMContentLoaded", () => {

  // ── Ping button demo ──────────────────────────────────────────────────────
  const pingBtn = document.getElementById("ping-btn");
  const output  = document.getElementById("output");

  if (pingBtn && output) {
    pingBtn.addEventListener("click", async () => {
      pingBtn.disabled = true;
      output.textContent = "Loading…";
      try {
        const res  = await fetch("api/data");  // relative URL — works via proxy
        const data = await res.json();
        output.textContent = JSON.stringify(data, null, 2);
      } catch (err) {
        output.textContent = "Error: " + err.message;
        output.style.color = "var(--red)";
      } finally {
        pingBtn.disabled = false;
      }
    });
  }

});

// ── Utility helpers ───────────────────────────────────────────────────────────

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
