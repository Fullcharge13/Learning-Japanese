// 유키의 오사카 다코야키 가게 데이터 표 (설계: docs/superpowers/specs/2026-11-09-다코야키-가게-설계.md §3·§4)
// 일본어 한자는 「字{よみ}」 표기(화면이 ruby로 그림). 그림: src/img/shop/ (tools/cut_sheets.py)

export const SHOP_TIP = 0.10;
export const BASE_GUESTS = 6;
export const MAX_GUESTS = 8;
export const DAY_XP = 10;
export const XP_RUNS_PER_DAY = 2;

export const MENU = [
  { id: "takoyaki", jp: "たこ焼{や}き", ko: "다코야키", price: 400, img: "img/shop/menu-takoyaki.png", start: true },
  { id: "ocha", jp: "お茶{ちゃ}", ko: "차", price: 150, img: null, start: true },
  { id: "juice", jp: "ジュース", ko: "주스", price: 200, img: null, start: false },
  { id: "dango", jp: "団子{だんご}", ko: "당고", price: 300, img: "img/shop/menu-dango.png", start: false },
  { id: "taiyaki", jp: "たい焼{や}き", ko: "타이야키", price: 250, img: "img/shop/menu-taiyaki.png", start: false },
  { id: "negitako", jp: "ねぎたこ", ko: "파 다코야키", price: 500, img: null, start: false },
  { id: "ramune", jp: "ラムネ", ko: "라무네", price: 200, img: null, start: false },
];

// need: 이 장(앱 장 번호, 평가 통과)을 끝내면 나옴 · learn: 이 장을 끝내면 한국어 힌트가 사라짐
export const TEMPLATES = [
  { id: "t_name", jp: "{menu}！", ko: "{menu_ko}요!", need: 2, learn: 2, count: false },
  { id: "t_kudasai", jp: "{menu}を ください。", ko: "{menu_ko} 주세요.", need: 2, learn: 9, count: false },
  { id: "t_count", jp: "{menu}を {count} ください。", ko: "{menu_ko} {count_ko} 주세요.", need: 9, learn: 12, count: true },
  { id: "t_onegai", jp: "{menu}、{count} お願{ねが}いします。", ko: "{menu_ko} {count_ko} 부탁해요.", need: 9, learn: 12, count: true },
];

export const COUNTS = [
  { n: 1, jp: "一{ひと}つ", ko: "1개" },
  { n: 2, jp: "二{ふた}つ", ko: "2개" },
  { n: 3, jp: "三{みっ}つ", ko: "3개" },
];

export const GREETINGS = {
  enter: {
    answer: { jp: "いらっしゃいませ", ko: "어서 오세요" },
    wrong: [{ jp: "ありがとうございました", ko: "감사했습니다" }, { jp: "いただきます", ko: "잘 먹겠습니다" },
      { jp: "おやすみなさい", ko: "안녕히 주무세요" }, { jp: "はじめまして", ko: "처음 뵙겠습니다" }],
  },
  leave: {
    answer: { jp: "ありがとうございました", ko: "감사합니다(가게에서 손님을 보낼 때)" },
    wrong: [{ jp: "いらっしゃいませ", ko: "어서 오세요" }, { jp: "いただきます", ko: "잘 먹겠습니다" },
      { jp: "はじめまして", ko: "처음 뵙겠습니다" }, { jp: "おやすみなさい", ko: "안녕히 주무세요" }],
  },
};

// 손님 시트 칸 순서(5×3, 왼쪽 위부터). 이름은 그림 내용에 맞춤(시트 3행 이름표가 어긋나 있음)
export const GUESTS = [
  { id: "ojisan", name: "오사카 토박이 아저씨", likes: ["takoyaki", "negitako"], bye: { jp: "やっぱり この味{あじ}や！", ko: "역시 이 맛이야!" } },
  { id: "obaachan", name: "인자한 할머니", likes: ["ocha", "dango"], bye: { jp: "ゆっくりで いいよ。", ko: "천천히 해도 돼." } },
  { id: "kinder", name: "호기심 많은 유치원생", likes: ["juice", "taiyaki"], bye: { jp: "タコ、おおきい！", ko: "문어 커요!" } },
  { id: "joshi", name: "단골 여고생 둘", likes: ["ramune", "takoyaki"], bye: { jp: "また 来{く}るね！", ko: "또 올게요!" } },
  { id: "salary", name: "퇴근길 직장인", likes: ["takoyaki", "ocha"], bye: { jp: "今日{きょう}も おつかれさま！", ko: "오늘도 수고했어!" } },
  { id: "tokyo", name: "도쿄에서 온 대학생", likes: ["takoyaki"], bye: { jp: "本場{ほんば}の 味{あじ}だ！", ko: "본고장 맛이다!" } },
  { id: "youtuber", name: "유튜브 크리에이터", likes: ["negitako"], bye: { jp: "大阪{おおさか}の 名物{めいぶつ}です！", ko: "오사카 명물이에요!" } },
  { id: "tourist", name: "카메라를 든 외국인 관광객", likes: ["takoyaki", "ramune"], bye: { jp: "おいしい！ また 来{き}ます！", ko: "맛있어요! 또 올게요!" } },
  { id: "family", name: "지방에서 온 가족", likes: ["takoyaki", "juice"], bye: { jp: "みんなで 食{た}べよう！", ko: "다 같이 먹자!" } },
  { id: "business", name: "출장 온 비즈니스맨", likes: ["ocha", "takoyaki"], bye: { jp: "新幹線{しんかんせん}で 食{た}べます。", ko: "신칸센에서 먹을게요." } },
  { id: "mania", name: "다코야키 매니아", likes: ["takoyaki"], bye: { jp: "いつもの、はやく！", ko: "늘 먹던 걸로, 빨리요!" } },
  { id: "dogwalk", name: "강아지 산책하는 이웃", likes: ["dango"], bye: { jp: "ワンちゃんも ほしいって。", ko: "강아지도 먹고 싶대요." } },
  { id: "ensoku", name: "소풍 가는 학생들", likes: ["juice", "taiyaki"], bye: { jp: "もう ひとつ！", ko: "하나 더!" } },
  { id: "couple", name: "데이트 중인 연인", likes: ["taiyaki", "ramune"], bye: { jp: "あーん して！", ko: "아~ 해 봐!" } },
  { id: "memory", name: "추억을 남기는 가족", likes: ["takoyaki", "dango"], bye: { jp: "いい 思{おも}い出{で}に なりました。", ko: "좋은 추억이 됐어요." } },
];

