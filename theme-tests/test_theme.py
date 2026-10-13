"""#2182: the 3v3.dev look on status.3v3.dev, tested on a built copy of the site (Upptime's own build).

    python3 theme-tests/test_theme.py <the build's export dir> [repo root]

The export dir is what Upptime's "site" step publishes (site/status-page/__sapper__/export, with assets/ copied
in). Every request to status.3v3.dev is answered from it; GitHub's data is answered here too (Playwright routing),
so the states are the test's and nothing reaches the network. WHAT IT CHECKS, each a named line (ok / FAIL):
  - the pure helpers in assets/3v3/status.js (node): percentages and milliseconds read, the bars' segments and
    colours, unreadable values give no bar;
  - the config: every theme file on this site, none of them a path the build's crawler would follow;
  - all up: each card a green LED, its uptime as the big faded figure, two bars with Upptime's own numbers, the
    3v3.dev fonts loaded from this site, carbon behind;
  - one service down: its LED red and blinking, its uptime bar red, the others green;
  - a degraded one: an orange LED;
  - numbers the script cannot read: no bars, Upptime's text left visible;
  - a service's page: two meters with Upptime's figures;
  - at 375 px nothing scrolls sideways and the nav's links are all on screen;
  - the page asks no host but status.3v3.dev and 3v3.dev: GitHub's API and raw files are read through our own
    cache (#2183, status-website apiBaseUrl / userContentBaseUrl), so no visitor talks to GitHub at all.
"""
import json
import mimetypes
import os
import re
import subprocess
import sys

from playwright.sync_api import sync_playwright

EXP = os.path.abspath(sys.argv[1])
ROOT = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), ".."))
SITE = "https://status.3v3.dev"
_cfg = open(os.path.join(ROOT, ".upptimerc.yml")).read()
API_BASE = re.search(r"\n  apiBaseUrl: (\S+)", _cfg).group(1)            # https://3v3.dev/status-api/gh (#2183)
RAW_BASE = re.search(r"\n  userContentBaseUrl: (\S+)", _cfg).group(1)    # https://3v3.dev/status-api/raw
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"{'ok  ' if ok else 'FAIL'} {name}" + (f" — {detail}" if detail and not ok else ""), flush=True)


# ── the helpers, in node ──
harness = ("const vm=require('vm'),fs=require('fs');const m={exports:{}};"
           "vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{module:m});const h=m.exports;"
           "console.log(JSON.stringify({p:[h.num('100.00%','%'),h.num(' 99.5 %','%'),h.num('n/a','%'),h.num('641 ms','ms'),h.num('641ms','ms'),h.num('','ms')],"
           "u:[h.uptimeBar(100,'up'),h.uptimeBar(99.4,'up'),h.uptimeBar(97,'up'),h.uptimeBar(100,'down'),h.uptimeBar(null,'up'),h.uptimeBar(140,'up')],"
           "r:[h.responseBar(641),h.responseBar(1500),h.responseBar(2600),h.responseBar(30),h.responseBar(null)],"
           "l:[h.ledFor('up'),h.ledFor('down'),h.ledFor('degraded'),h.ledFor('x')]}))")
r = subprocess.run(["node", "-e", harness, os.path.join(ROOT, "assets", "3v3", "status.js")], capture_output=True, text=True)
h = json.loads(r.stdout) if r.returncode == 0 else {}
check("num() reads Upptime's percentages and milliseconds, and nothing else", h.get("p") == [100, 99.5, None, 641, 641, None], str(h.get("p") or r.stderr[:300]))
check("the uptime bar: 20 segments for 100 %, green from 99.5, orange from 98, red below or when down, none if unreadable",
      h.get("u") == [{"lit": 20, "level": "green"}, {"lit": 20, "level": "orange"}, {"lit": 19, "level": "red"}, {"lit": 20, "level": "red"}, None, None], str(h.get("u")))
check("the response bar: a segment per 100 ms up to 2 s, green under 1 s, orange under 2 s, red from 2 s",
      h.get("r") == [{"lit": 6, "level": "green"}, {"lit": 15, "level": "orange"}, {"lit": 20, "level": "red"}, {"lit": 1, "level": "green"}, None], str(h.get("r")))
check("the LED: green up, red down, orange degraded, grey otherwise", h.get("l") == ["green", "red", "orange", "grey"], str(h.get("l")))

# ── the config ──
cfg = open(os.path.join(ROOT, ".upptimerc.yml")).read()
ours = re.findall(r"(?:logoUrl|favicon|faviconSvg|themeUrl|href|src): (\S+)", cfg.split("status-website:", 1)[1])
theme = [u for u in ours if "/3v3/" in u]
check("every theme file is on this site, by its full address (the build's crawler leaves those alone)",
      len(theme) == 6 and all(u.startswith(SITE + "/3v3/") for u in theme), str(ours))
