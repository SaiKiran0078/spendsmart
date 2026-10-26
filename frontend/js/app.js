"use strict";

const API = "/api";
const CURRENCY = "₹";
const CATEGORIES = [
  "Food", "Transport", "Rent", "Utilities", "Shopping",
  "Health", "Entertainment", "Education", "Other",
];

let token = localStorage.getItem("spendsmart_token");
let editingId = null;
let chart = null;
let searchTimer = null;

const $ = (selector) => document.querySelector(selector);
const money = (n) => `${CURRENCY}${Number(n).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
const todayISO = () => new Date().toLocaleDateString("en-CA"); // YYYY-MM-DD in local time

/* ---------- API helper ---------- */
async function api(path, { method = "GET", body, form, raw = false } = {}) {
  const headers = {};
  let payload;
  if (token) headers.Authorization = `Bearer ${token}`;
  if (form) {
    payload = new URLSearchParams(form);
  } else if (body) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const res = await fetch(API + path, { method, headers, body: payload });

  if (res.status === 401 && token) {
    logout();
    throw new Error("Session expired. Please log in again.");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = Array.isArray(err.detail) ? err.detail.map((d) => d.msg).join(", ") : err.detail;
    throw new Error(detail || "Something went wrong");
  }
  if (raw) return res;
  return res.status === 204 ? null : res.json();
}

function toast(message) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2200);
}

/* ---------- Auth ---------- */
let mode = "login";

function setMode(next) {
  mode = next;
  const isRegister = next === "register";
  $("#tab-login").classList.toggle("active", !isRegister);
  $("#tab-register").classList.toggle("active", isRegister);
  $("#name-field").classList.toggle("hidden", !isRegister);
  $("#auth-name").required = isRegister;
  $("#auth-submit").textContent = isRegister ? "Create account" : "Log in";
  $("#auth-password").autocomplete = isRegister ? "new-password" : "current-password";
  $("#auth-error").textContent = "";
}

async function handleAuth(event) {
  event.preventDefault();
  const email = $("#auth-email").value.trim();
  const password = $("#auth-password").value;
  $("#auth-error").textContent = "";
  try {
    if (mode === "register") {
      await api("/auth/register", {
        method: "POST",
        body: { email, password, full_name: $("#auth-name").value.trim() },
      });
    }
    const data = await api("/auth/login", { method: "POST", form: { username: email, password } });
    token = data.access_token;
    localStorage.setItem("spendsmart_token", token);
    $("#auth-form").reset();
    await showApp();
  } catch (err) {
    $("#auth-error").textContent = err.message;
  }
}

function logout() {
  token = null;
  localStorage.removeItem("spendsmart_token");
  $("#app-view").classList.add("hidden");
  $("#auth-view").classList.remove("hidden");
}

/* ---------- Dashboard ---------- */
function monthBounds() {
  const [year, month] = $("#month-picker").value.split("-").map(Number);
  const pad = (n) => String(n).padStart(2, "0");
  const lastDay = new Date(year, month, 0).getDate();
  return { year, month, start: `${year}-${pad(month)}-01`, end: `${year}-${pad(month)}-${pad(lastDay)}` };
}

async function loadSummary() {
  const { year, month } = monthBounds();
  const s = await api(`/summary?year=${year}&month=${month}`);

  $("#stat-spent").textContent = money(s.total_spent);
  $("#stat-budget").textContent = s.monthly_budget > 0 ? money(s.monthly_budget) : "Not set";
  $("#stat-remaining").textContent = s.monthly_budget > 0 ? money(s.remaining) : "–";
  $("#stat-count").textContent = s.expense_count;

  const bar = $("#progress-bar");
  bar.style.width = `${Math.min(s.budget_used_percent, 100)}%`;
  bar.style.background =
    s.budget_used_percent >= 100 ? "var(--danger)" : s.budget_used_percent >= 80 ? "var(--warn)" : "var(--accent)";
  $("#progress-text").textContent =
    s.monthly_budget > 0 ? `${s.budget_used_percent}% of your budget used` : "Set a monthly budget to track progress.";

  drawChart(s.by_category);
}

function drawChart(items) {
  $("#chart-empty").classList.toggle("hidden", items.length > 0);
  $("#category-chart").classList.toggle("hidden", items.length === 0);
  if (chart) chart.destroy();
  if (!items.length || typeof Chart === "undefined") return;
  chart = new Chart($("#category-chart"), {
    type: "doughnut",
    data: {
      labels: items.map((i) => i.category),
      datasets: [{
        data: items.map((i) => i.total),
        backgroundColor: ["#2dd4a7", "#60a5fa", "#f472b6", "#fbbf24", "#a78bfa", "#fb7185", "#34d399", "#f97316", "#94a3b8"],
        borderWidth: 0,
      }],
    },
    options: { maintainAspectRatio: false, plugins: { legend: { position: "right", labels: { color: "#8da0c3" } } } },
  });
}

async function loadExpenses() {
  const { start, end } = monthBounds();
  const params = new URLSearchParams({ start_date: start, end_date: end });
  const category = $("#filter-category").value;
  const search = $("#search-input").value.trim();
  if (category) params.set("category", category);
  if (search) params.set("search", search);

  const expenses = await api(`/expenses?${params}`);
  const body = $("#expense-rows");
  body.replaceChildren();
  $("#table-empty").classList.toggle("hidden", expenses.length > 0);

  for (const e of expenses) {
    const tr = document.createElement("tr");
    const cell = (text, className) => {
      const td = document.createElement("td");
      td.textContent = text; // textContent (never innerHTML) prevents XSS
      if (className) td.className = className;
      tr.appendChild(td);
      return td;
    };
    cell(e.spent_on);
    cell(e.title);
    const catCell = cell("");
    const pill = document.createElement("span");
    pill.className = "pill";
    pill.textContent = e.category;
    catCell.appendChild(pill);
    cell(money(e.amount), "num");

    const actions = cell("", "actions");
    const editBtn = Object.assign(document.createElement("button"), { className: "btn small", textContent: "Edit" });
    const delBtn = Object.assign(document.createElement("button"), { className: "btn small danger", textContent: "Delete" });
    editBtn.addEventListener("click", () => startEdit(e));
    delBtn.addEventListener("click", () => removeExpense(e.id));
    actions.append(editBtn, " ", delBtn);
    body.appendChild(tr);
  }
}

async function refresh() {
  try {
    await Promise.all([loadSummary(), loadExpenses()]);
  } catch (err) {
    toast(err.message);
  }
}

/* ---------- Expense form ---------- */
function resetForm() {
  editingId = null;
  $("#expense-form").reset();
  $("#e-date").value = todayISO();
  $("#form-title").textContent = "Add expense";
  $("#e-submit").textContent = "Add expense";
  $("#e-cancel").classList.add("hidden");
  $("#form-error").textContent = "";
}

function startEdit(expense) {
  editingId = expense.id;
  $("#e-title").value = expense.title;
  $("#e-amount").value = expense.amount;
  $("#e-date").value = expense.spent_on;
  $("#e-category").value = expense.category;
  $("#e-note").value = expense.note || "";
  $("#form-title").textContent = "Edit expense";
  $("#e-submit").textContent = "Save changes";
  $("#e-cancel").classList.remove("hidden");
  $("#expense-form").scrollIntoView({ behavior: "smooth", block: "center" });
}

async function submitExpense(event) {
  event.preventDefault();
  const body = {
    title: $("#e-title").value.trim(),
    amount: Number($("#e-amount").value),
    spent_on: $("#e-date").value,
    category: $("#e-category").value,
    note: $("#e-note").value.trim() || null,
  };
  try {
    if (editingId) {
      await api(`/expenses/${editingId}`, { method: "PUT", body });
      toast("Expense updated");
    } else {
      await api("/expenses", { method: "POST", body });
      toast("Expense added");
    }
    resetForm();
    await refresh();
  } catch (err) {
    $("#form-error").textContent = err.message;
  }
}

async function removeExpense(id) {
  if (!confirm("Delete this expense?")) return;
  try {
    await api(`/expenses/${id}`, { method: "DELETE" });
    toast("Expense deleted");
    await refresh();
  } catch (err) {
    toast(err.message);
  }
}

async function saveBudget(event) {
  event.preventDefault();
  const value = Number($("#budget-input").value);
  try {
    await api("/auth/me/budget", { method: "PUT", body: { monthly_budget: value } });
    toast("Budget saved");
    await loadSummary();
  } catch (err) {
    toast(err.message);
  }
}

async function exportCsv() {
  try {
    const res = await api("/expenses/export/csv", { raw: true });
    const url = URL.createObjectURL(await res.blob());
    const link = Object.assign(document.createElement("a"), { href: url, download: "expenses.csv" });
    link.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    toast(err.message);
  }
}

/* ---------- Boot ---------- */
async function showApp() {
  try {
    const me = await api("/auth/me");
    $("#user-name").textContent = me.full_name;
    $("#budget-input").value = me.monthly_budget || "";
  } catch {
    return; // api() already logged the user out on 401
  }
  $("#auth-view").classList.add("hidden");
  $("#app-view").classList.remove("hidden");
  await refresh();
}

function init() {
  for (const select of [$("#e-category"), $("#filter-category")]) {
    if (select.id === "filter-category") select.add(new Option("All categories", ""));
    CATEGORIES.forEach((c) => select.add(new Option(c, c)));
  }
  $("#month-picker").value = todayISO().slice(0, 7);
  $("#e-date").value = todayISO();

  $("#tab-login").addEventListener("click", () => setMode("login"));
  $("#tab-register").addEventListener("click", () => setMode("register"));
  $("#auth-form").addEventListener("submit", handleAuth);
  $("#logout-btn").addEventListener("click", logout);
  $("#expense-form").addEventListener("submit", submitExpense);
  $("#e-cancel").addEventListener("click", resetForm);
  $("#budget-form").addEventListener("submit", saveBudget);
  $("#export-btn").addEventListener("click", exportCsv);
  $("#month-picker").addEventListener("change", refresh);
  $("#filter-category").addEventListener("change", loadExpenses);
  $("#search-input").addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(loadExpenses, 300); // debounce typing
  });

  if (token) showApp();
  else $("#auth-view").classList.remove("hidden");
}

document.addEventListener("DOMContentLoaded", init);
