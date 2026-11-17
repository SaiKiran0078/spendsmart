// Runs before first paint (loaded in <head>) so the saved theme never flashes.
(function () {
  try {
    var saved = localStorage.getItem("spendsmart_theme");
    if (saved === "light" || saved === "dark") document.documentElement.dataset.theme = saved;
  } catch (e) { /* storage unavailable: fall back to the OS theme */ }
})();
