# Maze Relay

WASD로 조작하는 브라우저 도트 던전 게임. 순수 HTML/CSS/JS(Canvas 2D) + 16px 픽셀아트 타일셋.

## 컨셉

지하 미로에 갇혔다. 안개 때문에 앞이 거의 안 보이고 바닥엔 가시 함정이 있다. 미로 끝에 도달하면
누군가 쓰러진 채 **살려달라고 빈다.** 죽일 수도 있고 살릴 수도 있다. 하지만 **어느 쪽을 골라도
결과는 같다** — 죽이면 출구가 없다는 걸 알게 되고, 살리면 그 사람에게 뒤통수를 맞는다. 결국
플레이어도 그 자리에 갇혀, 다음 사람에게 살려달라는 메시지를 남기고 그 사람의 선택을 기다린다.

**그 쓰러진 사람은 NPC가 아니라 직전에 이 게임을 플레이한 실제 사람이다.**

## ⭐ 핵심 설계 결정: 반전은 끝까지 숨긴다

이 게임의 정체가 비동기 멀티플레이라는 사실을 **마지막 outcome 화면 전까지 절대 노출하지 않는다.**
그 깨달음 자체가 페이로드이기 때문이다 (사용자가 Moirai 방식으로 확정).

⚠️ **타이틀·조우·결과 화면 문구를 고칠 때 "이전 플레이어" 같은 말이 새어나가지 않게 할 것.**
`game.js` 파일 상단 주석에도 같은 경고가 있다.

## 확정된 게임 규칙

1. 시작 시 **닉네임(최대 12자)과 캐릭터(8종)** 를 고른다.
2. WASD로 미로를 탐색한다. 시야는 안개로 좁게 제한된다.
3. 바닥의 **가시 함정**은 완전히 돌출했을 때만 데미지를 준다. 하트 3개, 0이 되면 사망.
4. 미로 끝에서 쓰러진 사람을 만난다. 그 대사는 **직전 플레이어가 직접 입력한 문장**이다.
5. **죽인다 / 살려준다** 를 고른다. 어느 쪽이든 플레이어는 갇힌다 (살리면 배신당함).
6. 갇힌 뒤 **다음 사람에게 남길 부탁(최대 80자)** 을 입력한다. 안 남겨도 된다.
7. 마지막에 반전이 공개되고, **내가 전에 남긴 부탁이 누구에게 전해졌고 그 사람이 나를 죽였는지
   살렸는지** 를 보여준다.
8. 트랩에 죽어도 6~7번으로 간다 (출구를 못 봤다는 것만 다름).

## Moirai 참고

