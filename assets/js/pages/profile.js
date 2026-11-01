(() => {
  const apiBase = (window.U_INVEST_API_BASE_URL || "").replace(/\/+$/, "");
  const status = document.querySelector("[data-profile-status]");
  const content = document.querySelector("[data-profile-content]");
  let client;
  let accessToken;

  function showStatus(message, kind = "info") {
    status.textContent = message;
    status.dataset.kind = kind;
    status.hidden = !message;
  }

  try {
    client = window.UInvestSupabase.getClient();
  } catch (error) {
    showStatus(error.message || "Supabase Auth тимчасово недоступний.", "error");
    return;
  }

  function money(value) {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
    }).format(Number(value));
  }

  function date(value) {
    return new Intl.DateTimeFormat("uk-UA", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  }

  async function api(path, options = {}) {
    const response = await fetch(`${apiBase}${path}`, {
      ...options,
      headers: {
        Authorization: `Bearer ${accessToken}`,
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...options.headers,
      },
    });
    const body = await response.json().catch(() => ({}));
    if (response.status === 401) {
      await client.auth.signOut();
      window.UInvestPaths.redirect("pages/auth/login.html");
      throw new Error("Сесію завершено. Увійдіть знову.");
    }
    if (!response.ok) {
      throw new Error(typeof body.detail === "string" ? body.detail : `Помилка сервера (${response.status}).`);
    }
    return body;
  }

  async function loadPortfolio() {
    const [portfolio, transactions] = await Promise.all([
      api("/api/portfolio"),
      api("/api/portfolio/transactions"),
    ]);
    document.querySelector("[data-balance]").textContent = money(portfolio.balance);
    document.querySelector("[data-portfolio-value]").textContent = money(portfolio.portfolio_value);
    document.querySelector("[data-account-value]").textContent = money(portfolio.account_value);
    renderPositions(portfolio.positions);
    renderTransactions(transactions);
  }

  function renderPositions(positions) {
    const body = document.querySelector("[data-position-rows]");
    body.replaceChildren();
    document.querySelector("[data-position-empty]").hidden = positions.length > 0;
    for (const position of positions) {
      const row = document.createElement("tr");
      for (const value of [
        position.ticker,
        position.company,
        `${Number(position.quantity).toFixed(6).replace(/0+$/, "").replace(/\.$/, "")}`,
        money(position.average_price),
        money(position.invested_amount),
      ]) {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.append(cell);
      }
      body.append(row);
    }
  }

  function renderTransactions(transactions) {
    const list = document.querySelector("[data-transactions]");
    list.replaceChildren();
    document.querySelector("[data-transactions-empty]").hidden = transactions.length > 0;
    const labels = { deposit: "Поповнення демобалансу", buy: "Демо-купівля", sell: "Демо-продаж" };
    for (const transaction of transactions) {
      const item = document.createElement("li");
      const description = document.createElement("span");
      description.textContent = [
        labels[transaction.transaction_type],
        transaction.ticker || "",
        transaction.quantity ? `${transaction.quantity} шт.` : "",
      ].filter(Boolean).join(" · ");
      const detail = document.createElement("small");
      detail.textContent = `${money(transaction.amount)} · ${date(transaction.created_at)}`;
      item.append(description, detail);
      list.append(item);
    }
  }

  document.querySelector("[data-deposit-form]").addEventListener("submit", async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector("[type='submit']");
    if (!form.reportValidity()) return;
    button.disabled = true;
    try {
      const amount = new FormData(form).get("amount");
      await api("/api/portfolio/demo-deposits", {
        method: "POST",
        body: JSON.stringify({ request_id: crypto.randomUUID(), amount }),
      });
      form.reset();
      showStatus("Демо-баланс поповнено. Це не платіж і кошти не списувалися.", "success");
      await loadPortfolio();
    } catch (error) {
      showStatus(error.message, "error");
    } finally {
      button.disabled = false;
    }
  });

  document.querySelector("[data-trade-form]").addEventListener("submit", async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector("[type='submit']");
    if (!form.reportValidity()) return;
    button.disabled = true;
    try {
      const values = Object.fromEntries(new FormData(form));
      const ticker = String(values.ticker).trim().toUpperCase();
      await api("/api/portfolio/trades", {
        method: "POST",
        body: JSON.stringify({
          request_id: crypto.randomUUID(),
          side: values.side,
          ticker,
          company: String(values.company).trim(),
          quantity: values.quantity,
          unit_price: values.unit_price,
        }),
      });
      form.reset();
      showStatus("Віртуальну операцію записано. Це не реальна угода та не актуальне котирування.", "success");
      await loadPortfolio();
    } catch (error) {
      showStatus(error.message, "error");
    } finally {
      button.disabled = false;
    }
  });

  document.querySelector("[data-profile-logout]").addEventListener("click", async event => {
    event.currentTarget.disabled = true;
    const { error } = await client.auth.signOut();
    if (error) {
      event.currentTarget.disabled = false;
      showStatus("Не вдалося вийти. Спробуйте ще раз.", "error");
      return;
    }
    window.UInvestPaths.navigate("index.html");
  });

  client.auth.onAuthStateChange((_event, session) => {
    if (!session) window.UInvestPaths.redirect("pages/auth/login.html");
    if (session) accessToken = session.access_token;
  });

  async function initialize() {
    try {
      const { data, error } = await client.auth.getSession();
      if (error || !data.session) {
        window.UInvestPaths.redirect("pages/auth/login.html");
        return;
      }
      const { data: userData, error: userError } = await client.auth.getUser();
      if (userError || !userData.user) {
        await client.auth.signOut();
        window.UInvestPaths.redirect("pages/auth/login.html");
        return;
      }
      accessToken = data.session.access_token;
      const user = userData.user;
      const metadata = user.user_metadata || {};
      document.querySelector("[data-user-name]").textContent =
        metadata.username || metadata.full_name || "Інвестор";
      document.querySelector("[data-user-email]").textContent = user.email || "—";
      document.querySelector("[data-user-created]").textContent =
        user.created_at ? new Intl.DateTimeFormat("uk-UA", { dateStyle: "medium" }).format(new Date(user.created_at)) : "—";
      await api("/api/profile");
      await loadPortfolio();
      status.hidden = true;
      content.hidden = false;
    } catch (error) {
      showStatus(error.message || "Не вдалося завантажити профіль.", "error");
    }
  }

  void initialize();
})();
