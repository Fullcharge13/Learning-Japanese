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

test("listen dialog: 「글자로 보기」 shows 남:/여: lines; without voice the same lines show at once", () => {
  const d = "男：駅{えき}はどこですか。\n女：あそこです。";
  const on = listenBox(d, speaking);
  assert.match(on, /<details[\s\S]*<p[^>]*>남: <ruby>駅<rt>えき<\/rt><\/ruby>はどこですか。<\/p><p[^>]*>여: あそこです。<\/p>/, on);
  assert.ok(!on.split("<details")[1].includes("男"), on); // 보이는 글자에 男 없음(🔊 data-say에는 있어야 함)
  const off = listenBox(d, {});
  assert.match(off, /남: [\s\S]*여: あそこです。/, off);
  assert.ok(!off.includes("say-btn"));
});
