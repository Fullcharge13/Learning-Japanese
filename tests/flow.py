"""화면 순회 시험.

실행: python3 tests/flow.py [시험 이름 …]

- 배포와 같은 한 장짜리 HTML을 시험용으로 빌드한다(python3 build.py --out tests/out/flow/dist).
- WebKit이 없어 Chromium에 Playwright 기기 설정(아이폰·아이패드)을 적용한다.
  사파리 고유 동작(홈 화면 추가, 저장 7일 규칙)은 docs/device-checklist.md에서 실기기로 본다.
- 캡처: tests/out/flow/*.png

시험
- test_no_overflow: 화면 8개 × 기기 5종(아이폰 3·아이패드 세로/가로) — 가로 스크롤 0, 화면 밖 버튼 0, 콘솔 오류 0
- test_touch_targets: 화면마다 보이는 버튼 44×44 CSS px 이상
- test_ipad_zoomed: 아이패드(폭 700px 이상)는 html zoom 1.3, 아이폰은 1
- test_no_text_inputs: 레슨 화면에 입력창(input·textarea·contenteditable)이 하나도 없음
- test_longest_meaning_fits: 가장 긴 보기(뜻·일본어)가 보기 카드 안에서 줄바꿈되고 넘치지 않음
- test_furigana_and_speak: 단어 레슨에 후리가나(rt)가 보이고 🔊 단추가 44px 이상, 누르면 읽기를 기기 음성에 넘김
- test_other_saves_coexist: 같은 주소의 리아·해치 앱 저장(ria-python.save, haechi-korean.save)을 읽지도 바꾸지도 않음
- test_first_lesson: 새 저장 → 1-1 전부 정답 → 완료 화면 XP +15, completed_lessons ["1-1"]
- test_wrong_then_retry: 한 문제 틀림 → 본 문제 끝에 다시 나옴 → 완료 화면은 실수 없음 아님
- test_status_after_milestone: 연속 6일(어제 달성) → 레슨 완료로 7일 축하 창이 떠 있는 동안 상태 줄 7일
"""

import atexit
import datetime
import functools
import http.server
import json
import os
import socketserver
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
from make_lessons import plain, kana  # noqa: E402

# 화면 글자에서 후리가나(rt)·🔊 단추를 뺀 것 = 데이터 표기의 plain()
SHOWN_JS = "(e) => { const c = e.cloneNode(true); c.querySelectorAll('rt, .say-btn').forEach((r) => r.remove()); return c.textContent; }"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "tests", "out", "flow")
DIST = os.path.join(OUT, "dist")
SAVE_KEY = "sanada-japanese.save"
HAECHI_KEY = "haechi-korean.save"
RIA_KEY = "ria-python.save"
GUARD_WAIT = 450          # 결과 창 입력 보호(400ms)보다 조금 길게

DEVICES = ["iPhone 17", "iPhone 17e", "iPhone 17 Pro Max", "iPad Pro 11", "iPad Pro 11 landscape"]
SCREENS = ["splash", "home", "lesson-card", "touch-item", "done", "jlpt", "badges", "closet", "settings"]

# 터치 영역 예외(근거가 있는 것만). 비어 있으면 예외 없음.
TOUCH_EXCEPTIONS = {}


# ---------------------------------------------------------------- 서버·브라우저

class _Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript", ".mjs": "text/javascript", ".wasm": "application/wasm",
        ".json": "application/json", ".webmanifest": "application/manifest+json",
        ".zip": "application/zip",
    }

    def log_message(self, *a):
        pass


class _Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        # 창을 닫을 때 끊긴 내려받기(ConnectionResetError 등)는 시험과 무관
        if not isinstance(sys.exc_info()[1], (ConnectionError, BrokenPipeError)):
            super().handle_error(request, client_address)


_env = {}


def env():
    """빌드 한 번 + 서버 + Chromium 하나를 시험 전체가 같이 쓴다."""
    if _env:
        return _env
    os.makedirs(OUT, exist_ok=True)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "build.py"), "--out", DIST],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, "build.py failed:\n" + r.stdout + r.stderr
    httpd = _Server(("127.0.0.1", 0), functools.partial(_Handler, directory=DIST))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    browser = pw.chromium.launch()
    _env.update(httpd=httpd, pw=pw, browser=browser, url="http://127.0.0.1:%d/" % httpd.server_address[1],
                build=r.stdout.strip())

    def stop():
        try:
            browser.close()
            pw.stop()
        finally:
            httpd.shutdown()
    atexit.register(stop)
    return _env


def device_opts(name):
    if name.startswith("PC"):
        return {"viewport": {"width": 1280, "height": 800}}
    d = dict(env()["pw"].devices[name])
    d.pop("default_browser_type", None)
    return d


def slug(name):
    return name.lower().replace(" ", "-")


def today(n=0):
    return (datetime.date.today() - datetime.timedelta(days=n)).isoformat()


