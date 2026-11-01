(() => {
  const status = document.querySelector("[data-auth-status]");
  const form = document.querySelector("[data-auth-form]");
  const submitButton = form?.querySelector("[type='submit']");
  const recoveryForm = document.querySelector("[data-recovery-form]");
  const recoveryButton = recoveryForm?.querySelector("[type='submit']");
  const resetForm = document.querySelector("[data-reset-form]");
  const resetButton = resetForm?.querySelector("[type='submit']");
  let supabaseClient;
  let recoverySessionReady = false;

  function showStatus(message, kind = "info") {
    if (!status) return;
    status.textContent = message;
    status.dataset.kind = kind;
    status.hidden = !message;
  }

  try {
    supabaseClient = window.UInvestSupabase.getClient();
  } catch (error) {
    showStatus(error.message || "Supabase Auth тимчасово недоступний.", "error");
    [form, recoveryForm, resetForm].filter(Boolean).forEach(item => {
      item.querySelectorAll("input, button").forEach(control => {
        control.disabled = true;
      });
    });
    return;
  }

  async function isValidSession() {
    const { data, error } = await supabaseClient.auth.getUser();
    return !error && Boolean(data.user);
  }

  if (form?.dataset.authMode === "register" || form?.dataset.authMode === "login") {
    void isValidSession().then(valid => {
      if (valid) window.UInvestPaths.redirect(window.UInvestPaths.routes.profile);
    });
  }

  function friendlyAuthError(error) {
    const message = String(error?.message || "");
    if (/email rate limit exceeded|rate limit/i.test(message)) {
      return "Досягнуто ліміту листів Supabase. Зачекайте перед наступною спробою та перевірте пошту.";
    }
    if (/already registered|already exists/i.test(message)) {
      return "Акаунт із цією адресою вже існує. Спробуйте увійти.";
    }
    if (/invalid login credentials/i.test(message)) {
      return "Неправильна адреса електронної пошти або пароль.";
    }
    return message || "Не вдалося виконати запит. Спробуйте пізніше.";
  }

  form?.addEventListener("submit", async event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    submitButton.disabled = true;
    const values = Object.fromEntries(new FormData(form));
    try {
      if (form.dataset.authMode === "register") {
        const password = String(values.password || "");
        if (!/[a-z]/.test(password) || !/[A-Z]/.test(password) || !/[0-9]/.test(password)) {
          throw new Error("Пароль має містити великі й малі латинські літери та цифру.");
        }
        if (password !== values.passwordConfirmation) {
          throw new Error("Паролі не збігаються.");
        }
        const { data, error } = await supabaseClient.auth.signUp({
          email: String(values.email).trim(),
          password,
          options: {
            data: { username: String(values.username).trim() },
            emailRedirectTo: window.UInvestPaths.href(window.UInvestPaths.routes.login),
          },
        });
        if (error) throw error;
        if (data.session && await isValidSession()) {
          window.UInvestPaths.redirect(window.UInvestPaths.routes.profile);
          return;
        }
        form.hidden = true;
        showStatus("Акаунт створено. Перевірте пошту та підтвердьте адресу, щоб увійти.", "success");
        return;
      }

      const { error } = await supabaseClient.auth.signInWithPassword({
        email: String(values.email).trim(),
        password: String(values.password),
      });
      if (error) throw error;
      if (!await isValidSession()) {
        throw new Error("Не вдалося підтвердити сесію. Спробуйте увійти ще раз.");
      }
      window.UInvestPaths.redirect(window.UInvestPaths.routes.profile);
    } catch (error) {
      showStatus(friendlyAuthError(error), "error");
    } finally {
      submitButton.disabled = false;
    }
  });

  recoveryForm?.addEventListener("submit", async event => {
    event.preventDefault();
    if (!recoveryForm.reportValidity()) return;
    recoveryButton.disabled = true;
    try {
      const email = String(new FormData(recoveryForm).get("email")).trim();
      const { error } = await supabaseClient.auth.resetPasswordForEmail(email, {
        redirectTo:         window.UInvestPaths.href(window.UInvestPaths.routes.resetPassword),
      });
      if (error) throw error;
      showStatus("Якщо для цієї адреси є акаунт, надіслано інструкцію для відновлення пароля.", "success");
    } catch (error) {
      showStatus(friendlyAuthError(error), "error");
    } finally {
      recoveryButton.disabled = false;
    }
  });

  supabaseClient.auth.onAuthStateChange(event => {
    if (event === "PASSWORD_RECOVERY") {
      recoverySessionReady = true;
      if (resetForm) {
        resetForm.hidden = false;
        showStatus("Введіть новий пароль для акаунта.");
      }
    }
  });

  if (resetForm) {
    void isValidSession().then(valid => {
      recoverySessionReady = valid;
      if (valid) {
        resetForm.hidden = false;
        showStatus("Введіть новий пароль для акаунта.");
      } else {
        showStatus("Посилання недійсне або застаріло. Запросіть відновлення пароля ще раз.", "error");
      }
    });
    resetForm.addEventListener("submit", async event => {
      event.preventDefault();
      if (!recoverySessionReady || !resetForm.reportValidity()) return;
      resetButton.disabled = true;
      const values = Object.fromEntries(new FormData(resetForm));
      try {
        if (values.password !== values.passwordConfirmation) {
          throw new Error("Паролі не збігаються.");
        }
        const password = String(values.password);
        if (!/[a-z]/.test(password) || !/[A-Z]/.test(password) || !/[0-9]/.test(password)) {
          throw new Error("Пароль має містити великі й малі латинські літери та цифру.");
        }
        const { error } = await supabaseClient.auth.updateUser({ password });
        if (error) throw error;
        showStatus("Пароль оновлено. Тепер можна увійти.", "success");
        resetForm.hidden = true;
      } catch (error) {
        showStatus(friendlyAuthError(error), "error");
      } finally {
        resetButton.disabled = false;
      }
    });
  }
})();
