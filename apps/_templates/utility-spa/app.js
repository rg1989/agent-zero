// app.js — utility-spa template
//
// This sample implements a text transformer tool.
// Replace the transform functions and button wiring with your own logic.
//
// Pattern: input → process → output
//   1. Read from #tool-input
//   2. Apply a transform function
//   3. Write result to #tool-output

// ── DOM references ────────────────────────────────────────────────────────────
const inputEl  = document.getElementById("tool-input");
const outputEl = document.getElementById("tool-output");

// ── Helper: set output ────────────────────────────────────────────────────────
function setOutput(text) {
  outputEl.textContent = text;
}

function getInput() {
  return inputEl.value;
}

// ── Transform functions ───────────────────────────────────────────────────────
// Replace these with your own tool logic.

function toUpperCase(text) {
  return text.toUpperCase();
}

function toLowerCase(text) {
  return text.toLowerCase();
}

function toTitleCase(text) {
  return text.replace(/\w\S*/g, word =>
    word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
  );
}

function reverseText(text) {
  return text.split("").reverse().join("");
}

function countChars(text) {
  const chars    = text.length;
  const words    = text.trim() ? text.trim().split(/\s+/).length : 0;
  const lines    = text ? text.split("\n").length : 0;
  return `Characters: ${chars}\nWords: ${words}\nLines: ${lines}`;
}

// ── Button wiring ─────────────────────────────────────────────────────────────
document.getElementById("btn-upper").addEventListener("click", () => {
  setOutput(toUpperCase(getInput()));
});

document.getElementById("btn-lower").addEventListener("click", () => {
  setOutput(toLowerCase(getInput()));
});

document.getElementById("btn-title").addEventListener("click", () => {
  setOutput(toTitleCase(getInput()));
});

document.getElementById("btn-reverse").addEventListener("click", () => {
  setOutput(reverseText(getInput()));
});

document.getElementById("btn-count").addEventListener("click", () => {
  setOutput(countChars(getInput()));
});

document.getElementById("btn-clear").addEventListener("click", () => {
  inputEl.value = "";
  outputEl.innerHTML = '<span class="output-placeholder">Result will appear here...</span>';
});

// ── Copy output ───────────────────────────────────────────────────────────────
document.getElementById("btn-copy").addEventListener("click", () => {
  const text = outputEl.textContent;
  if (!text || outputEl.querySelector(".output-placeholder")) return;
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.getElementById("btn-copy");
    const orig = btn.textContent;
    btn.textContent = "Copied!";
    setTimeout(() => { btn.textContent = orig; }, 1200);
  });
});