class App:
    """기기 하나 + 새 저장소의 앱 한 판."""

    def __init__(self, device="iPhone 17", save=None, reduced=False, url=None, extra=None, locale=None, init=None):
        e = env()
        opts = device_opts(device)
        if reduced:
            opts["reduced_motion"] = "reduce"
        if locale:
            opts["locale"] = locale
        # sw.js가 옛 빌드를 저장해 두지 않도록 서비스 작업자는 막는다(오프라인은 build_test.py가 시험)
        self.context = e["browser"].new_context(service_workers="block", **opts)
        self.page = self.context.new_page()
        self.device = device
        self.errors = []
        self.page.on("pageerror", lambda x: self.errors.append("pageerror: " + str(x)))
        self.page.on("console", lambda m: self.errors.append("console.error: " + m.text) if m.type == "error" else None)
        if save is not None:
            self.page.add_init_script(
                "if (!sessionStorage.getItem('flow-seeded')) { localStorage.setItem(%s, %s); sessionStorage.setItem('flow-seeded', '1'); }"
                % (json.dumps(SAVE_KEY), json.dumps(json.dumps(save))))
        if init:
            self.page.add_init_script(init)
        for k, v in (extra or {}).items():
            self.page.add_init_script("if (!localStorage.getItem(%s)) localStorage.setItem(%s, %s);" % (json.dumps(k), json.dumps(k), json.dumps(v)))
        self.page.goto(url or e["url"])
        self.page.wait_for_selector(".screen.splash #go", timeout=20_000)

    def close(self):
        self.context.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    # -- 공용 동작 --
    def shot(self, name, full=False):
        path = os.path.join(OUT, name)
        self.page.screenshot(path=path, full_page=full)
        return path

    def js(self, expr, arg=None):
        return self.page.evaluate(expr, arg)

    def save(self):
        return self.js("() => JSON.parse(localStorage.getItem(%s))" % json.dumps(SAVE_KEY))

    def dismiss(self):
        """홈 화면 추가 안내(iOS 사파리 흉내 UA라서 뜰 수 있음)·확인되지 않은 창을 닫는다. 닫은 이름 목록."""
        closed = []
        for _ in range(3):
            if self.page.is_visible("#ins-ok"):
                self.page.wait_for_timeout(100)
                self.page.click("#ins-ok")
                self.page.wait_for_selector(".modal.install", state="detached")
                closed.append("install")
                continue
            break
        return closed

    def start(self):
        self.page.click("#go")
        self.page.wait_for_selector("#app[data-screen=home] .screen.home")
        self.page.wait_for_timeout(200)
        self.dismiss()

    def lesson(self, lid):
        # 레슨 목록(index.html)에는 문제가 없어 장 파일에서 받는다(v0.3 작업 1)
        return self.js("(id) => window.__ria.ctx.getLesson(id)", lid)

    def which_item(self, items):
        """지금 화면의 문제가 레슨 items의 몇 번인지 (보기 순서가 섞여 있어도 글자 묶음으로 찾음)"""
        norm = lambda v: " ".join(str(v or "").split())
        q = self.page.eval_on_selector("h1.q", SHOWN_JS)
        shown = sorted(t.strip() for t in self.page.eval_on_selector_all(
            ".opt .opt-text, .chip, #op .line", "es => es.map(%s)" % SHOWN_JS))
        code = self.page.eval_on_selector_all("article.item > pre.code", "es => es.map(e => e.innerText).join('')")

        def keyset(x):
            return sorted(plain(str(v)).strip() for v in (x.get("options") or x.get("chips") or x.get("lines") or []))
        # 빈칸 문제는 질문·보기가 같을 수 있어 예문까지 본다
        sent = self.page.eval_on_selector(".sent .sent-jp", SHOWN_JS) if self.page.query_selector(".sent .sent-jp") else None
        cands = [i for i, x in enumerate(items) if norm(plain(x.get("q"))) == norm(q) and keyset(x) == shown
                 and ((plain(x["sentence"]["jp"]) if x.get("sentence") else None) == sent)]
        if len(cands) > 1:
            cands = [i for i in cands if norm(items[i].get("code")) == norm(code)] or cands
        assert cands, "unknown item on screen: %r %r" % (q, shown)
        return cands[0]

    def answer_touch(self, it, correct=True):
        t = it["type"]
        if t in ("choice", "check"):
            right = it["options"][it["answer"]]
            target = right if correct else next(o for o in it["options"] if o != right)
            for b in self.page.query_selector_all(".opt"):
                if b.query_selector(".opt-text").evaluate(SHOWN_JS).strip() == plain(target):
                    b.click()
                    break
        elif t == "order":
            lines = list(it["lines"]) if correct else list(it["lines"][1:]) + [it["lines"][0]]
            for line in lines:
                for b in self.page.query_selector_all("#op .line:not([disabled])"):
                    if b.inner_text().strip() == line.strip():
                        b.click()
                        break
        self.page.click("#act")

    def cont(self):
        """결과 창의 「계속」 (입력 보호 시간 뒤)"""
        ok = "ok" in (self.page.get_attribute("#result", "class") or "")
        self.page.wait_for_timeout(GUARD_WAIT)
        self.page.click("#cont")
        return ok

    def play(self, lid, wrong=(), hook=None):
        """레슨 lid를 끝까지 푼다. wrong: 처음 한 번 틀릴 문제 번호들. hook(name, app): 화면별로 부름.
        돌려줌: 본 문제 순서 ["0", "1", ..., "0r", ...]"""
        items = self.lesson(lid)["items"]
        seq = []
        wrong_left = set(wrong)
        first_card = first_touch = True
        for _ in range(60):
            self.page.wait_for_timeout(80)
            if self.page.query_selector(".screen.done"):
                break
            if self.page.query_selector(".card-view"):
                if first_card and hook:
                    hook("lesson-card", self)
                first_card = False
                self.page.click("#act")
                continue
            if not self.page.query_selector("article.item"):
                continue
            idx = self.which_item(items)
            retry = self.page.query_selector(".tag.retry") is not None
            seq.append(str(idx) + ("r" if retry else ""))
            it = items[idx]
            bad = False
            if first_touch and hook:
                hook("touch-item", self)
            first_touch = False
            bad = idx in wrong_left
            wrong_left.discard(idx)
            self.answer_touch(it, correct=not bad)
            self.page.wait_for_selector("#result:not([hidden])")
            ok = self.cont()
            assert ok == (not bad), "item %d (%s) judged ok=%s, expected %s" % (idx, it["type"], ok, not bad)
        self.page.wait_for_selector(".screen.done", timeout=10_000)
        self.page.wait_for_timeout(300)
        return seq

    def result(self):
        return self.js("() => window.__ria.app.params && window.__ria.app.params.result")


# ---------------------------------------------------------------- 화면 측정

MEASURE_JS = r"""() => {
  const vw = window.innerWidth, vh = window.innerHeight;
  const sel = 'button, a[href], input:not([type=hidden]), select, textarea, label.btn, [role=button], [role=radio], [role=switch], [role=tab]';
  const items = [];
  for (const e of document.querySelectorAll(sel)) {
    if (e.closest('[hidden]')) continue;
    const cs = getComputedStyle(e);
    if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) continue;
    const r = e.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) continue;          // .sr로 숨긴 파일 입력 등
    let fixed = false, scroller = false;
    for (let p = e; p && p !== document.body; p = p.parentElement) {
      const ps = getComputedStyle(p);
      if (ps.position === 'fixed' || ps.position === 'sticky') fixed = true;
      if (p !== e && /(auto|scroll)/.test(ps.overflowX) && p.scrollWidth > p.clientWidth + 1) scroller = true;
    }
    const text = (e.getAttribute('aria-label') || e.innerText || e.value || '').trim().replace(/\s+/g, ' ').slice(0, 24);
    const name = e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (e.classList.length ? '.' + [...e.classList].join('.') : '') + ' "' + text + '"';
    items.push({ name, l: r.left, r: r.right, t: r.top, b: r.bottom, w: r.width, h: r.height, fixed, scroller });
  }
  return { vw, vh, sw: document.documentElement.scrollWidth, bsw: document.body.scrollWidth, items };
}"""


def measure(app, screen):
    m = app.js(MEASURE_JS)
    problems = []
    if max(m["sw"], m["bsw"]) > m["vw"]:
        problems.append("horizontal scroll: scrollWidth %d > %d" % (max(m["sw"], m["bsw"]), m["vw"]))
    # 가로 스크롤을 시도해서 실제로 움직이는지도 확인
    sx = app.js("() => { window.scrollTo(200, window.scrollY); const x = window.scrollX; window.scrollTo(0, window.scrollY); return x; }")
    if sx:
        problems.append("page scrolls horizontally by %dpx" % sx)
    offscreen, small, scrolled = [], [], []
    for it in m["items"]:
        out_h = it["l"] < -1 or it["r"] > m["vw"] + 1
        out_v = it["fixed"] and (it["t"] < -1 or it["b"] > m["vh"] + 1)
        if out_h or out_v:
            (scrolled if it["scroller"] and not out_v else offscreen).append(
                "%s [%d,%d..%d,%d]" % (it["name"], it["l"], it["t"], it["r"], it["b"]))
        if (it["w"] < 43.5 or it["h"] < 43.5) and it["name"] not in TOUCH_EXCEPTIONS:
            small.append("%s %dx%d" % (it["name"], round(it["w"]), round(it["h"])))
    problems += ["offscreen: " + x for x in offscreen]
    return {"screen": screen, "problems": problems, "small": small, "in_scroller": scrolled,
            "errors": list(app.errors), "count": len(m["items"])}


