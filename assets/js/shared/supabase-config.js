(() => {
  let client;

  window.UInvestSupabase = {
    getClient() {
      if (client) return client;
      if (!window.supabase?.createClient) {
        throw new Error("Не вдалося завантажити бібліотеку входу.");
      }
      if (!window.U_INVEST_SUPABASE_URL || !window.U_INVEST_SUPABASE_ANON_KEY) {
        throw new Error("Supabase Auth ще не налаштовано.");
      }
      client = window.supabase.createClient(
        window.U_INVEST_SUPABASE_URL,
        window.U_INVEST_SUPABASE_ANON_KEY,
        {
          auth: {
            autoRefreshToken: true,
            detectSessionInUrl: true,
            persistSession: true,
          },
        },
      );
      return client;
    },
  };
})();
