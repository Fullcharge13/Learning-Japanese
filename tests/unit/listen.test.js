import { test } from "node:test";
import assert from "node:assert/strict";
import { listenBox } from "../../src/ui/dom.js";

const speaking = { speechSynthesis: {}, SpeechSynthesisUtterance: function () {} };

test("listen fallback: with a voice only the speaker button, without one the sentence text", () => {
  const on = listenBox("駅{えき}はどこですか。", speaking);
  assert.ok(on.includes("say-btn") && !on.split("<details")[0].includes("<ruby>"), on); // 글자는 접힌 「글자로 보기」 안에만
  const off = listenBox("駅{えき}はどこですか。", {});
  assert.ok(off.includes("<ruby>駅<rt>えき</rt></ruby>") && !off.includes("say-btn"), off);
});

test("listen with a speaker but maybe no Japanese voice: a folded 「글자로 보기」 reveals the sentence", () => {
  const on = listenBox("駅{えき}はどこですか。", speaking);
  assert.match(on, /<details[^>]*>\s*<summary>글자로 보기<\/summary>[\s\S]*<ruby>駅<rt>えき<\/rt><\/ruby>/, on);
});