_traversals = {}


def traverse(device):
    """새 저장으로 화면을 차례로 열어 측정하고 캡처한다(기기마다 한 번, 결과는 다시 씀)."""
    if device in _traversals:
        return _traversals[device]
    res = {}
    tag = slug(device)
    with App(device) as a:
        def at(name, app, full=False):
            app.page.wait_for_timeout(150)
            res[name] = measure(app, name)
            app.shot("%s-%s.png" % (tag, name), full=full)
            app.errors.clear()

        at("splash", a)
        a.start()
        at("home", a)
        a.page.click("#continue")
        a.page.wait_for_selector(".screen.lesson")
        a.play("1-1", hook=lambda n, app: at(n, app))
        if a.page.is_visible("#ins-ok"):
            at("install-sheet", a)
            a.dismiss()
        at("done", a, full=False)
        a.page.click("#home")
        a.page.wait_for_selector(".screen.home")
        if a.page.is_visible("#ins-ok"):
            at("install-sheet", a)
            a.dismiss()
        for name in ("jlpt", "badges", "closet", "settings"):
            a.page.click('[data-go="%s"]' % name)
            a.page.wait_for_selector(".screen.%s" % name)
            at(name, a)
        res["_errors_left"] = list(a.errors)
    _traversals[device] = res
    return res


# ---------------------------------------------------------------- 시험

def test_no_overflow():
    fails = []
    for dev in DEVICES:
        res = traverse(dev)
        missing = [s for s in SCREENS if s not in res]
        if missing:
            fails.append("%s: screens not reached %s" % (dev, missing))
        for s, r in res.items():
            if s.startswith("_"):
                if r:
                    fails.append("%s: console errors %s" % (dev, r))
                continue
            for p in r["problems"]:
                fails.append("%s/%s: %s" % (dev, s, p))
            for e in r["errors"]:
                fails.append("%s/%s: %s" % (dev, s, e))
            if r["in_scroller"]:
                print("    note %s/%s: inside horizontal scroller (partly hidden by design): %s" % (dev, s, r["in_scroller"]))
        print("    %s: %s" % (dev, ", ".join("%s(%d)" % (s, r["count"]) for s, r in res.items() if not s.startswith("_"))))
    assert not fails, "\n".join(fails)


def test_touch_targets():
    fails = []
    for dev in DEVICES:
        res = traverse(dev)
        for s, r in res.items():
            if not s.startswith("_") and r["small"]:
                fails.append("%s/%s: %s" % (dev, s, "; ".join(r["small"])))
    assert not fails, "touch targets < 44x44:\n" + "\n".join(fails)


def _n_items(a, lid):
    return len(a.lesson(lid)["items"])


def test_first_lesson():
    with App("iPhone 17") as a:
        a.start()
        assert "첫 레슨 시작" in a.page.inner_text("#continue")
        a.page.click("#continue")
        seq = a.play("1-1")
        n = _n_items(a, "1-1")
        assert seq == [str(i) for i in range(n)], seq
        xp_tile = a.page.inner_text(".tile.xp b")
        a.shot("first-lesson-done.png", full=True)
        r = a.result()
        s = a.save()
        print("    done tiles: %s | result xp=%s bytes=%s perfect=%s" % (
            a.page.inner_text(".tiles").replace("\n", " "), r["xp"], r["totalBytes"], r["perfect"]))
        assert xp_tile == "+15", xp_tile
        assert r["xp"] == 15 and r["perfect"] and r["firstTime"], r
        assert s["completed_lessons"] == ["1-1"], s["completed_lessons"]
        a.dismiss()
        assert not a.errors, a.errors


def test_wrong_then_retry():
    with App("iPhone 17") as a:
        a.start()
        a.page.click("#continue")
        seq = a.play("1-1", wrong=(0,))
        r = a.result()
        a.shot("retry-done.png", full=True)
        acc = a.page.inner_text(".tile.acc b")
        print("    sequence %s, accuracy tile %s, perfect %s" % (seq, acc, r["perfect"]))
        n = _n_items(a, "1-1")
        # 0번을 틀림 → 본 문제 뒤에 0번을 다시, 그다음 이해도 확인(마지막)
        assert seq == [str(i) for i in range(n - 1)] + ["0r", str(n - 1)], seq
        assert r["perfect"] is False and r["xp"] == 10, r
        assert acc != "100%", acc
        assert "실수 없이 끝냄" not in a.page.inner_text(".screen.done")
        s = a.save()
        assert s["grading_results"]["1-1"]["perfect"] is False, s["grading_results"]
        a.dismiss()
        assert not a.errors, a.errors


def test_status_after_milestone():
    seed = {"saveVer": 1, "xp": 100, "bytes": 0, "completed_lessons": [],
            "streak": {"days": 6, "best": 6, "lastGoalDate": today(1), "todayDate": today(), "todayXp": 0},
            "settings": {"sound": True, "dailyGoal": 10, "name": ""}}
    fails = []
    # 가) 레슨 완료로 7일 → 축하 창
    with App("iPhone 17", save=seed) as a:
        a.start()
        assert a.page.inner_text(".status .stat.flame b") == "6"
        a.page.click("#continue")
        a.play("1-1")
        a.page.wait_for_selector(".celebrate", timeout=3000)
        bars = a.js("() => [...document.querySelectorAll('.status .stat.flame b')].map(e => e.textContent)")
        tile = a.page.inner_text(".tile.flame b")
        a.shot("milestone-lesson.png")
        print("    lesson path: status bars behind overlay %s, done tile %s, overlay %r" % (
            bars, tile, a.page.inner_text(".celebrate .cel-title")))
        if any(b != "7" for b in bars):
            fails.append("lesson path: status bar shows %s while overlay open" % bars)
        if tile != "7":
            fails.append("lesson path: done tile %s" % tile)
        a.page.wait_for_timeout(GUARD_WAIT)
        a.page.click("#cel-ok")
        a.page.wait_for_selector(".celebrate", state="detached")
        a.dismiss()
        a.page.click("#home")
        a.page.wait_for_selector(".screen.home")
        a.dismiss()
        home = a.page.inner_text(".status .stat.flame b")
        if home != "7":
            fails.append("lesson path: home shows %s" % home)
        if a.errors:
            fails.append("lesson path errors: %s" % a.errors)
    # 나) 설정에서 목표를 낮춰 7일 → 축하 창 (상태 줄이 같은 화면에 있음; 실행 기록 작업 9 남은 경미)
    seed2 = dict(seed, streak=dict(seed["streak"], todayXp=12), settings=dict(seed["settings"], dailyGoal=20))
    with App("iPhone 17", save=seed2) as a:
        a.start()
        a.page.click('[data-go="settings"]')
        a.page.wait_for_selector(".screen.settings")
        a.page.click('[data-g="10"]')
        a.page.wait_for_selector(".celebrate", timeout=3000)
        a.page.wait_for_timeout(100)
        bars = a.js("() => [...document.querySelectorAll('.status .stat.flame b')].map(e => e.textContent)")
        a.shot("milestone-settings.png")
        print("    settings path: status bars behind overlay %s" % bars)
        if not bars or any(b != "7" for b in bars):
            fails.append("settings path: status bar shows %s while overlay open" % bars)
        a.page.wait_for_timeout(GUARD_WAIT)
        a.page.click("#cel-ok")
        a.page.wait_for_selector(".celebrate", state="detached")
        after = a.page.inner_text(".status .stat.flame b")
        if after != "7":
            fails.append("settings path: after closing shows %s" % after)
        if a.errors:
            fails.append("settings path errors: %s" % a.errors)
    assert not fails, "\n".join(fails)


