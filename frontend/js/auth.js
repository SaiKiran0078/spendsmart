import { ApiError, api, getToken, request, setToken } from "./api.js";
import { icon } from "./icons.js";
import { bindThemeToggle } from "./theme.js";

const $ = (selector) => document.querySelector(selector);
let mode = "login";

bindThemeToggle($("#theme-toggle"));

for (const text of ["Monthly budget and savings-rate dashboard", "Category budgets with smart alerts", "Goals, recurring bills and CSV import"]) {
  const item = document.createElement("li");
  item.append(icon("check"), text);
  $("#auth-points").append(item);
}

function setMode(next) {
  mode = next;
  const registering = next === "register";
  $("#tab-login").setAttribute("aria-selected", String(!registering));
  $("#tab-register").setAttribute("aria-selected", String(registering));
  $("#name-field").classList.toggle("hidden", !registering);
  $("#strength").classList.toggle("hidden", !registering);
  $("#strength-label").classList.toggle("hidden", !registering);
  $("#auth-title").textContent = registering ? "Create your account" : "Welcome back";
  $("#auth-sub").textContent = registering ? "Start tracking in under a minute." : "Log in to see your dashboard.";
  $("#auth-submit").textContent = registering ? "Create account" : "Log in";
  $("#auth-password").autocomplete = registering ? "new-password" : "current-password";
  $("#auth-error").textContent = "";
  history.replaceState(null, "", registering ? "#register" : location.pathname);
}

function passwordStrength(value) {
  let score = 0;
  if (value.length >= 8) score += 1;
  if (value.length >= 12) score += 1;
  if (/[a-z]/.test(value) && /[A-Z]/.test(value)) score += 1;
  if (/\d/.test(value) && /[^A-Za-z0-9]/.test(value)) score += 1;
  return value ? Math.max(score, 1) : 0;
}

$("#auth-password").addEventListener("input", (event) => {
  const level = passwordStrength(event.target.value);
  $("#strength").dataset.level = String(level);
  $("#strength-label").textContent = ["", "Weak", "Okay", "Good", "Strong"][level];
});

$("#toggle-password").addEventListener("click", () => {
  const input = $("#auth-password");
  const show = input.type === "password";
  input.type = show ? "text" : "password";
  $("#toggle-password").textContent = show ? "Hide" : "Show";
  $("#toggle-password").setAttribute("aria-label", show ? "Hide password" : "Show password");
});

$("#tab-login").addEventListener("click", () => setMode("login"));
$("#tab-register").addEventListener("click", () => setMode("register"));

$("#auth-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const email = $("#auth-email").value.trim();
  const password = $("#auth-password").value;
  const fullName = $("#auth-name").value.trim();
  const error = $("#auth-error");
  const button = $("#auth-submit");
  error.textContent = "";

  if (!email || !password) { error.textContent = "Please enter your email and password."; return; }
  if (mode === "register" && !fullName) { error.textContent = "Please enter your name."; return; }
  if (mode === "register" && password.length < 8) { error.textContent = "Password must be at least 8 characters."; return; }

  button.disabled = true;
  try {
    if (mode === "register") {
      await request("/auth/register", { method: "POST", body: { email, full_name: fullName, password } });
    }
    const data = await request("/auth/login", { method: "POST", form: { username: email, password } });
    setToken(data.access_token);
    location.replace("app.html");
  } catch (err) {
    error.textContent = err instanceof ApiError ? err.message : "Something went wrong.";
    button.disabled = false;
  }
});

// Already signed in? Skip straight to the app.
(async function init() {
  setMode(location.hash === "#register" ? "register" : "login");
  if (!getToken()) return;
  try {
    await api.get("/auth/me");
    location.replace("app.html");
  } catch {
    setToken(null);
  }
})();
