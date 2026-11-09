import { test } from "node:test";
import assert from "node:assert/strict";
import { listenBox } from "../../src/ui/dom.js";

const speaking = { speechSynthesis: {}, SpeechSynthesisUtterance: function () {} };

test("listen fallback: with a voice only the speaker button, without one the sentence text", () => {
  const on = listenBox("駅{えき}はどこですか。", speaking);
  assert.ok(on.includes("say-btn") && !on.includes("<ruby>"), on);
  const off = listenBox("駅{えき}はどこですか。", {});
  assert.ok(off.includes("<ruby>駅<rt>えき</rt></ruby>") && !off.includes("say-btn"), off);
});
