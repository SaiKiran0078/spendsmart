// Reusable dialogs for creating / editing records. Each calls onSaved() after a successful save.
import { ApiError, api } from "./api.js";
import { CATEGORIES, field, h, openModal, select, todayISO, toast, withBusy } from "./ui.js";

const FREQUENCIES = [["weekly", "Every week"], ["monthly", "Every month"], ["yearly", "Every year"]];

/** Generic form dialog: `fields` is an array of label/control pairs, `save` performs the request. */
function formDialog({ title, fields, submitText, save, onSaved }) {
  openModal(title, (close) => {
    const error = h("p", { class: "form-error", role: "alert" });
    const submit = h("button", { class: "btn primary", type: "submit" }, submitText);
    const form = h("form", { novalidate: true }, ...fields, error,
      h("div", { class: "modal-actions" }, h("button", { class: "btn ghost", type: "button", onClick: close }, "Cancel"), submit));
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      error.textContent = "";
      if (!form.checkValidity()) { form.reportValidity(); return; }
      await withBusy(submit, async () => {
        try {
          await save();
          close();
          if (onSaved) await onSaved();
        } catch (err) {
          error.textContent = err instanceof ApiError ? err.message : "Could not save. Please try again.";
        }
      });
    });
    queueMicrotask(() => form.querySelector("input, select")?.focus());
    return form;
  });
}

const textInput = (value = "", extra = {}) => h("input", { type: "text", maxlength: 100, value, required: true, ...extra });
const amountInput = (value = "") => h("input", { type: "number", min: "0.01", step: "0.01", required: true, inputmode: "decimal", value: value === "" ? "" : String(value) });
const dateInput = (value) => h("input", { type: "date", required: true, value });
const noteInput = (value = "") => h("input", { type: "text", maxlength: 255, value: value || "", placeholder: "Optional" });

export function openExpenseForm({ expense, onSaved }) {
  const title = textInput(expense?.title, { placeholder: "e.g. Groceries" });
  const amount = amountInput(expense?.amount);
  const date = dateInput(expense?.spent_on || todayISO());
  const category = select(CATEGORIES, expense?.category || "Food");
  const note = noteInput(expense?.note);
  formDialog({
    title: expense ? "Edit expense" : "Add expense",
    submitText: expense ? "Save changes" : "Add expense",
    fields: [field("Title", title), h("div", { class: "form-grid" }, field("Amount", amount), field("Date", date)), field("Category", category), field("Note", note)],
    save: () => {
      const body = { title: title.value.trim(), amount: Number(amount.value), spent_on: date.value, category: category.value, note: note.value.trim() || null };
      return expense ? api.put(`/expenses/${expense.id}`, body) : api.post("/expenses", body);
    },
    onSaved: async () => { toast(expense ? "Expense updated" : "Expense added"); if (onSaved) await onSaved(); },
  });
}

export function openIncomeForm({ income, onSaved }) {
  const source = textInput(income?.source, { placeholder: "e.g. Salary" });
  const amount = amountInput(income?.amount);
  const date = dateInput(income?.received_on || todayISO());
  const note = noteInput(income?.note);
  formDialog({
    title: income ? "Edit income" : "Add income",
    submitText: income ? "Save changes" : "Add income",
    fields: [field("Source", source), h("div", { class: "form-grid" }, field("Amount", amount), field("Date", date)), field("Note", note)],
    save: () => {
      const body = { source: source.value.trim(), amount: Number(amount.value), received_on: date.value, note: note.value.trim() || null };
      return income ? api.put(`/income/${income.id}`, body) : api.post("/income", body);
    },
    onSaved: async () => { toast(income ? "Income updated" : "Income added"); if (onSaved) await onSaved(); },
  });
}

export function openGoalForm({ goal, onSaved }) {
  const name = textInput(goal?.name, { placeholder: "e.g. Emergency fund" });
  const target = amountInput(goal?.target_amount);
  const saved = h("input", { type: "number", min: "0", step: "0.01", value: "0" });
  const deadline = h("input", { type: "date", value: goal?.deadline || "" });
  const fields = [field("Goal name", name), field("Target amount", target)];
  if (!goal) fields.push(field("Already saved (optional)", saved));
  fields.push(field("Target date (optional)", deadline));
  formDialog({
    title: goal ? "Edit goal" : "New savings goal",
    submitText: goal ? "Save changes" : "Create goal",
    fields,
    save: () => goal
      ? api.put(`/goals/${goal.id}`, { name: name.value.trim(), target_amount: Number(target.value), deadline: deadline.value || null })
      : api.post("/goals", { name: name.value.trim(), target_amount: Number(target.value), saved_amount: Number(saved.value || 0), deadline: deadline.value || null }),
    onSaved: async () => { toast(goal ? "Goal updated" : "Goal created"); if (onSaved) await onSaved(); },
  });
}

export function openContributionForm({ goal, withdraw = false, onSaved }) {
  const amount = amountInput();
  formDialog({
    title: `${withdraw ? "Withdraw from" : "Add funds to"} ${goal.name}`,
    submitText: withdraw ? "Withdraw" : "Add funds",
    fields: [field("Amount", amount)],
    save: () => api.post(`/goals/${goal.id}/contribute`, { amount: (withdraw ? -1 : 1) * Number(amount.value) }),
    onSaved: async () => { toast(withdraw ? "Withdrawn" : "Funds added"); if (onSaved) await onSaved(); },
  });
}

export function openRecurringForm({ item, onSaved }) {
  const title = textInput(item?.title, { placeholder: "e.g. Netflix" });
  const amount = amountInput(item?.amount);
  const category = select(CATEGORIES, item?.category || "Utilities");
  const frequency = select(FREQUENCIES, item?.frequency || "monthly");
  const start = dateInput(item?.next_due || todayISO());
  const note = noteInput(item?.note);
  formDialog({
    title: item ? "Edit recurring bill" : "New recurring bill",
    submitText: item ? "Save changes" : "Create",
    fields: [
      field("Title", title),
      h("div", { class: "form-grid" }, field("Amount", amount), field("Category", category)),
      h("div", { class: "form-grid" }, field("Repeats", frequency), field(item ? "Next due" : "First due date", start)),
      field("Note", note),
    ],
    save: () => {
      const common = { title: title.value.trim(), amount: Number(amount.value), category: category.value, frequency: frequency.value, note: note.value.trim() || null };
      return item ? api.put(`/recurring/${item.id}`, { ...common, next_due: start.value }) : api.post("/recurring", { ...common, start_date: start.value });
    },
    onSaved: async () => { toast(item ? "Bill updated" : "Recurring bill created"); if (onSaved) await onSaved(); },
  });
}

/** A one-field dialog for money limits (monthly budget, category limit). */
export function openLimitForm({ title, label, value, allowZero = false, onSave, onSaved }) {
  const amount = h("input", { type: "number", min: allowZero ? "0" : "0.01", step: "0.01", required: true, inputmode: "decimal", value: value ? String(value) : "" });
  formDialog({
    title,
    submitText: "Save",
    fields: [field(label, amount)],
    save: () => onSave(Number(amount.value)),
    onSaved: async () => { toast("Saved"); if (onSaved) await onSaved(); },
  });
}
