#!/usr/bin/env python3
"""JLPT N5 목록(vendor/jlpt/n5.csv) 정리 규칙과 단어 표(data/jlpt-n5.csv) 읽기 (설계서 2026-11-09-jlpt-n5 §2).

- 정리: 접사·조수사 줄(～, お～, 何～)과 옛날 말(DATED)을 빼고, 첫 표기·첫 읽기만, 읽기 메모 「(する)」「(〜を)」는 뗀다.
  같은 (표기, 읽기)는 하나. 결과 664개 = 범위 시험의 기준.
- 원본의 영어 뜻 칸은 쓰지 않는다(출처 불분명).
"""
import csv
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR_N5 = os.path.join(ROOT, "vendor", "jlpt", "n5.csv")
DATED = frozenset({"テープ", "テープレコーダー", "ラジオカセ", "レコード", "マッチ", "灰皿", "フィルム", "字引", "万年筆",
                   "たばこ", "背広", "ストーブ"})
NOTE = re.compile(r"\s*\([^)]*\)\s*")


def _first(s):
    return NOTE.sub("", re.split(r"[;；]", s)[0]).strip()


def pruned_n5(path=VENDOR_N5):
    out, seen = [], set()
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            jp, reading = _first(r["expression"]), _first(r["reading"])
            if "～" in jp or "〜" in jp or jp in DATED:
                continue
            if (jp, reading) in seen:
                continue
            seen.add((jp, reading))
            out.append({"jp": jp, "reading": reading})
    return out

_GODAN = {"き": "く", "ぎ": "ぐ", "し": "す", "ち": "つ", "に": "ぬ", "び": "ぶ", "み": "む", "り": "る", "い": "う"}


def plain(s):
    return re.sub(r"\{[^}]*\}", "", s or "")


def reading(s):
    return re.sub(r"[\u3400-\u9fff々〆ヶ]+\{([^}]*)\}", r"\1", s or "")


def forms(s):
    """비교용 형태들: 끝 문장부호·です 떼기(동사 활용은 일부러 맞추지 않음 — JLPT 길은 동사를 사전형으로 따로 가르친다)"""
    s = (s or "").strip().rstrip("。？?！!")
    out = {s}
    for suf in ("です", "ですか"):
        if s.endswith(suf):
            out.add(s[: -len(suf)])
    return out


JLPT_CSV = os.path.join(ROOT, "data", "jlpt-n5.csv")
WORDS_CSV = os.path.join(ROOT, "data", "words.csv")


def load_jlpt(path=JLPT_CSV, words_path=WORDS_CSV):
    """JLPT 단어 표. 회화 길과 겹치는 단어(jp 칸이 빈 줄)는 words.csv의 표기·뜻·품사를 가져오고 shared=True"""
    with open(words_path, encoding="utf-8") as f:
        base = {w["id"]: w for w in csv.DictReader(f)}
    out = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            shared = not r["jp"].strip()
            src = base[r["id"]] if shared else r
            out.append({"id": r["id"], "chapter": int(r["chapter"]), "unit": int(r["unit"]), "jp": src["jp"], "ko": src["ko"],
                        "pos": src["pos"], "note": r.get("note", "") or (src.get("note", "") if shared else ""), "shared": shared})
    return out
