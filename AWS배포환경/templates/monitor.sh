#!/bin/bash
# /srv/monitor.sh — cron으로 5분마다 실행
# 앱 헬스체크(HTTP 200) + DB 컨테이너 healthcheck + 디스크 사용률을 확인하고,
# 상태가 바뀔 때(정상→이상, 이상→정상)만 SNS로 알린다. 매번 알리면 다운된 동안 스팸이 된다.
set -uo pipefail

STATE_FILE=/srv/monitor.state
SNS_TOPIC_ARN="arn:aws:sns:ap-northeast-2:403187831140:server-alerts"
REGION=ap-northeast-2
FAILURES=()

check_url() {
  local name="$1" url="$2" code
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url" || echo "000")
  if [ "$code" != "200" ]; then
    FAILURES+=("$name ($url): HTTP $code")
  fi
}

check_container_health() {
  local name="$1" status
  status=$(docker inspect --format='{{.State.Health.Status}}' "$name" 2>/dev/null || echo "missing")
  if [ "$status" != "healthy" ]; then
    FAILURES+=("컨테이너 $name: $status")
  fi
}

check_disk() {
  local usage
  usage=$(df --output=pcent / | tail -1 | tr -dc '0-9')
  if [ -n "$usage" ] && [ "$usage" -ge 85 ]; then
    FAILURES+=("디스크 사용률 ${usage}% (root)")
  fi
}

# 배포된 앱이 늘어나면 이 줄만 추가하면 된다.
check_url "deploy-test" "https://test.ai-agent-develop.cloud"
check_url "rag" "https://rag.ai-agent-develop.cloud"
check_container_health "postgres"
check_container_health "redis"
check_disk

PREV_STATE="ok"
[ -f "$STATE_FILE" ] && PREV_STATE="$(cat "$STATE_FILE")"

if [ "${#FAILURES[@]}" -gt 0 ]; then
  if [ "$PREV_STATE" != "fail" ]; then
    MSG="이상 감지: $(date '+%Y-%m-%d %H:%M:%S %Z')"
    for f in "${FAILURES[@]}"; do MSG="$MSG
- $f"; done
    aws sns publish --topic-arn "$SNS_TOPIC_ARN" --region "$REGION" \
      --subject "[서버 알림] 이상 감지" --message "$MSG"
    echo "$MSG"
  fi
  echo "fail" > "$STATE_FILE"
else
  if [ "$PREV_STATE" = "fail" ]; then
    MSG="정상 복구: $(date '+%Y-%m-%d %H:%M:%S %Z')"
    aws sns publish --topic-arn "$SNS_TOPIC_ARN" --region "$REGION" \
      --subject "[서버 알림] 정상 복구" --message "$MSG"
    echo "$MSG"
  fi
  echo "ok" > "$STATE_FILE"
fi
