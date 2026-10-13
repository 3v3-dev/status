// status.3v3.dev (#2182): Giagia's LED bars and big faded figures over Upptime's own numbers. It reads the figures
// Upptime has already put on the page (never another source), so a period switch or a new reading redraws them;
// Upptime's text stays in the page for screen readers. Nothing here fetches anything. (Mia)
(() => {
  const SEGMENTS = 20;

  // "100.00%" → 100; "641 ms" / "641ms" → 641; anything else → null.
  function num(text, unit) {
    const m = String(text == null ? "" : text).replace(/\s+/g, " ").trim().match(unit === "%" ? /^(\d{1,3}(?:\.\d+)?)\s*%$/ : /^(\d+(?:\.\d+)?)\s*ms$/i);
    return m ? parseFloat(m[1]) : null;
  }

  // An uptime bar: lit in proportion to the percentage (20 segments = 100 %), green from 99.5 %, orange from 98 %,
  // red below that or when the service is down now. A response bar: one segment per 100 ms up to 2 s, green under
  // 1 s, orange under 2 s, red from 2 s. Unreadable → no bar at all.
  function uptimeBar(pct, state) {
    if (pct === null || pct < 0 || pct > 100) return null;
    const level = state === "down" ? "red" : pct >= 99.5 ? "green" : pct >= 98 ? "orange" : "red";
    return { lit: Math.round((pct / 100) * SEGMENTS), level };
  }
  function responseBar(ms) {
    if (ms === null || ms < 0) return null;
    return { lit: Math.min(SEGMENTS, Math.max(ms > 0 ? 1 : 0, Math.round(ms / 100))), level: ms < 1000 ? "green" : ms < 2000 ? "orange" : "red" };
  }
  function ledFor(state) { return state === "down" ? "red" : state === "degraded" ? "orange" : state === "up" ? "green" : "grey"; }

  if (typeof module === "object" && module && module.exports) module.exports = { num, uptimeBar, responseBar, ledFor, SEGMENTS };
  if (typeof document === "undefined") return;

  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
  const stateOf = (a) => (a.classList.contains("down") ? "down" : a.classList.contains("degraded") ? "degraded" : a.classList.contains("up") ? "up" : "unknown");

  function bar(label, value, b) {
    const row = el("div", `v3-bar ${b.level}`);
    const segs = el("span", "bt");
    segs.setAttribute("aria-hidden", "true");
    for (let i = 0; i < SEGMENTS; i++) segs.append(el("i", i < b.lit ? "on" : ""));
    row.append(el("span", "bl", label), segs, el("span", "bv", value));
    return row;
  }
  function figure(cls, text, unit) {
    const n = el("span", cls);
    n.setAttribute("aria-hidden", "true");
    n.append(text, el("small", "", unit));
    return n;
  }

  // The front page: each live card gets a LED, its uptime as a big faded figure, and an uptime and a response bar.
  function paintCard(a) {
    const spans = a.querySelectorAll(":scope > div:not(.v3-bars) > span.data");
    const upText = spans[0] ? spans[0].textContent.replace(/\s+/g, " ").trim() : "";
    const msText = spans[1] ? spans[1].textContent.replace(/\s+/g, " ").trim() : "";
    const state = stateOf(a);
    const sig = `${state}|${upText}|${msText}`;
    if (a.dataset.v3 === sig) return;
    a.dataset.v3 = sig;
    a.querySelectorAll(":scope > .v3-wm, :scope > .v3-bars").forEach((n) => n.remove());
    const h4 = a.querySelector("h4");
    let led = h4 && h4.querySelector(".v3-led");
    if (h4 && !led) { led = el("span", "v3-led"); h4.prepend(led); }
    if (led) { led.className = `v3-led ${ledFor(state)}`; led.title = state; }
    const pct = num(upText, "%"), ms = num(msText, "ms");
    const ub = uptimeBar(pct, state), rb = responseBar(ms);
    if (!ub && !rb) return; // nothing readable: Upptime's own text stays as it is
    a.querySelectorAll(":scope > div:not(.v3-bars)").forEach((d) => d.classList.add("v3-plain"));
    if (ub) a.append(figure("v3-wm", upText.replace(/\s*%$/, ""), "%"));
    const bars = el("div", "v3-bars");
    if (ub) bars.append(bar("Uptime", upText, ub));
    if (rb) bars.append(bar("Response", `${Math.round(ms)} ms`, rb));
    a.append(bars);
  }

  // A service's page: its uptime and its average response as two Giagia meters (a small label, the value, the
  // same value big and faded); Upptime's list stays in the page, hidden, so nothing is lost.
  function paintMeters(dl) {
    if (dl.classList.contains("v3-done") || dl.previousElementSibling && dl.previousElementSibling.classList.contains("v3-meters")) return;
    const dts = dl.querySelectorAll("dt"), dds = dl.querySelectorAll("dd");
    if (!dts.length || dts.length !== dds.length) return;
    const box = el("div", "v3-meters");
    dts.forEach((dt, i) => {
      const v = dds[i].textContent.replace(/\s+/g, " ").trim();
      const m = v.match(/^(\d+(?:\.\d+)?)\s*(%|ms)$/i);
      const meter = el("div", "v3-meter");
      meter.append(el("span", "k", dt.textContent.trim()), el("span", "v", v));
      if (m) meter.append(figure("wm", m[1], m[2]));
      box.append(meter);
    });
    dl.before(box);
    dl.classList.add("v3-done");
  }

  let queued = false;
  function paint() {
    queued = false;
    document.querySelectorAll("section.live-status > article").forEach(paintCard);
    document.querySelectorAll("main dl").forEach(paintMeters);
  }
  const later = () => { if (!queued) { queued = true; requestAnimationFrame(paint); } };
  new MutationObserver(later).observe(document.documentElement, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ["class"] });
  later();
})();
