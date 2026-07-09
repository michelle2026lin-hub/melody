/* ============================================================
   HONGTAI — client engagement tracker
   Records: open, 30s heartbeats, max scroll depth, close+duration.
   Fires to your Google Apps Script Web App endpoint.
   Fill in WEB_APP_URL below with your deployed /exec URL.
   Usage: give each client a unique link, e.g.
     hinge-product.html?cid=RX001
   ============================================================ */
(function () {
  const WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyobeLBqaPk72AsdJEffZf4FwDdSGC2owFMDJlyOU0zmSsve1cF9r7NsUcgV4lEoMYxDA/exec"; // TODO: replace

  const params = new URLSearchParams(window.location.search);
  const cid = params.get("cid") || "unknown";
  const page = document.title || location.pathname;

  function ping(action, extra) {
    const q = new URLSearchParams({ cid, page, action, ...extra });
    // fire-and-forget; no need to wait on response
    fetch(`${WEB_APP_URL}?${q.toString()}`).catch(() => {});
  }

  // 1) open
  ping("open");

  // 2) heartbeat every 30s while tab is visible
  let heartbeatCount = 0;
  const heartbeat = setInterval(() => {
    if (document.visibilityState === "visible") {
      heartbeatCount++;
      ping("heartbeat");
    }
  }, 30000);

  // 3) scroll depth (only report new maximums)
  let maxScroll = 0;
  window.addEventListener("scroll", () => {
    const scrollable = document.body.scrollHeight - window.innerHeight;
    if (scrollable <= 0) return;
    const pct = Math.round((window.scrollY / scrollable) * 100);
    if (pct > maxScroll) {
      maxScroll = Math.min(pct, 100);
      ping("scroll", { progress: maxScroll });
    }
  }, { passive: true });

  // 4) close + total duration (sendBeacon survives page unload)
  window.addEventListener("beforeunload", () => {
    const q = new URLSearchParams({
      cid, page, action: "close", duration: String(heartbeatCount * 30)
    });
    navigator.sendBeacon(`${WEB_APP_URL}?${q.toString()}`);
    clearInterval(heartbeat);
  });
})();