# ---------------------------------------------------------------- 해치와 한국어 v0.1

def test_ipad_zoomed():
    zoom = "() => getComputedStyle(document.documentElement).zoom"
    for dev, want in (("iPad Pro 11", "1.3"), ("iPad Pro 11 landscape", "1.3"), ("iPhone 17", "1")):
        with App(dev) as a:
            got = a.js(zoom)
            print("    %s: zoom %s" % (dev, got))
            assert got == want, (dev, got)


def test_no_text_inputs():
    q = "() => document.querySelectorAll('input:not([type=hidden]):not([type=file]), textarea, [contenteditable]').length"
    with App("iPhone 17") as a:
        a.start()
        a.page.click("#continue")
        seen = []
        a.play("1-1", hook=lambda n, app: seen.append((n, app.js(q))))
        seen.append(("done", a.js(q)))
        print("    inputs per screen: %s" % seen)
        assert all(n == 0 for _, n in seen), seen


def _longest_meaning_lesson():
    """가장 긴 보기가 든 레슨 id와 그 보기(화면 글자: 후리가나 뺀 표기)"""
    best = (0, None, None)
    for f in sorted(os.listdir(os.path.join(ROOT, "data", "lessons"))):
        text = open(os.path.join(ROOT, "data", "lessons", f), encoding="utf-8").read()
        data = json.loads(text.split("export const LESSONS = ", 1)[1].rstrip().rstrip(";"))
        for l in data:
            for it in l["items"]:
                for o in it.get("options", []):
                    if len(o) > best[0]:
                        best = (len(o), l["id"], plain(o))
    return best[1], best[2]


def test_longest_meaning_fits():
    lid, text = _longest_meaning_lesson()
    fits = """(t) => { const SHOWN = %s; return [...document.querySelectorAll('.opt')].filter(b => SHOWN(b).includes(t))
        .map(b => ({ sw: b.scrollWidth, cw: b.clientWidth, right: b.getBoundingClientRect().right, vw: innerWidth })); }""" % SHOWN_JS
    with App("iPhone 17e") as a:
        a.start()
        a.js("(id) => window.__ria.ctx.show('lesson', { id })", lid)
        found = []
        items = a.lesson(lid)["items"]
        for _ in range(40):
            a.page.wait_for_timeout(80)
            if a.page.query_selector(".screen.done"):
                break
            if a.page.query_selector(".card-view"):
                a.page.click("#act")
                continue
            if not a.page.query_selector("article.item"):
                continue
            found += a.js(fits, text)
            if found:
                a.shot("longest-meaning.png")
                break
            a.answer_touch(items[a.which_item(items)])
            a.page.wait_for_selector("#result:not([hidden])")
            a.cont()
        print("    %s %r: %s" % (lid, text, found))
        assert found, "longest meaning not shown as an option in " + lid
        assert all(f["sw"] <= f["cw"] + 1 and f["right"] <= f["vw"] + 1 for f in found), found
        assert not a.errors, a.errors


def _first_lesson_with(kind):
    for n in range(3, 40):
        path = os.path.join(ROOT, "data", "lessons", "ch%d.js" % n)
        if not os.path.exists(path):
            break
        for l in json.loads(open(path, encoding="utf-8").read().split("export const LESSONS = ", 1)[1].rstrip().rstrip(";")):
            if not l.get("isExam") and any(it["type"] == kind for it in l["items"]):
                return l["id"]
    raise AssertionError("no lesson with " + kind)


def test_no_code_font():
    """가나 카드·보기에 코드(고정폭) 글꼴이 쓰이지 않음 (가나 카드 문제가 있는 첫 단어 레슨)"""
    q = "() => [...document.querySelectorAll('.mono')].filter(e => e.offsetParent).length"
    lid = _first_lesson_with("order")
    with App("iPhone 17") as a:
        a.start()
        a.js("(id) => window.__ria.ctx.show('lesson', { id })", lid)
        seen = []
        items = a.lesson(lid)["items"]
        for _ in range(40):
            a.page.wait_for_timeout(80)
            if a.page.query_selector(".screen.done"):
                break
            if a.page.query_selector(".card-view"):
                a.page.click("#act")
                continue
            if not a.page.query_selector("article.item"):
                continue
            it = items[a.which_item(items)]
            seen.append((it["type"], a.js(q)))
            a.answer_touch(it)
            a.page.wait_for_selector("#result:not([hidden])")
            a.cont()
        print("    mono per item: %s" % seen)
        assert any(t == "order" for t, _ in seen), seen
        assert all(n == 0 for _, n in seen), seen


def test_exam_done_has_no_empty_summary():
    with App("iPhone 17") as a:
        a.start()
        exam = a.js("() => window.__ria.ctx.chapters[0].lessons.find((l) => l.isExam).id")
        a.js("(id) => window.__ria.ctx.show('lesson', { id })", exam)
        a.page.wait_for_selector("article.item, .card-view")
        a.play(exam)
        n = a.js("() => document.querySelectorAll('.panel.summary').length")
        print("    %s done: summary panels %d" % (exam, n))
        assert n == 0


def _lesson_ids(chapters):
    ids = []
    for n in chapters:
        text = open(os.path.join(ROOT, "data", "lessons", "ch%d.js" % n), encoding="utf-8").read()
        ids += [l["id"] for l in json.loads(text.split("export const LESSONS = ", 1)[1].rstrip().rstrip(";"))]
    return ids


