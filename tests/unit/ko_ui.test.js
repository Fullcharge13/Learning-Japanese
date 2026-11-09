import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";

const root = new URL("../../", import.meta.url);
const read = (p) => readFileSync(new URL(p, root), "utf8");
// 중국어 간체 전용 글자(일본어 표기에는 안 나옴) — 바탕 앱의 중국어 화면 글자가 남으면 잡힌다
const ZH = /[课们这么吗吧呢没说认识单词语继续题错对关习个开时间样让进后门]/;

// 주석을 지운 코드(문자열 속 //는 드물어서 줄 시작·공백 뒤의 //만 주석으로 봄)
function code(text) {
  return text.replace(/\/\*[\s\S]*?\*\//g, "").replace(/<!--[\s\S]*?-->/g, "").replace(/(^|\s)\/\/.*$/gm, "$1");
}

const FILES = [
  ...readdirSync(new URL("src/", root)).filter((f) => f.endsWith(".js")).map((f) => "src/" + f),
  ...readdirSync(new URL("src/ui/", root)).filter((f) => f.endsWith(".js")).map((f) => "src/ui/" + f),
  "src/index.html", "manifest.webmanifest", "data/lines.js", "data/quests.js", "data/badges.js", "data/items.js",
];

test("screen text has no Chinese left from the Haechi app", () => {
  const bad = [];
  for (const f of FILES) {
    code(read(f)).split("\n").forEach((line, i) => { if (ZH.test(line)) bad.push(`${f}:${i + 1}: ${line.trim().slice(0, 80)}`); });
  }
  assert.deepEqual(bad, []);
});

test("page language is Korean and the app is called 사나다 일본어", () => {
  const html = read("src/index.html");
  assert.match(html, /<html lang="ko"/);
  assert.match(html, /<title>사나다 일본어<\/title>/);
  assert.match(read("manifest.webmanifest"), /"name": "사나다 일본어"/);
});
