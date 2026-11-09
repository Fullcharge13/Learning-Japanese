import { test } from "node:test";
import assert from "node:assert/strict";
import { ruby, kana, plain } from "../../src/ruby.js";

test("ruby: kanji{reading} becomes <ruby>", () => {
  assert.equal(ruby("学生{がくせい}です"), "<ruby>学生<rt>がくせい</rt></ruby>です");
  assert.equal(ruby("行{い}きます"), "<ruby>行<rt>い</rt></ruby>きます");
  assert.equal(ruby("すみません"), "すみません");
  assert.equal(ruby("日本{にほん}の大学{だいがく}"), "<ruby>日本<rt>にほん</rt></ruby>の<ruby>大学<rt>だいがく</rt></ruby>");
});

test("ruby escapes html in base, reading and plain text", () => {
  assert.equal(ruby("<b>&"), "&lt;b&gt;&amp;");
  assert.equal(ruby("字{<x>}"), "<ruby>字<rt>&lt;x&gt;</rt></ruby>");
  assert.equal(ruby("'\"学{が}"), "&#39;&quot;<ruby>学<rt>が</rt></ruby>");
});

test("ruby keeps unpaired braces as text", () => {
  assert.equal(ruby("a{b"), "a{b");
  assert.equal(ruby("{}"), "{}");
  assert.equal(ruby(null), "");
});

test("ruby base is only the kanji run right before the reading", () => {
  // 한국어 뜻과 섞인 말풍선: 괄호 뜻 앞 한자만 덮는다
  assert.equal(ruby("오늘 勉強{べんきょう}해요"), "오늘 <ruby>勉強<rt>べんきょう</rt></ruby>해요");
  assert.equal(ruby("お茶{ちゃ}"), "お<ruby>茶<rt>ちゃ</rt></ruby>");
});

test("kana and plain", () => {
  assert.equal(kana("学生{がくせい}です"), "がくせいです");
  assert.equal(plain("学生{がくせい}です"), "学生です");
  assert.equal(kana("行{い}きます"), "いきます");
  assert.equal(plain("コーヒー"), "コーヒー");
  assert.equal(kana(undefined), "");
});
