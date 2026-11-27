/**
 * Chanakya Research Commons - Core Interactive JavaScript
 */

document.addEventListener("DOMContentLoaded", function () {
  // Attach CSRF token to all POST forms and fetch() requests automatically
  const csrfMeta = document.querySelector('meta[name="csrf-token"]');
  const csrfToken = csrfMeta ? csrfMeta.getAttribute("content") : "";
  if (csrfToken) {
    document.querySelectorAll('form[method="POST"], form[method="post"]').forEach(form => {
      if (!form.querySelector('input[name="csrf_token"]')) {
        const input = document.createElement("input");
        input.type = "hidden";
        input.name = "csrf_token";
        input.value = csrfToken;
        form.appendChild(input);
      }
    });

    const originalFetch = window.fetch;
    window.fetch = function (resource, init = {}) {
      const method = (init.method || "GET").toUpperCase();
      if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
        const headers = new Headers(init.headers || {});
        if (!headers.has("X-CSRFToken")) {
          headers.set("X-CSRFToken", csrfToken);
        }
        init.headers = headers;
      }
      return originalFetch(resource, init);
    };
  }

  // 0. Left Overlay Hamburger Sidebar (closed by default)
  const sidebar = document.getElementById("leftSidebar");
  const backdrop = document.getElementById("sidebarBackdrop");
  const toggleBtn = document.getElementById("sidebarToggle");
  const closeBtn = document.getElementById("sidebarClose");

  function setSidebarOpen(isOpen) {
    if (!sidebar || !backdrop) return;
    sidebar.classList.toggle("open", isOpen);
    backdrop.classList.toggle("open", isOpen);
    sidebar.setAttribute("aria-hidden", isOpen ? "false" : "true");
    if (toggleBtn) {
      toggleBtn.setAttribute("aria-expanded", isOpen ? "true" : "false");
    }
  }

  if (toggleBtn && sidebar && backdrop) {
    toggleBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      const currentlyOpen = sidebar.classList.contains("open");
      setSidebarOpen(!currentlyOpen);
    });

    if (closeBtn) {
      closeBtn.addEventListener("click", function () {
        setSidebarOpen(false);
      });
    }

    backdrop.addEventListener("click", function () {
      setSidebarOpen(false);
    });

    document.addEventListener("click", function (e) {
      if (sidebar.classList.contains("open") && !sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
        setSidebarOpen(false);
      }
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && sidebar.classList.contains("open")) {
        setSidebarOpen(false);
      }
    });

    sidebar.querySelectorAll(".crc-sidebar-link").forEach(link => {
      link.addEventListener("click", function () {
        setSidebarOpen(false);
      });
    });
  }

  // 1. AJAX Upvote handler
  document.querySelectorAll(".ajax-vote-form").forEach(form => {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      const url = this.action;
      const countSpan = this.querySelector(".vote-count");
      const btn = this.querySelector("button");

      fetch(url, {
        method: "POST",
        headers: { "X-Requested-With": "XMLHttpRequest" }
      })
      .then(res => res.json())
      .then(data => {
        if (data.upvote_count !== undefined && countSpan) {
          countSpan.textContent = data.upvote_count;
          btn.classList.toggle("active");
        }
      })
      .catch(err => console.error("Vote failed:", err));
    });
  });

  // 2. AJAX Follow/Unfollow handler
  document.querySelectorAll(".ajax-follow-btn").forEach(btn => {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      const targetId = this.dataset.userId;
      const isFollowing = this.dataset.following === "true";
      const url = isFollowing ? `/unfollow/${targetId}` : `/follow/${targetId}`;

      fetch(url, {
        method: "POST",
        headers: { "X-Requested-With": "XMLHttpRequest", "Content-Type": "application/json" }
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          this.dataset.following = isFollowing ? "false" : "true";
          if (isFollowing) {
            this.textContent = "Follow";
            this.classList.remove("btn-outline-secondary");
            this.classList.add("btn-primary");
          } else {
            this.textContent = "Following";
            this.classList.remove("btn-primary");
            this.classList.add("btn-outline-secondary");
          }
        }
      })
      .catch(err => console.error("Follow error:", err));
    });
  });

  // 3. Quick question chips for Research Assistant
  document.querySelectorAll(".query-chip").forEach(chip => {
    chip.addEventListener("click", function () {
      const input = document.getElementById("assistant-input");
      if (input) {
        input.value = this.textContent.trim().replace(/^"|"$/g, "");
        const submitBtn = document.getElementById("assistant-submit-btn");
        if (submitBtn) submitBtn.click();
      }
    });
  });
});
