const adminStatus = document.querySelector("[data-admin-status]");
const loginPanel = document.querySelector("[data-admin-login]");
const dashboard = document.querySelector("[data-admin-dashboard]");
const loginForm = document.querySelector("[data-admin-login-form]");
const apiBaseUrl = (window.U_INVEST_API_BASE_URL || "").replace(/\/+$/, "");
const pageSize = 25;
let supabaseClient;
let accessToken;
let currentPage = 1;
let totalRecords = 0;
let currentFilters = {};

function showStatus(message, isError = false) {
  adminStatus.textContent = message;
  adminStatus.classList.toggle("is-error", isError);
  adminStatus.hidden = !message;
}

function interestLabel(value) {
  return { yes: "Так", maybe: "Можливо", no: "Ні" }[value] || value || "—";
}

function importanceLabel(value) {
  return (
    {
      not_important: "Зовсім не важливо",
      slightly_important: "Мало важливо",
      moderately_important: "Помірно важливо",
      very_important: "Дуже важливо",
      unsure: "Важко відповісти",
    }[value] || value || "—"
  );
}

async function apiRequest(path, options = {}) {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...options,
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${accessToken}`,
      ...options.headers,
    },
  });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch (error) {
      if (!(error instanceof SyntaxError)) throw error;
    }
    throw new Error(detail);
  }
  return response;
}

function renderStats(summary) {
  const stats = document.querySelector("[data-admin-stats]");
  const cards = [
    ["Відповідей", summary.total_submissions],
    [
      "Середня оцінка",
      summary.average_rating === null
        ? "Немає оцінок"
        : `${summary.average_rating.toFixed(2)} / 5`,
    ],
    ["Так, цікавить", summary.investment_interest.yes || 0],
    ["Можливо, цікавить", summary.investment_interest.maybe || 0],
    ["Дуже важливо: довкілля", summary.environmental.very_important || 0],
    ["Дуже важливо: соціальне", summary.social.very_important || 0],
    ["Дуже важливо: етика", summary.ethical.very_important || 0],
  ];
  stats.replaceChildren(
    ...cards.map(([label, value]) => {
      const card = document.createElement("article");
      card.className = "admin-stat";
      const title = document.createElement("span");
      title.textContent = label;
      const number = document.createElement("strong");
      number.textContent = String(value);
      card.append(title, number);
      return card;
    }),
  );
}

function renderFeedback(items) {
  const body = document.querySelector("[data-admin-feedback]");
  body.replaceChildren();
  for (const item of items) {
    const row = document.createElement("tr");
    const cells = [
      new Intl.DateTimeFormat("uk-UA", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(new Date(item.submitted_at)),
      item.rating === null ? "—" : `${item.rating} / 5`,
      interestLabel(item.investment_interest),
      item.comment || "—",
      importanceLabel(item.environmental_importance),
      importanceLabel(item.social_importance),
      importanceLabel(item.ethical_importance),
    ];
    for (const value of cells) {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    }
    body.append(row);
  }
  const pageCount = Math.max(1, Math.ceil(totalRecords / pageSize));
  document.querySelector("[data-page-indicator]").textContent =
    `Сторінка ${currentPage} з ${pageCount} · ${totalRecords} відповідей`;
  document.querySelector("[data-page-previous]").disabled = currentPage <= 1;
  document.querySelector("[data-page-next]").disabled = currentPage >= pageCount;
}

async function loadDashboard() {
  const parameters = new URLSearchParams({
    page: String(currentPage),
    page_size: String(pageSize),
  });
  for (const [key, value] of Object.entries(currentFilters)) {
    if (value) parameters.set(key, value);
  }
  try {
    const [feedbackResponse, summaryResponse] = await Promise.all([
      apiRequest(`/api/admin/feedback?${parameters.toString()}`),
      apiRequest("/api/admin/feedback/summary"),
    ]);
    const feedbackPage = await feedbackResponse.json();
    const summary = await summaryResponse.json();
    totalRecords = feedbackPage.total;
    renderStats(summary);
    renderFeedback(feedbackPage.items);
    showStatus("");
  } catch (error) {
    showStatus(error.message || "Не вдалося завантажити панель.", true);
  }
}

async function setSession(session) {
  accessToken = session?.access_token;
  loginPanel.hidden = Boolean(accessToken);
  dashboard.hidden = !accessToken;
  if (!accessToken) {
    showStatus("Увійдіть за допомогою запрошеного облікового запису.");
    return;
  }
  document.querySelector("[data-admin-identity]").textContent =
    `Ви увійшли як ${session.user.email}.`;
  await loadDashboard();
}

function configureAuth() {
  if (!apiBaseUrl) {
    showStatus("Панель не має налаштованого API URL.", true);
    return;
  }
  try {
    supabaseClient = window.UInvestSupabase.getClient();
  } catch (error) {
    showStatus(error.message || "Не вдалося налаштувати Supabase Auth.", true);
    return;
  }
  supabaseClient.auth.onAuthStateChange((_event, session) => {
    window.setTimeout(() => void setSession(session), 0);
  });
  void supabaseClient.auth.getSession().then(({ data, error }) => {
    if (error) {
      showStatus(error.message, true);
      return;
    }
    void setSession(data.session);
  });
}

loginForm.addEventListener("submit", async event => {
  event.preventDefault();
  const button = document.querySelector("[data-admin-login-button]");
  button.disabled = true;
  try {
    const email = new FormData(loginForm).get("email").toString().trim();
    const { error } = await supabaseClient.auth.signInWithOtp({
      email,
      options: {
        shouldCreateUser: false,
        emailRedirectTo: window.location.href.split("#")[0],
      },
    });
    if (error) throw error;
    showStatus("Якщо адресу запрошено, посилання для входу надіслано на пошту.");
  } catch (error) {
    showStatus(error.message || "Не вдалося надіслати посилання для входу.", true);
  } finally {
    button.disabled = false;
  }
});

document.querySelector("[data-admin-logout]").addEventListener("click", async () => {
  const { error } = await supabaseClient.auth.signOut();
  if (error) showStatus(error.message, true);
});

document.querySelector("[data-filter-submit]").addEventListener("click", () => {
  currentPage = 1;
  currentFilters = {
    q: document.querySelector("[data-filter-search]").value.trim(),
    rating: document.querySelector("[data-filter-rating]").value,
    investment_interest: document.querySelector("[data-filter-interest]").value,
  };
  void loadDashboard();
});

document.querySelector("[data-page-previous]").addEventListener("click", () => {
  if (currentPage > 1) {
    currentPage -= 1;
    void loadDashboard();
  }
});

document.querySelector("[data-page-next]").addEventListener("click", () => {
  if (currentPage * pageSize < totalRecords) {
    currentPage += 1;
    void loadDashboard();
  }
});

document.querySelector("[data-admin-export]").addEventListener("click", async () => {
  try {
    const response = await apiRequest("/api/admin/feedback/export");
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = "u-invest-feedback.csv";
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    showStatus("CSV-файл підготовлено.");
  } catch (error) {
    showStatus(error.message || "Не вдалося експортувати відповіді.", true);
  }
});

configureAuth();
