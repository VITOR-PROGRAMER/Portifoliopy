document.addEventListener("DOMContentLoaded", function () {
  // ---------- helpers ----------
  function cap(s) { return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase(); }
  function qs(sel, root) { return (root || document).querySelector(sel); }
  function qsa(sel, root) { return (root || document).querySelectorAll(sel); }

  // ---------- elementos / estado ----------
  var topbarEl = qs('.topbar');
  var sections = qsa('section[id]');
  var navLinks = qsa('.nav a');

  // variáveis de observer (para podermos desconectar/recriar)
  var spy = null;
  var sectionIO = null;
  var revealer = null;
  var bodyMut = null;

  // ---------- calcula e aplica TOPBAR_H (CSS var usada no CSS) ----------
  var TOPBAR_H = computeTopbarHeight();
  applyTopbarCssVar(TOPBAR_H);

  function computeTopbarHeight() {
    return (topbarEl ? topbarEl.offsetHeight : 70) + 8;
  }

  function applyTopbarCssVar(h) {
    document.documentElement.style.setProperty('--topbar-h', h + 'px');
  }

  // ---------- observers (criar / destruir) ----------
  function createObservers() {
    if (spy) try { spy.disconnect(); } catch (e) { /* ignore */ }
    if (sectionIO) try { sectionIO.disconnect(); } catch (e) { /* ignore */ }
    if (revealer) try { revealer.disconnect(); } catch (e) { /* ignore */ }

    var spyRootMargin = '-40% 0px -50% 0px';
    spy = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        var id = entry.target.getAttribute('id');
        var link = qs('.nav a[href="#' + id + '"]');
        if (entry.isIntersecting) {
          navLinks.forEach(function (a) { a.classList.remove('active'); });
          if (link) link.classList.add('active');
        }
      });
    }, { rootMargin: spyRootMargin, threshold: 0.1 });

    sections.forEach(function (sec) { spy.observe(sec); });

    var sectionRootMargin = '-' + TOPBAR_H + 'px 0px 0px 0px';
    sectionIO = new IntersectionObserver(function (entries) {
      // atualmente não faz nada visível além do spy, mas mantemos para futuras hooks
      var best = null, bestRatio = 0;
      entries.forEach(function (e) {
        if (e.intersectionRatio > bestRatio) { best = e.target; bestRatio = e.intersectionRatio; }
      });
    }, {
      root: null,
      rootMargin: sectionRootMargin,
      threshold: [0, 0.25, 0.5, 0.75, 1]
    });
    sections.forEach(function (sec) { sectionIO.observe(sec); });

    revealer = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('show');
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });

    var revealEls = qsa('.reveal, .card, .proj-card');
    revealEls.forEach(function (el) {
      if (!el.classList.contains('show')) revealer.observe(el);
    });
  }

  // cria inicialmente
  createObservers();

  // ---------- resize handler nomeado (para podermos remover) ----------
  var resizeTimeout = null;
  function resizeHandler() {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(function () {
      TOPBAR_H = computeTopbarHeight();
      applyTopbarCssVar(TOPBAR_H);
      createObservers();
    }, 120);
  }
  window.addEventListener('resize', resizeHandler);

  // ---------- MutationObserver para mudanças de conteúdo dinâmico ----------
  bodyMut = new MutationObserver(function () {
    TOPBAR_H = computeTopbarHeight();
    applyTopbarCssVar(TOPBAR_H);
    createObservers();
  });
  bodyMut.observe(document.body, { childList: true, subtree: true });

  // ---------- Smooth scroll com offset (ao clicar nos links da navbar) ----------
  qsa('.nav a[href^="#"]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      var id = a.getAttribute('href').slice(1);
      var target = document.getElementById(id);
      if (target) {
        var rect = target.getBoundingClientRect();
        var top = rect.top + window.scrollY - TOPBAR_H;
        window.scrollTo({ top: top, behavior: 'smooth' });
        navLinks.forEach(function (ln) { ln.classList.remove('active'); });
        a.classList.add('active');
      }
    });
  });

  // ---------- tratar hash inicial ----------
  if (location.hash) {
    setTimeout(function () {
      var id = location.hash.slice(1);
      var target = document.getElementById(id);
      if (target) {
        var rect = target.getBoundingClientRect();
        var top = rect.top + window.scrollY - TOPBAR_H;
        window.scrollTo({ top: top, behavior: 'auto' });
      }
    }, 60);
  }

  // ---------- expose helpers ----------
  window.__pageHelpers = window.__pageHelpers || {};
  window.__pageHelpers.recomputeTopbar = function () {
    TOPBAR_H = computeTopbarHeight();
    applyTopbarCssVar(TOPBAR_H);
    createObservers();
    console.log("TOPBAR_H recomputado:", TOPBAR_H);
  };

  // ---------- Carrega counts (embutido -> arquivo) ----------
  function getCounts() {
    return new Promise(function (resolve, reject) {
      var emb = document.getElementById("counts");
      if (emb) {
        try {
          var j = JSON.parse(emb.textContent);
          console.log("[counts] usando JSON embutido");
          resolve(j);
          return;
        } catch (e) {
          console.warn("JSON embutido inválido:", e);
        }
      }
      var urls = ["data/counts.json", "WEB/data/counts.json"];
      (function tryNext(i) {
        if (i >= urls.length) {
          reject(new Error("Não consegui carregar counts.json (embutido nem arquivo)."));
          return;
        }
        fetch(urls[i], { cache: "no-store" })
          .then(function (r) {
            if (!r.ok) throw new Error(r.status + " " + r.statusText);
            console.log("[counts] usando " + urls[i]);
            return r.json();
          })
          .then(resolve)
          .catch(function () { tryNext(i + 1); });
      })(0);
    });
  }

  // ---------- Render (1 card por subpasta) ----------
  getCounts().then(function (json) {
    var MAX = 50;
    var skills = Array.isArray(json.skills) ? json.skills : [];
    var dados = json.dados || {};

    skills.forEach(function (skill) {
      var sec = document.getElementById(skill);
      if (!sec) { console.warn("Seção ausente:", skill); return; }
      var grid = qs('.proj-grid[data-skill="' + skill + '"]', sec);
      if (!grid) {
        grid = document.createElement("div");
        grid.className = "proj-grid";
        grid.setAttribute("data-skill", skill);
        sec.appendChild(grid);
      }
    });

    skills.forEach(function (skill) {
      var sec = document.getElementById(skill);
      if (!sec) return;
      var grid = qs('.proj-grid[data-skill="' + skill + '"]', sec);
      if (!grid) return;

      var subpastas = Array.isArray(dados[skill] && dados[skill].pastas)
        ? dados[skill].pastas : [];

      var chip = qs(".sec-head .count-inline", sec);
      if (!chip) {
        var h2 = qs(".sec-head h2", sec);
        if (h2) {
          chip = document.createElement("span");
          chip.className = "count-inline";
          h2.appendChild(chip);
        }
      }
      if (chip) chip.textContent = "Projetos: " + subpastas.length;

      grid.innerHTML = "";
      subpastas.slice(0, MAX).forEach(function (nome) {
        var el = document.createElement("article");
        el.className = "proj-card";

        var title = document.createElement("h3");
        title.className = "proj-title";
        title.setAttribute("title", nome);
        title.textContent = nome;

        var meta = document.createElement("p");
        meta.className = "proj-meta";
        meta.textContent = "Subpasta do projeto";

        var actions = document.createElement("div");
        actions.className = "proj-actions";

        var btn = document.createElement("button");
        btn.className = "proj-open";
        btn.setAttribute("type", "button");
        btn.textContent = "Abrir";

        btn.addEventListener("click", function () {
          var url = ".." + "/Projetos/" + cap(skill) + "/" + encodeURIComponent(nome) + "/";
          if (location.protocol === "file:") {
            var base = location.href.replace(/[^/]+$/, "");
            url = base + url;
          }
          try { window.open(url, "_blank"); } catch (e) { console.warn("Falha ao abrir:", url, e); }
        });

        actions.appendChild(btn);
        el.appendChild(title);
        el.appendChild(meta);
        el.appendChild(actions);
        grid.appendChild(el);
      });

      console.log(skill + ": " + Math.min(subpastas.length, MAX) + " cards renderizados.");
    });

    // após renderizar, recomputa observers para observar novos elementos
    TOPBAR_H = computeTopbarHeight();
    applyTopbarCssVar(TOPBAR_H);
    createObservers();

  }).catch(function (e) {
    console.error(e);
  });

  // ---------- cleanup / desconexão segura ----------
  function cleanup() {
    try { if (spy && typeof spy.disconnect === 'function') spy.disconnect(); } catch (err) { }
    try { if (sectionIO && typeof sectionIO.disconnect === 'function') sectionIO.disconnect(); } catch (err) { }
    try { if (revealer && typeof revealer.disconnect === 'function') revealer.disconnect(); } catch (err) { }
    try { if (bodyMut && typeof bodyMut.disconnect === 'function') bodyMut.disconnect(); } catch (err) { }
    try { document.documentElement.style.removeProperty('--topbar-h'); } catch (err) { }
    window.removeEventListener('resize', resizeHandler);
    window.removeEventListener('beforeunload', cleanup);
  }

  window.__pageHelpers.cleanup = cleanup;
  window.addEventListener('beforeunload', cleanup);

}); // fecha DOMContentLoaded
