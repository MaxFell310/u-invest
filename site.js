(() => {
  const toggle = document.querySelector("[data-account-toggle]");
  const menu = document.querySelector("[data-account-menu]");
  if (!toggle || !menu) return;

  const anonymousLinks = menu.querySelector("[data-anonymous-links]");
  const authenticatedLinks = menu.querySelector("[data-authenticated-links]");
  const logoutButton = menu.querySelector("[data-site-logout]");
  let supabaseClient;

  function closeMenu(restoreFocus = false) {
    menu.hidden = true;
    toggle.setAttribute("aria-expanded", "false");
    if (restoreFocus) toggle.focus();
  }

  function setAuthenticated(isAuthenticated) {
    anonymousLinks.hidden = isAuthenticated;
    authenticatedLinks.hidden = !isAuthenticated;
  }

  function visibleMenuItems() {
    return [...menu.querySelectorAll("[role='menuitem']")].filter(
      item => !item.closest("[hidden]") && item.getClientRects().length > 0,
    );
  }

  function closeMenuOnLink(event) {
    if (event.target.closest("[data-account-cta]")) {
      closeMenu();
      document
        .getElementById("app-window")
        ?.scrollIntoView({ behavior: "smooth" });
      return;
    }
    if (event.target.closest("[role='menuitem']")) closeMenu();
  }

  toggle.addEventListener("click", () => {
    const opening = menu.hidden;
    menu.hidden = !opening;
    toggle.setAttribute("aria-expanded", String(opening));
    if (opening) visibleMenuItems()[0]?.focus();
  });
  menu.addEventListener("click", closeMenuOnLink);
  document.addEventListener("pointerdown", event => {
    if (!menu.hidden && !menu.contains(event.target) && !toggle.contains(event.target)) {
      closeMenu();
    }
  });
  document.addEventListener("keydown", event => {
    if (menu.hidden) return;
    if (event.key === "Escape") {
      closeMenu(true);
      return;
    }
    const items = visibleMenuItems();
    const currentIndex = items.indexOf(document.activeElement);
    let nextIndex;
    if (event.key === "ArrowDown") {
      nextIndex = currentIndex < 0 ? 0 : (currentIndex + 1) % items.length;
    }
    if (event.key === "ArrowUp") {
      nextIndex =
        currentIndex < 0
          ? items.length - 1
          : (currentIndex - 1 + items.length) % items.length;
    }
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = items.length - 1;
    if (nextIndex !== undefined) {
      event.preventDefault();
      items[nextIndex]?.focus();
    }
  });

  async function loadExchangeRates() {
    const container = document.querySelector("[data-exchange-rates]");
    if (!container) return;
    const status = container.querySelector("[data-rates-status]");
    try {
      const base = (window.U_INVEST_API_BASE_URL || "").replace(/\/+$/, "");
      const response = await fetch(`${base}/api/exchange-rates`);
      if (!response.ok) throw new Error("Курс тимчасово недоступний.");
      const data = await response.json();
      for (const currency of ["USD", "EUR"]) {
        const row = container.querySelector(`[data-rate="${currency}"]`);
        const rate = data.rates?.[currency];
        if (!row || !rate) throw new Error("Сервер повернув неповні курси.");
        row.querySelector("[data-buy]").textContent = Number(rate.buy).toFixed(2);
        row.querySelector("[data-sale]").textContent = Number(rate.sale).toFixed(2);
        row.hidden = false;
      }
      const updated = new Date(data.updated_at);
      const updatedLabel = new Intl.DateTimeFormat("uk-UA", {
        dateStyle: "short",
        timeStyle: "short",
      }).format(updated);
      status.textContent = data.stale
        ? `Застарілі дані · оновлено ${updatedLabel}`
        : `Оновлено ${updatedLabel}`;
      status.classList.toggle("is-stale", data.stale);
    } catch (error) {
      status.textContent = "Курс тимчасово недоступний";
      container.querySelectorAll("[data-rate]").forEach(row => {
        row.hidden = true;
      });
    }
  }

  async function initializeAuth() {
    try {
      supabaseClient = window.UInvestSupabase.getClient();
      supabaseClient.auth.onAuthStateChange((_event, session) => {
        setAuthenticated(Boolean(session?.user));
      });
      const { data, error } = await supabaseClient.auth.getUser();
      setAuthenticated(!error && Boolean(data.user));
    } catch {
      setAuthenticated(false);
      const status = document.querySelector("[data-site-status]");
      if (status) {
        status.hidden = false;
        status.textContent = "Вхід тимчасово недоступний.";
      }
    }
  }

  logoutButton.addEventListener("click", async () => {
    logoutButton.disabled = true;
    try {
      const { error } = await supabaseClient.auth.signOut();
      if (error) throw error;
      setAuthenticated(false);
      closeMenu();
      window.location.assign("index.html");
    } catch {
      logoutButton.disabled = false;
      const status = document.querySelector("[data-site-status]");
      if (status) {
        status.hidden = false;
        status.textContent = "Не вдалося вийти. Спробуйте ще раз.";
      }
    }
  });

  void initializeAuth();
  void loadExchangeRates();
})();