def test_words_open_after_kana():
    """히라가나·가타카나 장을 끝내면 1과(앱 3장)가 열리고 풀 수 있다"""
    done = _lesson_ids(range(1, 3))
    seed = {"saveVer": 2, "xp": 600, "completed_lessons": done, "current_lesson": "3-1", "current_chapter": 3}
    with App("iPhone 17", save=seed) as a:
        a.start()
        btn = a.page.inner_text("#continue")
        titles = a.js("() => [...document.querySelectorAll('.chapter-title')].map(e => e.innerText)")
        print("    continue %r, chapter titles shown %s" % (btn, titles))
        assert "3-1" in btn and "이어서 배우기" in btn, btn
        assert any("1과 · 장소 묻기" in t for t in titles), titles
        a.page.click("#continue")
        a.play("3-1")
        assert "3-1" in a.save()["completed_lessons"]
        a.dismiss()
        assert not a.errors, a.errors


def test_lesson13_opens_after_lesson12():
    """1~12과(앱 1~14장)를 끝내면 13과(앱 15장)가 열리고 풀 수 있다"""
    done = _lesson_ids(range(1, 15))
    seed = {"saveVer": 2, "xp": 3000, "completed_lessons": done, "current_lesson": "15-1", "current_chapter": 15}
    with App("iPhone 17", save=seed) as a:
        a.start()
        btn = a.page.inner_text("#continue")
        titles = a.js("() => [...document.querySelectorAll('.chapter-title')].map(e => e.innerText)")
        print("    continue %r" % btn)
        assert "15-1" in btn and "이어서 배우기" in btn, btn
        assert any("13과 · 하고 싶은 것" in t for t in titles), titles
        a.page.click("#continue")
        a.play("15-1")
        assert "15-1" in a.save()["completed_lessons"]
        a.dismiss()
        assert not a.errors, a.errors


def _fill_lesson(longest=False):
    """예문 빈칸 문제가 있는 일반 레슨 (lesson_id, 문제 번호). longest면 예문이 가장 긴 것"""
    best = None
    for f in sorted(os.listdir(os.path.join(ROOT, "data", "lessons"))):
        text = open(os.path.join(ROOT, "data", "lessons", f), encoding="utf-8").read()
        for l in json.loads(text.split("export const LESSONS = ", 1)[1].rstrip().rstrip(";")):
            if l.get("isExam"):
                continue
            for i, it in enumerate(l["items"]):
                if it.get("sentence") and it["type"] == "choice":
                    n = len(plain(it["sentence"]["jp"])) + len(it["sentence"]["ko"])
                    if not longest:
                        return l["id"], i
                    if best is None or n > best[2]:
                        best = (l["id"], i, n)
    return best[0], best[1]


def _play_to_item(a, lid, idx):
    a.js("(id) => window.__ria.ctx.show('lesson', { id })", lid)
    items = a.lesson(lid)["items"]
    for _ in range(60):
        a.page.wait_for_timeout(80)
        if a.page.query_selector(".card-view"):
            a.page.click("#act")
            continue
        if not a.page.query_selector("article.item"):
            continue
        k = a.which_item(items)
        if k == idx:
            return items[k]
        a.answer_touch(items[k])
        a.page.wait_for_selector("#result:not([hidden])")
        a.cont()
    raise AssertionError("item %d of %s not reached" % (idx, lid))


def test_fill_item_shows_sentence():
    """예문 빈칸: 일본어 예문(후리가나·빈칸 하나)과 한국어 뜻 힌트가 보이고, 맞히면 결과 창 🔊가 예문 전체를 읽는다"""
    lid, idx = _fill_lesson()
    fake = ("Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: { cancel() {}, "
            "speak(u) { window.__said = u.text; } } }); window.SpeechSynthesisUtterance = function (t) { this.text = t; };")
    with App("iPhone 17", init=fake) as a:
        a.start()
        it = _play_to_item(a, lid, idx)
        jp = a.page.eval_on_selector(".sent .sent-jp", SHOWN_JS)
        hint = a.page.inner_text(".sent .sent-hint")
        print("    %s #%d: %r / %r" % (lid, idx, jp, hint))
        assert jp == plain(it["sentence"]["jp"]), jp
        assert a.js("() => document.querySelectorAll('.sent .blank').length") == 1
        assert it["sentence"]["ko"] in hint
        if "{" in it["sentence"]["jp"]:
            assert a.js("() => document.querySelectorAll('.sent rt').length") > 0
        a.answer_touch(it)
        a.page.wait_for_selector("#result:not([hidden])")
        a.page.locator("#result .say-btn").click()
        assert a.js("() => window.__said") == kana(it["say"]), a.js("() => window.__said")
        assert not a.errors, a.errors


def test_fill_sentence_fits():
    """가장 긴 예문이 아이폰 작은 화면·아이패드에서 넘치지 않음"""
    lid, idx = _fill_lesson(longest=True)
    for dev in ("iPhone 17e", "iPad Pro 11"):
        with App(dev) as a:
            a.start()
            _play_to_item(a, lid, idx)
            m = a.js("""() => { const b = document.querySelector('.sent'); const r = b.getBoundingClientRect();
                return { sw: b.scrollWidth, cw: b.clientWidth, right: r.right, vw: innerWidth, hsc: document.documentElement.scrollWidth }; }""")
            print("    %s %s #%d: %s" % (dev, lid, idx, m))
            a.shot("fill-longest-%s.png" % slug(dev))
            assert m["sw"] <= m["cw"] + 1 and m["right"] <= m["vw"] + 1 and m["hsc"] <= m["vw"] + 1, m


# ---------------------------------------------------------------- 다코야키 가게

def _kana_done_save(**shop):
    seed = {"saveVer": 2, "completed_lessons": _lesson_ids(range(1, 3)), "current_lesson": "3-1", "current_chapter": 3}
    if shop:
        seed["shop"] = {"v": 1, "day": 0, "money": 0, "upgrades": [], "stories": [], "xpToday": {"date": None, "n": 0}, "run": None, **shop}
    return seed


SHOP_ANSWER_JS = """() => { const c = window.__ria.ctx, R = c.shopRules, run = c.save.shop.run;
  const g = R.dayCustomers(run)[run.idx], seed = run.seed + ':' + run.idx;
  if (run.step === 'order') return { menu: g.menu, count: g.count, who: g.who, step: run.step, idx: run.idx };
  return { i: R.greetCards(run.step === 'greet' ? 'enter' : 'leave', seed).answer, who: g.who, step: run.step, idx: run.idx }; }"""


def _shop_answer(a):
    """지금 단계의 정답 카드를 누르고 확인 → 결과 창 계속"""
    ans = a.js(SHOP_ANSWER_JS)
    if ans["step"] == "order":
        a.page.click('.menu-card[data-menu="%s"]' % ans["menu"])
        if a.page.query_selector(".count-card"):
            a.page.click('.count-card[data-count="%d"]' % ans["count"])
    else:
        a.page.click('.options .opt[data-i="%d"]' % ans["i"])
    a.page.click("#act")
    a.page.wait_for_selector("#result:not([hidden])")
    ok = "ok" in (a.page.get_attribute("#result", "class") or "")
    a.page.wait_for_timeout(GUARD_WAIT)
    a.page.click("#cont")
    a.page.wait_for_timeout(120)
    return ok


