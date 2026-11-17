// DOM helpers, formatting, toasts and dialogs shared by every page.
// Text is always inserted with textContent / text nodes (never innerHTML) to prevent XSS.
import { icon } from "./icons.js";

export const $ = (selector, root = document) => root.querySelector(selector);

/** Create an element: h("button", { class: "btn", onClick: fn }, "Label", childNode) */
export function h(tag, props = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(props || {})) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "class") el.className = value;
    else if (key === "dataset") Object.assign(el.dataset, value);
    else if (key.startsWith("on") && typeof value === "function") el.addEventListener(key.slice(2).toLowerCase(), value);
    else if (key === "value" || key === "checked" || key === "disabled" || key === "htmlFor") el[key] = value;
    else el.setAttribute(key, value === true ? "" : value);
  }
  appendAll(el, children);
  return el;
}

export function appendAll(parent, children) {
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    // Nullable API fields must never leak into the interface as literal "null".
    if (typeof child === "string" && /^(?:null|undefined)$/i.test(child.trim())) continue;
    parent.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
}

/* ---------------- Formatting ---------------- */
const CURRENCY_KEY = "spendsmart_currency";
export const CURRENCIES = { INR: "₹ Indian Rupee (INR)", USD: "$ US Dollar (USD)", EUR: "€ Euro (EUR)", GBP: "£ Pound Sterling (GBP)" };

export function getCurrency() {
  try {
    const saved = localStorage.getItem(CURRENCY_KEY);
    return saved && CURRENCIES[saved] ? saved : "INR";
  } catch { return "INR"; }
}

export function setCurrency(code) {
  try { localStorage.setItem(CURRENCY_KEY, code); } catch { /* ignore */ }
}

export function money(value, { compact = false } = {}) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "–";
  const number = Number(value);
  const currency = getCurrency();
  return new Intl.NumberFormat(currency === "INR" ? "en-IN" : "en-US", {
    style: "currency",
    currency,
    notation: compact ? "compact" : "standard",
    minimumFractionDigits: Number.isInteger(number) || compact ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(number);
}

const pad = (n) => String(n).padStart(2, "0");
export const todayISO = () => {
  const now = new Date();
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
};
export const parseISO = (iso) => new Date(`${iso}T00:00:00`);
export const fmtDate = (iso) => parseISO(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
export const monthLabel = (year, month, style = "long") =>
  new Date(year, month - 1, 1).toLocaleDateString(undefined, { month: style, year: "numeric" });

export function monthBounds(year, month) {
  const last = new Date(year, month, 0).getDate();
  return { start: `${year}-${pad(month)}-01`, end: `${year}-${pad(month)}-${pad(last)}` };
}

/* ---------------- Categories ---------------- */
export const CATEGORIES = ["Food", "Transport", "Rent", "Utilities", "Shopping", "Health", "Entertainment", "Education", "Other"];
export const CATEGORY_COLORS = {
  Food: "#2dd4a7", Transport: "#60a5fa", Rent: "#a78bfa", Utilities: "#fbbf24", Shopping: "#f472b6",
  Health: "#fb7185", Entertainment: "#f97316", Education: "#22d3ee", Other: "#94a3b8",
};

export function categoryPill(category) {
  return h("span", { class: "pill" }, h("i", { class: "dot", style: `background:${CATEGORY_COLORS[category] || "#94a3b8"}` }), category);
}

/* ---------------- Feedback ---------------- */
export function toast(message, kind = "info") {
  let stack = $(".toast-stack");
  if (!stack) {
    stack = h("div", { class: "toast-stack", "aria-live": "polite" });
    document.body.append(stack);
  }
  const node = h("div", { class: `toast ${kind === "error" ? "error" : ""}`, role: kind === "error" ? "alert" : "status" }, message);
  stack.append(node);
  setTimeout(() => node.remove(), kind === "error" ? 5000 : 2800);
}

export function openModal(title, build, { onClose } = {}) {
  const dialog = h("dialog", { class: "modal" });
  const close = () => { if (dialog.open) dialog.close(); };
  dialog.append(
    h("div", { class: "modal-head" }, h("h2", {}, title),
      h("button", { class: "btn ghost icon", type: "button", "aria-label": "Close", onClick: close }, icon("x"))),
    h("div", { class: "modal-body" }, build(close)),
  );
  dialog.addEventListener("close", () => { dialog.remove(); if (onClose) onClose(); });
  dialog.addEventListener("click", (event) => { if (event.target === dialog) close(); });
  document.body.append(dialog);
  dialog.showModal();
  return { close };
}

export function confirmDialog(message, { title = "Are you sure?", confirmText = "Delete", danger = true } = {}) {
  return new Promise((resolve) => {
    openModal(title, (close) =>
      h("div", {},
        h("p", { class: "muted" }, message),
        h("div", { class: "modal-actions" },
          h("button", { class: "btn ghost", type: "button", onClick: close }, "Cancel"),
          h("button", { class: `btn ${danger ? "danger solid" : "primary"}`, type: "button", onClick: () => { resolve(true); close(); } }, confirmText),
        ),
      ), { onClose: () => resolve(false) });
  });
}

/** Disable a button while an async action runs. */
export async function withBusy(button, action) {
  button.disabled = true;
  try { return await action(); } finally { button.disabled = false; }
}

/* ---------------- Form helpers ---------------- */
export const field = (label, control) => h("label", { class: "field" }, label, control);

export function select(options, value) {
  const el = h("select", {});
  for (const option of options) {
    const [val, text] = Array.isArray(option) ? option : [option, option];
    el.append(h("option", { value: val }, text));
  }
  if (value !== undefined) el.value = value;
  return el;
}

export const emptyState = (title, text, action) =>
  h("div", { class: "empty" }, h("h3", {}, title), h("p", {}, text), action);

export const loading = () => h("div", { class: "loading" }, h("div", { class: "spinner", role: "status", "aria-label": "Loading" }));
