(() => {
  const localHosts = new Set(["localhost", "127.0.0.1", "[::1]"]);
  const isLocalDevelopment = localHosts.has(window.location.hostname);
  const siteRoot =
    document.querySelector('meta[name="u-invest-site-root"]')?.content || "./";

  window.U_INVEST_API_BASE_URL = isLocalDevelopment
    ? "http://127.0.0.1:8000"
    : "https://u-invest-fastapi.onrender.com";
  window.U_INVEST_SITE_ROOT = siteRoot;
  const routes = Object.freeze({
    home: "index.html",
    about: "index.html#about",
    how: "index.html#how",
    features: "index.html#features",
    responsible: "index.html#responsible",
    feedback: "index.html#feedback",
    faq: "index.html#faq",
    start: "index.html#app-window",
    login: "pages/auth/login.html",
    register: "pages/auth/register.html",
    resetPassword: "pages/auth/reset-password.html",
    profile: "pages/profile/profile.html",
    portfolio: "pages/profile/profile.html#portfolio",
    admin: "pages/admin/admin.html",
  });
  window.UInvestPaths = {
    routes,
    href(path) {
      return new URL(`${siteRoot}${path}`, window.location.href).href;
    },
    navigate(path) {
      window.location.assign(this.href(path));
    },
    redirect(path) {
      window.location.replace(this.href(path));
    },
  };
  window.U_INVEST_SUPABASE_URL = "https://tybfamlmqipyeqouklru.supabase.co";
  window.U_INVEST_SUPABASE_ANON_KEY =
    "sb_publishable_NVK-8-CInOQ1jB3PvtNffA_9Low-ZCy";
})();
