import { api } from "../api.js";
import { openContributionForm, openGoalForm } from "../forms.js";
import { icon } from "../icons.js";
import { confirmDialog, emptyState, fmtDate, h, money, toast } from "../ui.js";

export async function render(ctx) {
  const goals = await api.get("/goals");
  if (!ctx.isCurrent()) return;
  const refresh = () => ctx.reload();

  const remove = async (goal) => {
    if (!(await confirmDialog(`Delete the goal "${goal.name}"?`))) return;
    try { await api.del(`/goals/${goal.id}`); toast("Goal deleted"); refresh(); } catch (err) { toast(err.message, "error"); }
  };

  const card = (goal) => {
    const deadline = goal.deadline
      ? goal.days_left >= 0 ? `Target ${fmtDate(goal.deadline)} · ${goal.days_left} day${goal.days_left === 1 ? "" : "s"} left` : `Target date passed (${fmtDate(goal.deadline)})`
      : "No target date";
    return h("article", { class: "card goal-card" },
      h("div", { class: "goal-top" },
        h("div", { class: `ring ${goal.is_complete ? "done" : ""}`, style: `--p:${goal.progress_percent}` }, h("span", {}, goal.is_complete ? "✓" : `${Math.round(goal.progress_percent)}%`)),
        h("div", {}, h("h3", {}, goal.name), h("p", { class: "muted small" }, `${money(goal.saved_amount)} of ${money(goal.target_amount)}`),
          goal.is_complete ? h("span", { class: "badge ok" }, "Goal reached") : null)),
      h("div", { class: "goal-meta" },
        h("span", {}, goal.is_complete ? "Nicely done!" : `${money(goal.remaining)} to go`),
        h("span", {}, deadline),
        goal.monthly_needed !== null && !goal.is_complete ? h("span", {}, `Save about ${money(goal.monthly_needed)} per month to make it`) : null),
      h("div", { class: "goal-actions" },
        h("button", { class: "btn sm primary", type: "button", onClick: () => openContributionForm({ goal, onSaved: refresh }) }, icon("plus"), "Add funds"),
        goal.saved_amount > 0 ? h("button", { class: "btn sm", type: "button", onClick: () => openContributionForm({ goal, withdraw: true, onSaved: refresh }) }, "Withdraw") : null,
        h("button", { class: "btn sm ghost", type: "button", onClick: () => openGoalForm({ goal, onSaved: refresh }) }, icon("edit"), "Edit"),
        h("button", { class: "btn sm ghost danger", type: "button", "aria-label": `Delete ${goal.name}`, onClick: () => remove(goal) }, icon("trash"))));
  };

  const newGoal = h("button", { class: "btn primary", type: "button", onClick: () => openGoalForm({ onSaved: refresh }) }, icon("plus"), "New goal");
  ctx.view.replaceChildren(
    h("div", { class: "page-head" }, h("div", {}, h("h2", {}, "Savings goals"), h("p", {}, "Save for what matters, and see exactly how much to set aside.")), newGoal),
    goals.length
      ? h("section", { class: "grid-3" }, goals.map(card))
      : h("div", { class: "card" }, emptyState("No goals yet", "Create a goal like “Emergency fund” or “New laptop” and track your progress.",
          h("button", { class: "btn primary", type: "button", onClick: () => openGoalForm({ onSaved: refresh }) }, "Create your first goal"))));
}
