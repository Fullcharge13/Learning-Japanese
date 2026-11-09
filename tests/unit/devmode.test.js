import { test } from "node:test";
import assert from "node:assert/strict";
import { isDev, gateCompleted, DEV_MARK } from "../../src/devgate.js";
import { DEV_FLAG_KEY, DEV_SAVE_KEY, DEV_RESUME_KEY, keysFor, readDevFlag, setDevMode, loadSlot, storeSlot, markDev } from "../../src/devmode.js";
import { SAVE_KEY, newSave, store, loadEx } from "../../src/save.js";
import { RESUME_KEY, writeResume, readResume } from "../../src/resume.js";
import { curriculum } from "../../src/curriculum.js";

const mem = () => { const m = new Map(); return { m, getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), removeItem: (k) => m.delete(k) }; };
const CH = [{ id: 1, title: "a", lessons: [{ id: "1-1" }, { id: "1-2", isExam: true }] }, { id: 2, title: "b", lessons: [{ id: "2-1" }, { id: "2-2", isExam: true }] }];

test("dev keys are this app's own and separate from the learning record", () => {
  for (const k of [DEV_FLAG_KEY, DEV_SAVE_KEY, DEV_RESUME_KEY]) assert.ok(k.startsWith("sanada-japanese.dev"), k);
  assert.deepEqual(keysFor(false), { save: SAVE_KEY, resume: RESUME_KEY });
  assert.deepEqual(keysFor(true), { save: DEV_SAVE_KEY, resume: DEV_RESUME_KEY });
});

test("gateCompleted opens every main lesson only for a dev save, without changing the save", () => {
  const real = { ...newSave(), completed_lessons: ["1-1"] };
  assert.deepEqual(gateCompleted(real, CH), ["1-1"]);
  const dev = markDev(real, true);
  assert.equal(isDev(dev), true);
  assert.deepEqual(gateCompleted(dev, CH).sort(), ["1-1", "1-2", "2-1", "2-2"]);
  assert.deepEqual(dev.completed_lessons, ["1-1"]);
  assert.equal(DEV_MARK in markDev(dev, false), false);
});

test("switching on reads the dev slot, off reads the learning record back untouched", () => {
  const st = mem();
  store(st, { ...newSave(), xp: 77, completed_lessons: ["1-1"] });
  const on = setDevMode(st, true);
  assert.equal(readDevFlag(st), true);
  assert.equal(on.save.xp, 0);
  assert.equal(isDev(on.save), true);
  storeSlot(st, { ...on.save, xp: 999 }, true);
  assert.equal(JSON.parse(st.getItem(SAVE_KEY)).xp, 77, "learning record untouched");
  const off = setDevMode(st, false);
  assert.equal(readDevFlag(st), false);
  assert.equal(off.save.xp, 77);
  assert.equal(isDev(off.save), false);
  assert.equal(loadSlot(st, true).save.xp, 999, "dev slot kept for next time");
});

test("save and resume can use another key", () => {
  const st = mem();
  assert.ok(store(st, { ...newSave(), xp: 5 }, "x.save"));
  assert.equal(st.getItem(SAVE_KEY), null);
  assert.equal(loadEx(st, "x.save").save.xp, 5);
  writeResume(st, { lessonId: "1-1", at: Date.now(), flow: {}, item: null }, "x.resume");
  assert.equal(st.getItem(RESUME_KEY), null);
  assert.ok(st.getItem("x.resume"));
  assert.equal(readResume(st, {}, "nope.resume"), null);
});

test("curriculum with open: every lesson is open, done stays real", () => {
  const c = curriculum({ chapters: CH, completed: ["1-1"], currentId: "1-2", open: true });
  const st = Object.fromEntries(c.chapters.flatMap((ch) => ch.lessons.map((l) => [l.id, l.status])));
  assert.equal(st["1-1"], "done");
  assert.notEqual(st["2-2"], "locked");
  assert.equal(c.done, 1);
});
