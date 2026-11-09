"""JLPT N5 목록 정리·단어 표 점검 (설계서 2026-11-09-jlpt-n5 §2)"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from jlpt_n5 import pruned_n5, DATED  # noqa: E402


def test_pruned_count():
    assert len(pruned_n5()) == 664


def test_no_affix_or_dated():
    ws = pruned_n5()
    assert not [w for w in ws if "～" in w["jp"] or "〜" in w["jp"]]
    assert not {w["jp"] for w in ws} & DATED


def test_no_duplicates():
    keys = [(w["jp"], w["reading"]) for w in pruned_n5()]
    assert len(keys) == len(set(keys))


def test_reading_notes_stripped():
    r = {w["jp"]: w["reading"] for w in pruned_n5()}
    assert r["勉強"] == "べんきょう"


# ---- 단어 표 data/jlpt-n5.csv (Task 2) ----
import csv, json, re  # noqa: E402
from jlpt_n5 import load_jlpt, forms, plain, reading  # noqa: E402
from make_lessons import BARE_KANJI, RUBY  # noqa: E402
from jmdict_subset import candidates  # noqa: E402

WORDS = {w["id"]: w for w in csv.DictReader(open(os.path.join(ROOT, "data", "words.csv"), encoding="utf-8"))}
POS = {w["pos"] for w in WORDS.values()} - {"kana"}


def test_covers_pruned_n5():
    keys = set()
    for r in load_jlpt():
        keys |= {(f, reading(r["jp"])) for f in forms(plain(r["jp"]))} | {(f, f) for f in forms(reading(r["jp"]))}
    miss = [w["jp"] for w in pruned_n5() if (w["jp"], w["reading"]) not in keys and (w["reading"], w["reading"]) not in keys]
    assert not miss, miss


def test_ids():
    rows = load_jlpt()
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids))
    for r in rows:
        if r["shared"]:
            assert r["id"] in WORDS, r
        else:
            assert re.fullmatch(r"c1(0[1-9]|1[0-4])-\d{3}", r["id"]) and r["id"] not in WORDS, r


def test_chapters_units():
    rows = load_jlpt()
    by = {}
    for r in rows:
        assert 101 <= r["chapter"] <= 114, r
        by.setdefault(r["chapter"], {}).setdefault(r["unit"], []).append(r)
    assert sorted(by) == list(range(101, 115))
    for ch, units in by.items():
        assert sorted(units) == list(range(1, len(units) + 1)), ch
        for u, rs in units.items():
            assert 6 <= len(rs) <= 8, (ch, u, len(rs))


def test_new_words_complete():
    for r in load_jlpt():
        if r["shared"]:
            continue
        assert not BARE_KANJI.search(RUBY.sub("", r["jp"])), r
        assert r["ko"].strip() and r["pos"] in POS, r


def test_counters():
    got = {plain(r["jp"]) for r in load_jlpt() if r["chapter"] == 101}
    assert {"三時", "二人", "三枚", "一冊", "二本", "一匹", "一杯", "一階", "百円"} <= got, got


def test_new_words_in_jmdict():
    pairs = {tuple(p) for p in json.load(open(os.path.join(ROOT, "vendor", "jmdict", "subset.json"), encoding="utf-8"))["pairs"]}
    bad = [r["jp"] for r in load_jlpt() if not r["shared"] and r["pos"] != "num" and not any(c in pairs for c in candidates(r["jp"]))]
    assert not bad, bad
