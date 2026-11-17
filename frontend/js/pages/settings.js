import { ApiError, api, request, setToken } from "../api.js";
import { icon } from "../icons.js";
import { CURRENCIES, field, getCurrency, h, openModal, select, setCurrency, toast, withBusy } from "../ui.js";

export async function render(ctx) {
  const user = ctx.user;

  /* Profile */
  const nameInput = h("input", { type: "text", maxlength: 100, required: true, value: user.full_name });
  const profileError = h("p", { class: "form-error", role: "alert" });
  const profileSave = h("button", { class: "btn primary", type: "submit" }, "Save profile");
  const profileForm = h("form", { novalidate: true }, field("Full name", nameInput),
    field("Email", h("input", { type: "email", value: user.email, disabled: true })), profileError, profileSave);
  profileForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    profileError.textContent = "";
    await withBusy(profileSave, async () => {
      try { await api.put("/auth/me", { full_name: nameInput.value.trim() }); await ctx.refreshUser(); toast("Profile updated"); } catch (err) { profileError.textContent = err.message; }
    });
  });

  /* Preferences */
  const currencySelect = select(Object.entries(CURRENCIES), getCurrency());
  currencySelect.addEventListener("change", () => { setCurrency(currencySelect.value); toast("Currency updated"); ctx.reload(); });

  /* Password */
  const current = h("input", { type: "password", required: true, autocomplete: "current-password", maxlength: 72 });
  const next = h("input", { type: "password", required: true, minlength: 8, maxlength: 72, autocomplete: "new-password" });
  const confirm = h("input", { type: "password", required: true, minlength: 8, maxlength: 72, autocomplete: "new-password" });
  const passError = h("p", { class: "form-error", role: "alert" });
  const passSave = h("button", { class: "btn primary", type: "submit" }, "Change password");
  const passForm = h("form", { novalidate: true }, field("Current password", current), field("New password", next), field("Confirm new password", confirm), passError, passSave);
  passForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    passError.textContent = "";
    if (next.value.length < 8) { passError.textContent = "New password must be at least 8 characters."; return; }
    if (next.value !== confirm.value) { passError.textContent = "The new passwords don't match."; return; }
    await withBusy(passSave, async () => {
      try { await api.post("/auth/me/password", { current_password: current.value, new_password: next.value }); passForm.reset(); toast("Password changed"); } catch (err) { passError.textContent = err.message; }
    });
  });

  /* Data export */
  const exportData = async () => {
    try {
      const response = await request("/expenses/export/csv", { raw: true });
      const url = URL.createObjectURL(await response.blob());
      const link = h("a", { href: url, download: "spendsmart-expenses.csv" });
      document.body.append(link); link.click(); link.remove(); URL.revokeObjectURL(url);
    } catch (err) { toast(err.message, "error"); }
  };

  /* Delete account */
  const deleteAccount = () => openModal("Delete your account", (close) => {
    const password = h("input", { type: "password", required: true, autocomplete: "current-password", maxlength: 72 });
    const error = h("p", { class: "form-error", role: "alert" });
    const submit = h("button", { class: "btn danger solid", type: "submit" }, "Delete everything");
    const form = h("form", { novalidate: true },
      h("p", { class: "muted", style: "margin-bottom:1rem" }, "This permanently deletes your account, expenses, income, budgets, goals and recurring bills. It can't be undone."),
      field("Confirm with your password", password), error,
      h("div", { class: "modal-actions" }, h("button", { class: "btn ghost", type: "button", onClick: close }, "Cancel"), submit));
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      error.textContent = "";
      await withBusy(submit, async () => {
        try {
          await api.del("/auth/me", { password: password.value });
          setToken(null);
          location.replace("index.html");
        } catch (err) { error.textContent = err instanceof ApiError ? err.message : "Could not delete the account."; }
      });
    });
    return form;
  });

  ctx.view.replaceChildren(
    h("div", { class: "page-head" }, h("div", {}, h("h2", {}, "Settings"), h("p", {}, "Manage your profile, security and data."))),
    h("section", { class: "settings-grid" },
      h("div", { class: "stack" },
        h("article", { class: "card" }, h("h2", {}, "Profile"), profileForm),
        h("article", { class: "card" }, h("h2", {}, "Preferences"), field("Currency", currencySelect),
          h("p", { class: "muted small" }, "Changes how amounts are displayed on this device. It does not convert values."))),
      h("div", { class: "stack" },
        h("article", { class: "card" }, h("h2", {}, "Password"), passForm),
        h("article", { class: "card" }, h("h2", {}, "Your data"), h("p", { class: "muted small", style: "margin-bottom:.8rem" }, "Download all your expenses as a CSV file."),
          h("button", { class: "btn", type: "button", onClick: exportData }, icon("download"), "Export expenses")),
        h("article", { class: "card danger-zone" }, h("h2", {}, "Danger zone"),
          h("p", { class: "muted small", style: "margin-bottom:.8rem" }, "Delete your account and every record that belongs to it."),
          h("button", { class: "btn danger", type: "button", onClick: deleteAccount }, icon("trash"), "Delete account")))));
}
