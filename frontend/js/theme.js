import { icon } from "./icons.js";

const KEY = "spendsmart_theme";

export function currentTheme() {
  const set = document.documentElement.dataset.theme;
  if (set === "light" || set === "dark") return set;
  return matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

export function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  try { localStorage.setItem(KEY, theme); } catch { /* ignore */ }
  document.dispatchEvent(new CustomEvent("themechange", { detail: theme }));
}

/** Turns a button into a light/dark switch that shows the icon for the opposite theme. */
export function bindThemeToggle(button) {
  const paint = () => {
    button.replaceChildren(icon(currentTheme() === "dark" ? "sun" : "moon"));
    button.setAttribute("aria-label", `Switch to ${currentTheme() === "dark" ? "light" : "dark"} theme`);
  };
  button.addEventListener("click", () => {
    setTheme(currentTheme() === "dark" ? "light" : "dark");
    paint();
  });
  paint();
}
