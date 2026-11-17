import { api } from "../api.js";
import { openRecurringForm } from "../forms.js";
import { icon } from "../icons.js";
import { categoryPill, confirmDialog, emptyState, fmtDate, h, money, toast } from "../ui.js";

const LABELS = { weekly: "Every week", monthly: "Every month", yearly: "Every year" };
const PER_MONTH = { weekly: 52 / 12, monthly: 1, yearly: 1 / 12 };

export async function render(ctx) {
  const items = await api.get("/recurring");
  if (!ctx.isCurrent()) return;
  const refresh = () => ctx.reload();

  const toggle = async (item) => {
    try { await api.put(`/recurring/${item.id}`, { active: !item.active }); toast(item.active ? "Paused" : "Resumed"); refresh(); } catch (err) { toast(err.message, "error"); }
  };
  const remove = async (item) => {
    if (!(await confirmDialog(`Delete "${item.title}"? Expenses already added will stay.`))) return;
    try { await api.del(`/recurring/${item.id}`); toast("Deleted"); refresh(); } catch (err) { toast(err.message, "error"); }
  };

  const monthly = items.filter((i) => i.active).reduce((sum, i) => sum + i.amount * (PER_MONTH[i.frequency] || 0), 0);
  const row = (item) => h("tr", {},
    h("td", {}, h("div", {}, item.title), item.note ? h("small", { class: "muted" }, item.note) : null),
    h("td", {}, categoryPill(item.category)),
    h("td", { class: "num" }, money(item.amount)),
    h("td", {}, LABELS[item.frequency] || item.frequency),
    h("td", {}, fmtDate(item.next_due)),
    h("td", {}, h("span", { class: `badge ${item.active ? "ok" : ""}` }, item.active ? "Active" : "Paused")),
    h("td", { class: "actions" },
      h("button", { class: "btn ghost icon sm", type: "button", "aria-label": `${item.active ? "Pause" : "Resume"} ${item.title}`, onClick: () => toggle(item) }, icon(item.active ? "pause" : "play")),
      h("button", { class: "btn ghost icon sm", type: "button", "aria-label": `Edit ${item.title}`, onClick: () => openRecurringForm({ item, onSaved: refresh }) }, icon("edit")),
      h("button", { class: "btn ghost icon sm danger", type: "button", "aria-label": `Delete ${item.title}`, onClick: () => remove(item) }, icon("trash"))));

  ctx.view.replaceChildren(
    h("div", { class: "page-head" },
      h("div", {}, h("h2", {}, "Recurring bills"), h("p", {}, "Rent, subscriptions and EMIs are added automatically when they fall due.")),
      h("button", { class: "btn primary", type: "button", onClick: () => openRecurringForm({ onSaved: refresh }) }, icon("plus"), "New recurring bill")),
    items.length
      ? h("section", { class: "card stack" },
          h("p", { class: "muted" }, `Active bills add up to about ${money(monthly)} per month.`),
          h("div", { class: "table-wrap" }, h("table", {},
            h("thead", {}, h("tr", {}, ["Bill", "Category", "Amount", "Repeats", "Next due", "Status", ""].map((t, i) => h("th", { class: i === 2 ? "num" : "" }, t)))),
            h("tbody", {}, items.map(row)))))
      : h("div", { class: "card" }, emptyState("No recurring bills", "Add things like rent or Netflix once and SpendSmart records them for you.",
          h("button", { class: "btn primary", type: "button", onClick: () => openRecurringForm({ onSaved: refresh }) }, "Add your first bill"))));
}
