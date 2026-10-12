// Only an explicitly selected appearance is remembered for this browser tab.
(() => {
  let selected;
  try {
    selected = sessionStorage.getItem("anbar-theme");
  } catch {
    /* Storage may be disabled. */
  }
  document.documentElement.dataset.theme =
    selected === "dark" ? "dark" : "light";
})();
