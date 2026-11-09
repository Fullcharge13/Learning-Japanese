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
