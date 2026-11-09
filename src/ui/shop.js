// 「유키의 다코야키 가게」 화면: 가게 앞 · 하루 장사(손님 × 인사·주문·인사) · 정산 · 가게 키우기 · 가게 일기
// 규칙은 src/shop/rules.js(순수 함수), 표는 data/shop.js. 이 화면은 그리기와 누르기만 한다.
// 단계마다 결과 창을 닫을 때 저장한다(새로 고쳐도 같은 손님·같은 단계부터).
import {
  shopOpen, doneChapter, startRun, dayCustomers, orderLine, greetCards, judgeOrder, payFor, recordStep, runDone,
  finishDay, buyUpgrade, flowCut,
} from "../shop/rules.js";
import { MENU, COUNTS, GREETINGS, GUESTS, UPGRADES, FLOW, STORIES } from "../../data/shop.js";
import { yukiImg } from "../yuki.js";
import { ruby, plain } from "../ruby.js";
import { esc, icon, toast, sayBtn, celebrate } from "./dom.js";
import { QUESTS } from "../../data/quests.js";
import { statusBar, tabBar, bindTabs } from "./nav.js";

const GUARD_MS = 400;
const MENU_BY = Object.fromEntries(MENU.map((m) => [m.id, m]));
const GUEST_BY = Object.fromEntries(GUESTS.map((g) => [g.id, g]));
const yen = (n) => `${Number(n).toLocaleString("ko-KR")}円`;
const pic = (id, alt, cls = "shop-pic") => `<img class="${cls}" src="img/shop/${id}.png" width="256" height="256" alt="${esc(alt)}">`;

export function render(root, ctx, params = {}) {
  const shop = ctx.save.shop;
  const open = shopOpen(ctx.examIds(), ctx.gateDone());
  if (!open) { ctx.show("home"); return undefined; }
  const view = params.view || "front";
  if (view === "day") return dayView(root, ctx, params);
  if (view === "settle") return settleView(root, ctx, params);
  if (view === "upgrades") return upgradesView(root, ctx);
  if (view === "diary") return diaryView(root, ctx);
  return frontView(root, ctx, shop);
}

function frame(root, ctx, title, body) {
  root.innerHTML = `<div class="screen shop with-tabs">
    ${statusBar(ctx.save)}
    <main>
      <div class="shop-head"><button class="icon-btn" id="back" aria-label="뒤로">${icon("close")}</button><h1 class="page-title">${esc(title)}</h1></div>
      ${body}
    </main>
    ${tabBar("home")}
  </div>`;
  bindTabs(root, ctx);
  root.querySelector("#back").addEventListener("click", () => ctx.show(title === "유키의 다코야키 가게" ? "home" : "shop"));
}

function frontView(root, ctx, shop) {
  const going = !!shop.run;
  frame(root, ctx, "유키의 다코야키 가게", `
    <section class="panel shop-front">
      ${pic("flow-01", FLOW[0].title, "shop-pic wide")}
      <p class="shop-meta"><b>${going ? shop.run.dayNo : shop.day + 1}일째</b> · 가게 금고 <b>${yen(shop.money)}</b></p>
      <button class="btn primary wide" id="start">${icon("play")}<span>${going ? "이어서 장사" : "장사 시작"}</span></button>
      <div class="btn-row">
        <button class="btn ghost" id="upgrades">가게 키우기</button>
        <button class="btn ghost" id="diary">가게 일기 ${shop.stories.length}/${STORIES.length}</button>
      </div>
    </section>`);
  root.querySelector("#start").addEventListener("click", () => {
    const s = ctx.save.shop;
    if (!s.run) {
      ctx.commit({ ...ctx.save, shop: startRun(s, { date: ctx.today(), doneCh: doneChapter(ctx.examIds(), ctx.gateDone()) }) });
      ctx.show("shop", { view: "day", cut: FLOW[0].id });
    } else ctx.show("shop", { view: "day" });
  });
  root.querySelector("#upgrades").addEventListener("click", () => ctx.show("shop", { view: "upgrades" }));
  root.querySelector("#diary").addEventListener("click", () => ctx.show("shop", { view: "diary" }));
}

/** 흐름 컷 한 장(누르면 다음) */
function cutView(root, id, next) {
  const f = FLOW.find((x) => x.id === id);
  root.innerHTML = `<div class="screen shop shop-cut">
    <main><figure class="cut">${pic(id, f.title, "shop-pic big")}<figcaption>${esc(f.title)}</figcaption></figure></main>
    <footer class="lesson-foot"><button class="btn primary wide" id="act">계속</button></footer>
  </div>`;
  root.querySelector("#act").addEventListener("click", next);
}

