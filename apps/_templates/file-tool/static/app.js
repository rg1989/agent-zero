// app.js — file-tool template
// Handles drag-and-drop upload, file listing, download, delete, and conversion.

// ── Conversion options per extension ──────────────────────────────────────────
const CONVERT_OPTIONS = {
  txt:  [{ value: "json", label: "→ JSON" }, { value: "uppercase", label: "→ Uppercase" }],
  csv:  [{ value: "json", label: "→ JSON" }],
  json: [{ value: "csv",  label: "→ CSV"  }],
};

// ── File icon helper ───────────────────────────────────────────────────────────
function getFileIcon(ext) {
  const e = (ext || "").toLowerCase();
  if (["txt", "md", "csv", "pdf"].includes(e))               return "📄";
  if (["py", "js", "ts", "html", "css", "json"].includes(e)) return "💻";
  if (["png", "jpg", "jpeg", "gif", "svg"].includes(e))      return "🖼";
  if (["zip", "tar", "gz", "rar"].includes(e))               return "📦";
  return "📁";
}

// ── Toast helper ───────────────────────────────────────────────────────────────
function showToast(message, type = "success") {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.3s";
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// ── Upload function ────────────────────────────────────────────────────────────
async function uploadFiles(fileList) {
  if (!fileList || fileList.length === 0) return;

  const progress    = document.getElementById("upload-progress");
  const progressBar = document.getElementById("progress-bar");
  const progressMsg = document.getElementById("upload-filename");

  // Show progress indicator
  if (progress) {
    progress.style.display = "block";
    progressBar.style.width = "30%";
    progressMsg.textContent = `Uploading ${fileList.length} file(s)…`;
  }

  const formData = new FormData();
  for (const file of fileList) {
    formData.append("files", file);
  }

  try {
    if (progressBar) progressBar.style.width = "70%";
    const res  = await fetch("api/upload", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || "Upload failed", "error");
    } else {
      const count = data.uploaded ? data.uploaded.length : 0;
      showToast(`${count} file(s) uploaded`, "success");
      loadFiles();
    }
  } catch (err) {
    showToast("Upload error: " + err.message, "error");
  } finally {
    if (progress) {
      progressBar.style.width = "100%";
      setTimeout(() => { progress.style.display = "none"; progressBar.style.width = "0%"; }, 400);
    }
    // Reset file input so same file can be re-uploaded
    const input = document.getElementById("file-input");
    if (input) input.value = "";
  }
}

// ── Delete function ────────────────────────────────────────────────────────────
async function deleteFile(name) {
  if (!confirm(`Delete "${name}"?`)) return;
  try {
    const res  = await fetch(`api/files/${encodeURIComponent(name)}`, { method: "DELETE" });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || "Delete failed", "error");
    } else {
      showToast(`Deleted ${name}`, "success");
      loadFiles();
    }
  } catch (err) {
    showToast("Delete error: " + err.message, "error");
  }
}

// ── Convert function ───────────────────────────────────────────────────────────
async function convertFile(name, format) {
  try {
    const res  = await fetch(`api/convert/${encodeURIComponent(name)}`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ format }),
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || "Conversion failed", "error");
    } else {
      showToast(`Converted to ${format}: ${data.name}`, "success");
      loadFiles();
    }
  } catch (err) {
    showToast("Conversion error: " + err.message, "error");
  }
}

// ── Render file list ───────────────────────────────────────────────────────────
function renderFileList(files) {
  const container = document.getElementById("file-list");
  if (!container) return;

  if (!files || files.length === 0) {
    container.innerHTML = '<div class="empty-state">No files uploaded yet.</div>';
    return;
  }

  container.innerHTML = files.map(f => {
    const icon    = getFileIcon(f.ext);
    const opts    = CONVERT_OPTIONS[f.ext] || [];
    const canConvert = opts.length > 0;

    const convertHTML = canConvert
      ? `<select class="convert-select" data-name="${escHtml(f.name)}" title="Choose conversion">
           <option value="">Convert…</option>
           ${opts.map(o => `<option value="${o.value}">${o.label}</option>`).join("")}
         </select>`
      : "";

    return `
      <div class="file-card">
        <div class="file-icon">${icon}</div>
        <div class="file-name" title="${escHtml(f.name)}">${escHtml(f.name)}</div>
        <div class="file-meta">
          <span>${escHtml(f.size_human)}</span>
          <span>${escHtml(f.ext.toUpperCase() || "—")}</span>
          <span>${formatDate(f.uploaded_at)}</span>
        </div>
        <div class="file-actions">
          <a class="btn btn-sm btn-green" href="api/download/${encodeURIComponent(f.name)}" download="${escHtml(f.name)}">Download</a>
          ${convertHTML}
          <button class="btn btn-sm btn-red btn-icon" data-name="${escHtml(f.name)}" data-action="delete" title="Delete">✕</button>
        </div>
      </div>`;
  }).join("");

  // Wire delete buttons
  container.querySelectorAll("[data-action='delete']").forEach(btn => {
    btn.addEventListener("click", () => deleteFile(btn.dataset.name));
  });

  // Wire convert selects
  container.querySelectorAll(".convert-select").forEach(sel => {
    sel.addEventListener("change", () => {
      const fmt = sel.value;
      if (!fmt) return;
      sel.value = "";  // reset after selection
      convertFile(sel.dataset.name, fmt);
    });
  });
}

// ── Load files ─────────────────────────────────────────────────────────────────
async function loadFiles() {
  try {
    const res   = await fetch("api/files");
    const files = await res.json();
    renderFileList(files);
  } catch (err) {
    showToast("Failed to load files: " + err.message, "error");
  }
}

// ── Utilities ──────────────────────────────────────────────────────────────────
function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatDate(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch { return iso; }
}

// ── DOMContentLoaded ───────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const dropzone  = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");

  if (dropzone && fileInput) {
    // Click / keyboard to open file picker
    dropzone.addEventListener("click",   () => fileInput.click());
    dropzone.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") fileInput.click(); });

    // Drag events
    dropzone.addEventListener("dragover",  e => { e.preventDefault(); dropzone.classList.add("dragover"); });
    dropzone.addEventListener("dragenter", e => { e.preventDefault(); dropzone.classList.add("dragover"); });
    dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
    dropzone.addEventListener("drop",      e => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
      uploadFiles(e.dataTransfer.files);
    });

    // File input change
    fileInput.addEventListener("change", () => uploadFiles(fileInput.files));
  }

  // Load initial file list
  loadFiles();
});
