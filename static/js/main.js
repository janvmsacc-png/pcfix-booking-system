document.addEventListener("DOMContentLoaded", () => {
  // ==========================================
  // 1. Theme Toggle Management
  // ==========================================
  const toggleBtn = document.getElementById('theme-toggle');

  // Check for saved theme preference, otherwise use system preference
  const savedTheme = localStorage.getItem('theme');
  const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

  if (savedTheme === 'dark' || (!savedTheme && systemPrefersDark)) {
    document.documentElement.setAttribute('data-theme', 'dark');
  } else {
    document.documentElement.setAttribute('data-theme', 'light');
  }

  // Handle button click to switch themes
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-theme');
      const newTheme = currentTheme === 'light' ? 'dark' : 'light';

      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('theme', newTheme); // Save preference
    });
  }

  // ==========================================
  // 2. Mobile Navigation Toggle
  // ==========================================
  const toggle = document.getElementById("navToggle");
  const links = document.getElementById("navLinks");
  if (toggle && links) {
    toggle.addEventListener("click", () => {
      links.classList.toggle("open");
    });
  }

  // ==========================================
  // 3. Flash Notifications Dismissal
  // ==========================================
  document.querySelectorAll(".flash-close").forEach((btn) => {
    btn.addEventListener("click", () => {
      btn.parentElement.remove();
    });
  });

  // Auto-dismiss flashes after 6s
  setTimeout(() => {
    document.querySelectorAll(".flash").forEach((f) => f.remove());
  }, 6000);

  // ==========================================
  // 4. Smooth Intersection Fade-In
  // ==========================================
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

  // ==========================================
  // 5. 3D Tilt Effect
  // ==========================================
  const tiltElements = document.querySelectorAll(".tilt-card");

  tiltElements.forEach((el) => {
    el.addEventListener("mousemove", (e) => {
      const rect = el.getBoundingClientRect();
      
      // Calculate mouse position relative to the element edges
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      
      // Map coordinates to center axis (0,0)
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      
      // Max tilt threshold set to 15 degrees
      const rotateX = ((centerY - y) / centerY) * 15;
      const rotateY = ((x - centerX) / centerX) * 15;
      
      // Apply 3D matrix transformation changes
      el.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02, 1.02, 1.02)`;
    });

    // Reset components to flat state smoothly when layout mouse leaves
    el.addEventListener("mouseleave", () => {
      el.style.transform = "perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)";
    });
  });
});
