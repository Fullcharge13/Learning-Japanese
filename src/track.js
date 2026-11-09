// 학습 길 나누기 (JLPT 설계 2026-11-09 §3-3): 장 번호 100 이상 = JLPT 길, 그 아래 = 회화 길. 이 규칙은 여기 한 곳에만.
export const JLPT_FROM = 100;

/** 장 번호 → "talk" | "jlpt" */
export const trackOf = (chapterId) => (Number(chapterId) >= JLPT_FROM ? "jlpt" : "talk");

/** 레슨 id("101-3", 심화 "5-A1") → 길 */
export const trackOfLesson = (lessonId) => trackOf(parseInt(String(lessonId), 10));

export const trackChapters = (chapters, track) => (chapters || []).filter((c) => trackOf(c.id) === track);

/** JLPT 탭 열림: 가나 두 장(1·2장) 평가를 모두 끝냄 */
export function jlptOpen(examIds, done) {
  const d = new Set(done || []);
  return !!(examIds && examIds[1] && examIds[2] && d.has(examIds[1]) && d.has(examIds[2]));
}

/** N5 단어 중 끝낸 레슨(어느 길이든)에 나온 단어 수 */
export function n5Learned(n5Ids, lessons, completed) {
  const d = new Set(completed || []);
  const got = new Set((lessons || []).filter((l) => d.has(l.id)).flatMap((l) => l.concepts || []));
  return (n5Ids || []).filter((id) => got.has(id)).length;
}

/** 이번에 처음 끝낸 레슨이 JLPT 길의 마지막 레슨이고, JLPT 레슨을 모두 끝냈을 때 */
export function n5Finished(jlptLessons, completed, firstTime, lessonId) {
  const ls = jlptLessons || [];
  if (!firstTime || !ls.length || ls[ls.length - 1].id !== lessonId) return false;
  const d = new Set(completed || []);
  return ls.every((l) => d.has(l.id));
}

/** 레슨을 끝낸 뒤 회화 길의 「지금 레슨」: JLPT 레슨이면 null(회화 「이어서 배우기」를 바꾸지 않음) */
export function nextInTrack(talkLessons, completed, lessonId) {
  if (trackOfLesson(lessonId) === "jlpt" || !(talkLessons || []).length) return null;
  const d = new Set([...(completed || []), lessonId]);
  const next = talkLessons.find((l) => !d.has(l.id)) || talkLessons[talkLessons.length - 1];
  return { nextLessonId: next.id, nextChapter: next.chapter };
}

/** 화면에 보이는 장 번호: JLPT 장은 급수 안 번호(101 → 1) */
export const chapterNo = (chapterId) => (trackOf(chapterId) === "jlpt" ? Number(chapterId) - JLPT_FROM : Number(chapterId));
/** 화면에 보이는 레슨 번호: "101-3" → "1-3" (회화 레슨은 그대로) */
export function shortLessonId(id) {
  const m = /^(\d+)-(.+)$/.exec(String(id));
  return m && trackOf(+m[1]) === "jlpt" ? `${+m[1] - JLPT_FROM}-${m[2]}` : String(id);
}
