// 보관함: 전통 물건 10개 미리보기, 바이트로 사기, 해치 옆에 두기(한 번에 1개), 기록 보호권
import { ruby, plain } from "../ruby.js";
import { ITEMS } from "../../data/items.js";
import { buy, place } from "../shop.js";
import { buyFreeze, FREEZE_PRICE, FREEZE_MAX } from "../rules.js";
import { checkBadges } from "../badges.js";
import { yukiImg } from "../yuki.js";
import { esc, icon, toast } from "./dom.js";
import { tabBar, bindTabs, statusBar } from "./nav.js";

const nameOf = (o) => `${o.ko} · ${o.jp}`;

export function render(root, ctx, params = {}) {
  let sel = params.sel || ctx.save.item;
  let line = params.line || null;

  function paint() {
    const s = ctx.save;
    const o = ITEMS.find((x) => x.id === sel) || ITEMS[0];
    const own = s.items.includes(o.id);
    const placed = s.item === o.id;
    let action;
    if (placed) action = `<button class="btn ghost wide" disabled>옆에 두었어요</button>`;
    else if (own) action = `<button class="btn primary wide" id="place">유키 옆에 두기</button>`;
    else if (o.price == null) action = `<p class="lock-note">${icon("lock")}30일 연속 보상</p>`;
    else action = `<button class="btn sun wide" id="buy"${s.bytes < o.price ? " disabled" : ""}>${icon("byte")}<span>${o.price}엔으로 사기</span></button>
      ${s.bytes < o.price ? `<p class="muted center">${o.price - Math.max(0, s.bytes)}엔 더 모으면 살 수 있어요</p>` : ""}`;
    root.innerHTML = `<div class="screen closet with-tabs">
      ${statusBar(s)}
      <main>
        <h1 class="page-title">보관함</h1>
        <section class="stage">
          <div class="ria-wrap big">${yukiImg({ face: placed ? "smile" : "sparkle", item: o.id, size: 170 })}</div>
          <div class="stage-info">
            <h2>${esc(o.ko)} · <span lang="ja">${ruby(o.jp)}</span></h2>
            ${line ? `<p class="bubble">${ruby(line)}</p>` : ""}
            ${action}
          </div>
        </section>
        <ul class="outfit-grid" aria-label="물건 목록">${ITEMS.map((x) => {
          const owned = s.items.includes(x.id);
          const tag = s.item === x.id ? "옆에" : owned ? "가짐" : x.price == null ? "30일 보상" : `${x.price}엔`;
          return `<li><button class="outfit${x.id === sel ? " sel" : ""}${owned ? " owned" : ""}" data-o="${x.id}" aria-pressed="${x.id === sel}" aria-label="${esc(`${plain(nameOf(x))}, ${tag}`)}">
            ${x.id === "none" ? yukiImg({ face: "smile", size: 74 }) : `<img class="item-thumb" src="img/items/${x.id}.png" width="74" height="74" alt="">`}
            <span class="o-name">${esc(x.ko)}<br><span lang="ja">${ruby(x.jp)}</span></span>
            <span class="o-tag${owned ? " own" : ""}">${!owned && x.price == null ? icon("lock") : ""}${esc(tag)}</span>
          </button></li>`;
        }).join("")}</ul>
        <section class="panel freeze">
          <div class="freeze-text">
            <h2>${icon("shield")}연속 기록 보호권 <b>${s.freezes}/${FREEZE_MAX}</b></h2>
            <p>목표를 못 채운 날이 있으면 다음에 열 때 저절로 써서 연속 기록을 지켜 줘요.</p>
          </div>
          <button class="btn ghost" id="freeze"${s.freezes >= FREEZE_MAX || s.bytes < FREEZE_PRICE ? " disabled" : ""}>${s.freezes >= FREEZE_MAX ? "가득" : `${FREEZE_PRICE}엔`}</button>
        </section>
      </main>
      ${tabBar("closet")}
    </div>`;
    bindTabs(root, ctx);
    root.querySelectorAll("[data-o]").forEach((b) => b.addEventListener("click", () => { sel = b.dataset.o; line = null; paint(); }));
    const placeBtn = root.querySelector("#place");
    if (placeBtn) placeBtn.addEventListener("click", () => {
      const r = place(ctx.save, o.id);
      if (r instanceof Error) { toast(r.message); return; }
      ctx.commit(r);
      line = o.id === "none" ? null : ctx.say("item_bought", { item: nameOf(o) }).text;
      paint();
    });
    const buyBtn = root.querySelector("#buy");
    if (buyBtn) buyBtn.addEventListener("click", () => {
      const r = buy(ctx.save, o.id);
      if (r instanceof Error) { toast(r.message); return; }
      let next = { ...r, item: o.id };
      const got = checkBadges(next, { hour: new Date().getHours(), lessonDone: false });
      if (got.length) { next = { ...next, badges: [...next.badges, ...got] }; toast("새 배지: 물건 수집가"); }
      ctx.commit(next);
      ctx.sound.play("buy");
      line = ctx.say("item_bought", { item: nameOf(o) }).text;
      paint();
    });
    root.querySelector("#freeze").addEventListener("click", () => {
      const r = buyFreeze(ctx.save);
      if (r instanceof Error) { toast(r.message); return; }
      ctx.commit(r);
      ctx.sound.play("buy");
      toast(`연속 기록 보호권을 샀어요 (${r.freezes}/${FREEZE_MAX})`);
      paint();
    });
  }
  paint();
}
