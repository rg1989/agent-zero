// app.js — static-html template
// Replace the sample data and chart config with your own.

// ── Sample data ───────────────────────────────────────────────────────────────
// Replace this with real data: fetched from an API, embedded as JSON, etc.
const DATA = {
  labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
  series: [
    { label: "Series A", values: [42, 68, 55, 71, 90, 83, 76, 95, 88, 102, 115, 98], color: "#00f2fe" },
    { label: "Series B", values: [18, 29, 37, 25, 44, 38, 52, 47, 61, 55, 70, 63],  color: "#ff9500" },
  ],
  table: [
    { Month: "Jan", "Series A": 42, "Series B": 18 },
    { Month: "Feb", "Series A": 68, "Series B": 29 },
    { Month: "Mar", "Series A": 55, "Series B": 37 },
    // ... extend as needed
  ],
};

// ── Chart ─────────────────────────────────────────────────────────────────────
let chart = null;

function renderChart(data) {
  const ctx = document.getElementById("main-chart");
  if (!ctx) return;
  const cfg = {
    type: "line",
    data: {
      labels: data.labels,
      datasets: data.series.map(s => ({
        label:           s.label,
        data:            s.values,
        borderColor:     s.color,
        backgroundColor: s.color + "22",
        borderWidth:     2,
        pointRadius:     3,
        tension:         0.35,
        fill:            true,
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: "#aaa", font: { size: 12 } } },
      },
      scales: {
        x: { ticks: { color: "#666", maxRotation: 0 }, grid: { color: "#1f1f1f" } },
        y: { ticks: { color: "#666" },                  grid: { color: "#1f1f1f" } },
      },
    },
  };
  if (chart) { chart.destroy(); }
  chart = new Chart(ctx, cfg);
}

// ── Table ─────────────────────────────────────────────────────────────────────
function renderTable(rows) {
  const head = document.getElementById("table-head");
  const body = document.getElementById("table-body");
  if (!head || !body || !rows.length) return;

  const cols = Object.keys(rows[0]);
  head.innerHTML = cols.map(c => `<th>${c}</th>`).join("");
  body.innerHTML = rows.map(row =>
    `<tr>${cols.map(c => `<td>${row[c]}</td>`).join("")}</tr>`
  ).join("");
}

// ── Init ──────────────────────────────────────────────────────────────────────
function init() {
  renderChart(DATA);
  renderTable(DATA.table);

  document.getElementById("refresh-btn")?.addEventListener("click", () => {
    // Re-render with same data, or fetch fresh data here:
    // fetchData().then(d => { renderChart(d); renderTable(d.table); });
    renderChart(DATA);
    renderTable(DATA.table);
  });
}

document.addEventListener("DOMContentLoaded", init);

// ── Optional: fetch data from a backend ──────────────────────────────────────
// async function fetchData() {
//   const res = await fetch("api/data");  // relative URL — works via proxy
//   return res.json();
// }
