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
const toggleBtn = document.getElementById('theme-toggle');

// 1. Check for saved theme preference, otherwise use system preference
const savedTheme = localStorage.getItem('theme');
const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

if (savedTheme === 'dark' || (!savedTheme && systemPrefersDark)) {
  document.documentElement.setAttribute('data-theme', 'dark');
} else {
  document.documentElement.setAttribute('data-theme', 'light');
}

// 2. Handle button click to switch themes
toggleBtn.addEventListener('click', () => {
  const currentTheme = document.documentElement.getAttribute('data-theme');
  let newTheme = 'light';

  if (currentTheme === 'light') {
    newTheme = 'dark';
  }

  document.documentElement.setAttribute('data-theme', newTheme);
  localStorage.setItem('theme', newTheme); // Save preference
});