function dayView(root, ctx, params) {
  if (params.cut) { cutView(root, params.cut, () => ctx.show("shop", { view: "day" })); return undefined; }
  const shop = ctx.save.shop;
  if (!shop.run) { ctx.show("shop"); return undefined; }
  if (runDone(shop)) { cutView(root, FLOW[FLOW.length - 1].id, () => settle(ctx)); return undefined; }
  const run = shop.run;
  const guests = dayCustomers(run);
  const c = guests[run.idx];
  const g = GUEST_BY[c.who];
  const firstDay = run.dayNo === 1;
  const earned = run.results.reduce((n, r) => n + (r.paid || 0), 0);
  const seed = `${run.seed}:${run.idx}`;
  let body = "", answerHTML = "", judge;

  if (run.step === "greet" || run.step === "bye") {
    const kind = run.step === "greet" ? "enter" : "leave";
    const { cards, answer } = greetCards(kind, seed);
    body = `<h1 class="q">${run.step === "greet" ? "손님이 들어왔어요. 뭐라고 맞이할까요?" : "손님이 나가요. 뭐라고 인사할까요?"}</h1>
      <div class="options" role="radiogroup" aria-label="인사">${cards.map((x, i) =>
        `<button class="opt" role="radio" aria-checked="false" data-i="${i}"><span class="opt-key" aria-hidden="true">${i + 1}</span>
          <span class="opt-text" lang="ja">${ruby(x.jp)}${firstDay ? `<small class="opt-ko">${esc(x.ko)}</small>` : ""}</span></button>`).join("")}</div>`;
    const right = GREETINGS[kind].answer;
    answerHTML = `<p class="answer">정답: <span lang="ja">${ruby(right.jp)}</span> (${esc(right.ko)})</p>`;
    judge = (pick) => pick.i === answer;
  } else {
    const line = orderLine(c, run.ctx.doneCh);
    const tpl = c.tpl === "t_count" || c.tpl === "t_onegai";
    body = `<div class="ria-row guest-say"><p class="bubble" lang="ja">${ruby(line.jp)}${sayBtn(line.jp)}</p></div>
      ${line.hint ? `<p class="muted hint">뜻: ${esc(line.hint)}</p>` : ""}
      <p class="ex-label">메뉴</p>
      <div class="menu-grid" role="radiogroup" aria-label="메뉴">${run.ctx.menus.map((id) => {
        const m = MENU_BY[id];
        return `<button class="opt menu-card" role="radio" aria-checked="false" data-menu="${id}">
          ${m.img ? `<img src="${m.img}" width="44" height="44" alt="">` : ""}<span lang="ja">${ruby(m.jp)}</span><small>${esc(m.ko)}</small></button>`;
      }).join("")}</div>
      ${tpl ? `<p class="ex-label">개수</p><div class="count-row" role="radiogroup" aria-label="개수">${COUNTS.map((k) =>
        `<button class="opt count-card" role="radio" aria-checked="false" data-count="${k.n}"><span lang="ja">${ruby(k.jp)}</span><small>${k.ko}</small></button>`).join("")}</div>` : ""}`;
    answerHTML = `<p class="answer">정답: <span lang="ja">${ruby(MENU_BY[c.menu].jp)}</span> ${tpl ? `<span lang="ja">${ruby(COUNTS[c.count - 1].jp)}</span>` : ""}</p>`;
    judge = (pick) => judgeOrder(c, pick.menu, tpl ? pick.count : 1);
  }

  root.innerHTML = `<div class="screen lesson shop-day">
    <header class="lesson-top">
      <button class="icon-btn" id="quit" aria-label="가게 앞으로">${icon("close")}</button>
      <p class="shop-progress">${run.dayNo}일째 · 손님 ${run.idx + 1}/${run.ctx.n} · ${yen(earned)}</p>
      <span class="lesson-tag">${{ greet: "어서 오세요", order: "주문", bye: "배웅" }[run.step]}</span>
    </header>
    <main class="lesson-body">
      <div class="guest">${pic("guest-" + c.who, g.name, "guest-pic")}<p class="guest-name">${esc(g.name)}</p></div>
      ${body}
    </main>
    <footer class="lesson-foot"><button class="btn primary wide" id="act" disabled>${run.step === "order" ? "내주기" : "확인"}</button></footer>
    <section class="result" id="result" role="status" aria-live="polite" hidden></section>
  </div>`;

  const pick = {};
  const act = root.querySelector("#act");
  const ready = () => run.step !== "order" ? pick.i != null : pick.menu && (!root.querySelector(".count-row") || pick.count);
  const choose = (sel, key, conv) => root.querySelectorAll(sel).forEach((b) => b.addEventListener("click", () => {
    pick[key] = conv(b);
    root.querySelectorAll(sel).forEach((x) => x.setAttribute("aria-checked", String(x === b)));
    act.disabled = !ready();
  }));
  choose(".options .opt", "i", (b) => +b.dataset.i);
  choose(".menu-card", "menu", (b) => b.dataset.menu);
  choose(".count-card", "count", (b) => +b.dataset.count);
  root.querySelector("#quit").addEventListener("click", () => ctx.show("shop"));

  act.addEventListener("click", () => {
    if (act.disabled || !ready()) return;
    act.disabled = true;
    const ok = judge(pick);
    ctx.sound.play(ok ? "correct" : "wrong");
    const line = ctx.say(ok ? "correct" : "wrong");
    const next = recordStep(ctx.save.shop, ok);
    const done = run.step === "bye" ? next.run.results[run.idx] : null;
    const result = root.querySelector("#result");
    result.className = "result " + (ok ? "ok" : "bad");
    result.innerHTML = `<div class="result-scroll">
        <div class="result-head"><span class="result-ic">${icon(ok ? "check" : "cross")}</span><h2>${ok ? "정답이에요" : "아까워요"}</h2></div>
        ${ok ? "" : answerHTML}
        ${run.step === "order" ? `<p class="result-explain" lang="ja">${ruby(orderLine(c, 99).jp)}${sayBtn(orderLine(c, 99).jp)}</p>` : ""}
        ${done ? `<p class="result-explain">${esc(g.name)}: <span lang="ja">${ruby(g.bye.jp)}</span> (${esc(g.bye.ko)}) · <b>+${yen(done.paid)}</b>${
          done.greet && done.order && done.bye ? " (팁 포함)" : ""}</p>` : ""}
        <div class="ria-row small"><div class="ria-wrap">${yukiImg({ face: line.face, size: 64 })}</div><p class="bubble">${ruby(line.text)}</p></div>
      </div>
      <button class="btn ${ok ? "primary" : "coral"} wide" id="cont">계속</button>`;
    result.hidden = false;
    document.body.classList.add("result-open");
    root.querySelector("#quit").disabled = true; // 「계속」 전에 나가면 이 손님 결과가 저장되지 않으므로
    const guard = performance.now() + GUARD_MS;
    const cont = result.querySelector("#cont");
    requestAnimationFrame(() => cont.focus({ preventScroll: true }));
    cont.addEventListener("click", () => {
      if (performance.now() < guard) return;
      document.body.classList.remove("result-open");
      ctx.commit({ ...ctx.save, shop: next });
      // 손님 2명을 보낼 때마다 흐름 컷 한 장(날마다 이어지는 순서, 02~14 돌림)
      const cut = run.step === "bye" ? flowCut(run, run.idx + 1) : null;
      ctx.show("shop", { view: "day", cut });
    });
  });
  // 키보드(아이패드): 숫자 = 인사 카드·메뉴 고르기(개수는 누르기), Enter = 확인. 결과 창이 뜨면 초점이 「계속」에 있어 Enter가 그대로 눌린다
  const result = root.querySelector("#result");
  const onKey = (e) => {
    if (!result.hidden || e.altKey || e.ctrlKey || e.metaKey) return;
    const n = /^[1-9]$/.test(e.key) ? +e.key - 1 : -1;
    const opts = root.querySelectorAll(run.step === "order" ? ".menu-card" : ".options .opt");
    if (n >= 0 && opts[n]) { e.preventDefault(); opts[n].click(); return; }
    if (e.key === "Enter" && !(document.activeElement instanceof HTMLButtonElement) && !act.disabled) { e.preventDefault(); act.click(); }
  };
  document.addEventListener("keydown", onKey);
  return () => { document.removeEventListener("keydown", onKey); document.body.classList.remove("result-open"); };
}

