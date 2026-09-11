# 4단계 — 도메인과 HTTPS

[배포 환경 구축 계획](README.md)의 4단계 상세 절차.

`ai-agent-develop.cloud`(가비아) 아래 서브도메인을 붙이고, Caddy가 Let's Encrypt 인증서를
자동 발급하게 한다. 왜샀어 때 세운 "범용 도메인 + 프로젝트별 서브도메인" 전략을 그대로 잇는다.

| 서브도메인 | 가리키는 곳 |
|---|---|
| `whybuy` | `49.50.134.102` — 네이버클라우드 |
| `test` | `13.209.128.48` — AWS deploy-server |

## 순서가 중요하다

**DNS 전파를 확인한 뒤에 Caddy를 reload한다.**

Caddy는 Let's Encrypt에서 인증서를 받을 때 HTTP-01 챌린지를 쓴다. Let's Encrypt가 그 도메인으로
서버의 80번 포트에 접속해 응답을 확인하는 방식이다. DNS가 아직 안 퍼진 상태에서 reload하면
발급이 실패하고, **Let's Encrypt는 실패 횟수에 한도가 있어 반복하면 한동안 재발급이 막힌다.**

## 1. A 레코드 추가

가비아 My가비아 → DNS 관리툴 → `ai-agent-develop.cloud` → DNS 설정

| 타입 | 호스트 | 값 | TTL |
|---|---|---|---|
| A | `test` | `13.209.128.48` | 600 |

기존 레코드는 건드리지 않는다.

## 2. 전파 확인

```bash
nslookup test.ai-agent-develop.cloud 8.8.8.8
```

Elastic IP가 나올 때까지 기다린다. 보통 몇 분.

ACME가 실제로 밟을 경로까지 미리 확인해두면 확실하다.

```bash
curl -s -o /dev/null -w "HTTP %{http_code} (%{remote_ip})\n" http://test.ai-agent-develop.cloud/
```

## 3. Caddyfile 교체 후 reload

```bash
sudo tee /srv/caddy/Caddyfile >/dev/null <<'EOF'
{
    email junhyeong7757@gmail.com
}

test.ai-agent-develop.cloud {
    reverse_proxy deploy-test:3000
}
EOF
docker compose -f /srv/caddy/docker-compose.yml exec caddy caddy reload --config /etc/caddy/Caddyfile
```

`reverse_proxy` 대상은 호스트 포트가 아니라 **`web` 네트워크상의 컨테이너 이름과 그 컨테이너가
리슨하는 포트**다. 앱은 호스트 포트를 열지 않으므로 외부에서 직접 닿을 방법이 없고,
들어오는 길은 Caddy의 80/443뿐이다.

## 4. 확인

```bash
docker compose -f /srv/caddy/docker-compose.yml logs --tail 20 caddy
```

`certificate obtained successfully` 가 나오면 성공. 바깥에서도 검증한다.

```bash
curl -s -o /dev/null -w "HTTP %{http_code} TLS:%{ssl_verify_result}\n" https://test.ai-agent-develop.cloud/
curl -s -o /dev/null -w "HTTP %{http_code} -> %{redirect_url}\n" http://test.ai-agent-develop.cloud/
echo | openssl s_client -connect test.ai-agent-develop.cloud:443 -servername test.ai-agent-develop.cloud 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates
```

## 앱을 추가할 때

Caddyfile에 블록 하나만 더 붙이고 reload하면 된다. A 레코드도 같이 추가한다.

```
rag.ai-agent-develop.cloud {
    reverse_proxy rag:8000
}
```

인증서는 Caddy가 만료 전에 자동 갱신한다. 갱신 기록은 `caddy_data` 볼륨에 남으므로
**이 볼륨을 지우면 인증서를 다시 받아야 하고, 발급 한도에 걸릴 수 있다.**

## 결과 (2026-09-11)

| 검사 | 결과 |
|---|---|
| HTTPS | `200`, TLS 검증 통과 |
| HTTP → HTTPS | `308` 리다이렉트 |
| 인증서 | `CN=test.ai-agent-develop.cloud`, Let's Encrypt |
| 유효기간 | 2026-09-11 ~ 2026-12-10 |
| 배포 커밋 | 응답의 `sha`가 push한 커밋과 일치 |
