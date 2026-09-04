/*
 * Blog & Updates page behaviour (staff post tools, "Add News" / "Share Your
 * Story" modals, theme/nav chrome, avatar loading).
 *
 * Extracted from an inline <script> block that used to live directly inside
 * origin/templates/html/blog_and_update.html. The handful of values that can
 * only come from Django (the logged-in user's name, and a few named-URL
 * reverses) are now passed in from the template via a small inline
 * `window.BLOG_PAGE_CONFIG = {...}` object instead of being interpolated
 * straight into this file - see the bottom of blog_and_update.html.
 */
(function () {
  'use strict';
  var CONFIG = window.BLOG_PAGE_CONFIG || {};
  const app = document.getElementById('blogApp');
  const heavyCss = document.getElementById('heavy-css');
  
  const $ = (s, c) => (c || document).querySelector(s);
  const $$ = (s, c) => (c || document).querySelectorAll(s);

  function getCookie(name) {
  const match = document.cookie.match('(?:^|;)\\s*' + name + '=([^;]*)');
  return match ? decodeURIComponent(match[1]) : '';
}

  function setCookie(name, value, days) {
    const d = new Date();
    d.setDate(d.getDate() + (days || 1));
    document.cookie =
      name + '=' + encodeURIComponent(value) +
      ';path=/;expires=' + d.toUTCString();
  }

  function boot() {
    if (!app || app.classList.contains('loaded')) return;

    app.classList.add('loaded');

    const indicator = document.getElementById('jsLoadingIndicator');
    if (indicator) {
      indicator.classList.add('hidden');
      setTimeout(() => {
        if (indicator.parentNode) indicator.remove();
      }, 500);
    }

    init();
  }

  if (heavyCss) {
    if (heavyCss.rel === 'stylesheet') boot();
    else heavyCss.addEventListener('load', boot);
  }

  setTimeout(boot, 8000);

  function init() {
    initTheme();
    initBackButton();
    initMobileNav();
    initLogout();
    initCategoryFilter();
    initAddNewsModal();
    initShareStoryModal();
    initStaffPostTools();
    initAsideAvatar();
  }

  /* Loads the aside sidebar's avatar the same way dashboard.html does - falls back
     to a generated initials avatar (dicebear) on any error, exactly like dashboard. */
  function initAsideAvatar() {
    const wrap = $('#asideAvatarWrap');
    if (!wrap) return; // aside only renders for authenticated users
    const sk = $('#asideAvatarSk');
    const DEFAULT_AVATAR = 'https://api.dicebear.com/7.x/initials/svg?seed=' +
                            encodeURIComponent(CONFIG.username) +
                            '&backgroundColor=1e293b&textColor=60a5fa&size=64';
    function apply(url) {
      const img = document.createElement('img');
      img.alt = CONFIG.username;
      img.style.cssText = 'width:100%;height:100%;object-fit:cover;border-radius:50%';
      img.onerror = function () { img.src = DEFAULT_AVATAR; };
      img.onload = function () { if (sk && sk.parentNode) sk.remove(); wrap.appendChild(img); };
      img.src = url;
    }
    fetch(CONFIG.userPictureUrl, { credentials: 'include' })
      .then(function (r) { return r.json(); })
      .then(function (d) { apply(d.url || DEFAULT_AVATAR); })
      .catch(function () { apply(DEFAULT_AVATAR); });
  }

  function initStaffPostTools() {
    const grid = $('#blogGrid');
    if (!grid) return;

    function csrf() { return getCookie('csrftoken'); }

    // Swaps a toolbar button into a disabled spinner while an action is in flight,
    // and restores its original icon afterwards - this is the missing "in progress"
    // feedback: without it a slow request (especially the image upload) just looked
    // like nothing was happening.
    function setBtnBusy(btn, busy) {
      if (!btn) return;
      if (busy) {
        btn.dataset.origHtml = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        btn.disabled = true;
        btn.style.pointerEvents = 'none';
        btn.style.opacity = '0.6';
      } else {
        if (btn.dataset.origHtml) btn.innerHTML = btn.dataset.origHtml;
        btn.disabled = false;
        btn.style.pointerEvents = '';
        btn.style.opacity = '';
      }
    }

    grid.addEventListener('click', function (e) {
      const editBtn = e.target.closest('.js-edit-post');
      const delBtn = e.target.closest('.js-delete-post');
      const copyBtn = e.target.closest('.js-copy-email');
      if (!editBtn && !delBtn && !copyBtn) return;

      const card = e.target.closest('.post-card');
      const id = card && card.getAttribute('data-post-id');
      if (!id) return;

      if (copyBtn) {
        // Ready-to-paste email body for manually notifying users when both email AND
        // push notifications fail (known hosting-related issue - see the WhatsApp
        // password-reset fallback for the same underlying reason). Pulls straight
        // from the rendered card so it's always exactly what's live on the blog.
        const title = card.querySelector('h3').textContent.trim();
        const excerpt = card.querySelector('.post-card-excerpt').textContent.trim();
        const linkEl = card.querySelector('.post-card-link');
        const url = linkEl ? linkEl.href : window.location.origin + CONFIG.blogUrl;
        const emailText =
          'Subject: New on STREAK & DISCIPLINE - ' + title + '\n\n' +
          'Hi,\n\n' +
          title + '\n\n' +
          excerpt + '\n\n' +
          'Read the full post here: ' + url + '\n\n' +
          '- The STREAK & DISCIPLINE team';
        (navigator.clipboard ? navigator.clipboard.writeText(emailText) : Promise.reject())
          .then(function () { showToast('Email text copied - paste it wherever you need to send it.', 'success'); })
          .catch(function () {
            // clipboard API unavailable/blocked (e.g. insecure context) - fall back to a
            // selectable prompt so staff can still copy it manually
            window.prompt('Copy this email text:', emailText);
          });
        return;
      }

      if (delBtn) {
        if (!confirm('Permanently delete this post? This cannot be undone.')) return;
        setBtnBusy(delBtn, true);
        const loadingToast = showToast('Deleting post…', 'loading', true);
        fetch('/v1/staff/news/' + id + '/delete/', { method: 'POST', headers: { 'X-CSRFToken': csrf() } })
          .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
          .then(function (res) {
            if (loadingToast) loadingToast.remove();
            setBtnBusy(delBtn, false);
            if (!res.ok) { showToast((res.data && res.data.message) || 'Could not delete post.', 'error'); return; }
            showToast(res.data.message || 'Post deleted.', 'success');
            card.remove();
          })
          .catch(function () {
            if (loadingToast) loadingToast.remove();
            setBtnBusy(delBtn, false);
            showToast('Network error while deleting.', 'error');
          });
        return;
      }

      if (editBtn) {
        const title = prompt('Edit title:', card.querySelector('h3').textContent.trim());
        if (title === null) return;
        const excerpt = prompt('Edit excerpt (max 1000 chars):', card.querySelector('.post-card-excerpt').textContent.trim());
        if (excerpt === null) return;
        setBtnBusy(editBtn, true);
        const loadingToast = showToast('Saving changes…', 'loading', true);
        const fd = new FormData();
        fd.append('title', title);
        fd.append('excerpt', excerpt);
        fetch('/v1/staff/news/' + id + '/edit/', { method: 'POST', headers: { 'X-CSRFToken': csrf() }, body: fd })
          .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
          .then(function (res) {
            if (loadingToast) loadingToast.remove();
            setBtnBusy(editBtn, false);
            if (!res.ok) { showToast((res.data && res.data.message) || 'Could not update post.', 'error'); return; }
            showToast(res.data.message || 'Post updated.', 'success');
            card.querySelector('h3').textContent = title;
            card.querySelector('.post-card-excerpt').textContent = excerpt;
          })
          .catch(function () {
            if (loadingToast) loadingToast.remove();
            setBtnBusy(editBtn, false);
            showToast('Network error while updating.', 'error');
          });
      }
    });

    grid.addEventListener('change', function (e) {
      const input = e.target.closest('.js-change-banner-input');
      if (!input || !input.files || !input.files[0]) return;
      const card = e.target.closest('.post-card');
      const id = card && card.getAttribute('data-post-id');
      const label = e.target.closest('.js-change-banner-label');
      if (!id) return;

      if (label) { label.dataset.origHtml = label.innerHTML.replace(input.outerHTML, ''); label.innerHTML = '<i class="fas fa-spinner fa-spin"></i>'; label.style.pointerEvents = 'none'; label.style.opacity = '0.6'; }
      const loadingToast = showToast('Uploading image…', 'loading', true);

      const fd = new FormData();
      fd.append('banner', input.files[0]);
      fetch('/v1/staff/news/' + id + '/banner/', { method: 'POST', headers: { 'X-CSRFToken': csrf() }, body: fd })
        .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
        .then(function (res) {
          if (loadingToast) loadingToast.remove();
          if (label) { label.innerHTML = '<i class="fas fa-image"></i><input type="file" class="js-change-banner-input" accept="image/png,image/jpeg,image/webp" hidden>'; label.style.pointerEvents = ''; label.style.opacity = ''; }
          if (!res.ok) { showToast((res.data && res.data.message) || 'Could not update image.', 'error'); return; }
          showToast(res.data.message || 'Banner updated.', 'success');
          const img = card.querySelector('.post-card-image img');
          if (img && res.data.banner_url) img.src = res.data.banner_url;
        })
        .catch(function () {
          if (loadingToast) loadingToast.remove();
          if (label) { label.innerHTML = '<i class="fas fa-image"></i><input type="file" class="js-change-banner-input" accept="image/png,image/jpeg,image/webp" hidden>'; label.style.pointerEvents = ''; label.style.opacity = ''; }
          showToast('Network error while uploading image.', 'error');
        });
    });
  }

  function initTheme() {
    const btn = $('#themeToggle');
    if (!btn) return;

    const icon = btn.querySelector('i');

    function apply(dark) {
      document.body.classList.toggle('sd-light', !dark);
      if (icon) icon.className = dark ? 'fas fa-moon' : 'fas fa-sun';
      setCookie('sd-theme', dark ? 'dark' : 'light', 365);
    }

    btn.addEventListener('click', function () {
      apply(document.body.classList.contains('sd-light'));
    });

    if (getCookie('sd-theme') === 'dark') {
      document.body.classList.remove('sd-light');
      if (icon) icon.className = 'fas fa-moon';
    }
  }

  function initBackButton() {
    const btn = $('#backBtn');
    if (!btn) return;

    const fallback = CONFIG.backFallbackUrl;

    btn.addEventListener('click', function () {
      const sameSite =
        document.referrer &&
        document.referrer.indexOf(window.location.origin) === 0;

      if (sameSite && window.history.length > 1) {
        window.history.back();
      } else {
        window.location.href = fallback;
      }
    });
  }

  function initMobileNav() {
    const nav = $('#mobileNav');
    const toggle = $('#menuToggle');
    const overlay = $('#navOverlay');
    const closeBtn = $('#navCloseBtn');

    if (!nav || !toggle || !overlay) return;

    function open() {
      nav.classList.add('open');
      overlay.classList.add('show');
      toggle.classList.add('open');
      toggle.setAttribute('aria-expanded', 'true');
    }

    function close() {
      nav.classList.remove('open');
      overlay.classList.remove('show');
      toggle.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
    }

    toggle.addEventListener('click', function () {
      nav.classList.contains('open') ? close() : open();
    });

    overlay.addEventListener('click', close);
    if (closeBtn) closeBtn.addEventListener('click', close);

    nav.querySelectorAll('.mobile-nav-link[href]').forEach(function (link) {
      link.addEventListener('click', close);
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') close();
    });

    const mobileAdd = $('#addNewsBtnMobile');
    if (mobileAdd) {
      mobileAdd.addEventListener('click', function () {
        close();
        if (window.__openNewsModal) window.__openNewsModal();
      });
    }

    const mobileStory = $('#shareStoryBtnMobile');
    if (mobileStory) {
      mobileStory.addEventListener('click', function () {
        close();
        if (window.__openStoryModal) window.__openStoryModal();
      });
    }
  }

  function initCategoryFilter() {
    const buttons = $$('.tag-chip');
    const cards = $$('.post-card');

    if (!buttons.length) return;

    buttons.forEach(function (btn) {
      btn.addEventListener('click', function () {
        buttons.forEach(b => b.classList.remove('active'));
        this.classList.add('active');

        const tag = this.dataset.tag;

        cards.forEach(function (card) {
          card.style.display =
            tag === 'all' || card.dataset.tag === tag ? '' : 'none';
        });
      });
    });
  }

  function initLogout() {
    if (!CONFIG.isAuthenticated) return;
    const form = $('#logoutForm');

    [$('#logoutBtn'), $('#asideLogoutBtn')].forEach(function (btn) {
      if (!btn) return;
      btn.addEventListener('click', function () {
        if (confirm('Log out?')) {
          if (form) form.submit();
          else window.location.href = CONFIG.logoutUrl;
        }
      });
    });
  }

  function showToast(message, type, persist) {
    const stack = $('#toastStack');
    if (!stack) return null;

    const toast = document.createElement('div');
    toast.className = 'toast toast-' + (type || 'success');
    const iconClass = type === 'error' ? 'fa-times-circle' : (type === 'loading' ? 'fa-spinner fa-spin' : 'fa-check-circle');
    toast.innerHTML = '<i class="fas ' + iconClass + '"></i><span>' + message + '</span>';

    stack.appendChild(toast);

    if (!persist) {
      setTimeout(function () { toast.remove(); }, 4000);
    }
    return toast; // callers doing a multi-step async action (e.g. an upload) can call .remove() on this themselves once done, then show a follow-up toast
  }

  function initAddNewsModal() {
    const modal = $('#addNewsModal');
    if (!modal) return;

    const overlay = $('#addNewsOverlay');
    const openBtn = $('#addNewsBtn');
    const closeBtn = $('#closeNewsModal');
    const cancelBtn = $('#cancelNewsBtn');
    const form = $('#addNewsForm');
    const errorBox = $('#newsFormError');
    const submitBtn = $('#submitNewsBtn');
    const excerpt = $('#newsExcerpt');
    const count = $('#excerptCount');
    const banner = $('#newsBanner');
    const preview = $('#filePreview');
    const empty = $('#fileDropEmpty');

    const ENDPOINT = CONFIG.publishNewsEndpoint;

    let lastFocused = null;

    function open() {
      lastFocused = document.activeElement;
      overlay.classList.add('show');
      modal.classList.add('open');
      modal.setAttribute('aria-hidden', 'false');

      setTimeout(function () {
        const title = $('#newsTitle');
        if (title) title.focus();
      }, 200);
    }

    function close() {
      overlay.classList.remove('show');
      modal.classList.remove('open');
      modal.setAttribute('aria-hidden', 'true');
      if (lastFocused) lastFocused.focus();
    }

    window.__openNewsModal = open;

    if (openBtn) openBtn.addEventListener('click', open);
    overlay.addEventListener('click', close);
    if (closeBtn) closeBtn.addEventListener('click', close);
    if (cancelBtn) cancelBtn.addEventListener('click', close);

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && modal.classList.contains('open')) {
        close();
      }
    });

    if (excerpt && count) {
      excerpt.addEventListener('input', function () {
        count.textContent = excerpt.value.length + ' / 1000';
      });
    }

    if (banner) {
      banner.addEventListener('change', function () {
        const file = banner.files && banner.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = function (e) {
          preview.src = e.target.result;
          preview.hidden = false;
          empty.hidden = true;
        };
        reader.readAsDataURL(file);
      });
    }

    function setSubmitting(state) {
      if (!submitBtn) return;
      submitBtn.disabled = state;

      const label = submitBtn.querySelector('.btn-label');
      if (label) label.textContent = state ? 'Publishing…' : 'Publish Post';
    }

    if (!form) return;

    form.addEventListener('submit', function (e) {
      e.preventDefault();

      if (errorBox) errorBox.hidden = true;

      const title = $('#newsTitle').value.trim();
      const tag = $('#newsTag').value;
      const readTime = $('#newsReadTime').value;
      const featured = $('#newsFeatured').checked;
      const content = $('#newsContent').value.trim();
      const bannerFile = banner.files && banner.files[0];

      if (!title || !tag || !excerpt.value.trim() || !readTime || !content) {
          if (errorBox) {
            errorBox.textContent = 'Please fill in all required fields before publishing.';
            errorBox.hidden = false;
          }
          return;
        }

      const fd = new FormData();
      fd.append('title', title);
      fd.append('tag', tag);
      fd.append('excerpt', excerpt.value.trim());
      fd.append('read_time', readTime);
    if (bannerFile) {
      fd.append('banner', bannerFile);}
      fd.append('featured', featured ? 'true' : 'false');
      fd.append('actual_content', content);

      setSubmitting(true);

      fetch(ENDPOINT, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        body: fd
      })
        .then(function (res) {
          return res.json().catch(function () { return {}; }).then(function (data) {
            return { ok: res.ok, status: res.status, data: data };
          });
        })
        .then(function (result) {
          setSubmitting(false);
          if (!result.ok) {
            var msg = (result.data && result.data.message) || ('Request failed with status ' + result.status + '.');
            if (errorBox) { errorBox.textContent = msg; errorBox.hidden = false; }
            showToast(msg, 'error');
            return;
          }
          showToast((result.data && result.data.message ? result.data.message + ' Email text copied for manual sending.' : 'Post published.'), 'success');

          // Auto-copy a ready-to-paste "notify manually" email as soon as the post is
          // live - see js-copy-email (initStaffPostTools) for the same text built from
          // an existing card; this is the same idea right at publish time so staff don't
          // have to hunt for the new card afterwards if email/push notifications fail.
          if (result.data && result.data.url) {
            var emailText =
              'Subject: New on STREAK & DISCIPLINE - ' + title + '\n\n' +
              'Hi,\n\n' + title + '\n\n' + excerpt.value.trim() + '\n\n' +
              'Read the full post here: ' + window.location.origin + result.data.url + '\n\n' +
              '- The STREAK & DISCIPLINE team';
            if (navigator.clipboard) navigator.clipboard.writeText(emailText).catch(function(){});
          }

          form.reset();
          preview.hidden = true;
          empty.hidden = false;
          if (count) count.textContent = '0 / 1000';
          close();
          if (typeof window.reloadBlogFeed === 'function') window.reloadBlogFeed();
          else setTimeout(function(){ window.location.reload(); }, 900);
        })
        .catch(function (err) {
          setSubmitting(false);
          var msg = 'Network error while publishing — check your connection and try again.';
          if (errorBox) { errorBox.textContent = msg; errorBox.hidden = false; }
          showToast(msg, 'error');
        });
    });
  }

  /* "Share Your Story" - deliberately mirrors initAddNewsModal's shape/patterns above
     (same open/close/toast/file-preview conventions) so the two are easy to compare
     and keep in sync if one changes later. Posts to CreateUserStory
     (origin/views/normal_view.py), which always forces tag='story' and stamps
     submitted_by/is_anonymous server-side - this form never sends a 'tag' field. */
  function initShareStoryModal() {
    const modal = $('#shareStoryModal');
    if (!modal) return;

    const overlay = $('#shareStoryOverlay');
    const openBtn = $('#shareStoryBtn');
    const closeBtn = $('#closeStoryModal');
    const cancelBtn = $('#cancelStoryBtn');
    const form = $('#shareStoryForm');
    const errorBox = $('#storyFormError');
    const submitBtn = $('#submitStoryBtn');
    const excerpt = $('#storyExcerpt');
    const count = $('#storyExcerptCount');
    const banner = $('#storyBanner');           // only present for gold-tier users
    const preview = $('#storyFilePreview');
    const empty = $('#storyFileDropEmpty');

    const ENDPOINT = CONFIG.createStoryEndpoint;

    let lastFocused = null;

    function open() {
      lastFocused = document.activeElement;
      overlay.classList.add('show');
      modal.classList.add('open');
      modal.setAttribute('aria-hidden', 'false');
      setTimeout(function () { const t = $('#storyTitle'); if (t) t.focus(); }, 200);
    }
    function close() {
      overlay.classList.remove('show');
      modal.classList.remove('open');
      modal.setAttribute('aria-hidden', 'true');
      if (lastFocused) lastFocused.focus();
    }
    window.__openStoryModal = open;

    if (openBtn) openBtn.addEventListener('click', open);
    if (overlay) overlay.addEventListener('click', close);
    if (closeBtn) closeBtn.addEventListener('click', close);
    if (cancelBtn) cancelBtn.addEventListener('click', close);

    if (excerpt && count) {
      excerpt.addEventListener('input', function () {
        count.textContent = excerpt.value.length + ' / 1000';
      });
    }

    if (banner && preview && empty) {
      banner.addEventListener('change', function () {
        const file = banner.files && banner.files[0];
        if (!file) { preview.hidden = true; empty.hidden = false; return; }
        const reader = new FileReader();
        reader.onload = function (e) { preview.src = e.target.result; preview.hidden = false; empty.hidden = true; };
        reader.readAsDataURL(file);
      });
    }

    function setSubmitting(state) {
      if (!submitBtn) return;
      submitBtn.disabled = state;
      const label = submitBtn.querySelector('.btn-label');
      if (label) label.textContent = state ? 'Publishing…' : 'Publish Story';
    }

    if (!form) return;

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (errorBox) errorBox.hidden = true;

      const title = $('#storyTitle').value.trim();
      const content = $('#storyContent').value.trim();
      const isAnonymous = $('#storyAnonymous').checked;
      const bannerFile = banner && banner.files && banner.files[0];

      if (!title || !excerpt.value.trim() || !content) {
        if (errorBox) { errorBox.textContent = 'Please fill in the title, summary, and your story before publishing.'; errorBox.hidden = false; }
        return;
      }

      const fd = new FormData();
      fd.append('title', title);
      fd.append('excerpt', excerpt.value.trim());
      fd.append('actual_content', content);
      fd.append('is_anonymous', isAnonymous ? 'true' : 'false');
      if (bannerFile) fd.append('banner', bannerFile); // dropped server-side too if the account isn't gold - see CreateUserStory

      setSubmitting(true);

      fetch(ENDPOINT, { method: 'POST', headers: { 'X-CSRFToken': getCookie('csrftoken') }, body: fd })
        .then(function (res) {
          return res.json().catch(function () { return {}; }).then(function (data) {
            return { ok: res.ok, status: res.status, data: data };
          });
        })
        .then(function (result) {
          setSubmitting(false);
          if (!result.ok) {
            const msg = (result.data && result.data.message) || ('Request failed with status ' + result.status + '.');
            if (errorBox) { errorBox.textContent = msg; errorBox.hidden = false; }
            showToast(msg, 'error');
            return;
          }
          showToast(result.data.message || 'Your story is live!', 'success');
          form.reset();
          if (preview) preview.hidden = true;
          if (empty) empty.hidden = false;
          if (count) count.textContent = '0 / 1000';
          close();
          if (typeof window.reloadBlogFeed === 'function') window.reloadBlogFeed();
          else setTimeout(function () { window.location.reload(); }, 900);
        })
        .catch(function () {
          setSubmitting(false);
          const msg = 'Network error while publishing — check your connection and try again.';
          if (errorBox) { errorBox.textContent = msg; errorBox.hidden = false; }
          showToast(msg, 'error');
        });
    });
  }
})();
