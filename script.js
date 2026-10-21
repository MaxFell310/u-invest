const body = document.body;
const menuToggle = document.querySelector(".nav-toggle");
const navLinks = document.querySelectorAll(".main-nav a");
const faqItems = document.querySelectorAll(".faq-item");
const revealItems = document.querySelectorAll(".reveal");
const modal = document.getElementById("demo-modal");
const modalTriggers = document.querySelectorAll("[data-open-modal]");
const modalCloseButtons = document.querySelectorAll("[data-close-modal]");
const fractionPicker = document.querySelector("[data-share-price]");

if (fractionPicker) {
  const fractionSelect = fractionPicker.querySelector("[data-fraction-select]");
  const fractionRange = fractionPicker.querySelector("[data-fraction-range]");
  const fractionOutput = fractionPicker.querySelector("[data-fraction-output]");
  const fractionTotal = fractionPicker.querySelector("[data-fraction-total]");
  const sharePrice = Number(fractionPicker.dataset.sharePrice);

  
  const updateFraction = value => {
    const fraction = Number(value);
    fractionSelect.value = fraction
      .toFixed(2)
      .replace(/0+$/, "")
      .replace(/\.$/, "");
    fractionRange.value = String(fraction);
    fractionOutput.textContent = `${fraction.toFixed(2)} акції`;
    fractionTotal.textContent = `₴ ${(sharePrice * fraction).toFixed(2)}`;
  };

  fractionSelect?.addEventListener("change", event => {
    updateFraction(event.target.value);
  });

  fractionRange?.addEventListener("input", event => {
    updateFraction(event.target.value);
  });
}

if (menuToggle) {
  menuToggle.addEventListener("click", () => {
    const expanded = menuToggle.getAttribute("aria-expanded") === "true";
    menuToggle.setAttribute("aria-expanded", String(!expanded));
    body.classList.toggle("menu-open");
  });
}

navLinks.forEach(link => {
  link.addEventListener("click", () => {
    body.classList.remove("menu-open");
    menuToggle?.setAttribute("aria-expanded", "false");
  });
});

faqItems.forEach(item => {
  const btn = item.querySelector(".faq-question");
  const answer = item.querySelector(".faq-answer");

  if (btn && answer) {
    btn.addEventListener("click", () => {
      const isActive = item.classList.contains("active");

      faqItems.forEach(faq => {
        faq.classList.remove("active");
        faq
          .querySelector(".faq-question")
          ?.setAttribute("aria-expanded", "false");
      });

      if (!isActive) {
        item.classList.add("active");
        btn.setAttribute("aria-expanded", "true");
      }
    });
  }
});

const observer = new IntersectionObserver(
  entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add("visible");
        observer.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.14 },
);

revealItems.forEach(element => observer.observe(element));

function openModal() {
  if (!modal) return;
  modal.classList.add("is-open");
  modal.setAttribute("aria-hidden", "false");
}

function closeModal() {
  if (!modal) return;
  modal.classList.remove("is-open");
  modal.setAttribute("aria-hidden", "true");
}

modalTriggers.forEach(trigger => {
  trigger.addEventListener("click", openModal);
});

modalCloseButtons.forEach(button => {
  button.addEventListener("click", closeModal);
});

document.addEventListener("keydown", event => {
  if (event.key === "Escape" && modal?.classList.contains("is-open")) {
    closeModal();
  }
});

