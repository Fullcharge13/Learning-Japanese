#!/usr/bin/env python3
"""레슨 표 점검: python3 tests/content.py [--lessons-dir DIR]

- 레슨 칸 모양, 문제 종류는 choice·order·check만(입력 칸 없음)
- choice·check: 보기 4개, 보기 글자 중복 없음, 정답 번호가 범위 안, 정답이 그 단어(뜻 또는 일본어)
- 오답 보기가 정답과 같은 뜻·같은 소리(괄호 앞 비교)이거나 같은 표기·읽기가 아님(정답이 둘로 보이지 않게)
- order: 2~6장 가나 카드, 이으면 그 단어 읽기
- 질문 옆 🔊(qSay)는 단어 장의 일→한에만
- 보류(hold) 단어는 어디에도 없고, 보류 아닌 단어는 모두 한 번 이상 문제에 나옴(성공 기준 1)
- 화면 글자에 로마자·중국어 간체 전용 글자가 없음
"""
import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from make_lessons import load_words, kana, plain, sound_key, KANA  # noqa: E402

DUMP = r"""
const fs = await import("node:fs"); const path = await import("node:path"); const url = await import("node:url");
const dir = process.argv[1]; const out = {};
for (const f of fs.readdirSync(dir).filter((f) => /^ch\d+\.js$/.test(f)).sort()) {
  const m = await import(url.pathToFileURL(path.join(dir, f)).href);
  out[f] = { CHAPTER: m.CHAPTER, LESSONS: m.LESSONS };
}
process.stdout.write(JSON.stringify(out));
"""
LESSON_KEYS = {"id", "chapter", "title", "goal", "summary", "cards", "items"}
TYPES = {"choice", "order", "check"}
ZH = re.compile(r"[课们这么吗吧呢没说认识单词语继续题错对关习个开时间样让进后门]")
ROMAJI = re.compile(r"[A-Za-z]")


def load(lessons_dir):
    r = subprocess.run(["node", "--input-type=module", "-e", DUMP, lessons_dir], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(r.stderr)
    return json.loads(r.stdout)


def twins(a, b):
    return sound_key(a["ko"]) == sound_key(b["ko"]) or plain(a["jp"]) == plain(b["jp"]) or kana(a["jp"]) == kana(b["jp"])


def check(mods, words, all_ids):
    errs = []
    by_id = {w["id"]: w for w in words}
    by_ch = {}
    for w in words:
        by_ch.setdefault(w["chapter"], []).append(w)
    seen = set()
    for fname, m in mods.items():
        for l in m["LESSONS"]:
            where = "%s %s" % (fname, l.get("id"))
            if not LESSON_KEYS <= set(l):
                errs.append("%s: missing keys %s" % (where, sorted(LESSON_KEYS - set(l))))
                continue
            texts = [m["CHAPTER"]["title"], l["title"], l["goal"]] + [c.get("say", "") for c in l["cards"]]
            for i, it in enumerate(l["items"]):
                at = "%s item %d" % (where, i)
                t = it.get("type")
                if t not in TYPES:
                    errs.append("%s: type %r not allowed" % (at, t))
                    continue
                w = by_id.get(it.get("concept"))
                seen.add(it.get("concept"))
                if not w:
                    continue  # 보류·없는 단어는 아래에서 한꺼번에
                if it.get("say") != w["jp"]:
                    errs.append("%s: say %r is not the word %r" % (at, it.get("say"), w["jp"]))
                texts.append(it.get("q", ""))
                if t in ("choice", "check"):
                    o = it.get("options", [])
                    if len(o) != 4 or len(set(o)) != 4:
                        errs.append("%s: options must be 4 distinct texts: %r" % (at, o))
                        continue
                    if not (isinstance(it.get("answer"), int) and 0 <= it["answer"] < 4):
                        errs.append("%s: bad answer %r" % (at, it.get("answer")))
                        continue
                    field = "ko" if o[it["answer"]] == w["ko"] else "jp" if o[it["answer"]] == w["jp"] else None
                    if not field:
                        errs.append("%s: answer %r is not the word %r" % (at, o[it["answer"]], w))
                        continue
                    pool = {x[field]: x for x in by_ch[w["chapter"]]}
                    for d in o[:it["answer"]] + o[it["answer"] + 1:]:
                        x = pool.get(d)
                        if not x:
                            errs.append("%s: distractor %r is not a word of this chapter" % (at, d))
                        elif twins(x, w):
                            errs.append("%s: distractor %r looks like a second answer for %r" % (at, d, w["jp"]))
                    if it.get("qSay") and not (field == "ko" and w["pos"] != "kana"):
                        errs.append("%s: 🔊 next to the question gives the answer away" % at)
                else:
                    ln = it.get("lines", [])
                    if not (2 <= len(ln) <= 6 and all(KANA.match(x) for x in ln) and "".join(ln) == kana(w["jp"])):
                        errs.append("%s: order lines must be 2-6 kana cards spelling %r: %r" % (at, kana(w["jp"]), ln))
            bad = [x for x in texts if ZH.search(x) or ROMAJI.search(x.replace("XP", ""))]
            if bad:
                errs.append("%s: romaji or Chinese in screen text: %r" % (where, bad[:3]))
    leaked = seen & (all_ids - set(by_id))
    if leaked:
        errs.append("hold words used: %s" % sorted(leaked))
    missing = set(by_id) - seen
    if missing:
        errs.append("%d words never asked (success criterion 1), e.g. %s" % (len(missing), sorted(missing)[:5]))
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lessons-dir", default=os.path.join(ROOT, "data", "lessons"))
    a = ap.parse_args()
    mods = load(os.path.abspath(a.lessons_dir))
    path = os.path.join(ROOT, "data", "words.csv")
    import csv
    with open(path, encoding="utf-8", newline="") as f:
        all_ids = {r["id"] for r in csv.DictReader(f)}
    errs = check(mods, load_words(path), all_ids)
    n = sum(len(m["LESSONS"]) for m in mods.values())
    for e in errs:
        print("FAIL", e)
    print("%d chapters, %d lessons: %s" % (len(mods), n, "OK" if not errs else "%d problems" % len(errs)))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
