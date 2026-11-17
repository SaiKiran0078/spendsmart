import { api, request } from "../api.js";
import { openExpenseForm, openIncomeForm } from "../forms.js";
import { icon } from "../icons.js";
import { CATEGORIES, categoryPill, confirmDialog, emptyState, fmtDate, h, money, monthBounds, monthLabel, openModal, select, toast } from "../ui.js";

const PAGE_SIZE = 50;

export async function render(ctx) {
  let tab = "expenses";
  let scope = "month";
  let search = "";
  let category = "";
  let items = [];
  let hasMore = false;
  let timer = null;

  const listBox = h("div", {});
  const summaryLine = h("p", { class: "muted small" });
  const loadMore = h("button", { class: "btn", type: "button", onClick: () => load(false) }, "Load more");
  const fileInput = h("input", { type: "file", accept: ".csv,text/csv", class: "hidden", "aria-label": "Choose CSV file" });

  const tabExpenses = h("button", { type: "button", role: "tab", onClick: () => switchTab("expenses") }, "Expenses");
  const tabIncome = h("button", { type: "button", role: "tab", onClick: () => switchTab("income") }, "Income");
  const searchInput = h("input", { type: "search", placeholder: "Search…", "aria-label": "Search", onInput: (e) => { search = e.target.value.trim(); clearTimeout(timer); timer = setTimeout(() => load(true), 300); } });
  const categorySelect = select([["", "All categories"], ...CATEGORIES.map((c) => [c, c])], "");
  categorySelect.setAttribute("aria-label", "Filter by category");
  categorySelect.addEventListener("change", () => { category = categorySelect.value; load(true); });
  const scopeSelect = select([["month", `Only ${monthLabel(ctx.month.year, ctx.month.month)}`], ["all", "All time"]], "month");
  scopeSelect.setAttribute("aria-label", "Date range");
  scopeSelect.addEventListener("change", () => { scope = scopeSelect.value; load(true); });

  const importBtn = h("button", { class: "btn", type: "button", onClick: () => fileInput.click() }, icon("upload"), "Import CSV");
  const exportBtn = h("button", { class: "btn", type: "button", onClick: exportCsv }, icon("download"), "Export CSV");
  const addBtn = h("button", { class: "btn primary", type: "button", onClick: () => (tab === "expenses" ? openExpenseForm : openIncomeForm)({ onSaved: () => load(true) }) }, icon("plus"), "Add");

  fileInput.addEventListener("change", async () => {
    const file = fileInput.files[0];
    fileInput.value = "";
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    try {
      const result = await request("/expenses/import/csv", { method: "POST", formData });
      toast(`Imported ${result.imported} expense${result.imported === 1 ? "" : "s"}${result.skipped ? `, skipped ${result.skipped}` : ""}`);
      if (result.errors.length) showImportErrors(result);
      load(true);
    } catch (err) {
      toast(err.message, "error");
    }
  });

  async function exportCsv() {
    try {
      const response = await request("/expenses/export/csv", { raw: true });
      const url = URL.createObjectURL(await response.blob());
      const link = h("a", { href: url, download: "spendsmart-expenses.csv" });
      document.body.append(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      toast(err.message, "error");
    }
  }

  function showImportErrors(result) {
    openModal("Some rows were skipped", (close) => h("div", {},
      h("p", { class: "muted" }, `${result.imported} imported, ${result.skipped} skipped.`),
      h("ul", { class: "simple-list" }, result.errors.map((e) => h("li", {}, e))),
      h("div", { class: "modal-actions" }, h("button", { class: "btn primary", type: "button", onClick: close }, "OK"))));
  }

  function switchTab(next) {
    tab = next;
    category = "";
    categorySelect.value = "";
    load(true);
  }

  function paintChrome() {
    tabExpenses.setAttribute("aria-selected", String(tab === "expenses"));
    tabIncome.setAttribute("aria-selected", String(tab === "income"));
    categorySelect.classList.toggle("hidden", tab !== "expenses");
    importBtn.classList.toggle("hidden", tab !== "expenses");
    exportBtn.classList.toggle("hidden", tab !== "expenses");
    addBtn.lastChild.textContent = tab === "expenses" ? "Add expense" : "Add income";
  }

  async function removeItem(item) {
    const label = tab === "expenses" ? item.title : item.source;
    if (!(await confirmDialog(`Delete "${label}"? This can't be undone.`))) return;
    try {
      await api.del(`/${tab}/${item.id}`);
      toast("Deleted");
      load(true);
    } catch (err) {
      toast(err.message, "error");
    }
  }

  function row(item) {
    const isExpense = tab === "expenses";
    const name = isExpense ? item.title : item.source;
    const date = isExpense ? item.spent_on : item.received_on;
    return h("tr", {},
      h("td", {}, fmtDate(date)),
      h("td", {}, h("div", {}, name), item.note ? h("small", { class: "muted" }, item.note) : null),
      isExpense ? h("td", {}, categoryPill(item.category)) : null,
      h("td", { class: "num" }, (isExpense ? "−" : "+") + money(item.amount)),
      h("td", { class: "actions" },
        h("button", { class: "btn ghost icon sm", type: "button", "aria-label": `Edit ${name}`, onClick: () => (isExpense ? openExpenseForm : openIncomeForm)({ [isExpense ? "expense" : "income"]: item, onSaved: () => load(true) }) }, icon("edit")),
        h("button", { class: "btn ghost icon sm danger", type: "button", "aria-label": `Delete ${name}`, onClick: () => removeItem(item) }, icon("trash"))));
  }

  function paint() {
    paintChrome();
    if (!items.length) {
      listBox.replaceChildren(emptyState("Nothing here yet", tab === "expenses" ? "Add an expense or import a CSV to get started." : "Log your salary or other income to track your savings rate."));
      summaryLine.textContent = "";
      return;
    }
    const total = items.reduce((sum, item) => sum + item.amount, 0);
    summaryLine.textContent = `Showing ${items.length} item${items.length === 1 ? "" : "s"} · total ${money(total)}`;
    listBox.replaceChildren(h("div", { class: "table-wrap" }, h("table", {},
      h("thead", {}, h("tr", {}, h("th", {}, "Date"), h("th", {}, tab === "expenses" ? "Title" : "Source"), tab === "expenses" ? h("th", {}, "Category") : null, h("th", { class: "num" }, "Amount"), h("th", {}, ""))),
      h("tbody", {}, items.map(row)))));
  }

  async function load(reset) {
    const params = { search, limit: PAGE_SIZE, skip: reset ? 0 : items.length };
    if (tab === "expenses" && category) params.category = category;
    if (scope === "month") Object.assign(params, { start_date: monthBounds(ctx.month.year, ctx.month.month).start, end_date: monthBounds(ctx.month.year, ctx.month.month).end });
    try {
      const page = await api.get(`/${tab}`, params);
      if (!ctx.isCurrent()) return;
      items = reset ? page : items.concat(page);
      hasMore = page.length === PAGE_SIZE;
      loadMore.classList.toggle("hidden", !hasMore);
      paint();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  ctx.view.replaceChildren(
    h("div", { class: "page-head" },
      h("div", {}, h("h2", {}, "Transactions"), h("p", {}, "Everything you've spent and earned.")),
      h("div", { class: "head-actions" }, importBtn, exportBtn, addBtn)),
    h("section", { class: "card stack" },
      h("div", { class: "row-between" }, h("div", { class: "segmented", role: "tablist" }, tabExpenses, tabIncome),
        h("div", { class: "toolbar" }, searchInput, categorySelect, scopeSelect)),
      listBox, summaryLine, h("div", { style: "text-align:center" }, loadMore), fileInput));
  await load(true);
}