def _shop_play_day(a):
    oks = []
    for _ in range(80):
        if a.page.query_selector(".shop-settle"):
            return oks
        if a.page.query_selector(".shop-cut"):
            a.page.click("#act")
            a.page.wait_for_timeout(120)
            continue
        oks.append(_shop_answer(a))
    raise AssertionError("day did not end")


def test_shop_locked_then_open():
    with App("iPhone 17") as a:
        a.start()
        assert a.page.is_disabled("#shop")
        assert "가타카나 평가를 통과하면 열려요" in a.page.inner_text(".shop-card")
        assert a.page.get_attribute("#shop", "aria-label") == "잠김", "icon-only locked button needs a name"
    with App("iPhone 17", save=_kana_done_save()) as a:
        a.start()
        assert not a.page.is_disabled("#shop")
        a.page.click("#shop")
        a.page.wait_for_selector(".shop-front")
        assert not a.errors, a.errors


def test_shop_full_day():
    """하루 6명을 모두 맞히면: 정산 매출 = 팁 포함 합계, XP +10, 1일째 이야기 컷"""
    with App("iPhone 17", save=_kana_done_save()) as a:
        a.start()
        a.page.click("#shop")
        a.page.click("#start")
        guests = a.js("() => window.__ria.ctx.shopRules.dayCustomers(window.__ria.ctx.save.shop.run)")
        price = {"takoyaki": 400, "ocha": 150}  # 설계 §3-1 처음 메뉴 값, 팁 10%(1円 아래 버림)
        expect = sum(price[g["menu"]] * g["count"] + price[g["menu"]] * g["count"] // 10 for g in guests)
        oks = _shop_play_day(a)
        assert oks == [True] * 18, oks
        s = a.save()
        print("    expect %d, saved money %d, xp %d" % (expect, s["shop"]["money"], s["xp"]))
        assert s["shop"]["money"] == expect and s["shop"]["day"] == 1 and s["shop"]["run"] is None
        assert s["xp"] == 10 and s["shop"]["stories"] == ["story-01"]
        txt = a.page.inner_text(".screen.shop")
        assert "6/6" in txt and "{:,}円".format(expect) in txt and "부모님과 인사!" in txt, txt
        assert not a.errors, a.errors


def test_shop_settle_rewards():
    """정산 XP로 7일 연속이 되면 축하 창, 일일 퀘스트를 끝내면 「끝낸 퀘스트」 (레슨 완료와 같게)"""
    seed = _kana_done_save()
    seed["streak"] = {"days": 6, "best": 6, "lastGoalDate": today(1), "todayDate": today(), "todayXp": 10}
    seed["quests"] = {"date": today(), "ids": ["q_xp20", "q_lessons2", "q_review3"], "progress": {"q_xp20": 10}, "done": [], "chest": False}
    with App("iPhone 17", save=seed) as a:
        a.start()
        a.page.click("#shop")
        a.page.click("#start")
        _shop_play_day(a)
        a.page.wait_for_selector(".celebrate")
        assert "7일 연속" in a.page.inner_text(".celebrate")
        a.page.wait_for_timeout(GUARD_WAIT)
        a.page.click("#cel-ok")
        a.page.wait_for_selector(".celebrate", state="detached")
        txt = a.page.inner_text(".shop-settle-quests")
        assert "20 XP 얻기" in txt, txt
        assert not a.errors, a.errors


def test_shop_quit_locked_during_result():
    """결과 창이 떠 있는 동안 「가게 앞으로」(그만하기)는 누를 수 없음 — 「계속」 전에 나가 손님 결과를 잃지 않게"""
    with App("iPhone 17", save=_kana_done_save()) as a:
        a.start()
        a.page.click("#shop")
        a.page.click("#start")
        while a.page.query_selector(".shop-cut"):
            a.page.click("#act")
            a.page.wait_for_timeout(120)
        assert not a.page.is_disabled("#quit")
        ans = a.js(SHOP_ANSWER_JS)
        a.page.click('.options .opt[data-i="%d"]' % ans["i"])
        a.page.click("#act")
        a.page.wait_for_selector("#result:not([hidden])")
        assert a.page.is_disabled("#quit"), "quit must be locked while the result panel is open"
        assert not a.errors, a.errors


def test_shop_keyboard():
    """아이패드 키보드: 화면 제목에 초점, 숫자로 카드 고르기, Enter로 확인"""
    with App("iPad Pro 11", save=_kana_done_save()) as a:
        a.start()
        a.page.click("#shop")
        a.page.wait_for_selector(".shop-front")
        assert a.js("() => document.activeElement.matches('h1')"), "front screen heading gets focus"
        a.page.click("#start")
        while a.page.query_selector(".shop-cut"):
            a.page.click("#act")
            a.page.wait_for_timeout(120)
        assert a.js("() => document.activeElement.matches('h1')"), "day screen heading gets focus"
        ans = a.js(SHOP_ANSWER_JS)
        a.page.keyboard.press(str(ans["i"] + 1))
        assert a.page.get_attribute('.options .opt[data-i="%d"]' % ans["i"], "aria-checked") == "true"
        a.page.keyboard.press("Enter")
        a.page.wait_for_selector("#result:not([hidden])")
        a.page.wait_for_timeout(GUARD_WAIT)
        a.page.keyboard.press("Enter")
        a.page.wait_for_selector("#result", state="hidden")
        ans = a.js(SHOP_ANSWER_JS)
        assert ans["step"] == "order"
        menus = a.js("() => window.__ria.ctx.save.shop.run.ctx.menus")
        a.page.keyboard.press(str(menus.index(ans["menu"]) + 1))
        assert a.page.get_attribute('.menu-card[data-menu="%s"]' % ans["menu"], "aria-checked") == "true"
        assert not a.errors, a.errors


def test_shop_result_focus():
    """결과 창이 열리면 키보드 초점이 「계속」으로(레슨과 같게)"""
    with App("iPhone 17", save=_kana_done_save()) as a:
        a.start()
        a.page.click("#shop")
        a.page.click("#start")
        a.page.click("#act")  # 오픈 컷
        a.page.locator(".options .opt").first.click()
        a.page.click("#act")
        a.page.wait_for_selector("#result:not([hidden])")
        a.page.wait_for_timeout(100)
        assert a.js("() => document.activeElement && document.activeElement.id") == "cont"


def test_shop_resume():
    """3번째 손님 주문 단계에서 새로 고침 → 같은 손님·같은 단계"""
    with App("iPhone 17", save=_kana_done_save()) as a:
        a.start()
        a.page.click("#shop")
        a.page.click("#start")
        for _ in range(40):
            if a.page.query_selector(".shop-cut"):
                a.page.click("#act")
                a.page.wait_for_timeout(120)
                continue
            st = a.js("() => window.__ria.ctx.save.shop.run")
            if st["idx"] == 2 and st["step"] == "order":
                break
            _shop_answer(a)
        name = a.page.inner_text(".guest-name")
        a.page.reload()
        a.page.wait_for_selector("#go")
        a.start()
        assert "이어서 장사" in a.page.inner_text("#shop")
        a.page.click("#shop")
        a.page.click("#start")
        a.page.wait_for_selector(".guest-name")
        print("    before %r, after %r" % (name, a.page.inner_text(".guest-name")))
        assert a.page.inner_text(".guest-name") == name
        assert a.page.query_selector(".menu-card") is not None, "still the order step"
        assert not a.errors, a.errors


def test_shop_upgrade_guests():
    with App("iPhone 17", save=_kana_done_save(money=5000)) as a:
        a.start()
        a.page.click("#shop")
        a.page.click("#upgrades")
        a.page.click('[data-up="plate2"]')
        a.page.wait_for_timeout(200)
        assert a.save()["shop"]["upgrades"] == ["plate2"] and a.save()["shop"]["money"] == 0
        a.page.click("#back")
        a.page.click("#start")
        a.page.click("#act")  # 오픈 컷
        a.page.wait_for_selector(".shop-progress")
        assert "손님 1/7" in a.page.inner_text(".shop-progress")
        assert not a.errors, a.errors


def test_shop_screens_fit():
    """가게 앞·인사·주문(개수 카드)·정산·키우기·일기: 기기 5종 넘침 없음, 터치 44px 이상"""
    fails = []
    for dev in DEVICES:
        with App(dev, save=_kana_done_save(money=99999, day=8, stories=["story-01", "story-02"])) as a:
            a.start()
            a.page.click("#shop")
            res = [measure(a, "shop-front")]
            a.js("() => { const c = window.__ria.ctx; c.commit({ ...c.save, shop: c.shopRules.startRun(c.save.shop, { date: c.today(), doneCh: 12 }) }); c.show('shop', { view: 'day' }); }")
            res.append(measure(a, "shop-greet"))
            _shop_answer(a)
            res.append(measure(a, "shop-order"))
            a.shot("%s-shop-order.png" % slug(dev))
            for v in ("upgrades", "diary"):
                a.js("(v) => window.__ria.ctx.show('shop', { view: v })", v)
                res.append(measure(a, "shop-" + v))
            for r in res:
                if r["problems"] or r["small"]:
                    fails.append("%s/%s: %s %s" % (dev, r["screen"], r["problems"], r["small"]))
            assert not a.errors, a.errors
    assert not fails, fails


def test_other_saves_coexist():
    """같은 github.io 주소의 리아·해치 앱 저장을 읽지도 바꾸지도 않음"""
    ria = json.dumps({"saveVer": 2, "xp": 777, "completed_lessons": ["1-1", "1-2"]})
    haechi = json.dumps({"saveVer": 2, "xp": 555, "completed_lessons": ["1-1"], "items": ["none", "janggu"]})
    with App("iPhone 17", extra={RIA_KEY: ria, HAECHI_KEY: haechi}) as a:
        a.start()
        assert a.page.inner_text(".status .stat.xp b") == "0", "another app's XP leaked into this app"
        a.page.click("#continue")
        a.play("1-1")
        a.dismiss()
        a.page.click("#home")
        a.page.wait_for_selector(".screen.home")
        assert a.js("(k) => localStorage.getItem(k)", RIA_KEY) == ria
        assert a.js("(k) => localStorage.getItem(k)", HAECHI_KEY) == haechi
        assert a.save()["completed_lessons"] == ["1-1"]


def test_furigana_and_speak():
    """단어 레슨: 새 단어 카드·보기에 후리가나(rt)가 보이고, 🔊 단추는 44px 이상이며 누르면 읽기(가나)를 넘긴다"""
    fake = ("Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: { cancel() {}, "
            "speak(u) { (window.__said = window.__said || []).push([u.text, u.lang]); } } });"
            "window.SpeechSynthesisUtterance = function (t) { this.text = t; };")
    for dev in ("iPhone 17e", "iPad Pro 11"):
        with App(dev, init=fake) as a:
            a.start()
            a.js("(id) => window.__ria.ctx.show('lesson', { id })", "4-1")
            a.page.wait_for_selector(".card-view")
            rts = a.js("() => [...document.querySelectorAll('.word-list rt')].map(r => r.getBoundingClientRect().height)")
            btns = a.js("() => [...document.querySelectorAll('.word-list .say-btn')].map(b => { const r = b.getBoundingClientRect(); return [r.width, r.height]; })")
            print("    %s: rt heights %s, speak buttons %s" % (dev, rts[:3], btns[:2]))
            assert rts and all(h > 4 for h in rts), rts
            assert btns and all(w >= 44 and h >= 44 for w, h in btns), btns
            a.page.locator(".word-list .say-btn").nth(1).click()
            said = a.js("() => window.__said")
            assert said and said[-1][1] == "ja-JP" and "{" not in said[-1][0], said
            a.shot("furigana-%s.png" % slug(dev))
            assert not a.errors, a.errors


def test_dev_mode_unlocks_and_keeps_record():
    """설정 맨 아래 개발자 모드: 켜면 모든 레슨·가게가 열리고 따로 저장, 끄면 학습 기록 그대로"""
    seed = {"saveVer": 2, "xp": 123, "completed_lessons": ["1-1"], "current_lesson": "1-2", "current_chapter": 1}
    last = _lesson_ids([26])[-1]
    state = "(id) => window.__ria.ctx.lessonState(id)"
    with App("iPhone 17", save=seed) as a:
        a.start()
        assert a.js(state, last) == "locked"
        _to_settings(a)
        assert a.js("() => [...document.querySelectorAll('main > *')].pop().matches('.devmode')"), "dev panel is last"
        a.page.click("#dev")
        a.page.wait_for_timeout(200)
        assert a.page.get_attribute("#dev", "aria-checked") == "true"
        assert a.js("() => document.activeElement.id") == "dev", "stays on the switch after redraw"
        assert a.page.query_selector(".ls.locked") is None, "course list all open"
        a.shot("devmode-on.png")
        assert a.js(state, last) == "open"
        assert a.js("() => window.__ria.ctx.save.xp") == 0, "dev slot is separate"
        a.page.click('[data-go="home"]')
        a.page.wait_for_selector(".screen.home")
        assert not a.page.is_disabled("#shop")
        assert a.save()["xp"] == 123 and a.save()["completed_lessons"] == ["1-1"], "learning record untouched"
        a.page.reload()
        a.page.wait_for_selector(".screen.splash #go")
        a.start()
        assert a.js(state, last) == "open", "dev mode survives reload"
        _to_settings(a)
        a.page.click("#dev")
        a.page.wait_for_timeout(200)
        assert a.page.get_attribute("#dev", "aria-checked") == "false"
        assert a.js(state, last) == "locked"
        assert a.js("() => window.__ria.ctx.save.xp") == 123
        assert "dev_mode" not in a.save()
        assert not a.errors, a.errors


def test_outfit_buy_wear():
    """보관함: 오사카 덴진 의상 사기 → 홈 인사에 의상 그림 → 벗기 → 표정 그림"""
    with App("iPhone 17", save={"saveVer": 2, "bytes": 500}) as a:
        a.start()
        a.page.click('[data-go="closet"]')
        a.page.wait_for_selector(".screen.closet")
        assert a.page.locator(".outfit-grid li").count() == 16
        a.page.click('[data-o="tenjin"]')
        a.page.click("#buy")
        assert a.save()["item"] == "tenjin" and a.save()["bytes"] == 380
        w = a.js("() => document.querySelector('.stage .yuki-img').getBoundingClientRect().width")
        assert w <= 175, "outfit picture keeps its 170px size, not the list button style (%s)" % w
        a.shot("outfit-closet.png")
        a.page.click('[data-go="home"]')
        a.page.wait_for_selector(".screen.home")
        assert a.page.query_selector('.screen.home img[src$="outfits/tenjin.png"]'), "home greeting wears the outfit"
        a.page.click('[data-go="closet"]')
        a.page.click('[data-o="tenjin"]')
        a.page.click("#unwear")
        assert a.save()["item"] == "none"
        a.page.click('[data-go="home"]')
        a.page.wait_for_selector(".screen.home")
        assert not a.page.query_selector('.screen.home img[src*="img/outfits/"]')
        assert a.page.query_selector('.screen.home .ria-row img[src*="img/yuki/"]')
        assert not a.errors, a.errors


def test_old_items_refund_notice():
    """옛 물건을 가진 저장: 연 뒤 돌려준 엔 안내 한 번, 엔 증가, 다시 열면 안내 없음"""
    old = {"saveVer": 2, "bytes": 10, "items": ["none", "dango", "kimono"], "item": "kimono"}
    with App("iPhone 17", save=old) as a:
        a.page.wait_for_selector("#toasts .toast")
        assert "물건 값 360엔을 돌려드렸어요" in a.page.inner_text("#toasts"), a.page.inner_text("#toasts")
        sv = a.save()
        assert sv["bytes"] == 370 and "item_refund" not in sv and sv["items"] == ["none"], sv
        a.page.wait_for_timeout(5500)
        assert "돌려드렸어요" in a.js("() => document.getElementById('toasts').innerText"), "refund notice stays longer than ordinary toasts"
        a.page.reload()
        a.page.wait_for_selector(".screen.splash #go")
        a.page.wait_for_timeout(500)
        assert "돌려드렸어요" not in (a.js("() => document.getElementById('toasts')?.innerText || ''"))
        assert a.save()["bytes"] == 370
        assert not a.errors, a.errors


def test_import_old_save_refund():
    """옛 물건이 든 저장 파일을 가져오면 그 자리에서 돌려준 엔 안내, 엔 증가"""
    old = {"app": "sanada-japanese", "saveVer": 2, "bytes": 0, "items": ["none", "kimono"], "item": "kimono"}
    path = os.path.join(OUT, "old-save.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(old, f)
    with App("iPhone 17") as a:
        a.start()
        _to_settings(a)
        a.page.set_input_files("#import", path)
        a.page.get_by_role("button", name="바꾸기").click()
        a.page.wait_for_selector(".screen.home")
        a.page.wait_for_function("() => (document.getElementById('toasts') || {}).innerText?.includes('돌려드렸어요')")
        assert "물건 값 300엔" in a.page.inner_text("#toasts")
        sv = a.save()
        assert sv["bytes"] == 300 and "item_refund" not in sv, sv
        assert not a.errors, a.errors


def test_jlpt_locked_then_open():
    """가나 전: JLPT 탭은 잠긴 안내 → 「가나 배우러 가기」는 학습 탭. 가나 뒤: N5 진행 요약과 「N5 · 1장」 이어서 배우기, 기기 5종 넘침 0"""
    with App("iPhone 17") as a:
        a.start()
        a.page.click('[data-go="jlpt"]')
        a.page.wait_for_selector(".screen.jlpt")
        assert "히라가나·가타카나를 끝내면 JLPT 공부가 열려요" in a.page.inner_text(".screen.jlpt")
        assert not a.page.query_selector("#jlpt-continue")
        a.page.click("#to-kana")
        a.page.wait_for_selector(".screen.home")
    fails = []
    for dev in DEVICES:
        with App(dev, save=_kana_done_save()) as a:
            a.start()
            a.page.click('[data-go="jlpt"]')
            a.page.wait_for_selector(".screen.jlpt")
            txt = a.page.inner_text(".screen.jlpt")
            assert "N5 단어" in txt and "개 중" in txt and "N4" in txt, txt
            assert "N5 · 1장" in a.page.inner_text("#jlpt-continue")
            r = measure(a, "jlpt-open")
            fails += ["%s: %s" % (dev, p) for p in r["problems"]] + ["%s: small %s" % (dev, x) for x in r["small"]]
            a.shot("jlpt-open-%s.png" % slug(dev))
            assert not a.errors, a.errors
    assert not fails, "\n".join(fails)


def test_jlpt_first_lesson():
    """JLPT 첫 레슨을 풀고 「계속」 → JLPT 화면으로. 회화 「이어서 배우기」는 그대로 3-1"""
    with App("iPhone 17", save=_kana_done_save()) as a:
        a.start()
        a.page.click('[data-go="jlpt"]')
        a.page.click("#jlpt-continue")
        a.play("101-1")
        a.dismiss()
        a.page.click("#home")
        a.page.wait_for_selector(".screen.jlpt")
        assert "101-1" in a.save()["completed_lessons"]
        assert "N5 · 1장" in a.page.inner_text("#jlpt-continue")
        a.page.click('[data-go="home"]')
        a.page.wait_for_selector(".screen.home")
        assert "3-1" in a.page.inner_text("#continue")
        assert not a.errors, a.errors


def test_jlpt_dev_mode():
    """개발자 모드: 새 저장이어도 JLPT 탭과 N5 모든 레슨이 열림"""
    with App("iPhone 17") as a:
        a.start()
        _to_settings(a)
        a.page.click("#dev")
        a.page.click('[data-go="jlpt"]')
        a.page.wait_for_selector(".screen.jlpt")
        assert a.page.query_selector("#jlpt-continue")
        last = _lesson_ids([114])[-1]
        assert a.js("(id) => window.__ria.ctx.lessonState(id)", last) == "open"
        assert not a.errors, a.errors


def _to_settings(a):
    a.page.click('[data-go="settings"]')
    a.page.wait_for_selector(".screen.settings")


def main():
    only = sys.argv[1:]
    tests = [(n, f) for n, f in globals().items() if n.startswith("test_") and callable(f) and (not only or n in only)]
    t0 = time.time()
    env()
    print("build: " + _env["build"].replace("\n", " | "))
    fails = 0
    for name, f in tests:
        t = time.time()
        try:
            f()
            print("PASS %s (%.0fs)" % (name, time.time() - t))
        except Exception as e:  # noqa: BLE001
            fails += 1
            print("FAIL %s (%.0fs) - %s: %s" % (name, time.time() - t, type(e).__name__, str(e)[:3000]))
    print("%d passed, %d failed (%.0fs). screenshots: %s" % (len(tests) - fails, fails, time.time() - t0, OUT))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
