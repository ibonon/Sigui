/**
 * Sigui Protocol — Ambient Cybernetic Experience Engine (js/sigui-ambient.js)
 * 
 * Implements Sentinel-grade high-tech animations across all pages:
 * 1. Interactive Ambient Golden Wave & Particle Canvas (60 FPS)
 * 2. Mouse-tracking Radial Spotlight on Cards & Panels
 * 3. Telemetry Stat Counter Roll-Ups on Scroll
 * 4. Staggered Scroll-Reveal Animations (IntersectionObserver)
 * 5. Dynamic Laser Scanlines on Technical Boxes
 * 6. Code Snippet Copy-to-Clipboard with Floating Toast
 */

(function () {
  'use strict';

  // ─────────────────────────────────────────────────────────────────────────
  // 1. Ambient Background Wave & Particle Canvas
  // ─────────────────────────────────────────────────────────────────────────
  function initAmbientCanvas() {
    // If sentinel.html already has an active wave loop, do not duplicate
    if (window.__sigui_wave_initialized) return;

    let canvas = document.getElementById('wave-canvas');
    if (!canvas) {
      canvas = document.createElement('canvas');
      canvas.id = 'wave-canvas';
      document.body.prepend(canvas);

      // Add vignette if missing
      if (!document.querySelector('.vignette') && !document.querySelector('.ambient-vignette')) {
        const vig = document.createElement('div');
        vig.className = 'vignette';
        canvas.after(vig);
      }
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    window.__sigui_wave_initialized = true;

    let W = 0, H = 0, t = 0;
    const mouse = { x: -9999, y: -9999, vx: 0, vy: 0, px: -9999, py: -9999 };
    let particles = [];

    function resize() {
      const dpr = window.devicePixelRatio || 1;
      W = window.innerWidth;
      H = window.innerHeight;
      canvas.width = W * dpr;
      canvas.height = H * dpr;
      ctx.scale(dpr, dpr);

      particles = [];
      const particleCount = Math.min(Math.floor(W / 35), 45);
      for (let i = 0; i < particleCount; i++) {
        particles.push({
          x: Math.random() * W,
          y: Math.random() * H,
          r: Math.random() * 1.6 + 0.6,
          vx: (Math.random() - 0.5) * 0.25,
          vy: (Math.random() - 0.5) * 0.25,
          alpha: Math.random() * 0.45 + 0.15
        });
      }
    }
    resize();
    window.addEventListener('resize', resize, { passive: true });

    window.addEventListener('mousemove', (e) => {
      mouse.vx = e.clientX - mouse.px;
      mouse.vy = e.clientY - mouse.py;
      mouse.px = mouse.x;
      mouse.py = mouse.y;
      mouse.x = e.clientX;
      mouse.y = e.clientY;
    }, { passive: true });

    let animId = null;
    function draw() {
      if (document.hidden) {
        animId = requestAnimationFrame(draw);
        return;
      }

      ctx.clearRect(0, 0, W, H);
      t += 0.012;

      // 4 Ambient Undulating Gold Harmonic Waves
      ctx.lineWidth = 1;
      for (let i = 0; i < 4; i++) {
        ctx.beginPath();
        const baseA = 0.025 + i * 0.018;
        ctx.strokeStyle = `rgba(245, 166, 35, ${baseA})`;
        
        for (let x = 0; x < W; x += 16) {
          const y = (H * 0.52) + Math.sin(x * 0.0028 + t + i * 1.3) * 55 * Math.cos(t * 0.45);
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      }

      // Floating Glow Dust Particles
      particles.forEach((p) => {
        p.x += p.vx + (mouse.vx * 0.015);
        p.y += p.vy + (mouse.vy * 0.015);

        if (p.x < 0) p.x = W;
        if (p.x > W) p.x = 0;
        if (p.y < 0) p.y = H;
        if (p.y > H) p.y = 0;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(245, 166, 35, ${p.alpha})`;
        ctx.fill();
      });

      // Mouse velocity dampening
      mouse.vx *= 0.92;
      mouse.vy *= 0.92;

      animId = requestAnimationFrame(draw);
    }
    draw();
  }

  // ─────────────────────────────────────────────────────────────────────────
  // 2. Mouse-Tracking Radial Spotlight on Cards & Panels
  // ─────────────────────────────────────────────────────────────────────────
  function initCardSpotlights() {
    const targets = document.querySelectorAll(
      '.sigui-card, .pipeline-step, .tier-step, .terminal-window, .status-cell, .next-page-card'
    );

    targets.forEach((card) => {
      card.classList.add('spotlight-card');
      card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        card.style.setProperty('--mouse-x', `${x}px`);
        card.style.setProperty('--mouse-y', `${y}px`);
      }, { passive: true });
    });
  }

  // ─────────────────────────────────────────────────────────────────────────
  // 3. Telemetry Numbers Counter Roll-Up Animation
  // ─────────────────────────────────────────────────────────────────────────
  function initCounters() {
    const valueElements = document.querySelectorAll('.status-cell .v');

    const counterObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const el = entry.target;
        observer.unobserve(el);

        const rawText = el.textContent.trim();

        // Match patterns like "92.9%", "35.3 ms", "< 3.0 ms", "1,000,000", "98.7%", "64 Bytes"
        const numMatch = rawText.match(/([<>]?\s*)([\d,]+(?:\.\d+)?)(.*)/);
        if (!numMatch) return;

        const prefix = numMatch[1] || '';
        const numStr = numMatch[2].replace(/,/g, '');
        const suffix = numMatch[3] || '';
        const targetNum = parseFloat(numStr);
        if (isNaN(targetNum) || targetNum === 0) return;

        const isDecimal = numStr.includes('.');
        const decimals = isDecimal ? numStr.split('.')[1].length : 0;
        const duration = 1000; // ms
        const startTime = performance.now();

        function update(currentTime) {
          const elapsed = currentTime - startTime;
          const progress = Math.min(elapsed / duration, 1);
          // Ease-out cubic
          const ease = 1 - Math.pow(1 - progress, 3);
          const current = targetNum * ease;

          let formatted = isDecimal ? current.toFixed(decimals) : Math.floor(current).toLocaleString();
          el.innerHTML = `${prefix}${formatted}${suffix}`;

          if (progress < 1) {
            requestAnimationFrame(update);
          } else {
            el.innerHTML = rawText; // restore exact original formatted string
          }
        }

        requestAnimationFrame(update);
      });
    }, { threshold: 0.2 });

    valueElements.forEach((el) => counterObserver.observe(el));
  }

  // ─────────────────────────────────────────────────────────────────────────
  // 4. Staggered Scroll-Reveal Animation
  // ─────────────────────────────────────────────────────────────────────────
  function initScrollReveal() {
    const revealItems = document.querySelectorAll(
      '.sigui-card, .status-dashboard, .pipeline-container, .terminal-window, .tier-ladder, .next-page-card, .dist-track'
    );

    const revealObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-revealed');
          revealObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });

    revealItems.forEach((item, index) => {
      item.classList.add('reveal-on-scroll');
      item.style.transitionDelay = `${(index % 4) * 0.08}s`;
      revealObserver.observe(item);
    });
  }

  // ─────────────────────────────────────────────────────────────────────────
  // 5. Laser Scanline Injection on Terminals & Pipeline Containers
  // ─────────────────────────────────────────────────────────────────────────
  function initScanlines() {
    const scanBoxes = document.querySelectorAll('.terminal-window, .pipeline-container');
    scanBoxes.forEach((box) => {
      if (!box.querySelector('.scan-line')) {
        const scan = document.createElement('div');
        scan.className = 'scan-line';
        box.style.position = 'relative';
        box.prepend(scan);
      }
    });
  }

  // ─────────────────────────────────────────────────────────────────────────
  // 6. Distribution Bar Animate-on-View (for dataset.html)
  // ─────────────────────────────────────────────────────────────────────────
  function initDistributionBar() {
    const track = document.querySelector('.dist-track');
    if (!track) return;

    const segs = track.querySelectorAll('.dist-seg');
    const targetWidths = [];
    segs.forEach((seg) => {
      targetWidths.push(seg.style.width);
      seg.style.width = '0%';
      seg.style.transition = 'width 1.2s cubic-bezier(0.16, 1, 0.3, 1)';
    });

    const distObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          segs.forEach((seg, i) => {
            setTimeout(() => {
              seg.style.width = targetWidths[i];
            }, 100);
          });
          distObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.2 });

    distObserver.observe(track);
  }

  // ─────────────────────────────────────────────────────────────────────────
  // 7. Interactive Code Copy with Feedback Toast
  // ─────────────────────────────────────────────────────────────────────────
  function initCodeCopyButtons() {
    const terminals = document.querySelectorAll('.terminal-window');
    terminals.forEach((term) => {
      const header = term.querySelector('.terminal-header');
      const body = term.querySelector('.terminal-body pre');
      if (!header || !body) return;

      // Check if button already exists
      if (header.querySelector('.terminal-copy-btn')) return;

      const copyBtn = document.createElement('button');
      copyBtn.type = 'button';
      copyBtn.className = 'terminal-copy-btn';
      copyBtn.innerHTML = '<span>Copy</span>';
      copyBtn.title = 'Copy code snippet';

      copyBtn.addEventListener('click', async () => {
        const textToCopy = body.innerText.replace(/^\$\s/gm, ''); // remove terminal '$' prompts
        try {
          await navigator.clipboard.writeText(textToCopy);
          copyBtn.innerHTML = '<span style="color: var(--safe);">Copied ✓</span>';
          setTimeout(() => {
            copyBtn.innerHTML = '<span>Copy</span>';
          }, 2000);
        } catch (err) {
          copyBtn.innerHTML = '<span>Failed</span>';
        }
      });

      header.appendChild(copyBtn);
    });
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Initialize Everything on DOMContentLoaded
  // ─────────────────────────────────────────────────────────────────────────
  function boot() {
    initAmbientCanvas();
    initCardSpotlights();
    initCounters();
    initScrollReveal();
    initScanlines();
    initDistributionBar();
    initCodeCopyButtons();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
