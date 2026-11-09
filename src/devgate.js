// 개발자 모드 표시와 잠금 풀기 (리아와 파이썬 devgate와 같은 모양). 실제 완료 기록은 바꾸지 않고 「열림」 판정에만 쓴다.
export const DEV_MARK = "dev_mode";
export const isDev = (save) => !!save && typeof save === "object" && save[DEV_MARK] === true;
export function mainLessonIds(chapters) { return (chapters || []).flatMap((c) => (c.lessons || []).map((l) => l.id)); }
/** 잠금 판정용 완료 목록: 개발자 저장이면 본 과정 레슨을 모두 끝낸 것으로 본다 */
export function gateCompleted(save, chapters) {
  const done = save && Array.isArray(save.completed_lessons) ? save.completed_lessons : [];
  if (!isDev(save)) return done;
  return [...new Set([...done, ...mainLessonIds(chapters)])];
}
