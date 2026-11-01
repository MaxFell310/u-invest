(() => {
  const sitePath = path => window.UInvestPaths.href(path);
  const links = window.UInvestPaths.routes;

  async function loadHeader() {
    const placeholder = document.querySelector("[data-site-header]");
    if (!placeholder) return;
    const response = await fetch(sitePath("assets/components/header.html"));
    if (!response.ok) {
      throw new Error(`Не вдалося завантажити спільну навігацію (${response.status}).`);
    }
    const template = document.createElement("template");
    template.innerHTML = await response.text();
    const header = template.content.querySelector("[data-shared-header]");
    if (!header) throw new Error("Спільний компонент навігації пошкоджений.");
    header.querySelector("[data-brand-icon]").src = sitePath("logo/logo.jpg");
    placeholder.replaceWith(header);
    document.querySelectorAll("[data-site-link]").forEach(link => {
      const path = links[link.dataset.siteLink];
      if (path) link.href = sitePath(path);
    });
    await initializeHeader(header);
  }

  function initializeHeader(header) {
    return new Promise(resolve => {
      const menu = header.querySelector("[data-account-menu]");
      const toggle = header.querySelector("[data-account-toggle]");
      const anonymousLinks = header.querySelector("[data-anonymous-links]");
      const authenticatedLinks = header.querySelector(
        "[data-authenticated-links]",
      );
      const logoutButton = header.querySelector("[data-site-logout]");
      let supabaseClient;

      function setAuthenticated(isAuthenticated) {
        anonymousLinks.hidden = isAuthenticated;
        authenticatedLinks.hidden = !isAuthenticated;
      }

      function closeMenu(restoreFocus = false) {
        menu.hidden = true;
        toggle.setAttribute("aria-expanded", "false");
        if (restoreFocus) toggle.focus();
      }

      function visibleMenuItems() {
        return [...menu.querySelectorAll("[role='menuitem']")].filter(
          item => !item.closest("[hidden]") && item.getClientRects().length > 0,
        );
      }

      toggle.addEventListener("click", () => {
        const opening = menu.hidden;
        menu.hidden = !opening;
        toggle.setAttribute("aria-expanded", String(opening));
        if (opening) visibleMenuItems()[0]?.focus();
      });
      menu.addEventListener("click", event => {
        if (event.target.closest("[role='menuitem']")) closeMenu();
      });
      document.addEventListener("pointerdown", event => {
        if (
          !menu.hidden &&
          !menu.contains(event.target) &&
          !toggle.contains(event.target)
        ) {
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

      logoutButton.addEventListener("click", async () => {
        logoutButton.disabled = true;
        try {
          const { error } = await supabaseClient.auth.signOut();
          if (error) throw error;
          setAuthenticated(false);
          closeMenu();
          window.UInvestPaths.navigate("index.html");
        } catch {
          logoutButton.disabled = false;
          showHeaderStatus(header, "Не вдалося вийти. Спробуйте ще раз.");
        }
      });

      void initializeAuth();

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
          showHeaderStatus(header, "Статус входу тимчасово недоступний.");
        } finally {
          header.hidden = false;
          resolve();
        }
      }
    }).then(() => loadExchangeRates());
  }

  function showHeaderStatus(header, message) {
    const status = header.querySelector("[data-rates-status]");
    if (status) {
      status.textContent = message;
      status.dataset.kind = "error";
    }
  }

  async function loadExchangeRates() {
    const container = document.querySelector("[data-exchange-rates]");
    if (!container) return;
    const status = container.querySelector("[data-rates-status]");
    try {
      const apiBase = (window.U_INVEST_API_BASE_URL || "").replace(/\/+$/, "");
      const response = await fetch(`${apiBase}/api/exchange-rates`);
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
      const updatedLabel = new Intl.DateTimeFormat("uk-UA", {
        dateStyle: "short",
        timeStyle: "short",
      }).format(new Date(data.updated_at));
      status.textContent = data.stale
        ? `Застарілі · ${updatedLabel}`
        : `Оновлено ${updatedLabel}`;
      status.classList.toggle("is-stale", data.stale);
    } catch {
      status.textContent = "Курс тимчасово недоступний";
      container.querySelectorAll("[data-rate]").forEach(row => {
        row.hidden = true;
      });
    }
  }

  void loadHeader().catch(error => {
    const placeholder = document.querySelector("[data-site-header]");
    if (placeholder) {
      placeholder.textContent = error.message || "Навігація тимчасово недоступна.";
      placeholder.classList.add("header-load-error");
    }
  });
})();
