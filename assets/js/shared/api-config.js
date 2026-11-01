(() => {
  const localHosts = new Set(["localhost", "127.0.0.1", "[::1]"]);
  const isLocalDevelopment = localHosts.has(window.location.hostname);
  const siteRoot =
    document.querySelector('meta[name="u-invest-site-root"]')?.content || "./";

  window.U_INVEST_API_BASE_URL = isLocalDevelopment
    ? "http://127.0.0.1:8000"
    : "https://u-invest-fastapi.onrender.com";
  window.U_INVEST_SITE_ROOT = siteRoot;
  window.UInvestPaths = {
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