const feedbackStatus = document.querySelector("[data-feedback-status]");
const ratingSummary = document.querySelector("[data-rating-summary]");
const ratingStars = document.querySelector("[data-rating-stars]");
const experienceStars = document.querySelector("[data-experience-stars]");
const reactionsElement = document.querySelector("[data-reactions]");
const pollElement = document.querySelector("[data-poll]");
const commentForm = document.querySelector("[data-comment-form]");
const commentList = document.querySelector("[data-comment-list]");
const feedbackForm = document.querySelector("[data-feedback-form]");
const feedbackStorageKeys = {
  ratings: "click-feedback-ratings-v1",
  reactions: "click-feedback-reactions-v1",
  votes: "click-feedback-poll-votes-v1",
  comments: "click-feedback-comments-v1",
  submissions: "click-feedback-submissions-v1",
  owner: "click-feedback-owner-v1",
};
const poll = {
  id: "click-feature-priority-v1",
  question: "Яка можливість CLICK для вас найважливіша?",
  multiple: false,
  ended: false,
  options: [
    { id: "small-investments", label: "Інвестування з невеликих сум" },
    { id: "clear-interface", label: "Зрозумілий інтерфейс" },
    { id: "asset-choice", label: "Вибір різних активів" },
  ],
};

let ownerId = "";
let ratings = [];
let reactions = [];
let pollVotes = [];
let comments = [];
let submissions = [];
let feedbackStorageReady = true;
let experienceRating = 0;
let editingCommentId = null;

function showFeedbackStatus(message, isError = false) {
  if (!feedbackStatus) return;
  feedbackStatus.textContent = message;
  feedbackStatus.classList.toggle("is-error", isError);
}

function readFeedbackRecords(key) {
  const stored = localStorage.getItem(key);
  if (stored === null) return [];
  const records = JSON.parse(stored);
  if (!Array.isArray(records)) {
    throw new Error("Некоректний формат даних зворотного зв’язку.");
  }
  return records;
}

