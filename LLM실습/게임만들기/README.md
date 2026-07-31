# Maze Relay

WASD로 조작하는 브라우저 도트 던전 게임. 순수 HTML/CSS/JS(Canvas 2D)와 16px 픽셀아트 타일셋으로 만들었습니다.

원본 저장소: [jjh7757/maze-relay](https://github.com/jjh7757/maze-relay)

## 컨셉

지하 미로에 갇혔다. 안개 때문에 앞이 거의 안 보이고 바닥엔 가시 함정이 있다. 미로 끝에 도달하면 누군가 쓰러진 채 살려달라고 빈다. 죽일 수도 있고 살릴 수도 있다. 하지만 어느 쪽을 골라도 결과는 같다 — 결국 플레이어도 그 자리에 갇혀, 다음 사람에게 살려달라는 메시지를 남기고 그 사람의 선택을 기다린다.

**핵심 반전**: 미로 끝에 쓰러진 사람은 NPC가 아니라 직전에 이 게임을 플레이한 실제 사람이다. 이 사실은 마지막 결과 화면 전까지 절대 드러나지 않는다. (2013년작 [Moirai](https://en.wikipedia.org/wiki/Moirai_(video_game))에서 착안)

## 게임 흐름

1. 닉네임(최대 12자)과 캐릭터(8종) 선택
2. WASD로 안개 낀 미로 탐색, 가시 함정 회피 (하트 3개)
3. 미로 끝에서 쓰러진 사람(= 직전 플레이어)을 만나 죽인다 / 살린다 선택
4. 결과와 무관하게 플레이어도 갇히고, 다음 사람에게 남길 부탁(최대 80자) 입력
5. 결과 화면에서 반전 공개: 내가 이전에 남긴 부탁을 누가 받았고, 죽였는지 살렸는지 확인

## 기술 스택

- **프론트엔드**: 프레임워크 없는 HTML/CSS/JS + Canvas 2D
- **메시지 저장소**: Supabase(REST, 공유 모드) + `localStorage`(로컬 폴백). `game.js` 상단 키를 비워두면 자동으로 로컬 전용 모드로 동작
- **1:1 메시지 배정**: Postgres `FOR UPDATE SKIP LOCKED` 기반 RPC(`claim_message`)로 동시 접속 시에도 중복 배정 없이 원자적으로 처리
- **배포**: GitHub Pages (Supabase 호출이 CORS에 막히므로 `file://` 직접 실행 대신 정적 호스팅 필요)

## 로컬 실행

```bash
python devserver.py     # http://localhost:8777
```

공유(Supabase) 모드로 쓰려면 [SETUP.md](SETUP.md)의 스키마/RPC SQL을 실행하고 `game.js` 상단에 프로젝트 URL과 anon 키를 채워야 합니다. 키를 비워두면 각자 브라우저에만 저장되는 로컬 모드로도 게임은 정상 진행됩니다.

## 파일 구조

```
index.html              화면 뼈대 + 오버레이 (DOM)
style.css               타일셋 팔레트 기반 UI
game.js                 게임 전체 로직
assets/                 픽셀아트 타일셋, 캐릭터/프롭 아틀라스, 배경음악·효과음
tools/build_atlases.py  아틀라스 재생성 스크립트
devserver.py            로컬 테스트 서버
SETUP.md                Supabase 스키마·RPC SQL + GitHub Pages 배포 가이드
CREDITS.md              캐릭터 에셋 출처 및 라이선스
```

## 에셋 출처

캐릭터 스프라이트는 OpenGameArt, itch.io 등 외부 소스에서 가져왔습니다. 자세한 출처와 라이선스는 [CREDITS.md](CREDITS.md)를 참고하세요. dwarf 캐릭터는 CC-BY 라이선스로 배포 시 출처 표기가 필요합니다.

## 알려진 제약

- 욕설·스팸 필터링 미적용 (부트캠프 규모의 짧은 행사 기준으로 생략, 공개 배포 시 반드시 추가 필요)
- 모바일/터치 미지원 (WASD 전용)
- 난이도 조절, 랭킹 기능은 범위 밖
