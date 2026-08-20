/**
 * StudyHub - Main JavaScript
 * Modern 2026 Animated UI
 */

(function() {
  'use strict';

  // ============================================
  // Configuration
  // ============================================
  const CONFIG = {
    themeKey: 'studyhub-theme',
    particleCount: 50,
    animationThreshold: 0.1,
    debounceDelay: 300,
    toastDuration: 3000,
  };

  // ============================================
  // Theme Toggle
  // ============================================
  const ThemeManager = {
    init() {
      const savedTheme = localStorage.getItem(CONFIG.themeKey) || 'dark';
      this.setTheme(savedTheme);

      const toggleBtn = document.getElementById('theme-toggle');
      if (toggleBtn) {
        toggleBtn.addEventListener('click', () => this.toggle());
      }
    },

    setTheme(theme) {
      document.body.setAttribute('data-theme', theme);
      document.documentElement.style.colorScheme = theme;

      const darkIcon = document.querySelector('.dark-icon');
      const lightIcon = document.querySelector('.light-icon');

      if (darkIcon && lightIcon) {
        if (theme === 'light') {
          darkIcon.classList.add('hidden');
          lightIcon.classList.remove('hidden');
        } else {
          darkIcon.classList.remove('hidden');
          lightIcon.classList.add('hidden');
        }
      }

      localStorage.setItem(CONFIG.themeKey, theme);
    },

    toggle() {
      const current = document.body.getAttribute('data-theme') || 'dark';
      const next = current === 'dark' ? 'light' : 'dark';
      this.setTheme(next);

      // Animate the toggle
      const toggleBtn = document.getElementById('theme-toggle');
      if (toggleBtn) {
        toggleBtn.classList.add('animate-pulse');
        setTimeout(() => toggleBtn.classList.remove('animate-pulse'), 500);
      }
    },
  };

  // ============================================
  // Mobile Menu Toggle
  // ============================================
  const MobileMenu = {
    init() {
      const btn = document.getElementById('mobile-menu-btn');
      const menu = document.getElementById('mobile-menu');

      if (btn && menu) {
        btn.addEventListener('click', () => {
          menu.classList.toggle('hidden');
          const icon = btn.querySelector('i');
          if (menu.classList.contains('hidden')) {
            icon.classList.remove('fa-times');
            icon.classList.add('fa-bars');
          } else {
            icon.classList.remove('fa-bars');
            icon.classList.add('fa-times');
          }
        });

        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
          if (!btn.contains(e.target) && !menu.contains(e.target)) {
            menu.classList.add('hidden');
            const icon = btn.querySelector('i');
            if (icon) {
              icon.classList.remove('fa-times');
              icon.classList.add('fa-bars');
            }
          }
        });
      }
    },
  };

  // ============================================
  // Scroll Animations (IntersectionObserver)
  // ============================================
  const ScrollAnimations = {
    init() {
      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              entry.target.classList.add('visible');

              // Animate counters inside the element
              const counters = entry.target.querySelectorAll('.counter');
              counters.forEach((counter) => this.animateCounter(counter));

              observer.unobserve(entry.target);
            }
          });
        },
        { threshold: CONFIG.animationThreshold }
      );

      document.querySelectorAll('.section-animate').forEach((el) => observer.observe(el));
    },

    animateCounter(el) {
      const target = parseInt(el.dataset.target) || 0;
      const duration = 2000;
      const startTime = performance.now();

      const update = (currentTime) => {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.floor(target * eased);

        if (progress < 1) {
          requestAnimationFrame(update);
        }
      };

      requestAnimationFrame(update);
    },
  };

  // ============================================
  // Particle Background
  // ============================================
  const ParticleBackground = {
    canvas: null,
    ctx: null,
    particles: [],
    mouseX: 0,
    mouseY: 0,

    init() {
      this.canvas = document.getElementById('particle-canvas');
      if (!this.canvas) return;

      this.ctx = this.canvas.getContext('2d');
      this.resize();
      this.createParticles();
      this.animate();

      window.addEventListener('resize', () => this.resize());
      document.addEventListener('mousemove', (e) => {
        this.mouseX = e.clientX;
        this.mouseY = e.clientY;
      });
    },

    resize() {
      this.canvas.width = window.innerWidth;
      this.canvas.height = window.innerHeight;
    },

    createParticles() {
      this.particles = [];
      for (let i = 0; i < CONFIG.particleCount; i++) {
        this.particles.push({
          x: Math.random() * this.canvas.width,
          y: Math.random() * this.canvas.height,
          size: Math.random() * 2 + 0.5,
          speedX: (Math.random() - 0.5) * 0.5,
          speedY: (Math.random() - 0.5) * 0.5,
          opacity: Math.random() * 0.5 + 0.2,
        });
      }
    },

    animate() {
      if (!this.ctx) return;

      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

      this.particles.forEach((p, i) => {
        // Mouse interaction
        const dx = this.mouseX - p.x;
        const dy = this.mouseY - p.y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < 150) {
          const force = (150 - dist) / 150;
          p.x -= dx * force * 0.02;
          p.y -= dy * force * 0.02;
        }

        // Movement
        p.x += p.speedX;
        p.y += p.speedY;

        // Wrap around
        if (p.x < 0) p.x = this.canvas.width;
        if (p.x > this.canvas.width) p.x = 0;
        if (p.y < 0) p.y = this.canvas.height;
        if (p.y > this.canvas.height) p.y = 0;

        // Draw particle
        this.ctx.beginPath();
        this.ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        this.ctx.fillStyle = `rgba(59, 130, 246, ${p.opacity})`;
        this.ctx.fill();

        // Draw connections
        this.particles.forEach((p2, j) => {
          if (i === j) return;
          const d = Math.sqrt((p.x - p2.x) ** 2 + (p.y - p2.y) ** 2);
          if (d < 120) {
            this.ctx.beginPath();
            this.ctx.moveTo(p.x, p.y);
            this.ctx.lineTo(p2.x, p2.y);
            this.ctx.strokeStyle = `rgba(59, 130, 246, ${0.1 * (1 - d / 120)})`;
            this.ctx.lineWidth = 0.5;
            this.ctx.stroke();
          }
        });
      });

      requestAnimationFrame(() => this.animate());
    },
  };

  // ============================================
  // Toast Notifications
  // ============================================
  const ToastManager = {
    container: null,

    init() {
      this.container = document.getElementById('toast-container');
    },

    show(message, type = 'info') {
      if (!this.container) return;

      const toast = document.createElement('div');
      toast.className = 'toast-enter pointer-events-auto';

      const colors = {
        success: 'from-green-500/20 to-emerald-500/20 border-green-500/30 text-green-400',
        error: 'from-red-500/20 to-rose-500/20 border-red-500/30 text-red-400',
        info: 'from-electric/20 to-cyan/20 border-electric/30 text-cyan-400',
        warning: 'from-yellow-500/20 to-orange-500/20 border-yellow-500/30 text-yellow-400',
      };

      const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        info: 'fa-info-circle',
        warning: 'fa-exclamation-triangle',
      };

      toast.innerHTML = `
        <div class="glass-card rounded-xl px-5 py-3 flex items-center gap-3 min-w-[280px] border ${colors[type] || colors.info}">
          <i class="fas ${icons[type] || icons.info}"></i>
          <span class="text-sm font-medium text-white">${message}</span>
        </div>
      `;

      this.container.appendChild(toast);

      setTimeout(() => {
        toast.classList.remove('toast-enter');
        toast.classList.add('toast-exit');
        setTimeout(() => toast.remove(), 300);
      }, CONFIG.toastDuration);
    },
  };

  // Global toast function
  window.showToast = function(message, type) {
    ToastManager.show(message, type);
  };

  // ============================================
  // Copy to Clipboard
  // ============================================
  const ClipboardManager = {
    init() {
      document.addEventListener('click', (e) => {
        const btn = e.target.closest('[onclick*="copy"]');
        if (!btn) return;

        const match = btn.getAttribute('onclick').match(/copyToClipboard\('([^']+)'/);
        if (match) {
          this.copy(match[1], btn);
        }
      });
    },

    copy(text, btn) {
      navigator.clipboard.writeText(text).then(() => {
        if (btn) {
          const original = btn.innerHTML;
          btn.innerHTML = '<i class="fas fa-check"></i> Copied!';
          btn.classList.add('text-green-400');

          setTimeout(() => {
            btn.innerHTML = original;
            btn.classList.remove('text-green-400');
          }, 2000);
        }
        ToastManager.show('Copied to clipboard!', 'success');
      }).catch(() => {
        ToastManager.show('Failed to copy', 'error');
      });
    },
  };

  // ============================================
  // Search Debounce
  // ============================================
  const SearchManager = {
    init() {
      const searchInputs = document.querySelectorAll('input[name="q"]');
      searchInputs.forEach((input) => {
        let timeout;
        input.addEventListener('input', () => {
          clearTimeout(timeout);
          timeout = setTimeout(() => {
            const form = input.closest('form');
            if (form && input.value.length >= 2) {
              // Could trigger live search here
            }
          }, CONFIG.debounceDelay);
        });
      });
    },
  };

  // ============================================
  // Lazy Loading
  // ============================================
  const LazyLoader = {
    init() {
      if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              const img = entry.target;
              if (img.dataset.src) {
                img.src = img.dataset.src;
                img.removeAttribute('data-src');
              }
              observer.unobserve(img);
            }
          });
        });

        document.querySelectorAll('img[data-src]').forEach((img) => observer.observe(img));
      }
    },
  };

  // ============================================
  // GSAP Animations
  // ============================================
  const GSAPAnimations = {
    init() {
      if (typeof gsap === 'undefined') return;

      gsap.registerPlugin(ScrollTrigger);

      // Animate hero section
      const hero = document.querySelector('.hero-gradient, .study-hero');
      if (hero) {
        gsap.from(hero.children, {
          y: 30,
          opacity: 0,
          duration: 0.8,
          stagger: 0.1,
          ease: 'power3.out',
        });
      }

      // Animate stat cards
      gsap.utils.toArray('.stat-card, .admin-stat-card').forEach((card, i) => {
        gsap.from(card, {
          scrollTrigger: {
            trigger: card,
            start: 'top 80%',
          },
          y: 30,
          opacity: 0,
          duration: 0.6,
          delay: i * 0.1,
          ease: 'power3.out',
        });
      });

      // Animate video cards
      gsap.utils.toArray('.video-card, .study-card, .catalog-card').forEach((card, i) => {
        gsap.from(card, {
          scrollTrigger: {
            trigger: card,
            start: 'top 85%',
          },
          y: 40,
          opacity: 0,
          duration: 0.6,
          delay: (i % 4) * 0.1,
          ease: 'power3.out',
        });
      });
    },
  };

  // ============================================
  // Navbar Scroll Effect
  // ============================================
  const NavbarScroll = {
    init() {
      const nav = document.getElementById('main-nav');
      if (!nav) return;

      let lastScroll = 0;

      window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;

        if (currentScroll > 50) {
          nav.classList.add('scrolled');
        } else {
          nav.classList.remove('scrolled');
        }

        lastScroll = currentScroll;
      });
    },
  };

  // ============================================
  // Counter Animation
  // ============================================
  const CounterAnimation = {
    init() {
      const counters = document.querySelectorAll('.counter[data-target]');
      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              this.animate(entry.target);
              observer.unobserve(entry.target);
            }
          });
        },
        { threshold: 0.5 }
      );

      counters.forEach((counter) => observer.observe(counter));
    },

    animate(el) {
      const target = parseInt(el.dataset.target) || 0;
      const duration = 2000;
      const startTime = performance.now();

      const update = (currentTime) => {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.floor(target * eased);

        if (progress < 1) {
          requestAnimationFrame(update);
        }
      };

      requestAnimationFrame(update);
    },
  };

  // ============================================
  // Footer Stats
  // ============================================
  const FooterStats = {
    init() {
      const videoCount = document.getElementById('footer-video-count');
      const subjectCount = document.getElementById('footer-subject-count');

      if (videoCount) {
        const total = document.querySelector('.counter[data-target]');
        if (total) {
          videoCount.textContent = total.dataset.target;
        }
      }

      if (subjectCount) {
        const subjects = document.querySelectorAll('.counter[data-target]');
        if (subjects.length > 1) {
          subjectCount.textContent = subjects[1].dataset.target;
        }
      }
    },
  };

  // ============================================
  // Smooth Scroll
  // ============================================
  const SmoothScroll = {
    init() {
      document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
        anchor.addEventListener('click', (e) => {
          const href = anchor.getAttribute('href');
          if (href === '#') return;

          e.preventDefault();
          const target = document.querySelector(href);
          if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        });
      });
    },
  };

  // ============================================
  // Initialize Everything
  // ============================================
  document.addEventListener('DOMContentLoaded', () => {
    ThemeManager.init();
    MobileMenu.init();
    ScrollAnimations.init();
    ParticleBackground.init();
    ToastManager.init();
    ClipboardManager.init();
    SearchManager.init();
    LazyLoader.init();
    GSAPAnimations.init();
    NavbarScroll.init();
    CounterAnimation.init();
    FooterStats.init();
    SmoothScroll.init();

    // Add loaded class for initial animations
    document.body.classList.add('loaded');
  });

  // ============================================
  // Performance: Reduce animations on slow devices
  // ============================================
  if (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 2) {
    document.documentElement.style.setProperty('--animation-duration', '0.01s');
  }

})();
