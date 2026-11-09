// 설정: 소리, 하루 목표, 이름, 저장 내보내기·가져오기, 판 번호
import { DAILY_GOALS } from "../rules.js";
import { esc, toast, dialog, celebrate, icon } from "./dom.js";
import { collectOfflineStatus } from "../offline.js";
import { curriculum, chapterWindow } from "../curriculum.js";
import { applyGoalChange } from "../finish.js";
import { isOwnSave } from "../save.js";
import { tabBar, bindTabs, statusBar } from "./nav.js";
import { localDate } from "../today.js";
import { chapterNo } from "../track.js";

/** 이름: 앞뒤 빈칸을 빼고 8자까지 */
export function cleanName(v) {
  let s = String(v || "").trim();
  return Array.from(s).slice(0, 8).join("");
}

const ST = {
  done: ["check", "끝냄"], current: ["play", "지금"], open: ["play", "열림"], locked: ["lock", "잠김"],
};

/** 학습 내용 카드 (C33): 요약 한 줄, 장마다 펼치기, 다음 업데이트 예정 */
function courseCard(ctx) {
  const c = curriculum({ chapters: ctx.chapters, completed: ctx.save.completed_lessons, currentId: ctx.currentLessonId(),
    seenUpdates: ctx.save.seen_updates, open: ctx.isDev() });
  const dot = (l) => (l.isNew ? '<span class="new-dot inline" role="img" aria-label="새 내용 있음">N</span>' : "");
  const first = c.upcoming.slice(0, 3);
  const rest = c.upcoming.slice(3);
  const upName = (u) => `${u.no}장 ${u.title}`;
  // 처음엔 지금 장과 앞뒤 셋만(C35). 나머지는 「다른 장 N개 더 보기」로
  const curCh = c.current ? (c.chapters.find((ch) => ch.lessons.some((l) => l.id === c.current.id)) || {}).id : null;
  const win = chapterWindow({ chapterIds: c.chapters.map((ch) => ch.id), currentChapter: curCh ?? null });
  const hiddenSet = new Set(win.hidden);
  return `<section class="panel course" aria-labelledby="course-title">
    <h2 id="course-title">학습 내용</h2>
    <p class="course-sum">레슨 ${c.total}개 중 <b>${c.done}</b>개 끝냄${c.current ? ` · 지금: ${esc(c.current.id)} ${esc(c.current.title)}` : ""}${c.advTotal ? `<br><small>심화(선택) ${c.advTotal}개 중 ${c.advDone}개 끝냄</small>` : ""}</p>
    <ul class="course-chapters" id="course-chapters">${c.chapters.map((ch) => `<li${hiddenSet.has(ch.id) ? ' class="ch-extra" hidden' : ""}>
      <button class="ch-row" aria-expanded="false" aria-controls="ch-${ch.id}">
        <span class="ch-no">${ch.id}</span>
        <span class="ch-main"><b>${esc(ch.title)}</b><small>${esc(ch.topics)}</small></span>
        <span class="ch-side"><span class="ch-count${ch.done === ch.total ? " full" : ""}">${ch.done}/${ch.total} 끝냄</span>
          ${ch.advTotal ? `<span class="ch-adv${ch.advDone === ch.advTotal ? " full" : ""}">${icon("star")}심화 ${ch.advDone}/${ch.advTotal}</span>` : ""}</span>
      </button>
      <ol class="ch-lessons" id="ch-${ch.id}" hidden>${ch.lessons.map((l) => `<li class="ls ${l.status}">
        <span class="ls-st">${icon(ST[l.status][0])}<span>${ST[l.status][1]}</span></span>
        <span class="ls-main"><b>${esc(l.id)} ${esc(l.title)}${dot(l)}</b><small>${esc(l.goal)}</small></span>
      </li>`).join("")}
      ${ch.advTotal ? `<li class="ch-adv-head">${icon("star")}심화 <small>장 평가 뒤 열림 · 선택</small></li>${ch.advanced.map((l) => `<li class="ls adv ${l.status}">
        <span class="ls-st">${icon(ST[l.status][0])}<span>${ST[l.status][1]}</span></span>
        <span class="ls-main"><b>${esc(l.id)} ${esc(l.title)}${dot(l)}</b><small>${esc(l.goal)}</small></span>
      </li>`).join("")}` : ""}</ol>
    </li>`).join("")}</ul>
    ${win.hidden.length ? `<button class="btn ghost small wide" id="ch-more" aria-expanded="false" aria-controls="course-chapters" data-n="${win.hidden.length}">다른 장 ${win.hidden.length}개 더 보기</button>` : ""}
    ${c.upcoming.length ? `<p class="muted course-next">다음 업데이트: ${esc(first.map(upName).join(" · "))}${rest.length ? `<span id="up-rest" hidden> · ${esc(rest.map(upName).join(" · "))}</span><span id="up-dots"> …</span>` : ""}</p>
      ${rest.length ? `<button class="link" id="up-all" aria-expanded="false" aria-controls="up-rest">모두</button>` : ""}` : ""}
  </section>`;
}

