/*
 * Mirror AI — developer portal shared JS.
 *
 * Pulled in by every dashboard page. Provides:
 *   - apiCall()         JSON fetch wrapper that decodes Flask's
 *                       {error:{code,message}} shape into a thrown Error.
 *   - apiCallWithKey()  same, but adds the user's Bearer api_key for
 *                       endpoints that still use api-key auth (balance,
 *                       usage, checkout/create). Cookie alone would not
 *                       authenticate those.
 *   - requireSession()  redirect to /login if /v1/me returns 401.
 *   - showError() / showOk()  inline banner helpers (no popups).
 *   - copyToClipboard() with brief confirmation feedback.
 *   - logout() helper.
 */
(function () {
  "use strict";

  const Portal = {};

  // ---------- low-level fetch wrappers ----------

  async function parseError(resp) {
    let detail = "";
    try {
      const body = await resp.json();
      if (body && body.error) {
        detail = body.error.message || body.error.code || "";
      }
    } catch (_) {
      // body not JSON
    }
    const err = new Error(detail || `HTTP ${resp.status}`);
    err.status = resp.status;
    return err;
  }

  Portal.apiCall = async function apiCall(method, url, body) {
    const opts = {
      method,
      credentials: "same-origin", // ship the session cookie
      headers: { "Content-Type": "application/json" },
    };
    if (body !== undefined && body !== null) {
      opts.body = JSON.stringify(body);
    }
    const resp = await fetch(url, opts);
    if (!resp.ok) {
      throw await parseError(resp);
    }
    if (resp.status === 204) return null;
    return resp.json();
  };

  Portal.apiCallWithKey = async function apiCallWithKey(method, url, apiKey, body) {
    if (!apiKey) {
      throw new Error("Missing API key. Reset your key from the dashboard.");
    }
    const opts = {
      method,
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + apiKey,
      },
    };
    if (body !== undefined && body !== null) {
      opts.body = JSON.stringify(body);
    }
    const resp = await fetch(url, opts);
    if (!resp.ok) {
      throw await parseError(resp);
    }
    if (resp.status === 204) return null;
    return resp.json();
  };

  // ---------- session / auth helpers ----------

  Portal.fetchMe = async function fetchMe() {
    return Portal.apiCall("GET", "/v1/me");
  };

  /**
   * Resolve to the /v1/me payload, or send the browser to /login on 401.
   * Pages that need auth call this on DOMContentLoaded.
   */
  Portal.requireSession = async function requireSession() {
    try {
      return await Portal.fetchMe();
    } catch (err) {
      if (err.status === 401) {
        const next = encodeURIComponent(window.location.pathname + window.location.search);
        window.location.href = "/login?next=" + next;
        // Keep the promise pending so callers don't continue rendering
        // the now-redirecting page.
        return new Promise(() => {});
      }
      throw err;
    }
  };

  Portal.logout = async function logout() {
    try {
      await Portal.apiCall("POST", "/v1/auth/logout");
    } catch (_) {
      // even on error we go to /login — the cookie may already be gone
    }
    window.location.href = "/login";
  };

  // ---------- UI helpers ----------

  Portal.showBanner = function showBanner(el, kind, msg) {
    if (!el) return;
    el.className = "banner banner-" + kind;
    el.textContent = msg;
    el.classList.remove("hidden");
  };
  Portal.showError = function showError(el, msg) {
    Portal.showBanner(el, "error", msg);
  };
  Portal.showOk = function showOk(el, msg) {
    Portal.showBanner(el, "ok", msg);
  };
  Portal.showWarn = function showWarn(el, msg) {
    Portal.showBanner(el, "warn", msg);
  };
  Portal.clearBanner = function clearBanner(el) {
    if (!el) return;
    el.classList.add("hidden");
    el.textContent = "";
  };

  Portal.copyToClipboard = async function copyToClipboard(text, button) {
    try {
      await navigator.clipboard.writeText(text);
      if (button) {
        const original = button.dataset.label || button.textContent;
        button.dataset.label = original;
        button.textContent = "Copied!";
        setTimeout(() => {
          button.textContent = original;
        }, 1200);
      }
      return true;
    } catch (_) {
      return false;
    }
  };

  Portal.formatYuan = function formatYuan(fen) {
    if (typeof fen !== "number") return "—";
    return "¥" + (fen / 100).toFixed(2);
  };

  Portal.formatTs = function formatTs(iso) {
    if (!iso) return "—";
    try {
      const d = new Date(iso);
      return d.toLocaleString();
    } catch (_) {
      return iso;
    }
  };

  Portal.maskKey = function maskKey(plaintext) {
    if (!plaintext) return "—";
    if (plaintext.length <= 12) return plaintext;
    return plaintext.slice(0, 6) + "…" + plaintext.slice(-4);
  };

  window.Portal = Portal;
})();
