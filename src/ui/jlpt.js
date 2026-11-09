// JLPT 탭 (JLPT 설계 2026-11-09 §3-2): 가나 2장 뒤 열림. 급수 고르기(N5만, N4~N1 준비 중) · 진행 요약 · 이어서 배우기 · 복습 · N5 학습 길
import { greetFace } from "../yuki.js";
import { esc, icon, riaSays } from "./dom.js";
import { tabBar, bindTabs, statusBar } from "./nav.js";
import { pathSection, reviewCard, bindPath } from "./home.js";
import { chapterNo } from "../track.js";

const LEVELS = ["N5", "N4", "N3", "N2", "N1"];

export function render(root, ctx) {
  const save = ctx.save;
  if (!ctx.jlptOpen()) {
    root.innerHTML = `<div class="screen jlpt with-tabs">
      ${statusBar(save)}
      <main>
        <h1 class="page-title">JLPT</h1>
        <section class="hello">
          ${riaSays({ item: save.item, face: "smile", text: "히라가나·가타카나를 끝내면 JLPT 공부가 열려요", size: 92 })}
          <button class="btn primary wide" id="to-kana">${icon("path")}<span>가나 배우러 가기</span></button>
        </section>
      </main>
      ${tabBar("jlpt")}
    </div>`;
    bindTabs(root, ctx);
    root.querySelector("#to-kana").addEventListener("click", () => ctx.show("home"));
    return;
  }
  const lessons = ctx.jlptLessons;
  const currentId = ctx.currentLessonId("jlpt");
  const cur = currentId ? ctx.lessonById(currentId) : null;
  const allDone = lessons.length > 0 && lessons.every((l) => save.completed_lessons.includes(l.id));
  const started = lessons.some((l) => save.completed_lessons.includes(l.id));
  let start = 0;
  const sections = ctx.jlptChapters.map((c) => { const html = pathSection(ctx, c, start, currentId); start += c.lessons.length; return html; }).join("");
  root.innerHTML = `<div class="screen jlpt with-tabs">
    ${statusBar(save)}
    <main>
      <h1 class="page-title">JLPT</h1>
      <ul class="levels" aria-label="급수">${LEVELS.map((lv) => lv === "N5"
        ? `<li class="level on" aria-current="true">${lv}</li>`
        : `<li class="level soon">${lv}<small>준비 중</small></li>`).join("")}</ul>
      <section class="hello">
        ${riaSays({ item: save.item, face: greetFace(), text: `N5 단어 ${ctx.n5Total}개 중 ${ctx.n5Learned()}개 배웠어요`, size: 92 })}
        ${cur && !allDone ? `<button class="btn primary wide" id="jlpt-continue">${icon("play")}<span>${started ? "이어서 배우기" : "첫 레슨 시작"} · N5 · ${chapterNo(cur.chapter)}장 ${esc(cur.title)}</span></button>` : ""}
      </section>
      ${reviewCard(save)}
      ${sections || '<p class="panel">레슨을 불러오지 못했어요. 페이지를 새로 고쳐 주세요.</p>'}
      <p class="path-end">${allDone ? "N5 단어를 모두 마쳤어요! N4는 다음 업데이트에 열려요" : "N5 · 14장까지 있어요. N4는 다음 업데이트에 열려요"}</p>
    </main>
    ${tabBar("jlpt")}
  </div>`;
  bindTabs(root, ctx);
  const go = root.querySelector("#jlpt-continue");
  if (go) go.addEventListener("click", () => ctx.show("lesson", { id: currentId }));
  bindPath(root, ctx, "jlpt");
}
