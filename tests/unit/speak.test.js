import { test } from "node:test";
import assert from "node:assert/strict";
import { canSpeak, speak, dialogLines } from "../../src/speak.js";

function fakeWin() {
  const calls = [];
  class SpeechSynthesisUtterance { constructor(text) { this.text = text; } }
  return {
    calls,
    SpeechSynthesisUtterance,
    speechSynthesis: { cancel: () => calls.push(["cancel"]), speak: (u) => calls.push(["speak", u.text, u.lang]) },
  };
}

test("speak reads the kana reading in ja-JP after stopping the previous one", () => {
  const w = fakeWin();
  assert.equal(canSpeak(w), true);
  assert.equal(speak("学生{がくせい}", w), true);
  assert.deepEqual(w.calls, [["cancel"], ["speak", "がくせい", "ja-JP"]]);
});

test("speak without speechSynthesis does nothing and says no", () => {
  assert.equal(canSpeak({}), false);
  assert.equal(speak("あ", {}), false);
  assert.equal(canSpeak(undefined), false);
});

test("speak swallows engine errors", () => {
  const w = fakeWin();
  w.speechSynthesis.speak = () => { throw new Error("boom"); };
  assert.equal(speak("あ", w), false);
});

test("speak ignores empty text", () => {
  const w = fakeWin();
  assert.equal(speak("", w), false);
  assert.deepEqual(w.calls, []);
});

// 대화 듣기(N5 청해): 줄마다 따로, 男 낮게·女 높게, 「男：」은 소리로 안 읽음
function pitchWin() {
  const calls = [];
  class SpeechSynthesisUtterance { constructor(text) { this.text = text; } }
  return { calls, SpeechSynthesisUtterance,
    speechSynthesis: { cancel: () => calls.push(["cancel"]), speak: (u) => calls.push(["speak", u.text, u.pitch]) } };
}

test("speak dialog: lines read one by one, 男 pitch 0.8, 女 pitch 1.25, one cancel, speaker mark not read", () => {
  const w = pitchWin();
  assert.equal(speak("男：駅{えき}はどこですか。\n女：あそこです。", w), true);
  assert.deepEqual(w.calls, [["cancel"], ["speak", "えきはどこですか。", 0.8], ["speak", "あそこです。", 1.25]]);
});

test("speak single sentence: unchanged (one utterance, default pitch)", () => {
  const w = pitchWin();
  speak("こんにちは", w);
  assert.deepEqual(w.calls, [["cancel"], ["speak", "こんにちは", undefined]]);
});

test("dialogLines splits speaker marks", () => {
  assert.deepEqual(dialogLines("男：はい。\n女：いいえ。"), [{ who: "男", text: "はい。" }, { who: "女", text: "いいえ。" }]);
  assert.deepEqual(dialogLines("はい。"), [{ who: "", text: "はい。" }]);
});