function settle(ctx) {
  const r = finishDay(ctx.save, ctx.today());
  if (r instanceof Error) { ctx.show("shop"); return; }
  ctx.commit(r.save);
  ctx.show("shop", { view: "settle", report: r.report });
}

function settleView(root, ctx, params) {
  const r = params.report;
  if (!r) { ctx.show("shop"); return; }
  const st = r.story ? STORIES.find((s) => s.id === r.story) : null;
  frame(root, ctx, `${ctx.save.shop.day}일째 장사 끝!`, `
    <section class="panel shop-settle">
      <ul class="tiles" aria-label="오늘 결과">
        <li class="tile byte">${icon("byte")}<b>${yen(r.money)}</b><span>오늘 매출</span></li>
        <li class="tile acc">${icon("check")}<b>${r.right}/${r.total}</b><span>만족한 손님</span></li>
        <li class="tile">${icon("xp")}<b>+${r.xp}</b><span>XP</span></li>
      </ul>
      ${r.xp ? "" : `<p class="muted center">오늘 받을 수 있는 XP는 다 받았어요(하루 두 번).</p>`}
      <p class="center">가게 금고 <b>${yen(ctx.save.shop.money)}</b></p>
    </section>
    ${st ? `<section class="panel story-new"><h2>새 이야기: ${esc(st.title)}</h2>${pic(st.id, st.title, "shop-pic big")}
      <p lang="ja">${ruby(st.line.jp)} <span class="muted">(${esc(st.line.ko)})</span></p></section>` : ""}
    ${(r.finished || []).length || r.chest ? `<section class="panel shop-settle-quests"><h2>끝낸 퀘스트</h2><ul class="plain">${(r.finished || [])
      .map((id) => QUESTS.find((q) => q.id === id)).filter(Boolean).map((q) => `<li>${icon("check")}${esc(q.name)} <b class="sun-text">+${q.reward}</b></li>`).join("")}
      ${r.chest ? `<li>${icon("chestOpen")}보물 상자를 열었어요 <b class="sun-text">+10</b></li>` : ""}</ul></section>` : ""}
    <div class="btn-row"><button class="btn ghost" id="up">가게 키우기</button><button class="btn primary" id="home">홈으로</button></div>`);
  root.querySelector("#up").addEventListener("click", () => ctx.show("shop", { view: "upgrades" }));
  root.querySelector("#home").addEventListener("click", () => ctx.show("home"));
  // 정산 XP로 연속 기록 이정표를 넘었으면 레슨 완료처럼 축하 창(새로 고침으로 다시 뜨지 않게 report에서만)
  if (r.milestone) celebrate({ item: ctx.save.item, milestone: r.milestone });
}