from urllib.parse import urlparse  # noqa: E402
missing = [u for u in theme if not os.path.isfile(os.path.join(ROOT, "assets", urlparse(u).path.lstrip("/")))]
check("and every one of them is in assets/", not missing, str(missing))
check("each monitored site's icon is ours, not an icon service's", cfg.count("icon: " + SITE + "/3v3/icon-32-dark.svg") == 3)
check("the build left assets/3v3 as files (no crawler 404 folders)", os.path.isfile(os.path.join(EXP, "3v3", "status.css")), EXP)


def summary(states):
    return [{"name": n, "url": "https://example.test", "icon": SITE + "/3v3/icon-32-dark.svg", "slug": n.lower(), "status": s,
             "uptime": u, "uptimeDay": u, "uptimeWeek": u, "uptimeMonth": u, "uptimeYear": u,
             "time": t, "timeDay": t, "timeWeek": t, "timeMonth": t, "timeYear": t, "dailyMinutesDown": {}}
            for n, s, u, t in states]


def serve_site(route):
    path = route.request.url[len(SITE):].split("?")[0].split("#")[0] or "/"
    f = os.path.join(EXP, path.lstrip("/"))
    if os.path.isdir(f):
        f = os.path.join(f, "index.html")
    if os.path.isfile(f):
        route.fulfill(status=200, body=open(f, "rb").read(), headers={"Content-Type": mimetypes.guess_type(f)[0] or "application/octet-stream"})
    else:  # GitHub Pages: 404.html, the app shell
        route.fulfill(status=404, body=open(os.path.join(EXP, "404.html"), "rb").read(), headers={"Content-Type": "text/html"})


