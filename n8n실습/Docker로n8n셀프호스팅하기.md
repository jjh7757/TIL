# Docker로 n8n 셀프호스팅하고 Telegram 웹훅 연동하기

**날짜**: 2026-08-12
**목표**: n8n Cloud 대신 내 컴퓨터에 무료로 셀프호스팅하고, Telegram 봇 트리거를 동작시키기

> 컨테이너·이미지·배포 대상 같은 일반 개념은 [컨테이너 기반 배포 기초](../CS지식/컨테이너배포기초.md) 참고. 이 글은 그 개념을 n8n 셀프호스팅에 실제로 적용하며 겪은 트러블슈팅 기록이다.

## 1. Docker 설치 — Windows Home에는 WSL2가 필수

Windows에 Docker Desktop을 설치하려면 WSL2가 필요하다. **Windows 11 Home 에디션은 Hyper-V 백엔드를 지원하지 않아서** WSL2가 필수다.

```powershell
wsl --install
```

**트러블슈팅 — `지정된 경로를 찾을 수 없습니다`**

`wsl --install`, `wsl --update` 모두 같은 에러가 발생했다. 원인은 내장 `wsl.exe`가 Microsoft Store 연동으로 커널·배포판을 받는데, 이 경로가 깨져 있었기 때문. 아래 순서로 우회했다.

1. Microsoft/WSL GitHub 릴리스에서 커널 업데이트 패키지(`wsl.2.7.11.0.x64.msi`)를 직접 다운로드해 수동 설치
2. DISM으로 Windows 기능 직접 활성화

   ```powershell
   dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
   dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
   ```

3. 재부팅 → `wsl --set-default-version 2` → `wsl --status`에서 `기본 버전: 2` 확인
4. `wsl --install -d Ubuntu`로 배포판 설치 성공

**Docker Desktop 설치**

```powershell
winget install -e --id Docker.DockerDesktop
```

설치 후 **Settings → Resources → WSL integration**에서 기본 배포(Ubuntu) 연동 체크박스를 켜야 한다.

## 2. n8n 셀프호스팅 (Docker)

```bash
docker run -d --name n8n -p 5678:5678 -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n
```

- `-p 5678:5678`: `http://localhost:5678`로 접속
- `-v n8n_data:/home/node/.n8n`: 데이터(계정, 워크플로우)를 볼륨에 영구 저장

**관리 명령**

```bash
docker ps          # 실행 중인 컨테이너 확인
docker logs -f n8n  # 로그 실시간 확인
docker stop n8n
docker start n8n
```

> **라이선스 참고**: n8n은 Sustainable Use License로, 개인/내부 자동화 용도는 자유롭게 무료다. 재판매·경쟁 SaaS 제공만 금지된다.

## 3. Telegram Trigger가 안 걸리는 문제 — 웹훅과 localhost

**증상**: Telegram Trigger 노드에 봇 API 키를 넣고 "Listen for test event"로 테스트해도 메시지가 안 들어옴.

**원인**: Telegram Trigger는 **웹훅 방식**이라 Telegram 서버가 n8n 인스턴스로 직접 HTTP 요청을 보내야 하는데, n8n이 `localhost:5678`에서만 열려 있어 인터넷(Telegram 서버)에서 접근할 수 없었다.

**해결 — ngrok으로 로컬 서버를 임시 공개**

```powershell
winget install ngrok.ngrok
ngrok config add-authtoken <토큰>
ngrok http 5678
```

`https://xxxx.ngrok-free.dev` 같은 공개 URL이 발급되면, 이 URL을 `WEBHOOK_URL`로 지정해 n8n 컨테이너를 재생성한다.

```bash
docker stop n8n
docker rm n8n
docker run -d --name n8n -p 5678:5678 -e WEBHOOK_URL=https://xxxx.ngrok-free.dev/ -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n
```

이후 Telegram Trigger 테스트가 성공했다.

**트러블슈팅 — 백신이 ngrok을 악성코드로 오탐**

AhnLab Safe Transaction이 `ngrok.exe`를 `HackTool/Win.Ngrok`으로 탐지했다. 터널링 도구가 C2 통신에 자주 악용되어 생기는 흔한 오탐이다. 이 제품은 개별 파일 예외처리 기능이 없어서, **환경설정 → 보안 → "유해 가능 프로그램"** 체크박스를 해제해 우회했다. 작업이 끝나면 다시 체크해 탐지 기능을 복원하는 게 좋다.

## 4. ngrok vs Cloudflare Tunnel

| | ngrok | Cloudflare Tunnel |
|---|---|---|
| 설정 난이도 | 간단 (가입 → 토큰 → 명령 1줄) | 복잡 (cloudflared, 도메인 필요) |
| URL 고정 | 무료 플랜은 재시작마다 URL 변경 | 도메인 연결 시 영구 고정 |
| 장기 상시 운영 | 무료 플랜 제한 있음 | 도메인만 있으면 완전 무료 |
| 용도 | 빠른 테스트 | 장기 자체 호스팅 서비스 |

지금은 테스트 목적이라 ngrok을 사용했다. 장기 운영 시에는 Cloudflare Tunnel로 전환을 고려한다.

## 5. 작업 종료 시 꺼야 할 것들

- ngrok 터널 창 (`Ctrl+C` 또는 창 닫기)
- n8n 컨테이너: `docker stop n8n`
- Docker Desktop 종료 (트레이 아이콘 → Quit)
- AhnLab "유해 가능 프로그램" 탐지 다시 체크
- WSL2는 안 써도 자동 유휴 상태라 안 꺼도 무방 (`wsl --shutdown`으로 완전 종료 가능)

## 핵심 배운 점

- Windows Home 에디션은 Hyper-V를 지원하지 않아 Docker Desktop에 WSL2가 필수다.
- `wsl --install` 계열 명령이 실패하면 Microsoft Store 의존성 문제일 수 있고, GitHub 릴리스 + DISM으로 우회할 수 있다.
- 로컬(`localhost`)에서 웹훅 기반 서비스(Telegram Trigger 등)를 테스트하려면 터널링 도구로 공개 URL이 필요하다.
- 터널링 도구(ngrok 등)는 백신에 "해킹 도구"로 오탐될 수 있다 — 공식 출처면 대부분 안전하다.
