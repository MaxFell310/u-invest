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
      .replace(/\\.$/, "");
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