with sync_playwright() as p:
    browser = p.chromium.launch()

    def open_page(states, path="/", width=1280):
        ctx = browser.new_context(viewport={"width": width, "height": 900})
        hosts, errors = set(), []
        ctx.on("request", lambda rq: hosts.add(rq.url.split("/")[2]))
        ctx.route(SITE + "/**", serve_site)
        # GitHub, as our cache answers for it (CORS for this site only), at the addresses the config gives
        ctx.route(RAW_BASE + "/**", lambda rt: rt.fulfill(status=200, headers={"Access-Control-Allow-Origin": SITE, "Content-Type": "application/json"},
                  body=json.dumps(summary(states))) if rt.request.url.endswith("/history/summary.json") else rt.fulfill(status=404, body="", headers={"Access-Control-Allow-Origin": SITE}))
        ctx.route(API_BASE + "/**", lambda rt: rt.fulfill(status=200, headers={"Access-Control-Allow-Origin": SITE, "Content-Type": "application/json"}, body="[]"))
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(SITE + path, wait_until="networkidle")
        pg.wait_for_timeout(1200)
        return ctx, pg, hosts, errors

    CARDS = """() => [...document.querySelectorAll('section.live-status > article')].map(a => ({
        name: a.querySelector('h4 a').textContent.trim(), led: (a.querySelector('.v3-led') || {}).className || null,
        wm: (a.querySelector('.v3-wm') || {}).textContent || null,
        bars: [...a.querySelectorAll('.v3-bar')].map(b => [b.className.replace('v3-bar ', ''), b.querySelector('.bv').textContent, b.querySelectorAll('.bt i.on').length]),
        plainHidden: [...a.querySelectorAll(':scope > div:not(.v3-bars)')].every(d => d.classList.contains('v3-plain')),
        blink: a.querySelector('.v3-led') ? getComputedStyle(a.querySelector('.v3-led')).animationName : null }))"""

    ctx, pg, hosts, errors = open_page([("App", "up", "100.00%", 641), ("Website", "up", "99.98%", 655), ("MCP", "up", "100.00%", 572)])
    cards = pg.evaluate(CARDS)
    check("all up: three cards, each a green LED", [c["led"] for c in cards] == ["v3-led green"] * 3, str(cards))
    check("each card's big faded figure is its uptime, Upptime's own number", [c["wm"] for c in cards] == ["100.00%", "99.98%", "100.00%"], str([c["wm"] for c in cards]))
    check("each card has an uptime bar and a response bar with Upptime's numbers",
          [c["bars"] for c in cards] == [[["green", "100.00%", 20], ["green", "641 ms", 6]], [["green", "99.98%", 20], ["green", "655 ms", 7]],
                                         [["green", "100.00%", 20], ["green", "572 ms", 6]]], str([c["bars"] for c in cards]))
    look = pg.evaluate("""() => ({ bg: getComputedStyle(document.body).backgroundColor, h1: getComputedStyle(document.querySelector('h1')).fontFamily,
        body: getComputedStyle(document.body).fontFamily, fonts: [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family).sort(),
        logo: (document.querySelector('nav a.logo img') || {}).src || null, allUp: (document.querySelector('main > article.v3-all .v3-led') || {}).className || null,
        tick: /\\u2705/.test(document.querySelector('main').textContent) })""")
    check("3v3.dev's carbon behind, Chakra Petch for headings, IBM Plex Sans for text, all three families loaded from this site",
          look["bg"] == "rgb(13, 13, 12)" and look["h1"].startswith('"Chakra Petch"') and look["body"].startswith('"IBM Plex Sans"')
          and {"Chakra Petch", "IBM Plex Sans", "IBM Plex Mono"} <= set(look["fonts"]), str(look))
    check("the nav carries the 3v3.dev wordmark", look["logo"] == SITE + "/3v3/wordmark-silkscreen.svg", str(look["logo"]))
    check("'All systems are operational' has a green LED for its tick", look["allUp"] == "v3-led green" and not look["tick"], str(look))
    check("no script error", not errors, str(errors[:3]))
    check("the page asks no host but status.3v3.dev and 3v3.dev: no GitHub, no font or icon service",
          hosts <= {"status.3v3.dev", "3v3.dev"} and "3v3.dev" in hosts, str(sorted(hosts)))
    pg.click("label[for=data_day]")
    pg.wait_for_timeout(600)
    check("a period switch redraws from Upptime's new numbers (the same here) without doubling anything",
          pg.evaluate("() => document.querySelectorAll('.v3-bar').length") == 6 and pg.evaluate("() => document.querySelectorAll('.v3-wm').length") == 3)
    ctx.close()

    ctx, pg, hosts, errors = open_page([("App", "up", "100.00%", 641), ("Website", "down", "97.10%", 2600), ("MCP", "degraded", "99.70%", 1400)])
    cards = {c["name"]: c for c in pg.evaluate(CARDS)}
    check("one down: its LED red and blinking, its uptime bar red, its slow response red",
          cards["Website"]["led"] == "v3-led red" and cards["Website"]["blink"] == "v3-blink"
          and cards["Website"]["bars"] == [["red", "97.10%", 19], ["red", "2600 ms", 20]], str(cards["Website"]))
    check("a degraded one: an orange LED, an orange response bar", cards["MCP"]["led"] == "v3-led orange" and cards["MCP"]["bars"][1][0] == "orange", str(cards["MCP"]))
    check("the others stay green", cards["App"]["led"] == "v3-led green" and cards["App"]["bars"][0][0] == "green", str(cards["App"]))
    ctx.close()

    ctx, pg, hosts, errors = open_page([("App", "up", "n/a", "soon")])
    cards = pg.evaluate(CARDS)
    vis = pg.evaluate("() => [...document.querySelectorAll('section.live-status > article > div')].map(d => d.getBoundingClientRect().width > 2)")
    check("numbers the script cannot read: no bars and no figure, Upptime's own text left visible",
          cards[0]["bars"] == [] and cards[0]["wm"] is None and not cards[0]["plainHidden"] and all(vis), str(cards) + str(vis))
    ctx.close()

    ctx, pg, hosts, errors = open_page([("App", "up", "100.00%", 641)], path="/history/app")
    pg.wait_for_timeout(1500)
    meters = pg.evaluate("() => [...document.querySelectorAll('.v3-meter')].map(m => [m.querySelector('.k').textContent, m.querySelector('.v').textContent, (m.querySelector('.wm') || {}).textContent || null])")
    check("a service's page: its two figures as meters, Upptime's numbers", len(meters) == 2 and meters[0][1] == "100.00%" and meters[0][2] == "100.00%", str(meters))
    ctx.close()

    ctx, pg, hosts, errors = open_page([("App", "up", "100.00%", 641), ("Website", "up", "100.00%", 655), ("MCP", "up", "100.00%", 572)], width=375)
    g = pg.evaluate("""() => ({ scroll: document.documentElement.scrollWidth - innerWidth,
        nav: [...document.querySelectorAll('nav ul a')].map(a => { const r = a.getBoundingClientRect(); return [a.textContent.trim(), Math.round(r.left), Math.round(r.right)]; }) })""")
    check("at 375 px nothing scrolls sideways and the nav's links are all on screen",
          g["scroll"] <= 0 and all(l >= 0 and r <= 375 for _, l, r in g["nav"]), str(g))
    ctx.close()
    browser.close()

failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)} passed, {len(failed)} failed", flush=True)
sys.exit(1 if failed else 0)
