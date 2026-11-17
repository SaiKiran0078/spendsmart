import { api } from "../api.js";
import { openLimitForm } from "../forms.js";
import { icon } from "../icons.js";
import { CATEGORIES, categoryPill, confirmDialog, h, money, monthLabel, toast } from "../ui.js";

function bar(percent) {
  const tone = percent >= 100 ? "danger" : percent >= 80 ? "warn" : "";
  return h("div", { class: "progress", role: "progressbar", "aria-valuenow": Math.round(percent), "aria-valuemin": 0, "aria-valuemax": 100 },
    h("div", { class: tone, style: `width:${Math.min(percent, 100)}%` }));
}

export async function render(ctx) {
  const { year, month } = ctx.month;
  const [statuses, summary] = await Promise.all([api.get("/budgets", { year, month }), api.get("/summary", { year, month })]);
  if (!ctx.isCurrent()) return;
  const byCategory = Object.fromEntries(statuses.map((s) => [s.category, s]));
  const total = ctx.user.monthly_budget;

  const editOverall = () => openLimitForm({
    title: "Monthly budget", label: "Total you plan to spend each month", value: total, allowZero: true,
    onSave: (value) => api.put("/auth/me/budget", { monthly_budget: value }),
    onSaved: async () => { await ctx.refreshUser(); await ctx.reload(); },
  });

  const overall = h("article", { class: "card budget-card" },
    h("div", { class: "top" }, h("h2", { style: "margin:0" }, "Overall monthly budget"),
      h("button", { class: "btn sm", type: "button", onClick: editOverall }, icon("edit"), total > 0 ? "Edit" : "Set budget")),
    total > 0
      ? [h("div", { class: "amounts" }, h("span", {}, `${money(summary.total_spent)} spent`), h("span", {}, `${money(total)} budget`)), bar(summary.budget_used_percent),
         h("p", { class: "muted small" }, summary.remaining >= 0 ? `${money(summary.remaining)} left in ${monthLabel(year, month)}` : `${money(-summary.remaining)} over budget`)]
      : h("p", { class: "muted" }, "Set a total monthly budget to track how much you have left."));

  const cards = CATEGORIES.map((category) => {
    const status = byCategory[category];
    const edit = () => openLimitForm({
      title: `${category} budget`, label: "Monthly limit", value: status?.limit_amount,
      onSave: (value) => api.put(`/budgets/${category}`, { limit_amount: value }), onSaved: ctx.reload,
    });
    const remove = async () => {
      if (!(await confirmDialog(`Remove the ${category} limit?`, { confirmText: "Remove" }))) return;
      try { await api.del(`/budgets/${category}`); toast("Limit removed"); ctx.reload(); } catch (err) { toast(err.message, "error"); }
    };
    if (!status) {
      return h("article", { class: "card budget-card" }, h("div", { class: "top" }, categoryPill(category), h("button", { class: "btn sm", type: "button", onClick: edit }, icon("plus"), "Set limit")),
        h("p", { class: "muted small" }, "No limit set."));
    }
    const tone = status.status === "over" ? "danger" : status.status === "warning" ? "warn" : "ok";
    return h("article", { class: "card budget-card" },
      h("div", { class: "top" }, categoryPill(category), h("span", { class: `badge ${tone}` }, status.status === "over" ? "Over budget" : status.percent_used >= 100 ? "Limit reached" : status.status === "warning" ? "Almost there" : `${status.percent_used}% used`)),
      h("div", { class: "amounts" }, h("span", {}, `${money(status.spent)} spent`), h("span", {}, `${money(status.limit_amount)} limit`)),
      bar(status.percent_used),
      h("div", { class: "row-between" },
        h("span", { class: "muted small" }, status.remaining >= 0 ? `${money(status.remaining)} left` : `${money(-status.remaining)} over`),
        h("span", {}, h("button", { class: "btn ghost icon sm", type: "button", "aria-label": `Edit ${category} limit`, onClick: edit }, icon("edit")),
          h("button", { class: "btn ghost icon sm danger", type: "button", "aria-label": `Remove ${category} limit`, onClick: remove }, icon("trash")))));
  });

  ctx.view.replaceChildren(
    h("div", { class: "page-head" }, h("div", {}, h("h2", {}, "Budgets"), h("p", {}, `Spending limits for ${monthLabel(year, month)}.`))),
    overall,
    h("section", { class: "grid-3" }, cards));
}
