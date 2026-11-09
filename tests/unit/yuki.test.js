import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { FACE_IDS, yukiImg } from "../../src/yuki.js";
import { ITEMS } from "../../data/items.js";

const root = new URL("../../", import.meta.url);

test("every face has its picture file (15 cuts of the Yuki sheet)", () => {
  assert.deepEqual(FACE_IDS, ["smile", "joy", "sparkle", "think", "surprise", "worry", "cheer", "wink", "hello", "done", "sleepy",
    "angry", "pout", "sad", "shy"]);
  for (const id of FACE_IDS) assert.ok(existsSync(new URL(`src/img/yuki/${id}.png`, root)), id);
});

test("every item has its picture, and the hachimaki is not one of them", () => {
  for (const x of ITEMS) if (x.id !== "none") assert.ok(existsSync(new URL(`src/img/items/${x.id}.png`, root)), x.id);
  assert.ok(!ITEMS.some((x) => /hachimaki/.test(x.id)));
  assert.ok(!existsSync(new URL("src/img/items/hachimaki.png", root)));
});

test("face picks its picture, unknown face falls back to smile", () => {
  assert.ok(yukiImg({ face: "joy" }).includes("img/yuki/joy.png"));
  assert.ok(yukiImg({ face: "pout" }).includes("img/yuki/pout.png"));
  assert.ok(yukiImg({ face: "nope" }).includes("img/yuki/smile.png"));
  assert.ok(yukiImg().includes("img/yuki/smile.png"));
  assert.ok(yukiImg({ face: "joy" }).includes('alt="유키 선생님"'));
});

test("item is drawn beside Yuki; none or a bad id draws nothing", () => {
  assert.ok(yukiImg({ item: "kimono" }).includes("img/items/kimono.png"));
  assert.ok(!yukiImg({ item: "none" }).includes("img/items/"));
  assert.ok(!yukiImg({ item: '"><script>' }).includes("<script>"));
});

test("same input, same output; size sets width", () => {
  assert.equal(yukiImg({ face: "wink", size: 64 }), yukiImg({ face: "wink", size: 64 }));
  assert.ok(yukiImg({ size: 64 }).includes('width="64"'));
});
