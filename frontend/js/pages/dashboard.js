import { api } from "../api.js";
import { categoryDoughnut, dailyLine, trendBars } from "../charts.js";
import { openExpenseForm, openIncomeForm } from "../forms.js";
import { icon } from "../icons.js";
import { categoryPill, emptyState, fmtDate, h, money, monthLabel } from "../ui.js";

function greeting(name) {
  const hour = new Date().getHours();
  const part = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
  const firstName = typeof name === "string" && name.trim() ? name.trim().split(/\\s+/)[0] : "there";
  return `${part}, ${firstName}`;
}

function kpi(label, value, note, tone) {
  return h("article", { class: "card kpi-card" }, h("div", { class: "label" }, label), h("div", { class: "value" }, value), h("div", { class: `delta ${tone || ""}` }, note));
}

function progressBar(percent) {
  const tone = percent >= 100 ? "danger" : percent >= 80 ? "warn" : "";
  return h("div", { class: "progress", role: "progressbar", "aria-valuenow": Math.round(percent), "aria-valuemin": 0, "aria-valuemax": 100 },
    h("div", { class: tone, style: `width:${Math.min(percent, 100)}%` }));
}

export async function render(ctx) {
  const { year, month } = ctx.month;
  const [summary, trend, recurring] = await Promise.all([
    api.get("/summary", { year, month }),
    api.get("/summary/trend", { months: 6, year, month }),
    api.get("/recurring"),
  ]);
  if (!ctx.isCurrent()) return;

  const refresh = () => ctx.reload();
  const isEmpty = summary.expense_count === 0 && summary.total_income === 0;
  const change = summary.change_vs_previous_percent;

  const header = h("div", { class: "page-head" },
    h("div", {}, h("h2", {}, greeting(ctx.user.full_name)), h("p", {}, `Here's your money in ${monthLabel(year, month)}.`)),
    h("div", { class: "head-actions" },
      h("button", { class: "btn", type: "button", onClick: () => openIncomeForm({ onSaved: refresh }) }, icon("plus"), "Add income"),
      h("button", { class: "btn primary", type: "button", onClick: () => openExpenseForm({ onSaved: refresh }) }, icon("plus"), "Add expense")));

  const kpis = h("section", { class: "kpis" },
    kpi("Spent", money(summary.total_spent),
      change === null ? "No data for last month" : `${change > 0 ? "▲" : "▼"} ${Math.abs(change)}% vs last month`,
      change === null ? "" : change > 0 ? "bad" : "good"),
    kpi("Income", money(summary.total_income), summary.total_income ? "This month" : "Nothing logged yet"),
    kpi("Net savings", money(summary.net_savings),
      summary.savings_rate_percent === null ? "Add income to see your rate" : `${summary.savings_rate_percent}% savings rate`,
      summary.net_savings < 0 ? "bad" : summary.net_savings > 0 ? "good" : ""),
    kpi("Budget left", summary.monthly_budget > 0 ? money(summary.remaining) : "Not set",
      summary.monthly_budget > 0 ? `${summary.budget_used_percent}% of ${money(summary.monthly_budget)} used` : "Set one on the Budgets page",
      summary.remaining < 0 && summary.monthly_budget > 0 ? "bad" : ""));

  const trendCanvas = h("canvas", { "aria-label": "Income versus expenses for the last six months", role: "img" });
  const categoryCanvas = h("canvas", { "aria-label": "Spending by category", role: "img" });
  const dailyCanvas = h("canvas", { "aria-label": "Daily spending this month", role: "img" });

  const insights = h("article", { class: "card" }, h("h2", {}, "Insights"),
    h("ul", { class: "insights" }, summary.insights.map((tip) => h("li", {}, icon("zap"), tip))));

  const budgetCard = h("article", { class: "card" }, h("h2", {}, "Monthly budget"));
  if (summary.monthly_budget > 0) {
    budgetCard.append(
      h("div", { class: "row-between" }, h("strong", {}, `${money(summary.total_spent)} of ${money(summary.monthly_budget)}`), h("span", { class: "muted small" }, `${summary.budget_used_percent}%`)),
      progressBar(summary.budget_used_percent));
    if (summary.projected_spend !== null) {
      budgetCard.append(h("p", { class: "muted small", style: "margin-top:.7rem" }, `Projected month-end spend: ${money(summary.projected_spend)}`));
    }
  } else {
    budgetCard.append(h("p", { class: "muted" }, "Set a monthly budget to see how much you have left."), h("a", { class: "btn", href: "#/budgets", style: "margin-top:.8rem" }, "Set budget"));
  }
  if (summary.budget_alerts.length) {
    budgetCard.append(h("h2", { style: "margin-top:1.1rem" }, "Category alerts"),
      h("ul", { class: "simple-list" }, summary.budget_alerts.map((a) =>
        h("li", {}, h("span", {}, categoryPill(a.category)), h("span", { class: `badge ${a.status === "over" ? "danger" : "warn"}` }, `${a.percent_used}% used`)))));
  }

  const upcoming = recurring.filter((r) => r.active).slice(0, 4);
  const sideCard = h("article", { class: "card" }, h("h2", {}, "Upcoming bills"),
    upcoming.length
      ? h("ul", { class: "simple-list" }, upcoming.map((r) => h("li", {}, h("div", { class: "meta" }, h("strong", {}, r.title), h("small", {}, `Due ${fmtDate(r.next_due)}`)), h("span", {}, money(r.amount)))))
      : h("p", { class: "muted" }, "No recurring bills yet."),
    h("h2", { style: "margin-top:1.1rem" }, "Biggest expenses"),
    summary.top_expenses.length
      ? h("ul", { class: "simple-list" }, summary.top_expenses.map((e) => h("li", {}, h("div", { class: "meta" }, h("strong", {}, e.title), h("small", {}, fmtDate(e.spent_on))), h("span", {}, money(e.amount)))))
      : h("p", { class: "muted" }, "Nothing spent this month."));

  const dashboardSections = [
    header,
    isEmpty ? h("div", { class: "card" }, emptyState("Welcome to SpendSmart", "Add your first expense or income to see charts and insights here.",
      h("button", { class: "btn primary", type: "button", onClick: () => openExpenseForm({ onSaved: refresh }) }, "Add your first expense"))) : null,
    kpis,
    h("section", { class: "grid-2-1" },
      h("article", { class: "card" }, h("h2", {}, "Income vs expenses"), h("div", { class: "chart-box" }, trendCanvas)),
      insights),
    h("section", { class: "grid-2" },
      h("article", { class: "card" }, h("h2", {}, "Spending by category"),
        summary.by_category.length ? h("div", { class: "chart-box short" }, categoryCanvas) : h("p", { class: "muted" }, "No expenses this month yet.")),
      h("article", { class: "card" }, h("h2", {}, "Daily spending"), h("div", { class: "chart-box short" }, dailyCanvas))),
    h("section", { class: "grid-2" }, budgetCard, sideCard),
  ].filter(Boolean);
  // Native replaceChildren(null) creates a visible "null" text node; filter empty sections first.
  ctx.view.replaceChildren(...dashboardSections);

  trendBars(trendCanvas, trend, (p) => monthLabel(p.year, p.month, "short"));
  if (summary.by_category.length) categoryDoughnut(categoryCanvas, summary.by_category);
  dailyLine(dailyCanvas, summary.daily);
}
