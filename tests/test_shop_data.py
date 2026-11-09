"""data/shop.js 점검: 개수·이야기 일수·참조·후리가나·틀 단어의 장·그림 파일 (설계 §3·§4)"""
import csv, json, os, re, subprocess, sys
import pytest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from make_lessons import RUBY, BARE_KANJI  # noqa: E402

DUMP = r"""
const url = await import("node:url");
const m = await import(url.pathToFileURL(process.argv[1]).href);
process.stdout.write(JSON.stringify(m));
"""


@pytest.fixture(scope="module")
def shop():
    r = subprocess.run(["node", "--input-type=module", "-e", DUMP, os.path.join(ROOT, "data", "shop.js")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_counts(shop):
    assert len(shop["MENU"]) == 7 and len([m for m in shop["MENU"] if m["start"]]) == 2
    assert len(shop["TEMPLATES"]) == 4 and len(shop["COUNTS"]) == 3
    ids = [g["id"] for g in shop["GUESTS"]]
    assert len(ids) == 15 and len(set(ids)) == 15
    assert len(shop["UPGRADES"]) == 8 and len(shop["FLOW"]) == 15 and len(shop["STORIES"]) == 15
    assert shop["BASE_GUESTS"] == 6 and shop["MAX_GUESTS"] == 8 and shop["DAY_XP"] == 10 and shop["XP_RUNS_PER_DAY"] == 2
    assert shop["SHOP_TIP"] == 0.10


def test_story_days(shop):
    assert [s["day"] for s in shop["STORIES"]] == [1, 2, 3, 4, 5, 7, 9, 11, 13, 15, 18, 21, 24, 27, 30]


def test_refs(shop):
    menus = {m["id"] for m in shop["MENU"]}
    for g in shop["GUESTS"]:
        assert g["likes"] and set(g["likes"]) <= menus, g
    up_menus = [u["effect"]["menu"] for u in shop["UPGRADES"] if "menu" in u["effect"]]
    assert sorted(up_menus) == sorted(m["id"] for m in shop["MENU"] if not m["start"])


def _jp_texts(shop):
    out = [m["jp"] for m in shop["MENU"]] + [t["jp"] for t in shop["TEMPLATES"]] + [c["jp"] for c in shop["COUNTS"]]
    for k in ("enter", "leave"):
        out += [shop["GREETINGS"][k]["answer"]["jp"]] + [w["jp"] for w in shop["GREETINGS"][k]["wrong"]]
    out += [g["bye"]["jp"] for g in shop["GUESTS"]] + [s["line"]["jp"] for s in shop["STORIES"]]
    return out


def test_furigana(shop):
    bad = [t for t in _jp_texts(shop) if BARE_KANJI.search(RUBY.sub("", re.sub(r"\{(menu|count)\}", "", t)))]
    assert not bad, bad


def test_template_words_learned(shop):
    """틀 속 단어 표 표현(ください·お願いします)은 그 틀의 learn 장 안에서 배우고, need ≤ learn"""
    with open(os.path.join(ROOT, "data", "words.csv"), encoding="utf-8") as f:
        chap = {r["jp"]: int(r["chapter"]) for r in csv.DictReader(f)}
    for t in shop["TEMPLATES"]:
        assert t["need"] <= t["learn"], t
        for word in ("ください", "お願{ねが}いします"):
            if word in t["jp"]:
                assert chap[word] <= t["learn"], (t["id"], word)


def test_pictures():
    d = os.path.join(ROOT, "src", "img", "shop")
    names = set(os.listdir(d)) if os.path.isdir(d) else set()
    want = {"flow-%02d.png" % i for i in range(1, 16)} | {"story-%02d.png" % i for i in range(1, 16)}
    assert want <= names, sorted(want - names)[:5]
    assert len([n for n in names if n.startswith("guest-")]) == 15