이 구조의 원형은 2013년작 [Moirai](https://en.wikipedia.org/wiki/Moirai_(video_game))
(Chris Johnson 외). 동굴에서 피투성이 농부를 만나 질문하고 죽일지 보낼지 고르는데, 그 대답은
직전 플레이어가 타이핑한 것이고 플레이어 자신이 다음 사람에게 그 농부가 된다. 5~10분 분량.

여기서 가져온 것:

| Moirai | 우리 적용 |
|---|---|
| 5~10분의 짧은 분량 | 미로를 대폭 축소 (아래 수치 참고) |
| 반전을 끝까지 은폐 | 동일 (핵심 설계 결정) |
| 이메일로 "내가 어떻게 됐는지" 통보 | 닉네임 기반 outcome 화면의 "내 부탁의 결말" |

의도적으로 다르게 간 것: Moirai는 살려주면 그 사람이 실제로 산다. 우리는 **어느 쪽이든 갇힌다**
(사용자 확정). 선택의 기계적 결과는 같지만 죽였을 때와 살렸을 때의 서사 텍스트가 다르고, 다음
사람에게 기록되는 판정(`killed`/`spared`)도 갈리므로 의미는 남는다.

## ⚠️ 모더레이션 미적용 — 알려진 최대 리스크

**Moirai는 게임성 때문이 아니라 모더레이션 실패로 죽었다.** 응답의 53%에 욕설이 섞였고,
2016년 Steam 출시 후 트롤링이 폭증했으며, 2017년 6월 한 명이 스크립트로 DB를 플러딩하자
개발자가 "시간·돈·리소스가 없다"며 서버를 영구히 내렸다.

우리는 구조적으로 **더 취약하다** — `anon` 키가 클라이언트 JS에 노출되므로 소스 보기 한 번이면
누구나 무제한 INSERT를 때릴 수 있다.

사용자가 "지금은 생략"으로 확정했으므로 필터를 넣지 않았다. 대신:

- `game.js` 의 `sanitize()` 를 **훅 자리로 비워뒀다** (현재는 trim + 80자 자르기만)
- 비상시 전체 초기화 절차를 [SETUP.md](SETUP.md) 운영 섹션에 적어뒀다

부트캠프 규모(수십 명, 짧은 행사)에서는 실제 발생 확률이 낮다는 판단이지만, 공개 배포로 넘어가면
**반드시 먼저 처리해야 한다.**

## 설계 시 확정한 세부 사항

| 항목 | 결정 |
|---|---|
| 메시지 백엔드 | **Supabase REST**(공유) + `localStorage`(항상 복사본 / 폴백). `game.js` 상단 키가 비면 자동 로컬 전용. SDK 없이 `fetch`만 사용. 설정은 [SETUP.md](SETUP.md) |
| **1:1 메시지 체인** | 한 사람이 남긴 부탁은 **정확히 한 사람만** 받는다. Postgres `FOR UPDATE SKIP LOCKED` 기반 RPC `claim_message`로 원자적 배정 → 동시 접속해도 중복 불가. 풀이 마르면 시드 문장으로 조용히 폴백하되, **outcome 화면에서는 저자를 지어내지 않고 "당신이 첫 번째"라고 정직하게 표시** |
| 배포 방식 | **GitHub Pages**. `file://`로 나눠주면 Supabase 호출이 CORS에 막힘 |
| 기술 스택 | 순수 HTML/CSS/JS + Canvas 2D, 프레임워크 없음 |
| 에셋 | 16px 던전 픽셀아트 팩 (`assets/`). 개별 PNG 183개를 아틀라스 2장으로 팩 |
| 캐릭터 | **8종**: priest, skull, vampire, knight, shieldmaiden, dwarf, plucky_girl, witch. **2026-07-29 전면 교체**: 이전 라인업(priest/skeleton/skull/vampire/knight/rogue/dwarf/viking/shieldmaiden)에서 skeleton·rogue·viking을 빼고 knight/dwarf/shieldmaiden을 다른 소스로 갈아치웠다 — 이전 knight/rogue/dwarf/viking/shieldmaiden는 32px~389px짜리 참고 시트·일러스트를 16px까지 20배 넘게 눌러 담아서(`BOX` 필터로도) 실루엣이 모자이크처럼 뭉개졌었다(사용자가 직접 발견). 새 소스는 원래 16px 근처이거나 순정 16px라 다운스케일 손실이 훨씬 적다: knight는 Disthron의 `Ye_Oldy_Knight_Guy.png`(CC0, "Classic-Knight")에서 손으로 배치된 idle-bob 4프레임(16×23)을 골라 씀. shieldmaiden은 DezrasDragons의 `Valkyrie.png`(CC0, "Viking Shieldmaiden")에서 서 있는 포즈 1장을 크롭. dwarf는 Svetlana Kushnariova("Cabbit") 외 공동작업인 `dwarf-1.0/`(**CC-BY 3.0/4.0 — 출처 표기 필수**, dwarf-1.0/LICENSE-CC-BY-*.txt 참고)의 24×32 그리드에서 정면(beard) 행의 중앙(idle) 프레임. plucky_girl은 Disthron의 `Ye_Oldy_Girl_02.png`(CC0, "Plucky Girl Adventuror") — RGB+마젠타 매트라 컬러키 처리 후 크롭. witch는 PidrouDays의 `16x16witch-spritesheet.png`(itch.io, 무료) — 이미 순정 16×16 8×7 그리드라 다운스케일 자체가 없음. knight/shieldmaiden/plucky_girl은 손으로 배치된 시트라 깔끔한 격자가 아니어서 `tools/build_atlases.py`의 `from_sheet_pose`/`from_sheet_frames`가 좌표를 하드코딩해서 자름 — 원본 시트가 바뀌면 좌표도 다시 잡아야 함 |
| NPC 외형 | 미로 끝에 쓰러진 사람은 **그 부탁을 남긴 플레이어가 실제로 골랐던 캐릭터**로 그린다 (`messages.char_index`). 반전 화면이 "아까 네가 본 그 모습"을 가리키게 만드는 장치. 시드 폴백일 땐 사람 형태(`HUMANOID_CHAR_INDICES` = priest, knight, shieldmaiden, dwarf, plucky_girl, witch)로 그림 |
| 미로 | 고정 맵 아님 — 매 런 새로 생성. randomized DFS(recursive backtracker)로 **완전 미로**(임의의 두 칸 사이 경로가 정확히 하나) |
| 시야 | 플레이어 중심 원형 안개. 안쪽 3.4칸 완전 가시 → 6.2칸 밖 완전 차단 |
| 트랩 | 가시(`peaks`) 1종. 4프레임 중 **완전 돌출 프레임에서만** 데미지. 트랩마다 위상이 달라 한 번 관찰로 전부 타이밍을 재지 못함 |
| 체력 | 하트 3개, 피격 시 넉백 + 1.2초 무적(깜빡임) |
| 점수 | **없음.** 탈출이 불가능한 구조라 클리어 타임/점수 개념이 성립하지 않아 이전 버전의 점수 공식을 삭제 |
| 사운드 | Web Audio API 합성 + 실제 샘플 2개(`assets/music/theme.mp3` 배경음악, `assets/sounds/hurt.wav` 피격음). 전부 같은 `AudioContext`에 물려서 첫 실제 클릭(`document`의 버튼 클릭 리스너 → `SoundFX.bootstrap()`)에 한 번만 시작. 배경음악은 `MediaElementAudioSourceNode` → 전용 `GainNode`로 물려서 루프 재생. hurt.wav는 `decodeAudioData`로 미리 디코드해두고 `AudioBufferSourceNode`로 재생하되, 로드 전/실패 시엔 기존 합성음(`sweep`+`noise`)으로 조용히 폴백 |
| 한글 조사 | 닉네임이 사용자 입력이라 `josa()` 헬퍼로 받침 유무를 판정해 이/가를 고름 |

## 미로 크기 근거

이전 버전(제한시간 35초)과 달리 **시간 제한이 없으므로** "탈출 불가" 계산은 더 이상 필요 없다.
대신 Moirai의 5~10분 분량에 맞춰 미로를 줄였다. 같은 알고리즘을 Python으로 포팅해 실측한 값:

| 크기 | 최단 경로 | 통로 | 막다른 길 |
|---|---|---|---|
| 15 × 21 | 83칸 | 175칸 | 11개 |
| **15 × 25 (채택)** | **97칸(평균)** | **207칸** | **12개** |
| 21 × 31 | 129칸 | 351칸 | 21개 |
| (이전 버전) 20 × 74 | 228칸 | 563칸 | 44개 |

⚠️ 시드마다 편차가 크다 — 브라우저에서 실측한 한 런은 최단 경로가 **144칸**이었다(평균 97).
`MAZE_ROWS`/`MAZE_COLS`를 건드리면 여러 시드로 다시 재볼 것.

최단 경로 97칸 × 32px ÷ 160px/s ≈ 최적 19초. 안개 + 막다른 길 되돌아오기를 감안하면 실제로는
1.5~3분.

## 렌더링 메모

- 타일 좌표는 `game.js` 상단에 `[col,row]` 로 상수화 (`T_FLOOR`, `T_WALL_FACE`, `T_WALL_TOP`)
- **벽 아래 칸이 바닥이면** 앞면 벽돌 타일을, 아니면 벽 몸통 타일을 그려 입체감을 냄
- ⚠️ 이 타일셋은 바닥과 벽돌의 **명도가 거의 같아서** 그냥 그리면 통로가 안 읽힌다. 바닥에
  `rgba(0,0,0,.26)` 을 덮어 눌러주고, 벽 바로 아래 바닥에 접지 그림자 2줄을 깔아 해결했다.
  (그라디언트 대신 솔리드 2줄 — 타일마다 `createLinearGradient`를 만들면 프레임마다 수백 개가 생김)
- **카메라는 플레이어에 완전히 고정**하고 월드 경계 클램핑을 하지 않는다. 미로가 뷰포트보다
  겨우 큰 정도라 클램핑하면 시야가 구석에 박히고, 안개 때문에 월드 밖 공백은 어차피 안 보인다.
  (실제로 클램핑 버전을 만들었다가 시야가 좌상단에 몰리는 걸 확인하고 제거함)
- 화면 밖 타일은 그리지 않음 (`r0..r1`, `c0..c1` 컬링)

## 파일 구조

```
index.html              화면 뼈대 + 오버레이 (DOM)
style.css               타일셋에서 뽑은 팔레트 기반 UI
game.js                 게임 전체 로직 (일반 스크립트 — type="module" 금지)
assets/
  tileset.png           Dungeon_Tileset.png 복사본 (경로에 공백 없게)
  atlas_chars.png       4프레임 × 캐릭터 8종 (priest/skull/vampire/knight/
                          shieldmaiden/dwarf/plucky_girl/witch)
  atlas_props.png       4프레임 × 프롭 5종 (peaks/torch/side_torch/flag/coin)
  music/theme.mp3       배경음악 (원본 해시 파일명을 build_atlases.py가 복사)
  sounds/hurt.wav       피격 사운드
  character and tileset/, Character_animation/, ... 원본 에셋 팩
tools/build_atlases.py  아틀라스 재생성 스크립트
devserver.py            로컬 테스트 서버 (+ 스크린샷 저장 엔드포인트, 배포 제외)
SETUP.md                Supabase 스키마·RPC SQL + GitHub Pages 배포
```

⚠️ `game.js` 는 반드시 **일반 `<script src>`** 로 로드한다. `type="module"` 로 바꾸면
`file://` 에서 CORS로 막혀 더블클릭 실행이 깨진다.

⚠️ 캐릭터/프롭 인덱스는 `tools/build_atlases.py` 의 행 순서와 `game.js` 의 `CHARACTERS[]`·`P_*`
상수가 **짝을 이룬다.** 한쪽만 고치면 엉뚱한 스프라이트가 나온다.

## 화면 흐름

```
title ──▶ setup(닉네임·캐릭터) ──▶ playing ──┬─(미로 끝)─▶ encounter ─┬─죽인다─▶ aftermath
                                              │                        └─살린다─▶ aftermath(배신)
                                              └─(하트 0)──────────────────────▶ aftermath(트랩사)
                                                                                      │
                                    outcome(반전 공개 + 내 부탁의 결말) ◀── plea(부탁 남기기)
                                       │
                             다시 들어간다 / 타이틀로
```

상태 전환 시 `hideAllOverlays()` 로 이전 오버레이를 항상 일괄 제거한다 (이전 버전에서 각 핸들러가
자기 화면만 지우다가 오버레이가 겹쳐 남는 버그를 겪고 도입한 패턴).

## Supabase 스키마

- `messages` — 부탁. `text`, `author`(닉네임), `char_index`(고른 캐릭터), `claimed_by`, `claimed_at`
- `message_boosts` — 이전 버전의 "힘이 나요" 테이블을 **판정 기록으로 재사용**.
  `message_id`, `message_text`, `judge`, `verdict`(`killed`/`spared`)
- `claim_message(p_nickname)` — 부탁을 정확히 한 번만 배정하는 RPC

클라이언트 권한은 두 테이블 모두 `select` + `insert` 뿐. 배정에 필요한 `update` 는 RPC가
`security definer` 로 대신 수행한다. SQL 전문은 [SETUP.md](SETUP.md).

## 로컬 테스트 방법

```bash
python devserver.py     # http://localhost:8777
```

`devserver.py` 는 정적 서빙 + `POST /shot` (canvas dataURL을 `.shots/*.png` 로 저장) 을 제공한다.
브라우저 패널을 띄울 수 없는 환경에서 렌더링을 눈으로 확인하려고 만든 것. 반드시
`ThreadingTCPServer` 여야 한다 — 단일 스레드면 같은 탭이 연결을 잡은 채 POST할 때 데드락이 난다.

⚠️ **자동화로 검증할 때의 함정**: 브라우저 탭이 화면에 표시되지 않으면 `requestAnimationFrame`
이 강하게 스로틀링돼서 **렌더 루프가 거의 안 돈다.** 이것 때문에 "캔버스가 전부 검정", "캐릭터
선택 미리보기가 하나도 안 그려짐" 같은 **거짓 버그를 두 번 겪었다.** 캔버스 내용을 검사하기
전에 `await new Promise(r => requestAnimationFrame(()=>requestAnimationFrame(r)))` 로 프레임을
강제로 돌리고 나서 측정할 것. `setTimeout` 으로 기다리는 건 소용없다.

## 브라우저에서 확인한 것

- 미로 생성 검증: 15×25, 통로 207칸이 **전부 도달 가능**(완전 미로), 갈림길 12개, 막다른 길 14개,
  트랩 11개
- **로컬 릴레이 체인 전체 동작 확인**: `테스터`가 남긴 부탁을 `두번째사람`이 정확히 받고, 살려준
  판정이 기록되고, 이후 `테스터`가 다시 플레이했을 때 outcome 화면에 "두번째사람이 그 말을 들었고,
  당신을 살려줬습니다" 가 뜨는 것까지 확인
- **캐릭터 전파 확인** (구 라인업 기준, skull/priest는 여전히 유효): `영희`가 skull로 플레이하고
  남긴 부탁을 `철수`가 받았을 때, 미로 끝에 쓰러진 사람이 실제로 skull로 그려지는 것 확인. 시드
  폴백일 땐 priest로 그려짐
- **캐릭터 9종 전수 검증** — ⚠️ 구 라인업(skeleton/rogue/viking 포함) 기준이라 지금은 무효.
  2026-07-29에 knight/shieldmaiden/dwarf/plucky_girl/witch로 갈아친 뒤에는 새 아틀라스가
  `atlas_chars.png`에 8행으로 정확히 구워지는 것과 캐릭터 선택 화면에 8개 셀이 올바른 이름으로
  뜨는 것까지만 확인함 — 브라우저 패널이 화면에 안 뜬 상태라 `requestAnimationFrame`이 막혀서
  실제 캔버스 애니메이션(아이들 보브)까지는 이 세션에서 못 봤다. **다음 세션에서 패널을 띄운 채로
  8종 전부 조우/outcome까지 순회하는 재검증이 필요.**
- **rAF 스로틀링 함정 재확인**: `warp()` 뒤에 `sleep()`만 하고 프레임을 안 돌리면 조우 판정 자체가 실행되지
  않아 "조우 메시지가 빈 문자열"처럼 보이는 거짓 버그가 재발함 → CLAUDE.md에 이미 있던 경고를 실제로
  다시 겪고 나서야 원인을 찾음. `warp()` 뒤엔 반드시 `requestAnimationFrame` 두 번을 강제로 돌릴 것
- **배경음악·피격 샘플 로드 확인**: 첫 버튼 클릭 후 네트워크 탭에서 `assets/music/theme.mp3`,
  `assets/sounds/hurt.wav` 둘 다 200으로 로드되는 것 확인. 관련 콘솔 에러 없음
- 죽인다/살린다/트랩사 3개 분기 + 부탁 남기기/건너뛰기 모두 정상
- 시드 폴백 시 저자를 지어내지 않고 "당신이 첫 번째입니다" 로 표시되는 것 확인
- 캔버스가 0×0이 되는 버그를 실제로 겪고 `fitCanvas()` 에 하한 클램프 추가
- 디버그 훅은 검증 후 제거함 (배포본에 없음)

## ⚠️ 현재 세션 상태 (다음 세션이 이어받을 때 꼭 확인)

- **커밋 안 된 변경사항이 작업 디렉토리에 있다.** TTS 제거, 배경음악(`assets/music`)·피격 샘플
  (`assets/sounds/hurt.wav`) 추가, 그리고 **2026-07-29 캐릭터 라인업 전면 교체**(9종→8종, 위
  "캐릭터" 표 참고)가 전부 `git status`상 미스테이징 상태. `git status --short`로 먼저 확인할 것.
  새로 들어온 소스 파일(`assets/character and tileset/Ye_Oldy_Knight_Guy.png`, `Valkyrie.png`,
  `Ye_Oldy_Girl_02.png`, `16x16witch-spritesheet.png`, `dwarf-1.0/`)도 마찬가지로 미스테이징.
  이전 라인업의 소스(`knight.png`, `Char 1/5/9`, `Viking_sprites/`, VEGA의 `Dwarfs.zip`)는 더는
  아틀라스에 안 쓰이지만 참고용으로 지우지 않고 남겨뒀다 — 필요 없다고 판단되면 정리해도 됨.
  dwarf는 **CC-BY라 배포 시 크레딧 표기가 필요** (`dwarf-1.0/README.txt` 참고).
- `devserver.py`가 `PORT` 환경변수를 읽도록 바꾸고 `.claude/launch.json`에 `autoPort: true`를
  추가함 — 여러 세션이 동시에 devserver를 띄워도 포트 충돌이 안 나게 하려는 용도. 동작은 그대로
  8777을 기본값으로 쓰고, 포트가 이미 점유돼 있을 때만 다른 포트로 넘어감.
- **사용자가 명시적으로 "배포는 하지마"라고 지시한 상태다.** 이전 배포(커밋 `7e5d5a1`,
  `https://jjh7757.github.io/maze-relay/`)는 이 변경사항들이 반영되기 **이전** 버전이다.
  사용자가 먼저 배포를 요청하기 전까지는 커밋·push하지 말 것.
- Supabase 스키마(`author`/`char_index`/`claimed_by`/`claim_message` RPC/`message_boosts.verdict`)는
  **실제 프로젝트에 전부 적용 완료됐고 종단 테스트도 통과함** (아래 "브라우저에서 확인한 것" 참고).
  단, 이건 로컬(devserver) 에서 같은 Supabase 프로젝트에 대고 확인한 것이고, **위 커밋 안 된
  변경사항을 포함한 최신 코드가 실제 GitHub Pages에 배포된 상태로 종단 확인한 적은 없다.**

## 남은 작업 / 알려진 이슈

- 사운드 톤은 합성음이라 감으로 잡은 값 — 실제로 들어보고 조정 필요.
- 배경음악 볼륨(`MUSIC_VOLUME`)도 감으로 잡은 값. 실제 파일 하나만 있어서 루프 지점이
  부자연스러울 수 있음 — 곡이 루프에 맞게 편집된 것인지 확인 필요.
- 안개 반경, 트랩 밀도(`TRAP_DENSITY`), 무적 시간은 실플레이 후 조정 여지 있음.
- 모바일/터치 미지원 (WASD 전용).
- **TTS는 사용자 요청으로 제거함** (Web Speech API로 조우 메시지를 읽어주던 기능). 배경음악과
  묶여 있던 `duckMusic`/`restoreMusic` 볼륨 조절 로직도 같이 삭제 — TTS 말고는 쓸 데가 없었음.
  다시 필요해지면 `speak()`/`stopSpeaking()`을 되살리고 `triggerEncounter()`에서 다시 호출.
- 난이도(맵 여러 개), 랭킹은 범위 밖.
