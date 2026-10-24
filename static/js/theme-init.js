(function () {
  try {
    var stored = localStorage.getItem("leobooks-theme");
    if (stored === "light" || stored === "dark") {
      document.documentElement.setAttribute("data-bs-theme", stored);
    }
    var theme = document.documentElement.getAttribute("data-bs-theme");
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      meta.setAttribute("content", theme === "dark" ? "#141210" : "#F3ECDD");
    }
  } catch (error) {
    /* preferência local indisponível */
  }
})();
