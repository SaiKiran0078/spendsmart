// Application shell: auth guard, sidebar, month switcher and hash-based routing.
import { ApiError, api, getToken, setToken } from "./api.js";
import { destroyCharts } from "./charts.js";
import { openExpenseForm } from "./forms.js";
import { icon } from "./icons.js";
import { render as dashboard } from "./pages/dashboard.js";
import { render as transactions } from "./pages/transactions.js";
import { render as budgets } from "./pages/budgets.js";
import { render as goals } from "./pages/goals.js";
import { render as recurring } from "./pages/recurring.js";
import { render as settings } from "./pages/settings.js";
import { bindThemeToggle } from "./theme.js";
import { $, h, loading, monthLabel, toast } from "./ui.js";

const ROUTES = {
  dashboard: { title: "Dashboard", icon: "home", render: dashboard, month: true },
  transactions: { title: "Transactions", icon: "list", render: transactions, month: true },
  budgets: { title: "Budgets", icon: "pie", render: budgets, month: true },
  goals: { title: "Savings goals", icon: "target", render: goals },
  recurring: { title: "Recurring bills", icon: "repeat", render: recurring },
  settings: { title: "Settings", icon: "sliders", render: settings },
};

const now = new Date();
const state = { user: null, month: { year: now.getFullYear(), month: now.getMonth() + 1 }, renderToken: 0 };

function currentRoute() {
  const name = location.hash.replace(/^#\/?/, "");
  return ROUTES[name] ? name : "dashboard";
}

async function renderRoute() {
  const name = currentRoute();
  const route = ROUTES[name];
  const token = ++state.renderToken;

  document.title = `${route.title} · SpendSmart`;
  $("#page-title").textContent = route.title;
  $("#month-switch").classList.toggle("hidden", !route.month);
  for (const link of document.querySelectorAll(".nav-item")) {
    link.classList.toggle("active", link.dataset.route === name);
    if (link.dataset.route === name) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
  $("#month-label").textContent = monthLabel(state.month.year, state.month.month);
  const selectedMonth = new Date(state.month.year, state.month.month - 1, 1);
  const currentMonth = new Date();
  $("#month-next").disabled = selectedMonth >= new Date(currentMonth.getFullYear(), currentMonth.getMonth(), 1);
  closeMenu();

  const view = $("#view");
  destroyCharts();
  view.replaceChildren(loading());

  const ctx = {
    view,
    get user() { return state.user; },
    month: { ...state.month },
    isCurrent: () => token === state.renderToken,
    reload: renderRoute,
    refreshUser: async () => { state.user = await api.get("/auth/me"); paintUser(); return state.user; },
  };
  try {
    await route.render(ctx);
    if (ctx.isCurrent()) view.focus({ preventScroll: true });
  } catch (err) {
    if (!ctx.isCurrent()) return;
    view.replaceChildren(h("div", { class: "card empty" },
      h("h3", {}, "Something went wrong"),
      h("p", {}, err instanceof ApiError ? err.message : "Please try again."),
      h("button", { class: "btn", type: "button", onClick: renderRoute }, "Retry")));
  }
}

function shiftMonth(delta) {
  const date = new Date(state.month.year, state.month.month - 1 + delta, 1);
  const today = new Date();
  const currentMonth = new Date(today.getFullYear(), today.getMonth(), 1);
  if (date > currentMonth) return;
  state.month = { year: date.getFullYear(), month: date.getMonth() + 1 };
  renderRoute();
}

function paintUser() {
  const { full_name: name, email } = state.user || {};
  const safeName = typeof name === "string" && name.trim() ? name.trim() : "Your account";
  $("#user-name").textContent = safeName;
  $("#user-email").textContent = typeof email === "string" ? email : "";
  $("#avatar").textContent = safeName[0].toUpperCase();
}

const openMenu = () => { $("#sidebar").classList.add("open"); $("#scrim").classList.add("show"); };
function closeMenu() { $("#sidebar").classList.remove("open"); $("#scrim").classList.remove("show"); }

function buildShell() {
  const nav = $("#side-nav");
  for (const [name, route] of Object.entries(ROUTES)) {
    nav.append(h("a", { class: "nav-item", href: `#/${name}`, dataset: { route: name } }, icon(route.icon), route.title));
  }
  $("#menu-btn").append(icon("menu"));
  $("#quick-add").append(icon("plus"), h("span", {}, "Add expense"));
  bindThemeToggle($("#theme-toggle"));

  $("#menu-btn").addEventListener("click", openMenu);
  $("#scrim").addEventListener("click", closeMenu);
  $("#month-prev").addEventListener("click", () => shiftMonth(-1));
  $("#month-next").addEventListener("click", () => shiftMonth(1));
  $("#quick-add").addEventListener("click", () => openExpenseForm({ onSaved: renderRoute }));
  $("#logout-btn").addEventListener("click", () => { setToken(null); location.replace("login.html"); });
  document.addEventListener("themechange", renderRoute); // charts read theme colours at draw time
  window.addEventListener("hashchange", renderRoute);
}

(async function start() {
  if (!getToken()) { location.replace("login.html"); return; }
  buildShell();
  try {
    state.user = await api.get("/auth/me");
  } catch {
    setToken(null);
    location.replace("login.html");
    return;
  }
  paintUser();
  try {
    const result = await api.post("/recurring/process");
    if (result && result.created > 0) toast(`Added ${result.created} recurring bill${result.created > 1 ? "s" : ""} that came due`);
  } catch { /* not critical */ }
  renderRoute();
})();


// Installable PWA shell. Authenticated API responses are deliberately never cached.
if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost")) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      // The app remains fully usable when service-worker installation is unavailable.
    });
  });
}