export const UPGRADES = [
  { id: "m_juice", name: "ジュース 메뉴", price: 2000, effect: { menu: "juice" } },
  { id: "neko", name: "마네키네코 장식", price: 3000, effect: { tip: 0.05 } },
  { id: "m_dango", name: "団子{だんご} 메뉴", price: 4000, effect: { menu: "dango" } },
  { id: "plate2", name: "철판 한 판 더", price: 5000, effect: { guests: 1 } },
  { id: "m_taiyaki", name: "たい焼{や}き 메뉴", price: 6000, effect: { menu: "taiyaki" } },
  { id: "m_negitako", name: "ねぎたこ 메뉴", price: 8000, effect: { menu: "negitako" } },
  { id: "noren", name: "노렌(가게 천 간판)", price: 8000, effect: { guests: 1 } },
  { id: "m_ramune", name: "ラムネ 메뉴", price: 10000, effect: { menu: "ramune" } },
];

// 하루 흐름 컷(첫 시트): 01 열 때, 15 닫을 때, 02~14는 손님 2명마다 돌아가며
export const FLOW = [
  "가게 오픈!", "문어 손질", "반죽 만들기", "파 썰기", "재료 채우기", "판에 기름 칠하기", "반죽 붓기", "문어 투척!",
  "재료 듬뿍", "굴리기 시작!", "주문 받기", "특제 소스 추천", "앗, 뜨거워요!", "단골과 수다", "감사합니다!",
].map((title, i) => ({ id: "flow-" + String(i + 1).padStart(2, "0"), title }));

// 이야기 컷(둘째 시트): 장사 일수 day를 마칠 때 풀림
export const STORIES = [
  ["부모님과 인사!", 1, "お父{とう}さん、お母{かあ}さん、よろしく！", "아빠, 엄마, 잘 부탁해요!"],
  ["아빠한테 배우기", 2, "くるっと 回{まわ}すんだ。", "휙 돌리는 거야."],
  ["엄마의 칭찬", 3, "上手{じょうず}に なったね！", "잘하게 됐네!"],
  ["가족회의", 4, "新{あたら}しい メニュー、どう？", "새 메뉴 어때?"],
  ["휴식 시간", 5, "ちょっと 休{やす}もう。", "잠깐 쉬자."],
  ["대학 제자의 방문", 7, "え、先生{せんせい}！？", "어, 교수님!?"],
  ["사인회?", 9, "サイン、ください！", "사인 주세요!"],
  ["단골 꼬마 손님", 11, "今日{きょう}も 来{き}たよ！", "오늘도 왔어요!"],
  ["외국인 관광객", 13, "ようこそ 大阪{おおさか}へ！", "오사카에 어서 오세요!"],
  ["고양이의 방해?", 15, "だめだめ、猫{ねこ}ちゃん！", "안 돼 안 돼, 고양이야!"],
  ["시장 이웃들과", 18, "みんな、ありがとう！", "모두 고마워요!"],
  ["완판!", 21, "売{う}り切{き}れです！", "다 팔렸어요!"],
  ["철판 청소", 24, "ぴかぴかに しよう。", "반짝반짝하게 하자."],
  ["오늘의 매출", 27, "今日{きょう}は いっぱい 売{う}れた！", "오늘 많이 팔았다!"],
  ["보람찬 하루", 30, "大阪{おおさか}が 一番{いちばん}！", "오사카가 최고!"],
].map(([title, day, jp, ko], i) => ({ id: "story-" + String(i + 1).padStart(2, "0"), title, day, line: { jp, ko } }));
