# 왜샀어 — Vercel에서 Docker 셀프호스팅으로 전환

- 기획서: [Docker 배포 전환 기획서](https://github.com/jjh7757/whybuy/blob/master/KIS-Web-Agent-Notes/08_Deploy/01_docker_migration.md) (jjh7757/whybuy)
- 관련: [왜샀어(WhyBuy) — 기획과 구현 정리](왜샀어구현.md), [컨테이너 기반 배포 기초](../../CS지식/컨테이너배포기초.md), [Docker로 n8n 셀프호스팅하기](../../n8n실습/Docker로n8n셀프호스팅하기.md)

> 작업 진행 중 작성하는 메모. 전환이 끝나면 이 내용을 정리해서 TIL에 반영한다.

## 왜 전환하나

Vercel 서버리스는 인스턴스마다 메모리가 분리돼서, [`lib/kis.ts`](https://github.com/jjh7757/whybuy/blob/master/lib/kis.ts)의 KIS 레이트리밋 큐(`kisQueue`, 모듈 레벨 변수)가 인스턴스별로 따로 논다. 동시 요청이 다른 인스턴스에 떨어지면 1.1초 간격 보장이 깨져 `EGW00201`이 재발할 수 있는 잠재 결함이었다. 상주 프로세스 1개로 옮기면 이 큐가 프로세스 전역으로 유일해져 근본 해결이 된다. 덧붙여 지정가 체결 자동 확인(스케줄러)과 분봉 차트의 플랫폼 함수 타임아웃(45초) 제약도 같이 풀린다.

## 1단계 — `output: "standalone"` 추가

[`next.config.ts`](https://github.com/jjh7757/whybuy/blob/master/next.config.ts)가 그동안 빈 설정이었다는 걸 이번에 알았다. `output: "standalone"`만 추가하고 `next build`를 돌렸는데, 예상 못한 지점에서 막혔다.

**빌드가 `/` 페이지 프리렌더링 중 실패했다** — `@supabase/ssr`이 "URL과 API 키가 필요하다"며 에러를 던졌다. 기획서에는 "API 라우트 16개가 전부 `force-dynamic`이라 빌드 중 KIS·Supabase 호출이 없다"고 돼 있었는데, 이건 API 라우트 얘기였고 **루트 페이지(`/`)의 `AuthButton` 컴포넌트가 `createClient()`를 호출하며 정적 프리렌더링 대상이었던 건 별개였다.** `NEXT_PUBLIC_SUPABASE_URL`/`NEXT_PUBLIC_SUPABASE_ANON_KEY`가 빌드 시점에 없으면 프로덕션 빌드 자체가 실패한다는 뜻 — 기획서 REQ-02가 "빌드 시점 환경변수" 문제를 API 라우트 기준으로만 짚었는데, 실제로는 페이지 레벨에서 먼저 걸렸다.

로컬에는 `.env` 자체가 없었다(`.gitignore`에 `.env*` 처리돼 있고, 실제 값은 Vercel 대시보드에만 있던 것으로 보임). 빌드 구조 검증이 목적이라 실제 키 대신 `.env.local`에 placeholder 값(`https://placeholder.supabase.co` 등)을 넣어 빌드를 통과시켰다. `output: standalone` 설정 후 `.next/standalone/server.js`가 정상 생성됨을 확인.

## 2단계 — Dockerfile 작성 + 로컬 T1

멀티스테이지(`deps → builder → runner`)로 작성. 로컬 Node가 v24라 베이스 이미지도 `node:24-alpine`으로 맞췄다.

- `NEXT_PUBLIC_*`는 `ARG`로 받아서 `builder` 스테이지의 `ENV`로 다시 넣어야 빌드 시점 인라인이 된다 — 여기서 빠뜨리면 1단계에서 겪은 것과 같은 이유로 이미지 빌드가 실패한다.
- `runner` 스테이지는 `standalone` 산출물이 `.next/static`과 `public`을 자동 포함하지 않는다는 기획서 경고대로, 이 둘을 `builder`에서 따로 `COPY` 했다.

로컬에 Docker Desktop이 설치는 돼 있었지만 데몬이 꺼져 있어서 처음엔 `docker build`가 파이프 연결 실패로 죽었다 — Docker Desktop을 띄우고 나서 재시도.

`--build-arg`로 placeholder Supabase 값을 넘겨 이미지 빌드 성공, `docker run -p 3000:3000 --env-file .env.local`로 띄운 컨테이너에서 `curl localhost:3000/`, `/trade` 모두 200 확인 (**T1 통과**). 로그인·주문 등 실기능은 당연히 placeholder 키로는 안 되고, 이건 다음 단계(실제 서버 + 실제 키)에서 확인 예정.

기획서 REQ-05가 "컨테이너 2개 이상 금지"를 `docker-compose.yml`에 주석으로 남기라고 해서, `services.whybuy` 위에 왜 안 되는지(인메모리 큐) 이유까지 적어 `docker-compose.yml`을 만들었다. 포트는 `127.0.0.1:3000:3000`으로 바인딩해 외부에 직접 노출되지 않게 해뒀다 (REQ-03 — 실제 서버에서는 Caddy만 443을 받는다).

## 다음 단계

- 서버 제공 업체 선정 (오라클 프리티어 / Lightsail / Vultr 등 — 미결)
- 이미지 레지스트리 선택 (GHCR vs Docker Hub — 미결)
- 서버 준비 → Caddy + HTTPS → OAuth 리다이렉트 URI 등록(Google·Supabase 양쪽) → 실제 환경변수로 컨테이너 기동 → T2~T8 검증

## 3단계 — 서버 준비 (진행 중)

한국 리전 사용을 전제로 오라클 클라우드 프리티어를 고르고 가입을 시작했는데, **가입 화면의 홈 리전 목록에 한국(서울/춘천)이 아예 뜨지 않았다.** Oracle Free Tier의 Always Free 리소스는 홈 리전에서만 생성 가능하고 홈 리전은 가입 후 변경도 안 되는데, 정작 목록에 원하는 리전이 없는 상황.

대안으로 Vultr(리전 제약 없이 서울 바로 선택 가능, 월 $5~6)도 검토했지만, 오라클의 "영구 무료"가 학습용 반복 사용에 더 맞다고 판단해 **오라클을 유지하고 한국과 가장 가까운 리전(일본 도쿄/오사카, 없으면 싱가포르)으로 타협**하기로 함. 기획서의 "서버 리전 = 한국" 결정(REQ 근거: KIS·DART 왕복 지연)에서 완전히 벗어나는 절충이라, 나중에 T5(분봉 차트 45초 제약 없이 완주) 확인할 때 지연시간이 체감되는지 같이 봐야 한다.

### 서버 업체 재선정 — Oracle → Vultr 검토 → 네이버클라우드 Micro Server

Oracle Cloud Free Tier로 진행하려 했으나 **가입 화면의 홈 리전 목록에 한국이 없었다.** Always Free 리소스는 홈 리전에서만 생성 가능하고 가입 후 변경도 안 되는 구조라, 리전 타협(일본/싱가포르) 없이는 못 쓰는 상황.

대안으로 검토한 것들:

| 옵션 | 리전 | 무료 기간 |
|---|---|---|
| Vultr | 서울 직접 선택 | 없음 (월 $5~6) |
| AWS 프리티어 | 서울 | 12개월 |
| GCP Always Free | 미국만 | 영구 |
| **네이버클라우드 Micro Server** | **한국(선택)** | **1년** |

리전 타협이 전혀 필요 없으면서 1년 무료인 네이버클라우드 Micro Server로 결정. 공식 FAQ로 확인한 과금 구조:

- **컴퓨팅(서버) 자체만 1년 무료**, 결제수단 등록일 기준 계산. 1년 후 자동 유료 전환(예시 기준 월 13,000원)
- **공인 IP·아웃바운드 트래픽·블록 스토리지는 무료 대상이 아니고 별도 과금** — 공인 IP는 월 4,032원(신청 시점부터 과금), 블록 스토리지(10GB, CB1)도 생성 시점부터 소액 과금
- 계정당 1대까지만 무료, 반납 후 동일 스펙으로 재생성해도 무료 유지

**VPC 서버 생성 마법사에서 한 번 헷갈렸던 점**: 일반 Compute → Server 마법사에서 "Micro" 스펙을 고르면 견적에 월 10,850원(OS 제외)이 표시돼서 유료 상품인가 헷갈렸다. 이 견적 화면 자체는 이 스펙의 정가를 보여주는 것이고, 실제 청구 시 신규 가입 무료 혜택이 크레딧처럼 상쇄되는 방식으로 보인다(가입 화면 프로모션 카드에 있던 "Micro Server" 상품과 이름이 같아 헷갈리기 쉬움).

**비용 정리(기획서 8장 갱신 필요)**: 컴퓨팅 $0(1년) + 공인 IP 월 4,032원 + 스토리지 소액 — 기존 기획서의 "월 $5~10" 추정보다 실제로는 더 저렴하게 시작 가능.

공인 IP는 서버 생성 시 바로 안 붙이고, 도메인 연결 단계(4단계) 진행할 준비가 됐을 때 Network → Public IP에서 나중에 붙이기로 함 (그때까지 그 비용은 안 나감).

인증키(.pem)는 AWS처럼 SSH 직접 인증용이 아니라, **콘솔의 "관리자 비밀번호 확인" 메뉴에서 초기 root 비밀번호를 복호화하는 용도**라는 걸 미리 확인 — SSH는 그 비밀번호로 접속하는 방식.

### 3단계 완료 — Docker 설치까지

**SSH 접속 방식**: 네이버클라우드는 인증키(.pem)로 바로 SSH하는 게 아니라 "관리자 비밀번호 확인" 메뉴에서 그 키로 초기 root 비밀번호를 복호화하는 방식이었다. 비밀번호를 Claude에게 노출하지 않기 위해, 사용자가 직접 로컬 터미널에서 `ssh root@IP "..."` 한 줄로 비밀번호를 입력해 내 ed25519 공개키를 `~/.ssh/authorized_keys`에 등록하는 방식으로 우회했다. 이후로는 키 기반 인증만 사용.

**트러블슈팅 — `apt-get upgrade` 도중 SSH가 끊김**: 패키지 업그레이드 중 원격 SSH 접속이 전부 `Connection refused`로 막혔다. 네트워크 문제가 아니라 `ssh.service`가 SIGTERM으로 내려가 있었던 것(`systemctl status ssh` 로그에서 확인) — 아마 업그레이드 도중 어떤 트리거로 서비스가 재시작되다가 완전히 죽어버린 것으로 추정. SSH가 안 되니 콘솔로도 확인 불가능한 상황을 걱정했는데, 다행히 **네이버클라우드의 웹 콘솔("서버 접속 콘솔")은 네트워크와 무관하게 동작**해서 여기로 `systemctl start ssh && systemctl enable ssh`를 실행해 복구했다. 이후 확인해보니 Ubuntu 24.04는 `ssh.socket` 기반 소켓 활성화 구조라 `ssh.service` 자체는 `disabled`가 정상이지만, 이번엔 소켓까지 내려간 것으로 보인다.

- 교훈: 원격 서버 작업 중 네트워크 서비스(sshd) 자체를 건드릴 수 있는 작업(대규모 업그레이드 등)을 할 땐, **콘솔 접속 수단을 반드시 미리 확보**해둬야 한다. 이번엔 클라우드 제공업체의 웹 콘솔 덕에 복구했지만, 그게 없었으면 서버를 못 살렸을 것.
- 사양이 낮아(vCPU 1개) 패키지 업그레이드 자체도 예상보다 훨씬 오래 걸렸다(체감 1시간 이상).

**스왑 파일 추가**: Micro Server 사양(RAM 1GB)에 스왑이 기본 0이라, 트래픽 튀는 순간 OOM으로 컨테이너가 강제 종료될 위험이 있었다. `fallocate`로 2GB 스왑 파일을 만들고 `/etc/fstab`에 등록(재부팅 유지), `vm.swappiness=10`으로 설정(RAM 여유 있는 한 스왑을 최대한 늦게 쓰도록).

**Docker 설치**: 공식 저장소(`download.docker.com`) 등록 후 `docker-ce`, `docker-ce-cli`, `containerd.io`, `docker-buildx-plugin`, `docker-compose-plugin` 설치. `docker run hello-world`로 정상 동작 확인 (Docker 29.7.2, Compose v5.4.0).

**ufw 방화벽**: NCP의 ACG(인프라 레벨 방화벽)와 별개로 OS 레벨에서도 `ufw`로 22(SSH)/80/443만 허용, 나머지 인바운드 기본 차단하도록 설정.

**남은 걱정**: 1GB RAM에 스왑 2GB를 더해도 여유가 크지 않다. 나중에 T4(동시 레이트리밋 테스트)·T5(분봉 차트) 검증할 때 메모리 사용량을 같이 관찰해야 한다.

### 도메인 없이 IP로 먼저 인프라 스모크 테스트

도메인·Caddy·OAuth를 준비하기 전에, 실제 서버에 컨테이너를 띄워 인프라 자체(네트워크·Docker·리소스)가 문제없는지 먼저 확인하기로 함. 참고: **Google OAuth는 리다이렉트 URI로 IP 주소를 허용하지 않아서** 로그인 테스트(T2)는 어차피 도메인이 있어야 가능 — 이번엔 "컨테이너가 뜨고 외부에서 접속되는지"까지만 확인하는 목적.

**로컬 Docker Desktop이 갑자기 고장남**: 로컬에서 빌드해둔 이미지를 `docker save`로 서버에 옮기려던 중, Docker Desktop이 `dockerInference` 소켓 파일 접근 오류로 크래시했다. WSL 종료·프로세스 강제 종료·`robocopy /MIR` 트릭까지 시도했지만 `C:\Users\user\AppData\Local\Docker\run` 아래 리파스 포인트 파일 3개(`dockerInference`, `dockerEthernetVfkit`, `userAnalyticsOtlpHttp.sock`)가 "Error 1920: 시스템에서 파일에 액세스할 수 없습니다"로 삭제 자체가 안 됐다. 재부팅 전에는 못 고칠 것으로 보고 우회.

**우회**: 로컬 이미지 전송 대신, 소스 코드(`node_modules`·`.next`·`.git` 제외, 141KB)를 tar로 압축해 서버로 `scp`, 서버에서 직접 `docker build`. 이 프로젝트는 원래(REQ-08) 로컬/CI에서 빌드하고 서버는 pull만 하는 구조를 의도했었는데, 이번 1회성 테스트에서 실제로 **서버에서 직접 빌드하면 얼마나 느린지 체감**했다 — `next build`의 "Compiled successfully"까지만 **25분**, TypeScript 검사 3.7분 추가, 전체 빌드 약 **39분**. vCPU 1개짜리 서버에서 상시 빌드는 확실히 안 된다는 게 실측으로 확인됨 → REQ-08의 "로컬/CI 빌드, 서버는 pull만" 설계가 옳았다는 근거가 생김.

**ACG 포트 이슈**: 컨테이너를 `-p 80:3000`으로 띄우고 `ufw`(OS 방화벽)도 80/443 열려 있는데 외부 curl이 타임아웃됐다. 서버 안에서 `curl localhost`는 200이 나와서 앱 자체는 정상 — 원인은 **NCP ACG(인프라 레벨 방화벽)에 80/443 인바운드 규칙이 없었던 것**. 서버 상세정보 화면의 "NIC(Network Interface) → ACG 수정"에서 규칙 추가 후 외부 접속(`http://49.50.134.102/`, `/trade`) 200 확인.

- 교훈: 방화벽이 **OS 레벨(ufw)과 인프라 레벨(ACG) 이중 구조**라서, 둘 중 하나만 확인하고 "왜 안 되지"하며 헤맬 수 있다. 외부 접속 문제 디버깅할 땐 항상 두 레이어 다 확인해야 함.

### 4단계 — 도메인 연결 + Caddy HTTPS

**도메인 전략**: 이 서버(NCP Micro Server)는 학습용으로 여러 프로젝트에 재사용할 계획이라, 프로젝트 전용 도메인 대신 범용 도메인 `ai-agent-develop.cloud`(가비아 구매)를 사고 **서브도메인 `whybuy.ai-agent-develop.cloud`**를 이 프로젝트에 붙였다. 나중에 다른 프로젝트는 `다른이름.ai-agent-develop.cloud`로 같은 도메인 아래 추가하면 됨.

- TLD는 `.cloud` 선택 — `.shop`/`.store`는 쇼핑몰로 각인된 TLD라 "ai-agent-develop"이라는 개발/인프라 성격과 안 맞아서 제외.
- 네임서버는 가비아 기본값(가비아 네임서버 사용) 유지 — Cloudflare 등 별도 DNS 서비스를 안 쓰므로 가비아 DNS 관리에서 바로 A 레코드(`whybuy` → `49.50.134.102`) 등록.

**Caddy 삽질**: 공식 가이드대로 `curl ... -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg`로 GPG 키를 저장했더니 apt가 `NO_PUBKEY` 서명 오류를 냈다. 원인은 ASCII-armored 키 파일을 그대로 저장해서 — apt가 요구하는 바이너리 keyring 포맷이 아니었음. `curl ... | gpg --dearmor -o ...`로 파이프해서 변환해야 했다 (공식 문서를 그대로 안 옮기고 손으로 치다가 이 단계를 빠뜨림).

**설정**: `/etc/caddy/Caddyfile`에 `whybuy.ai-agent-develop.cloud { reverse_proxy localhost:3000 { transport http { read_timeout 90s } } }` — REQ-03대로 분봉 차트 실측(15.8초)보다 넉넉하게 90초로 잡음. 컨테이너는 `-p 127.0.0.1:3000:3000`으로 바꿔서 외부에서 3000번 포트로 직접 접근은 막고 Caddy를 통해서만 열리게 함.

**결과**: `https://whybuy.ai-agent-develop.cloud/` 200, Let's Encrypt 인증서 자동 발급 확인(`openssl s_client`로 issuer가 Let's Encrypt인 것 확인, 유효기간 2026-08-14~2026-11-12 — Caddy가 만료 전 자동 갱신). HTTP로 접속해도 HTTPS로 자동 리다이렉트됨(Caddy 기본 동작).

### 5단계 — OAuth 리다이렉트 URI 등록

기획서 REQ-04대로 두 곳 다 등록. Google Cloud Console에서 헷갈렸던 점: "Google Auth Platform" 좌측 메뉴에 "Settings"가 있어서 거기 들어갔더니 리다이렉트 URI 설정이 아니라 OAuth 2.0 정책 관련 고급 설정(Session age claims 등) 화면이었다 — 실제로는 **"Clients"** 메뉴에서 기존 OAuth 2.0 클라이언트를 열어야 "Authorized redirect URIs" 항목이 나온다.

- Google: `https://whybuy.ai-agent-develop.cloud/auth/callback` 추가 (기존 Vercel URI는 롤백 대비로 유지)
- Supabase: Authentication → URL Configuration → Site URL 갱신, Redirect URLs에 `https://whybuy.ai-agent-develop.cloud/**` 추가 (Vercel URI 유지)

### 6단계 — 실제 환경변수로 컨테이너 재기동

**따옴표 함정**: `.env.production`에 값을 `KEY="value"` 형태로 따옴표를 붙여 채웠는데, `docker --env-file`은 bash와 달리 따옴표를 자동으로 벗겨주지 않는다. `docker build --build-arg`는 bash `source .env`를 거쳐서 넘겼기 때문에 문제없었지만(bash가 따옴표를 정상 처리), 순수 런타임 변수(`GEMINI_API_KEY` 등)는 따옴표 문자까지 값에 포함된 채로 컨테이너에 들어갈 뻔했다 — 전부 따옴표 없이 `KEY=value` 형태로 통일.

**진짜 원인은 따로 있었다 — URL·키 불일치**: 따옴표를 고쳐도 Supabase가 계속 "Invalid API key"를 냈다. `SUPABASE_SERVICE_ROLE_KEY`(JWT)를 디코딩해서 `ref` 클레임을 확인해보니 실제 프로젝트 참조값은 `pblhrpsjcssfxmnrjyff`인데, `.env.production`에 넣은 `NEXT_PUBLIC_SUPABASE_URL`은 `ykvlsdrholswxrkkuubo`라는 **다른 프로젝트**를 가리키고 있었다. Vercel 대시보드에서 값을 옮길 때 오래된/다른 프로젝트 URL을 잘못 복사한 것으로 추정. URL을 올바른 값으로 바꾸자 Supabase, KIS(같은 요청 안에서 같이 실패하던 토큰 발급 403도) 둘 다 한 번에 해결됨 — 두 에러가 같이 났던 건 각각 다른 원인이 아니라 애초에 요청 자체가 잘못된 프로젝트로 나가서 앞단에서부터 꼬였던 것으로 보임.

**빌드 중 무한 행(hang) 사고**: 재빌드 과정에서 `next build`가 Google Fonts(`fonts.gstatic.com`) 요청 중 응답을 못 받고 **15시간 넘게 멈춰버린** 적이 있었다. 이전엔 같은 증상이 몇 분 안에 에러로 끝났는데, 이번엔 타임아웃 없이 무한 대기했다. `ps aux`로 확인해보니 SSH 세션(로컬 wrapper)은 이미 끊겼는데 서버 쪽 `docker build` 프로세스는 고아 프로세스로 계속 살아있었다 — 예전 `apt-get upgrade` 때 겪은 것과 같은 패턴. `kill -9`로 정리하고 재시도하니 몇 초 만에 성공.

- `pkill -f "docker build"`로 죽이려다 **pkill이 자기 자신의 프로세스 목록 항목(인자에 "docker build" 문자열 포함)에 걸려 SSH 세션째로 죽는** 경험을 함 — `ps aux`로 찾은 정확한 PID를 `kill -9`로 지정하는 게 안전.
- 이후로는 `docker build` 앞에 `timeout 1800`을 붙여서, 다시 멈추더라도 30분 뒤엔 강제 종료되게 함.

**결과**: 실제 키로 재빌드·재기동 후 `https://whybuy.ai-agent-develop.cloud/`, `/api/popular`, `/api/stocks` 전부 200, 컨테이너 로그에 에러 없음.

### T2 — 로그인 리다이렉트 버그와 그 여정

실제 키로 배포 후 브라우저에서 구글 로그인을 눌러보니, 로그인 콜백 처리 후 브라우저가 `546394f3f923:3000`(컨테이너 ID)이라는, 외부에서 존재하지도 않는 주소로 리다이렉트되며 `DNS_PROBE_FINISHED_NXDOMAIN`으로 끊겼다.

**원인 추적**:
1. `app/auth/callback/route.ts`가 `new URL(request.url).origin`으로 리다이렉트 목적지를 만드는데, 이 `origin`이 실제로는 `https://546394f3f923:3000`으로 계산되고 있었다 — 컨테이너 자체의 `HOSTNAME`(Docker가 컨테이너마다 자동으로 컨테이너 ID로 설정)과 `PORT` 값이 새어나온 것.
2. Caddy가 원본 Host 헤더를 안 넘겨주는 줄 알고 `header_up Host/X-Forwarded-*`를 명시적으로 추가했지만 — Caddy는 애초에 기본으로 이 헤더들을 넘겨주고 있었다(설정 검증 시 "Unnecessary header_up" 경고로 확인). Caddy 문제가 아니었음.
3. 컨테이너에 직접(`localhost:3000`, Caddy 안 거치고) 올바른 `Host`/`X-Forwarded-*` 헤더를 수동으로 흉내내서 요청해봐도 origin이 여전히 컨테이너 ID로 나왔다 — **Next.js standalone `server.js`가 요청의 Host 헤더와 무관하게 `HOSTNAME`/`PORT` 환경변수로 origin을 만든다**는 걸 이렇게 확인함.
4. `next.config.ts`에 `experimental: { trustHostHeader: true }`를 추가하면 될 줄 알았으나, 실제로는 **존재하지 않는 옵션**이라 "Unrecognized key" 경고만 뜨고 무시됐다 (원래 `server.js`에 박혀있던 `trustHostHeader: false`는 Next.js 내부에서만 쓰는 값이지 next.config.ts로 사용자가 켤 수 있는 옵션이 아니었음).

**최종 수정**: 리다이렉트 origin 계산 자체를 코드에서 고침 — `x-forwarded-host`/`x-forwarded-proto` 헤더를 우선 사용하고, 없을 때만 `request.url`의 origin으로 폴백하도록 `app/auth/callback/route.ts` 변경 (Supabase 공식 Next.js SSR 예제가 프록시 뒤에서 배포할 때 정확히 이 패턴을 씀).

### 재빌드 지옥 — 서버 사양 문제 총정리

수정 사항을 반영하려고 서버에서 재빌드를 반복하다가 연달아 문제를 겪었다:

- **디스크 풀(`No space left on device`)**: 반복된 빌드로 캐시가 쌓여 10GB 디스크가 100% 참. `docker builder prune -af`(1.3GB), `apt-get clean`(1.1GB), `journalctl --vacuum-size=100M`(416MB), 안 쓰는 커널 패키지 6개 `apt-get autoremove`로 정리해서 69%까지 내림.
- **SSH 연결 불안정 → 빌드가 자꾸 취소됨**: `docker build`를 일반 SSH 세션 안에서 돌리면, 로컬 연결이 잠깐이라도 끊기는 순간 BuildKit이 `context canceled`로 빌드 자체를 취소해버렸다. `setsid nohup ... < /dev/null &`로 SSH 세션과 완전히 분리해서 띄우는 방식으로 바꿈.
- 그래도 서버가 vCPU 1개짜리라 빌드 자체가 느리고 Docker Hub 인증(TLS handshake timeout) 같은 일시적 네트워크 문제도 겹쳐서, 결국 **로컬 Docker Desktop을 고쳐서(아래) 로컬 빌드 → 이미지 전송(`docker save`/`load`) 방식으로 되돌아감** — 16초 만에 빌드 끝남. 이 프로젝트가 REQ-08에서 "서버는 빌드 안 하고 pull/load만" 하라고 한 이유를 제대로 체감함.

### 로컬 Docker Desktop 복구

전날 고장났던(`dockerInference` 리파스 포인트 파일, Error 1920) 문제가 재부팅 후에도 그대로였고, **`wsl --unregister docker-desktop`로 WSL 배포판을 통째로 지워도 그 파일들은 그대로 남아있었다** — 즉 이 파일들은 WSL 가상디스크 안이 아니라 Windows 쪽에 실제로 박혀있던 것. 결국 Docker Desktop 자체의 **"Reset to factory defaults"** 버튼으로 해결됨 (일반 파일 삭제 도구로는 못 건드리는 걸 Docker Desktop 자체 초기화 로직이 정리해준 것으로 보임). 로컬 이미지·컨테이너는 다 날아갔지만 이 시점엔 서버 쪽에 이미 다 옮겨져 있어서 손실 없음.

**결과**: 수정된 이미지로 컨테이너 재기동 후 `curl .../auth/callback` 응답의 `Location` 헤더가 정확한 도메인(`https://whybuy.ai-agent-develop.cloud/auth/error`)을 가리키는 것 확인. 실제 브라우저 로그인 테스트는 다음 확인 예정.

**T2 통과** — 실제 브라우저에서 구글 로그인 정상 동작 확인. 리다이렉트 버그 완전히 해결됨.

**T3 통과** — `/trade`에서 종목 검색 후 차트·종목정보·공시뉴스 3개 탭 모두 데이터 정상 표시.

**T4 통과 (이번 전환의 핵심 목표)** — 서로 다른 종목코드 8개로 `/api/quote`를 동시에 요청, 전부 200 응답·컨테이너 로그에 `EGW00201` 등 에러 전무 확인. 컨테이너 1개 + 프로세스 전역 큐 구조가 의도대로 동작함을 실측으로 확인.

**T5 통과** — 삼성전자(005930) 당일 분봉 전체 조회 14.4초 완주. Vercel `maxDuration: 45` 제약과 Caddy 502 둘 다 없음. Vercel 시절 실측치(15.8초)와 비슷한 수준이라 리전 타협(일본 대신 국내 유지)에 따른 지연 증가는 미미했던 것으로 보임.

(참고: `app/api/chart/route.ts`에 Vercel 전용 `export const maxDuration = 45`가 코드에 여전히 남아있음 — Docker에서는 무해하지만 9단계 정리 때 주석 처리하거나 제거 필요, REQ-06)

**T7 통과** — `docker stop whybuy` → `docker start whybuy` 후 수 초 만에 정상 응답 복구. 데이터는 Supabase(외부 호스팅)에 저장되므로 컨테이너 재시작과 무관하게 유지됨(원래 당연한 구조지만 실측으로 재확인).

**T6(모의 매수)은 주말이라 장이 닫혀 있어 월요일 이후로 보류.**

## 8단계 — DNS 전환 및 롤백 (기획서와 다르게 진행됨)

기획서는 "기존 커스텀 도메인을 Vercel → 새 서버로 DNS 재지정, 문제 생기면 DNS 원복"을 가정했는데, 실제로는 커스텀 도메인이 없었다 — 원래 배포는 `whybuy-gray.vercel.app`이라는 Vercel 전용 서브도메인이라 우리가 DNS를 옮길 수 있는 대상이 아니었다. 대신 이번에 완전히 새로운 도메인(`whybuy.ai-agent-develop.cloud`)을 사서 새 서버에 바로 연결하는 방식으로 진행했다.

그 결과 "DNS 전환"이라는 절차 자체가 필요 없어졌다 — 두 URL이 서로 무관하게 계속 공존한다:
- 새 서버: `https://whybuy.ai-agent-develop.cloud` (지금부터 메인으로 사용)
- 기존 Vercel: `https://whybuy-gray.vercel.app` (건드린 적 없어서 그대로 살아있음, 이게 곧 롤백 경로)

**T8(롤백 리허설)** — DNS 원복 대신, Vercel URL이 지금도 정상 응답하는지로 확인. `https://whybuy-gray.vercel.app/` 200 확인 — 문제가 생기면 이 URL로 돌아가면 그만이라 별도 조치가 필요 없는 구조. 기획서보다 오히려 더 안전한 롤백 경로(DNS 전파 대기 시간 없이 즉시 전환 가능).

## 9단계 — 정리

whybuy 프로젝트(포트폴리오 저장소, jjh7757/portfolio) 쪽에 Docker 관련 변경사항 커밋·푸시:
- `next.config.ts`(`output: standalone`), `Dockerfile`·`.dockerignore`·`docker-compose.yml`, `auth/callback` origin 버그 수정, README에 새 배포 주소 반영

**`vercel.json`·`app/api/chart/route.ts`의 `maxDuration = 45`는 일부러 지금 안 건드림.** 기획서 6장에서 이미 "Vercel 배포는 전환 후 최소 2주 유지"로 정해뒀는데, `maxDuration`을 지금 지우면 Vercel의 기본 함수 타임아웃이 더 짧아져서 아직 살려두기로 한 롤백 배포(Vercel)에서 분봉 차트가 다시 끊길 수 있다. 이 정리는 2주 뒤 Vercel 배포를 실제로 내릴 때 같이 하기로 함.

포트폴리오 저장소는 GitHub 연동으로 Vercel 자동 배포가 걸려있어서, 이번 push로 Vercel 재배포가 트리거됐을 가능성이 있음 — push 후 `https://whybuy-gray.vercel.app` 정상 응답(200) 재확인, 롤백 경로 영향 없음.

## 남은 것

- T6(모의 매수) — 주말이라 장 닫혀 있어 월요일 이후 확인
- 2주 뒤: Vercel 배포 삭제 + `vercel.json`·`maxDuration` 정리
