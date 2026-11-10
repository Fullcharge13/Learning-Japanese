#!/usr/bin/env python3
"""레슨 표 점검: python3 tests/content.py [--lessons-dir DIR]

- 레슨 칸 모양, 문제 종류는 choice·order·check만(입력 칸 없음)
- choice·check: 보기 4개, 보기 글자 중복 없음, 정답 번호가 범위 안, 정답이 그 단어(뜻 또는 일본어)
- 오답 보기가 정답과 같은 뜻·같은 소리(괄호 앞 비교)·같은 표기·읽기·같은 twin 묶음이 아님(정답이 둘로 보이지 않게)
- order: 2~6장 가나 카드, 이으면 그 단어 읽기
- 질문 옆 🔊(qSay)는 단어 장의 일→한에만
- 보류(hold) 단어는 어디에도 없고, 보류 아닌 단어는 모두 한 번 이상 문제에 나옴(성공 기준 1)
- 예문 빈칸: 빈칸 하나·한국어 힌트·정답이 그 단어, 빈칸 뒤 「avoid」 단어가 보기에 없음, 예문 있는(보류 아닌) 단어는 모두 빈칸으로 한 번 이상
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
from make_lessons import load_words, load_examples, jlpt_words, kana, plain, KANA, _twins as twins  # noqa: E402

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
BARE = re.compile(r"[\u3400-\u9fff々]")
RUBY_RE = re.compile(r"([㐀-鿿々〆ヶ]+)\{([^{}]+)\}")
JA = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")


def load(lessons_dir):
    r = subprocess.run(["node", "--input-type=module", "-e", DUMP, lessons_dir], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(r.stderr)
    return json.loads(r.stdout)


def _bare(t):
    return BARE.search(RUBY_RE.sub("", t or ""))


def check_kind(it):
    """kind가 있는 문제 하나의 규칙 위반 목록"""
    k, errs = it["kind"], []
    if it["type"] == "order":
        ln = it.get("lines", [])
        if not (2 <= len(ln) <= 6) or "".join(ln) != it.get("say"):
            errs.append("build cards must join into the sentence: %r" % ln)
        if any(_bare(x) for x in ln):
            errs.append("kanji without furigana in cards %r" % ln)
        return errs
    o = it.get("options", [])
    n = (3, 4) if k in ("listen", "speech") else (4,)  # 청해 발화 표현·즉시 응답은 시험처럼 보기 3개
    if len(o) not in n or len({RUBY_RE.sub(r"\1", x) for x in o}) != len(o):
        errs.append("options must be %s distinct: %r" % (n, o))
    if not (isinstance(it.get("answer"), int) and 0 <= it["answer"] < len(o)):
        errs.append("bad answer %r" % it.get("answer"))
    if k != "kanji-write" and any(_bare(x) for x in o):
        errs.append("kanji without furigana in options %r" % o)
    if k != "kanji-read" and _bare(it.get("q")):
        errs.append("kanji without furigana in question %r" % it.get("q"))
    if it.get("sentence") and _bare(it["sentence"].get("jp")):
        errs.append("kanji without furigana in sentence %r" % it["sentence"])
    if k == "listen" and (not it.get("qSay") or JA.search(it.get("q", "")) or it.get("sentence")):
        errs.append("listen item must hide the Japanese and have the speaker button")
    return errs


def check(mods, words, all_ids, examples=None):
    errs = []
    examples = examples or {}
    filled = set()
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
                if it.get("kind"):  # 문법·한자·모의고사 문제: 단어 규칙 대신 꼴마다 규칙(N5 완성 설계 §7)
                    seen.add(it.get("concept"))
                    texts.append(it.get("q", ""))
                    errs += ["%s: %s" % (at, e) for e in check_kind(it)]
                    continue
                w = by_id.get(it.get("concept"))
                seen.add(it.get("concept"))
                if not w:
                    continue  # 보류·없는 단어는 아래에서 한꺼번에
                sent = it.get("sentence")
                if sent is not None:
                    ex = examples.get(w["id"])
                    filled.add(w["id"])
                    if not ex or sent.get("jp", "").count("＿＿") != 1 or not sent.get("ko"):
                        errs.append("%s: fill needs one blank, a Korean hint and an example row: %r" % (at, sent))
                    elif it.get("say") != ex["pre"] + w["jp"] + ex["post"]:
                        errs.append("%s: fill say %r is not the full sentence" % (at, it.get("say")))
                    bad_avoid = [o for o in it.get("options", []) if ex and plain(o) in ex["avoid"]]
                    if bad_avoid:
                        errs.append("%s: option(s) %r also fit this sentence (examples.csv avoid)" % (at, bad_avoid))
                elif it.get("say") != w["jp"]:
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
                    # 오답은 이 레슨의 장 단어(겹치는 단어는 두 장에 있음). 모의고사(단어 없는 장)는 앞 JLPT 장에서 옮겨 온 문제
                    src = by_ch.get(m["CHAPTER"]["id"]) or [x for c, xs in by_ch.items() if c > 100 for x in xs]
                    pool = {x[field]: x for x in src}
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
            bad = [x for x in texts if ZH.search(x) or ROMAJI.search(re.sub(r"XP|N[1-5]", "", x))]
            if bad:
                errs.append("%s: romaji or Chinese in screen text: %r" % (where, bad[:3]))
    leaked = seen & (all_ids - set(by_id))
    if leaked:
        errs.append("hold words used: %s" % sorted(leaked))
    no_fill = set(examples) - filled
    if no_fill:
        errs.append("%d example words never asked as fill, e.g. %s" % (len(no_fill), sorted(no_fill)[:5]))
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
    words = load_words(path)
    words = words + jlpt_words(words)  # JLPT 장(101~)의 단어도 함께 점검
    ex_path = os.path.join(ROOT, "data", "examples.csv")
    examples = load_examples(ex_path, words) if os.path.exists(ex_path) else {}
    errs = check(mods, words, all_ids, examples)
    n = sum(len(m["LESSONS"]) for m in mods.values())
    for e in errs:
        print("FAIL", e)
    print("%d chapters, %d lessons: %s" % (len(mods), n, "OK" if not errs else "%d problems" % len(errs)))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