function createOwnerId() {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID();
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

try {
  ownerId = localStorage.getItem(feedbackStorageKeys.owner) || createOwnerId();
  localStorage.setItem(feedbackStorageKeys.owner, ownerId);
  ratings = readFeedbackRecords(feedbackStorageKeys.ratings);
  reactions = readFeedbackRecords(feedbackStorageKeys.reactions);
  pollVotes = readFeedbackRecords(feedbackStorageKeys.votes);
  comments = readFeedbackRecords(feedbackStorageKeys.comments);
  submissions = readFeedbackRecords(feedbackStorageKeys.submissions);
} catch {
  feedbackStorageReady = false;
  showFeedbackStatus(
    "Сховище браузера недоступне або містить пошкоджені дані. Перевірте налаштування браузера; взаємодія зі зворотним зв’язком тимчасово недоступна.",
    true,
  );
}

function ensureFeedbackStorage() {
  if (!feedbackStorageReady) {
    throw new Error("Сховище зворотного зв’язку недоступне.");
  }
}

function saveFeedbackRecords(key, records) {
  ensureFeedbackStorage();
  localStorage.setItem(key, JSON.stringify(records));
}

function handleFeedbackAction(action, successMessage) {
  try {
    ensureFeedbackStorage();
    action();
    showFeedbackStatus(successMessage);
  } catch {
    showFeedbackStatus(
      "Не вдалося зберегти дані в цьому браузері. Перевірте доступне місце та налаштування сховища.",
      true,
    );
  }
}

function updateStarButtons(container, value) {
  container?.querySelectorAll("[data-rating-value]").forEach(button => {
    const selected = Number(button.dataset.ratingValue) <= value;
    button.classList.toggle("is-selected", selected);
    button.textContent = selected ? "★" : "☆";
    button.setAttribute("aria-pressed", String(Number(button.dataset.ratingValue) === value));
  });
}

function addStarPicker(container, onSelect, currentValue = 0) {
  if (!container) return;
  updateStarButtons(container, currentValue);
  container.querySelectorAll("[data-rating-value]").forEach(button => {
    button.addEventListener("click", () => {
      const selected = Number(button.dataset.ratingValue);
      onSelect(selected);
    });
  });
}

function validRatings() {
  return ratings.filter(
    rating =>
      rating &&
      typeof rating.ownerId === "string" &&
      Number.isInteger(rating.value) &&
      rating.value >= 1 &&
      rating.value <= 5,
  );
}

function renderRating() {
  const allRatings = validRatings();
  const mine = allRatings.find(rating => rating.ownerId === ownerId);
  const average = allRatings.length
    ? allRatings.reduce((sum, rating) => sum + rating.value, 0) / allRatings.length
    : 0;

  if (ratingSummary) {
    ratingSummary.textContent = allRatings.length
      ? `Середня оцінка ${average.toFixed(1)} з 5 · ${allRatings.length} ${
          allRatings.length === 1 ? "оцінка" : "оцінок"
        }`
      : "Ще немає оцінок";
  }
  updateStarButtons(ratingStars, mine?.value || 0);
}

function validPollVotes() {
  const knownOptions = new Set(poll.options.map(option => option.id));
  const seenOwners = new Set();
  return pollVotes.filter(vote => {
    if (
      !vote ||
      typeof vote.ownerId !== "string" ||
      !Array.isArray(vote.choices) ||
      seenOwners.has(vote.ownerId)
    ) {
      return false;
    }
    const choices = vote.choices.filter(choice => knownOptions.has(choice));
    const validChoiceCount = poll.multiple
      ? choices.length > 0
      : choices.length === 1;
    if (!validChoiceCount) return false;
    seenOwners.add(vote.ownerId);
    return true;
  });
}

function createPollOption(option, hasVoted) {
  const label = document.createElement("label");
  label.className = "poll-option";
  const input = document.createElement("input");
  input.type = poll.multiple ? "checkbox" : "radio";
  input.name = "poll-choice";
  input.value = option.id;
  input.disabled = hasVoted || poll.ended;
  const text = document.createElement("span");
  text.textContent = option.label;
  label.append(input, text);
  return label;
}

function renderPoll() {
  if (!pollElement) return;
  const question = pollElement.querySelector("[data-poll-question]");
  const status = pollElement.querySelector("[data-poll-status]");
  const options = pollElement.querySelector("[data-poll-options]");
  const form = pollElement.querySelector("[data-poll-form]");
  const results = pollElement.querySelector("[data-poll-results]");
  const count = pollElement.querySelector("[data-poll-count]");
  const votes = validPollVotes();
  const myVote = votes.find(vote => vote.ownerId === ownerId);
  const showResults = Boolean(myVote) || poll.ended;

  question.textContent = poll.question;
  status.textContent = poll.ended ? "Завершене" : "Активне";
  status.classList.toggle("is-closed", poll.ended);
  options.replaceChildren(...poll.options.map(option => createPollOption(option, showResults)));
  form.hidden = showResults;
  results.hidden = !showResults;
  results.replaceChildren();

  if (showResults) {
    poll.options.forEach(option => {
      const optionVotes = votes.filter(vote => vote.choices.includes(option.id)).length;
      const percentage = votes.length
        ? Math.round((optionVotes / votes.length) * 100)
        : 0;
      const result = document.createElement("div");
      const label = document.createElement("div");
      label.className = "poll-result-label";
      const optionName = document.createElement("span");
      optionName.textContent = option.label;
      const total = document.createElement("span");
      total.textContent = `${optionVotes} · ${percentage}%`;
      const track = document.createElement("div");
      track.className = "poll-result-track";
      track.setAttribute("aria-label", `${optionVotes} голосів, ${percentage}%`);
      const bar = document.createElement("div");
      bar.className = "poll-result-bar";
      bar.style.width = `${percentage}%`;
      track.append(bar);
      label.append(optionName, total);
      result.append(label, track);
      results.append(result);
    });
  }

  count.textContent = `${votes.length} ${
    votes.length === 1 ? "голос" : "голосів"
  } · результати збережені лише в цьому браузері`;
}

function renderReactions() {
  if (!reactionsElement) return;
  const mine = reactions.find(reaction => reaction.ownerId === ownerId);
  reactionsElement.querySelectorAll("[data-reaction]").forEach(button => {
    const type = button.dataset.reaction;
    const total = reactions.filter(reaction => reaction?.value === type).length;
    button.querySelector("span").textContent = String(total);
    button.setAttribute("aria-pressed", String(mine?.value === type));
  });
}

function createElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function renderComments() {
  if (!commentList) return;
  commentList.replaceChildren();
  const orderedComments = comments
    .filter(
      comment =>
        comment &&
        typeof comment.id === "string" &&
        typeof comment.message === "string" &&
        typeof comment.createdAt === "string",
    )
    .sort((first, second) => second.createdAt.localeCompare(first.createdAt));

  if (!orderedComments.length) {
    commentList.append(
      createElement("p", "comment-empty", "Коментарів поки немає. Будьте першими!"),
    );
    return;
  }

  orderedComments.forEach(comment => {
    const article = createElement("article", "comment-item");
    const meta = createElement("div", "comment-meta");
    meta.append(
      createElement("span", "comment-author", comment.author || "Анонім"),
      createElement("time", "", formatCommentDate(comment.createdAt)),
    );
    article.append(meta);

    if (editingCommentId === comment.id && comment.ownerId === ownerId) {
      renderCommentEditor(article, comment);
    } else {
      article.append(createElement("p", "comment-message", comment.message));
      if (comment.ownerId === ownerId) {
        const actions = createElement("div", "comment-actions");
        const edit = createElement("button", "", "Редагувати");
        edit.type = "button";
        edit.addEventListener("click", () => {
          editingCommentId = comment.id;
          renderComments();
        });
        const remove = createElement("button", "", "Видалити");
        remove.type = "button";
        remove.addEventListener("click", () => {
          if (!window.confirm("Видалити цей коментар?")) return;
          handleFeedbackAction(() => {
            const updated = comments.filter(item => item.id !== comment.id);
            saveFeedbackRecords(feedbackStorageKeys.comments, updated);
            comments = updated;
            renderComments();
          }, "Коментар видалено.");
        });
        actions.append(edit, remove);
        article.append(actions);
      }
    }
    commentList.append(article);
  });
}

function formatCommentDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Дата невідома"
    : new Intl.DateTimeFormat("uk-UA", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(date);
}

function renderCommentEditor(article, comment) {
  const form = createElement("form", "comment-edit-form");
  const textarea = createElement("textarea");
  textarea.name = "message";
  textarea.rows = 3;
  textarea.minLength = 2;
  textarea.maxLength = 1000;
  textarea.required = true;
  textarea.setAttribute("aria-label", "Редагувати коментар");
  textarea.value = comment.message;
  const actions = createElement("div", "comment-actions");
  const save = createElement("button", "", "Зберегти");
  save.type = "submit";
  const cancel = createElement("button", "", "Скасувати");
  cancel.type = "button";
  cancel.addEventListener("click", () => {
    editingCommentId = null;
    renderComments();
  });
  actions.append(save, cancel);
  form.append(textarea, actions);
  form.addEventListener("submit", event => {
    event.preventDefault();
    const message = textarea.value.trim();
    if (message.length < 2 || message.length > 1000) {
      showFeedbackStatus("Коментар має містити від 2 до 1000 символів.", true);
      return;
    }
    handleFeedbackAction(() => {
      const updated = comments.map(item =>
        item.id === comment.id && item.ownerId === ownerId
          ? { ...item, message, updatedAt: new Date().toISOString() }
          : item,
      );
      saveFeedbackRecords(feedbackStorageKeys.comments, updated);
      comments = updated;
      editingCommentId = null;
      renderComments();
    }, "Коментар оновлено.");
  });
  article.append(form);
}

function renderFeedback() {
  renderRating();
  renderPoll();
  renderReactions();
  renderComments();
}

addStarPicker(ratingStars, value => {
  handleFeedbackAction(() => {
    const updated = validRatings().filter(rating => rating.ownerId !== ownerId);
    updated.push({ ownerId, value });
    saveFeedbackRecords(feedbackStorageKeys.ratings, updated);
    ratings = updated;
    renderRating();
  }, "Дякуємо за оцінку!");
});

addStarPicker(experienceStars, value => {
  experienceRating = experienceRating === value ? 0 : value;
  updateStarButtons(experienceStars, experienceRating);
});

reactionsElement?.addEventListener("click", event => {
  const button = event.target.closest("[data-reaction]");
  if (!button) return;
  handleFeedbackAction(() => {
    const current = reactions.find(reaction => reaction.ownerId === ownerId);
    const updated = reactions.filter(reaction => reaction.ownerId !== ownerId);
    if (current?.value !== button.dataset.reaction) {
      updated.push({ ownerId, value: button.dataset.reaction });
    }
    saveFeedbackRecords(feedbackStorageKeys.reactions, updated);
    reactions = updated;
    renderReactions();
  }, "Реакцію збережено.");
});

pollElement?.querySelector("[data-poll-form]")?.addEventListener("submit", event => {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  const choices = formData.getAll("poll-choice");
  if (
    !choices.length ||
    (!poll.multiple && choices.length !== 1) ||
    choices.some(choice => !poll.options.some(option => option.id === choice))
  ) {
    showFeedbackStatus("Оберіть варіант відповіді перед голосуванням.", true);
    return;
  }
  handleFeedbackAction(() => {
    if (poll.ended || validPollVotes().some(vote => vote.ownerId === ownerId)) {
      throw new Error("Ви вже голосували або опитування завершене.");
    }
    const updated = [
      ...validPollVotes(),
      { ownerId, pollId: poll.id, choices },
    ];
    saveFeedbackRecords(feedbackStorageKeys.votes, updated);
    pollVotes = updated;
    renderPoll();
  }, "Ваш голос зараховано. Дякуємо!");
});

commentForm?.addEventListener("submit", event => {
  event.preventDefault();
  const formData = new FormData(commentForm);
  const author = String(formData.get("author") || "").trim();
  const message = String(formData.get("message") || "").trim();
  if (author.length > 50 || message.length < 2 || message.length > 1000) {
    showFeedbackStatus("Ім’я має бути до 50, а коментар — від 2 до 1000 символів.", true);
    return;
  }
  handleFeedbackAction(() => {
    if (comments.filter(comment => comment?.ownerId === ownerId).length >= 20) {
      throw new Error("Досягнуто локального обмеження коментарів.");
    }
    const updated = [
      ...comments,
      {
        id: createOwnerId(),
        ownerId,
        author,
        message,
        createdAt: new Date().toISOString(),
      },
    ];
    saveFeedbackRecords(feedbackStorageKeys.comments, updated);
    comments = updated;
    commentForm.reset();
    renderComments();
  }, "Коментар додано.");
});

feedbackForm?.addEventListener("submit", event => {
  event.preventDefault();
  const formData = new FormData(feedbackForm);
  const type = String(formData.get("type") || "");
  const subject = String(formData.get("subject") || "").trim();
  const message = String(formData.get("message") || "").trim();
  const allowedTypes = ["suggestion", "problem", "complaint", "general"];
  if (
    !allowedTypes.includes(type) ||
    subject.length < 3 ||
    subject.length > 100 ||
    message.length < 10 ||
    message.length > 2000
  ) {
    showFeedbackStatus(
      "Перевірте тип, тему (3–100 символів) і повідомлення (10–2000 символів).",
      true,
    );
    return;
  }
  handleFeedbackAction(() => {
    if (submissions.filter(item => item?.ownerId === ownerId).length >= 20) {
      throw new Error("Досягнуто локального обмеження звернень.");
    }
    const updated = [
      ...submissions,
      {
        ownerId,
        type,
        subject,
        message,
        rating: experienceRating || null,
        createdAt: new Date().toISOString(),
      },
    ];
    saveFeedbackRecords(feedbackStorageKeys.submissions, updated);
    submissions = updated;
    feedbackForm.reset();
    experienceRating = 0;
    updateStarButtons(experienceStars, experienceRating);
  }, "Дякуємо! Ваш відгук збережено в цьому браузері.");
});

renderFeedback();