/** JLPT 학습 내용(JLPT 설계 §3-4): 장마다 끝낸 레슨 수. 펼치기 없이 한 줄씩 */
function jlptCard(ctx) {
  const chs = ctx.jlptChapters;
  if (!chs.length) return "";
  const d = new Set(ctx.save.completed_lessons);
  return `<section class="panel course jlpt-course" aria-labelledby="jlpt-course-title">
    <h2 id="jlpt-course-title">JLPT N5</h2>
    <p class="course-sum">N5 단어 ${ctx.n5Total}개 중 <b>${ctx.n5Learned()}</b>개 배움</p>
    <ul class="course-chapters">${chs.map((ch) => {
      const done = ch.lessons.filter((l) => d.has(l.id)).length;
      return `<li><div class="ch-row static"><span class="ch-no">${chapterNo(ch.id)}</span>
        <span class="ch-main"><b>${esc(ch.title.replace(/^N5 · \d+장 /, ""))}</b></span>
        <span class="ch-side"><span class="ch-count${done === ch.lessons.length ? " full" : ""}">${done}/${ch.lessons.length} 끝냄</span></span></div></li>`;
    }).join("")}</ul>
  </section>`;
}

export function render(root, ctx) {
  const s = ctx.save;
  const goal = DAILY_GOALS.includes(s.settings.dailyGoal) ? s.settings.dailyGoal : 20;
  root.innerHTML = `<div class="screen settings with-tabs">
    ${statusBar(s)}
    <main>
      <h1 class="page-title">설정</h1>
      ${courseCard(ctx)}
      ${jlptCard(ctx)}
      <section class="panel">
        <div class="row">
          <label for="snd" class="row-label">소리<small>정답·오답 효과음 (🔊 발음은 늘 들을 수 있어요)</small></label>
          <button class="switch" id="snd" role="switch" aria-checked="${s.settings.sound !== false}"><span></span></button>
        </div>
        <div class="row col" role="group" aria-labelledby="goal-label">
          <p class="row-label" id="goal-label">하루 목표<small>목표를 채운 날마다 연속 기록이 하루씩 늘어요</small></p>
          <div class="seg" role="radiogroup" aria-label="하루 목표">${DAILY_GOALS.map((g) =>
            `<button role="radio" aria-checked="${g === goal}" data-g="${g}">${g} XP</button>`).join("")}</div>
        </div>
        <div class="row col">
          <label for="name" class="row-label">부를 이름<small>유키 선생님이 이렇게 불러요. 비워 둬도 돼요</small></label>
          <input id="name" type="text" maxlength="9" autocomplete="nickname" autocapitalize="off" value="${esc(s.settings.name || "")}" placeholder="예: 민지">
        </div>
      </section>
      <section class="panel">
        <h2>저장</h2>
        <p class="muted">진도는 이 브라우저에만 저장돼요. 휴대폰을 바꾸거나 기록이 걱정되면 파일로 내보내 두세요.</p>
        <div class="btn-row">
          <button class="btn ghost" id="export">저장 내보내기</button>
          <label class="btn ghost" for="import">저장 가져오기</label>
          <input id="import" type="file" accept="application/json,.json" class="sr">
        </div>
        <p class="offline-status wait" id="offline" role="status" aria-live="polite">${icon("review")}<span>오프라인 준비 상태를 확인하는 중……</span></p>
      </section>
      <section class="panel">
        <h2>홈 화면에 추가</h2>
        <p class="muted">아이폰·아이패드 사파리에서 홈 화면에 추가하면 앱처럼 열리고 기록도 더 안전해요.</p>
        <button class="btn ghost wide" id="install">홈 화면에 추가하는 방법</button>
      </section>
      <p class="ver center">사나다 일본어 ${esc(ctx.version)} · <a class="lic-link" href="licenses.txt" target="_blank" rel="noopener">오픈 소스</a></p>
      <p class="muted center credit">진도 참고: NHK WORLD-JAPAN 『일본말 첫걸음』 1~24과 순서(교재 내용은 옮기지 않았어요)<br>읽기 대조: <a class="lic-link" href="https://www.edrdg.org/jmdict/j_jmdict.html" target="_blank" rel="noopener">JMdict</a>(EDRDG, CC BY-SA 4.0) · 단어 표 CC BY-SA 4.0<br>JLPT 급수 목록: <a class="lic-link" href="https://github.com/jamsinclair/open-anki-jlpt-decks" target="_blank" rel="noopener">open-anki-jlpt-decks</a>(MIT) · 원본 tanos.co.uk(Jonathan Waller, CC BY)<br>이 앱은 NHK와 관련이 없어요.</p>
      <section class="panel devmode" aria-labelledby="dev-label">
        <div class="row">
          <p class="row-label" id="dev-label">개발자 모드<small>잠긴 곳을 모두 열어 검수해요. 학습 기록과 따로 저장돼요.</small></p>
          <button class="switch" id="dev" role="switch" aria-checked="${ctx.isDev()}" aria-labelledby="dev-label"><span></span></button>
        </div>
        ${ctx.isDev() ? '<p class="muted">켜져 있어요 · 끄면 학습 기록으로 돌아가요</p>' : ""}
      </section>
    </main>
    ${tabBar("settings")}
  </div>`;
  bindTabs(root, ctx);

  // 학습 내용 펼치기
  root.querySelectorAll(".ch-row").forEach((b) => b.addEventListener("click", () => {
    const open = b.getAttribute("aria-expanded") !== "true";
    b.setAttribute("aria-expanded", String(open));
    root.querySelector("#" + b.getAttribute("aria-controls")).hidden = !open;
  }));
  const chMore = root.querySelector("#ch-more");
  if (chMore) chMore.addEventListener("click", () => {
    const open = chMore.getAttribute("aria-expanded") !== "true";
    chMore.setAttribute("aria-expanded", String(open));
    root.querySelectorAll(".ch-extra").forEach((li) => { li.hidden = !open; });
    chMore.textContent = open ? "접기" : `다른 장 ${chMore.dataset.n}개 더 보기`;
  });
  const upAll = root.querySelector("#up-all");
  if (upAll) upAll.addEventListener("click", () => {
    const open = upAll.getAttribute("aria-expanded") !== "true";
    upAll.setAttribute("aria-expanded", String(open));
    root.querySelector("#up-rest").hidden = !open;
    root.querySelector("#up-dots").hidden = open;
    upAll.textContent = open ? "접기" : "모두";
  });

  // 오프라인 준비 상태: 서비스 작업자 + 장 파일 전부. 색만이 아니라 아이콘과 글로 알림
  const off = root.querySelector("#offline");
  collectOfflineStatus(ctx.chapterFiles).then((r) => {
    if (!off.isConnected) return;
    off.className = "offline-status " + (r.ready ? "ready" : "wait");
    off.innerHTML = r.ready
      ? `${icon("check")}<span>오프라인 준비 끝</span>`
      : `${icon("review")}<span>아직 준비 중이에요 — 인터넷이 될 때 앱을 한 번 다시 열면 모든 레슨을 받아 둬요</span>`;
    off.dataset.ready = String(r.ready);
  });

  const setSettings = (patch) => {
    const cur = ctx.save;
    ctx.commit({ ...cur, settings: { ...cur.settings, ...patch } });
  };
  const snd = root.querySelector("#snd");
  snd.addEventListener("click", () => {
    const on = !(ctx.save.settings.sound !== false);
    setSettings({ sound: on });
    snd.setAttribute("aria-checked", String(on));
    if (on) ctx.sound.play("correct");
  });
  root.querySelectorAll("[data-g]").forEach((b) => b.addEventListener("click", async () => {
    // 목표를 낮춰 오늘 모은 XP가 이미 넘으면 그날을 바로 인정(이정표 보상 포함)
    const r = applyGoalChange(ctx.save, +b.dataset.g, ctx.today());
    ctx.commit(r.save);
    if (r.streakUp) toast(`오늘 목표 달성! ${r.save.streak.days}일 연속이에요.`);
    if (r.milestone) {
      ctx.sound.play("levelup");
      await celebrate({ item: ctx.save.item, milestone: r.milestone });
    }
    ctx.show("settings"); // 위 상태 줄 목표 숫자도 바로 맞춤
  }));
  const name = root.querySelector("#name");
  name.addEventListener("change", () => {
    const v = cleanName(name.value);
    name.value = v;
    setSettings({ name: v });
    toast(v ? `앞으로 「${v}」 씨라고 부를게요.` : "알겠어요, 이름 없이 부를게요.");
  });

  root.querySelector("#dev").addEventListener("click", () => {
    const on = !ctx.isDev();
    ctx.setDev(on);
    ctx.show("settings");
    document.getElementById("dev")?.focus(); // 다시 그린 뒤에도 맨 아래 스위치에 머문다
    toast(on ? "개발자 모드를 켰어요. 모든 레슨과 가게가 열려요." : "개발자 모드를 껐어요. 학습 기록으로 돌아왔어요.");
  });
  root.querySelector("#install").addEventListener("click", () => ctx.showInstallSheet());
  root.querySelector("#export").addEventListener("click", () => {
    const blob = new Blob([JSON.stringify(ctx.save, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `sanada-japanese-${ctx.isDev() ? "dev-" : ""}save-${localDate()}.json`;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
    toast("저장 파일을 내보냈어요.");
  });
  root.querySelector("#import").addEventListener("change", async (e) => {
    const f = e.target.files && e.target.files[0];
    e.target.value = "";
    if (!f) return;
    let raw;
    try { raw = JSON.parse(await f.text()); } catch { toast("저장 파일을 읽지 못했어요. 내보내기로 받은 .json 파일인지 확인해 주세요.", "warn"); return; }
    if (!isOwnSave(raw)) {
      toast("이 앱의 저장 파일이 아니에요. 「저장 내보내기」로 받은 파일을 골라 주세요.", "warn");
      return;
    }
    const next = ctx.migrate(raw);
    const ok = await dialog({
      title: "이 저장 파일로 바꿀까요?",
      body: `<p>레슨 ${next.completed_lessons.length}개 끝냄, XP ${Math.max(0, next.xp)}, ${Math.max(0, next.bytes)}엔, ${next.streak.days}일 연속</p><p>지금 브라우저의 진도가 이 파일 내용으로 바뀌어요.</p>`,
      buttons: [{ label: "취소", value: false }, { label: "바꾸기", value: true, kind: "primary" }],
    });
    if (!ok) return;
    ctx.commit(next);
    ctx.dayStart(); // 가져온 저장의 날짜로 연속 기록·퀘스트를 오늘에 맞춤
    toast("저장 파일을 가져왔어요.");
    ctx.noticeRefund();
    ctx.show("home");
  });
}
