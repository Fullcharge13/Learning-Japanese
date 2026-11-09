import { test } from "node:test";
import assert from "node:assert/strict";
import { cardExample, sayBtn, riaSays } from "../../src/ui/dom.js";

test("word card shows japanese with furigana and the korean meaning", () => {
  const html = cardExample({ say: "x", words: [{ jp: "学生{がくせい}", ko: "학생" }, { jp: "はい", ko: "네" }] });
  assert.ok(html.includes("<ruby>学生<rt>がくせい</rt></ruby>"), html);
  for (const t of ["학생", "はい", "네"]) assert.ok(html.includes(t), t);
  assert.ok(html.includes('lang="ja"'));
});

test("word card escapes text", () => {
  const html = cardExample({ words: [{ jp: "<b>", ko: "<i>" }] });
  assert.ok(html.includes("&lt;b&gt;") && !html.includes("<b>") && !html.includes("<i>"));
});

test("speak button only when the device can speak, with an escaped reading", () => {
  assert.equal(sayBtn("学生{がくせい}", {}), "");
  const win = { speechSynthesis: {}, SpeechSynthesisUtterance: function () {} };
  const b = sayBtn('学"生{がくせい}', win);
  assert.match(b, /data-say="学&quot;生\{がくせい\}"/);
  assert.match(b, /aria-label="발음 듣기"/);
  assert.match(cardExample({ words: [{ jp: "あ", ko: "아" }] }, win), /data-say="あ"/);
});

test("Yuki's speech bubble draws furigana", () => {
  assert.ok(riaSays({ face: "smile", text: "この調子{ちょうし}!(이 기세로!)" }).includes("<ruby>調子<rt>ちょうし</rt></ruby>"));
});
