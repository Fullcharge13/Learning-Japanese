// 사나다 유키 선생님 대사 표 — 상황 13종 × 3~7줄. 화면 언어는 한국어(해요체).
// 유키: 30세, 전국시대 사나다 가문의 후예, 오사카 출신. 도쿄대 국어학·동양사학 박사, 한국외대 한국어교육 박사, TOPIK 6급.
//   평소엔 표준어(도쿄 말), 오답일 때 가끔 오사카 사투리(wrong 7줄 중 2줄, 얼굴 angry·pout).
// 일본어 한마디 뒤에는 늘 (한국어 뜻)을 단다. 한자는 「字{よみ}」로 쓰면 말풍선에 후리가나가 붙는다(src/ruby.js).
// 표정: src/yuki.js FACE_IDS
// 자리 표시: {name} {streak} {xp} {item}
//   {item}에는 물건 이름(「기모노 · 着物{きもの}」)이 들어간다.
//   {streak}·{xp}·{item} 값이 없으면 say()가 그 줄을 건너뛴다. 상황마다 자리 표시 없는 줄을 하나 이상 둔다.
// {name}은 줄 맨 앞에 「{name} 씨, 」 꼴로 한 번만 쓴다. 이름이 비면 say()가 이 덩어리를 통째로 뺀다.

export const LINES = {
  greet: [
    { text: "{name} 씨, こんにちは!(안녕하세요!) 오늘도 같이 해요.", face: "smile" },
    { text: "사나다 유키예요. 오늘 목표는 어제보다 한 단어 더!", face: "wink" },
    { text: "오사카에서 왔어요. 한국어는 드라마로 배웠답니다.", face: "shy" },
    { text: "{name} 씨, 자리 맡아 뒀어요. 시작해 볼까요?", face: "hello" },
    { text: "하루 몇 분이면 충분해요. がんばろう!(힘내자!)", face: "cheer" },
  ],
  correct: [
    { text: "そうそう!(맞아요!) 완벽해요.", face: "joy" },
    { text: "정답! 제대로 기억하고 있네요.", face: "smile" },
    { text: "すごい!(대단해요!) 이 말은 이제 당신 거예요.", face: "sparkle" },
    { text: "맞았어요. 방금 그 느낌을 기억해 두세요.", face: "cheer" },
  ],
  combo: [
    { text: "연속 정답! 리듬이 아주 좋아요.", face: "sparkle" },
    { text: "この調子{ちょうし}!(이 기세로!) 계속 가요.", face: "joy" },
    { text: "이렇게 술술 풀리면 일본 친구도 놀라겠어요.", face: "wink" },
    { text: "멈출 수 없죠? 이 속도 그대로!", face: "cheer" },
  ],
  wrong: [
    { text: "おしい!(아까워요!) 어디가 다른지 같이 봐요.", face: "think" },
    { text: "괜찮아요. 틀린 답도 기억을 도와줘요.", face: "smile" },
    { text: "음, 한 글자씩 천천히 다시 봐요.", face: "think" },
    { text: "이건 처음엔 다들 헷갈려요.", face: "worry" },
    { text: "좋은 시도였어요! 다음엔 꼭 맞힐 거예요.", face: "cheer" },
    { text: "ちゃうちゃう!(아냐 아냐!) 앗, 오사카 말이 나와 버렸네요.", face: "pout" },
    { text: "なんでやねん!(왜 그래~!) …농담이에요. 정답을 봐요.", face: "angry" },
  ],
  running: [
    { text: "잠깐만요, 금방 돼요.", face: "think" },
    { text: "준비하고 있어요. ちょっと待{ま}ってね(잠깐 기다려요).", face: "smile" },
    { text: "곧 갈게요!", face: "wink" },
  ],
  error: [
    { text: "あれ?(어라?) 문제가 생겼어요. 다시 해 봐요.", face: "surprise" },
    { text: "걱정 마요. 다시 열면 괜찮아질 거예요.", face: "smile" },
    { text: "멈춘 것 같아요. 한 번 더 해 볼까요?", face: "worry" },
  ],
  hint: [
    { text: "힌트를 줄게요. 답은 스스로 찾아봐요.", face: "wink" },
    { text: "먼저 이 말이 무슨 뜻인지 떠올려 봐요.", face: "think" },
    { text: "한자어는 한국어 발음과 닮은 게 많아요.", face: "hello" },
    { text: "이 단서를 들고 한 걸음 더!", face: "cheer" },
  ],
  lesson_done: [
    { text: "끝! {xp} XP를 얻었어요.", face: "done" },
    { text: "{name} 씨, 끝까지 해냈어요! 오늘 배운 말은 당신 거예요.", face: "sparkle" },
    { text: "おつかれさま!(수고했어요!) {xp} XP 성장!", face: "smile" },
    { text: "레슨 하나 끝! 다음 레슨도 준비해 뒀어요.", face: "cheer" },
  ],
  course_done: [
    { text: "{name} 씨, 가나부터 24과까지 전부 끝냈어요! 정말 자랑스러워요!", face: "sparkle" },
    { text: "모든 레슨 완료! 이제 일본어로 인사할 수 있어요.", face: "done" },
    { text: "끝까지 왔어요. もう立派{りっぱ}な学習者{がくしゅうしゃ}!(이제 어엿한 학습자!)", face: "cheer" },
  ],
  streak_up: [
    { text: "{streak}일 연속! 꾸준함이 최고의 실력이에요.", face: "sparkle" },
    { text: "{name} 씨, 벌써 {streak}일째예요. 습관이 되고 있어요.", face: "joy" },
    { text: "오늘 목표 달성! 조금씩 쌓이고 있어요.", face: "joy" },
    { text: "오늘도 해냈어요. {streak}일 연속!", face: "cheer" },
  ],
  streak_broken: [
    { text: "깜빡 졸았나 봐요…… 1일째부터 다시 시작해요!", face: "sleepy" },
    { text: "하루 쉬어도 괜찮아요. 배운 말은 그대로 있어요.", face: "smile" },
    { text: "기록은 숫자일 뿐, 실력은 줄지 않았어요.", face: "sad" },
    { text: "{name} 씨, おかえり!(어서 와요!) 오늘 다시 시작해요.", face: "joy" },
  ],
  item_bought: [
    { text: "{item}, 어때요? 저랑 어울려요?", face: "sparkle" },
    { text: "{item}, 마음에 들어요! 오늘은 이걸로 할게요.", face: "joy" },
    { text: "새 물건 {item}! 보는 눈이 있네요.", face: "wink" },
    { text: "다 일본 물건이에요. 이름도 같이 외워 봐요.", face: "shy" },
  ],
  welcome_back: [
    { text: "{name} 씨, ひさしぶり!(오랜만이에요!) 잘 지냈어요?", face: "surprise" },
    { text: "돌아왔군요. 가볍게 복습부터 할까요?", face: "smile" },
    { text: "계속 기다리고 있었어요.", face: "shy" },
    { text: "어디까지 했는지 다 기억해요. 이어서 가요.", face: "cheer" },
  ],
};

// 모르는 상황일 때 쓰는 중립 대사
export const FALLBACK_LINE = { text: "천천히 해요. 저는 늘 여기 있어요.", face: "smile" };
