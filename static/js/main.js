document.addEventListener("DOMContentLoaded", () => {
  // Mobile nav toggle
  const toggle = document.getElementById("navToggle");
  const links = document.getElementById("navLinks");
  if (toggle && links) {
    toggle.addEventListener("click", () => {
      links.classList.toggle("open");
    });
  }

  // Flash dismiss
  document.querySelectorAll(".flash-close").forEach((btn) => {
    btn.addEventListener("click", () => {
      btn.parentElement.remove();
    });
  });

  // Auto-dismiss flashes after 6s
  setTimeout(() => {
    document.querySelectorAll(".flash").forEach((f) => f.remove());
  }, 6000);

  // Smooth fade-in for elements with .fade-in
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.style.animationPlayState = "running";
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.1 }
  );
  document.querySelectorAll(".fade-in").forEach((el) => {
    el.style.animationPlayState = "paused";
    observer.observe(el);
  });
});
