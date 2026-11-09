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
