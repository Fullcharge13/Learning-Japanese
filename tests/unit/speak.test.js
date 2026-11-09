import { test } from "node:test";
import assert from "node:assert/strict";
import { canSpeak, speak } from "../../src/speak.js";

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