function upgradesView(root, ctx) {
  const shop = ctx.save.shop;
  frame(root, ctx, "가게 키우기", `
    <p class="shop-meta">가게 금고 <b>${yen(shop.money)}</b></p>
    <ul class="up-list">${UPGRADES.map((u) => {
      const own = shop.upgrades.includes(u.id);
      const fx = u.effect.menu ? "새 메뉴" : u.effect.guests ? "손님 +1명" : "팁 +5%";
      return `<li class="panel up${own ? " owned" : ""}"><div><b>${ruby(u.name)}</b><small>${fx}</small></div>
        ${own ? `<span class="tag">있음</span>` : `<button class="btn sun" data-up="${u.id}"${shop.money < u.price ? " disabled" : ""}>${yen(u.price)}</button>`}</li>`;
    }).join("")}</ul>`);
  root.querySelectorAll("[data-up]").forEach((b) => b.addEventListener("click", () => {
    const next = buyUpgrade(ctx.save.shop, b.dataset.up);
    if (next instanceof Error) { toast(next.message, "warn"); return; }
    ctx.commit({ ...ctx.save, shop: next });
    toast(`${plain(UPGRADES.find((u) => u.id === b.dataset.up).name)}을(를) 들였어요!`);
    ctx.show("shop", { view: "upgrades" });
  }));
}

function diaryView(root, ctx) {
  const have = new Set(ctx.save.shop.stories);
  frame(root, ctx, "가게 일기", `<ul class="diary">${STORIES.map((s) => have.has(s.id)
    ? `<li class="panel"><figure>${pic(s.id, s.title)}<figcaption><b>${esc(s.title)}</b><span lang="ja">${ruby(s.line.jp)}</span><small>${esc(s.line.ko)}</small></figcaption></figure></li>`
    : `<li class="panel locked">${icon("lock")}<span>${s.day}일째에 열려요</span></li>`).join("")}</ul>`);
}
