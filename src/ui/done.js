// 레슨 완료: 얻은 XP·바이트, 정확도, 연속 기록, 요약 3줄, 퀘스트·배지·이정표
import { ruby } from "../ruby.js";
import { QUESTS } from "../../data/quests.js";
import { BADGES } from "../../data/badges.js";
import { yukiImg } from "../yuki.js";
import { esc, icon, celebrate, MILESTONE_REWARD } from "./dom.js";
import { badgeArt } from "./badges.js";
import { courseJustFinished } from "../curriculum.js";
import { n5Finished, shortLessonId } from "../track.js";
import { isAdvancedLesson } from "../advanced.js";

export function render(root, ctx, params = {}) {
  const r = params.result;
  if (!r) { ctx.show("home"); return; }
  const lesson = params.lesson;
  const review = r.mode === "review";
  const adv = !review && isAdvancedLesson(lesson);
  const finished = !review && courseJustFinished({ chapters: ctx.chapters, completed: ctx.save.completed_lessons, firstTime: r.firstTime, lessonId: r.lessonId });
  const jlptLesson = !review && lesson && ctx.trackOfLesson(lesson.id) === "jlpt";
  const n5Done = jlptLesson && n5Finished(ctx.jlptLessons, ctx.save.completed_lessons, r.firstTime, r.lessonId);
  const line = ctx.say(finished ? "course_done" : "lesson_done", { xp: r.xp }); // course_done 대사는 회화 과정(24과) 완주용
  const streakLine = r.streakUp || r.milestone ? ctx.say("streak_up", { streak: r.streak }) : null;
  const bytes = r.totalBytes ?? (r.lessonBytes + r.questBytes + (r.milestoneBytes || 0));
  const parts = [["레슨", r.lessonBytes], ["퀘스트", r.questBytes], ["연속 기록", r.milestoneBytes || 0]].filter(([, v]) => v > 0);
  const acc = Math.round((r.accuracy ?? 1) * 100);
  const quests = r.finished.map((id) => QUESTS.find((q) => q.id === id)).filter(Boolean);
  const badges = r.newBadges.map((id) => BADGES.find((b) => b.id === id)).filter(Boolean);

  root.innerHTML = `<div class="screen done">
    <main>
      <div class="done-hero">
        <div class="ria-wrap big jump">${yukiImg({ face: "done", item: ctx.save.item, size: 150 })}<span class="sfx" aria-hidden="true">짠!</span></div>
        <h1>${review ? "복습 끝!" : finished ? "모두 끝!" : n5Done ? "N5 완주!" : adv ? esc(`${lesson.id} 심화 끝!`)
          : jlptLesson ? esc(`N5 · ${shortLessonId(lesson.id)} 끝!`) : esc(`${lesson.id} 끝!`)}</h1>
        <p class="bubble center">${ruby(line.text)}</p>
      </div>
      ${r.milestone ? `<p class="milestone">${icon("flame")}<span>${esc(`${r.milestone}일 연속! ${MILESTONE_REWARD[r.milestone] || ""}`)}</span></p>` : ""}
      <ul class="tiles" aria-label="받은 보상">
        <li class="tile xp">${icon("xp")}<b>+${r.xp}</b><span>XP</span></li>
        <li class="tile byte">${icon("byte")}<b>+${bytes}</b><span>엔</span></li>
        <li class="tile acc">${icon("check")}<b>${acc}%</b><span>한 번에 맞힘</span></li>
        <li class="tile flame${r.streakUp ? " lit" : ""}">${icon("flame")}<b>${r.streak}</b><span>일 연속</span></li>
      </ul>
      ${parts.length > 1 ? `<p class="muted center">엔: ${parts.map(([k, v]) => `${k} ${v}`).join(" + ")}</p>` : ""}
      ${!r.firstTime && !review ? `<p class="muted center">다시 하기는 레슨 엔이 없지만, XP와 오늘의 퀘스트는 그대로 쳐요.</p>` : ""}
      ${r.firstTime && r.perfect ? `<p class="perk">${icon("star")}실수 없이 끝냄 (+5 XP, +5엔)</p>` : ""}
      ${streakLine ? `<div class="ria-row small"><div class="ria-wrap">${yukiImg({ face: streakLine.face, size: 56 })}</div><p class="bubble">${ruby(streakLine.text)}</p></div>` : ""}
      ${lesson && lesson.summary && lesson.summary.length ? `<section class="panel summary"><h2>오늘 배운 것</h2><ol>${lesson.summary.map((s) => `<li lang="ja">${ruby(s)}</li>`).join("")}</ol></section>` : ""}
      ${quests.length || r.chest ? `<section class="panel"><h2>끝낸 퀘스트</h2><ul class="plain">${quests.map((q) => `<li>${icon("check")}${esc(q.name)} <b class="sun-text">+${q.reward}</b></li>`).join("")}
        ${r.chest ? `<li>${icon("chestOpen")}보물 상자를 열었어요 <b class="sun-text">+10</b></li>` : ""}</ul></section>` : ""}
      ${badges.length ? `<section class="panel"><h2>새 배지</h2><ul class="new-badges">${badges.map((b) => `<li>${badgeArt(b.id, true, 56)}<span>${esc(b.name)}</span></li>`).join("")}</ul></section>` : ""}
    </main>
    <footer class="lesson-foot"><button class="btn primary wide" id="home">계속</button></footer>
  </div>`;
  root.querySelector("#home").addEventListener("click", () => ctx.show(params.from || (jlptLesson ? "jlpt" : "home"))); // 시작한 화면으로
  (async () => {
    if (r.milestone) {
      ctx.sound.play("levelup");
      await celebrate({ item: ctx.save.item, milestone: r.milestone });
    }
    await ctx.afterDone(); // 첫 레슨이면 「홈 화면에 추가」 안내(아이폰 사파리만)
    root.querySelector("#home")?.focus({ preventScroll: true });
  })();
}
