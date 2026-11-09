import { test } from "node:test";
import assert from "node:assert/strict";
import { JLPT_FROM, trackOf, trackChapters, jlptOpen, n5Learned, n5Finished, nextInTrack } from "../../src/track.js";
import { chaptersForConcepts } from "../../src/lessondata.js";
import { doneChapter } from "../../src/shop/rules.js";

const L = (id, chapter, concepts = [], isExam = false) => ({ id, chapter, concepts, isExam });
const CH = [
  { id: 1, lessons: [L("1-1", 1, ["c1-001"]), L("1-9", 1, [], true)] },
  { id: 2, lessons: [L("2-1", 2, ["c2-001"]), L("2-9", 2, [], true)] },
  { id: 3, lessons: [L("3-1", 3, ["c3-008"]), L("3-3", 3, [], true)] },
  { id: 101, lessons: [L("101-1", 101, ["c101-001", "c3-008"]), L("101-2", 101, [], true)] },
  { id: 102, lessons: [L("102-1", 102, ["c102-001"]), L("102-2", 102, [], true)] },
];
const lessonsOf = (track) => trackChapters(CH, track).flatMap((c) => c.lessons);
const examIdsOf = (chs) => Object.fromEntries(chs.map((c) => [c.id, c.lessons.find((l) => l.isExam).id]));

test("trackOf: chapter 100 and up is the JLPT path", () => {
  assert.equal(JLPT_FROM, 100);
  assert.equal(trackOf(26), "talk");
  assert.equal(trackOf(101), "jlpt");
  assert.deepEqual(trackChapters(CH, "jlpt").map((c) => c.id), [101, 102]);
  assert.deepEqual(trackChapters(CH, "talk").map((c) => c.id), [1, 2, 3]);
});

test("jlptOpen: both kana chapter exams", () => {
  const ex = { 1: "1-9", 2: "2-9" };
  assert.equal(jlptOpen(ex, ["1-9"]), false);
  assert.equal(jlptOpen(ex, ["1-9", "2-9"]), true);
});

test("n5Learned counts words from finished lessons on either path", () => {
  const ids = ["c101-001", "c3-008", "c102-001"];
  assert.equal(n5Learned(ids, CH.flatMap((c) => c.lessons), []), 0);
  assert.equal(n5Learned(ids, CH.flatMap((c) => c.lessons), ["3-1"]), 1, "shared word learned on the talk path");
  assert.equal(n5Learned(ids, CH.flatMap((c) => c.lessons), ["3-1", "101-1"]), 2);
});

test("n5Finished only on the first finish of the last JLPT lesson", () => {
  const jl = lessonsOf("jlpt");
  const all = jl.map((l) => l.id);
  assert.equal(n5Finished(jl, all, true, "102-2"), true);
  assert.equal(n5Finished(jl, all, false, "102-2"), false);
  assert.equal(n5Finished(jl, all, true, "3-3"), false);
  assert.equal(n5Finished(jl, all.slice(0, -2).concat("102-2"), true, "102-2"), false, "not all done");
});

test("examIds talk only keeps the shop below the JLPT chapters", () => {
  const talk = examIdsOf(trackChapters(CH, "talk"));
  assert.ok(!("101" in talk));
  assert.equal(doneChapter(talk, ["1-9", "2-9", "3-3", "101-2", "102-2"]), 3);
});

test("chaptersForConcepts finds the jlpt chapter of a JLPT-only word", () => {
  assert.deepEqual(chaptersForConcepts(CH, ["c101-001"]), [101]);
});

test("finish keeps talk current: nextInTrack is null for a JLPT lesson", () => {
  assert.equal(nextInTrack(lessonsOf("talk"), ["1-1"], "101-1"), null);
  assert.deepEqual(nextInTrack(lessonsOf("talk"), ["1-1"], "1-1"), { nextLessonId: "1-9", nextChapter: 1 });
  assert.deepEqual(nextInTrack(lessonsOf("talk"), ["1-1", "1-9", "2-1", "2-9", "3-1", "3-3"], "3-3"), { nextLessonId: "3-3", nextChapter: 3 });
});

import { shortLessonId, chapterNo } from "../../src/track.js";
test("JLPT numbers are shown inside N5: 101 → 1, 101-3 → 1-3", () => {
  assert.equal(chapterNo(101), 1);
  assert.equal(chapterNo(14), 14);
  assert.equal(shortLessonId("101-3"), "1-3");
  assert.equal(shortLessonId("114-10"), "14-10");
  assert.equal(shortLessonId("3-1"), "3-1");
});

import { courseJustFinished } from "../../src/curriculum.js";
test("finishing a JLPT lesson is not the talk course finish", () => {
  const talk = trackChapters(CH, "talk");
  const all = talk.flatMap((c) => c.lessons.map((l) => l.id));
  assert.equal(courseJustFinished({ chapters: talk, completed: all, firstTime: true, lessonId: "3-3" }), true);
  assert.equal(courseJustFinished({ chapters: talk, completed: [...all, "101-1"], firstTime: true, lessonId: "101-1" }), false);
});

test("review of a shared word stays in the chapters the learner has finished", () => {
  assert.deepEqual(chaptersForConcepts(CH, ["c3-008"], ["3-1"]), [3], "talk-only learner: no JLPT chapter");
  assert.deepEqual(chaptersForConcepts(CH, ["c3-008"], ["101-1"]), [101]);
  assert.deepEqual(chaptersForConcepts(CH, ["c3-008"], []), [3, 101], "nothing finished yet: any chapter");
});
