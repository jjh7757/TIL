#!/usr/bin/env bash
# EC2 t4g.small (Ubuntu 24.04 arm64) 초기 세팅
# 사용법: sudo bash bootstrap.sh
set -euo pipefail

log() { echo "==> $*"; }

if [ "$(id -u)" -ne 0 ]; then
  echo "root로 실행하세요: sudo bash bootstrap.sh" >&2
  exit 1
fi

# --- 1. 스왑 2GB -------------------------------------------------------------
# RAM 2GB에서는 스왑이 없으면 컨테이너 몇 개만 띄워도 OOM이 난다.
if ! swapon --show | grep -q '/swapfile'; then
  log "스왑 2GB 생성"
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
  # 물리 메모리를 최대한 쓰고 스왑은 보조로만
  sysctl -w vm.swappiness=10
  echo 'vm.swappiness=10' > /etc/sysctl.d/99-swappiness.conf
else
  log "스왑 이미 존재 — 건너뜀"
fi

# --- 2. 기본 패키지 ----------------------------------------------------------
log "패키지 업데이트"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ca-certificates curl gnupg unzip

# --- 3. Docker ---------------------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  log "Docker 설치"
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=arm64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  usermod -aG docker ubuntu
  # Session Manager는 ssm-user로 접속한다. 이 계정은 첫 세션 연결 시 만들어지므로
  # bootstrap 시점에 없을 수 있다. 없으면 세션 연결 후 아래를 직접 실행할 것:
  #   sudo usermod -aG docker ssm-user   (새 세션부터 적용)
  id ssm-user >/dev/null 2>&1 && usermod -aG docker ssm-user || true
else
  log "Docker 이미 설치됨 — 건너뜀"
fi

# 로그가 디스크를 채우지 않도록 제한 (왜샀어 때 디스크 풀을 겪은 지점)
log "Docker 로그 로테이션 설정"
cat > /etc/docker/daemon.json <<'JSON'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" }
}
JSON
systemctl restart docker
systemctl enable docker

# --- 4. AWS CLI (ECR 로그인용) ------------------------------------------------
if ! command -v aws >/dev/null 2>&1; then
  log "AWS CLI 설치"
  curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o /tmp/awscliv2.zip
  unzip -q /tmp/awscliv2.zip -d /tmp
  /tmp/aws/install
  rm -rf /tmp/aws /tmp/awscliv2.zip
fi

# --- 5. 공용 네트워크와 디렉토리 규칙 ------------------------------------------
log "docker network 'web' 생성"
docker network inspect web >/dev/null 2>&1 || docker network create web

mkdir -p /srv
chown ubuntu:ubuntu /srv

# --- 6. 배포 스크립트 ---------------------------------------------------------
# Actions에서 SSM으로 이걸 호출한다. 명령을 서버에 두면 워크플로의 따옴표 중첩이 사라진다.
log "/usr/local/bin/deploy-app 설치"
cat > /usr/local/bin/deploy-app <<'DEPLOY'
#!/usr/bin/env bash
# 사용법: deploy-app <앱이름> [이미지태그]
set -euo pipefail

APP="${1:?앱 이름이 필요합니다}"
TAG="${2:-latest}"
DIR="/srv/$APP"
REGION="$(curl -fsS -H "X-aws-ec2-metadata-token: $(curl -fsS -X PUT http://169.254.169.254/latest/api/token -H 'X-aws-ec2-metadata-token-ttl-seconds: 60')" http://169.254.169.254/latest/meta-data/placement/region)"
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
REGISTRY="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"

[ -d "$DIR" ] || { echo "$DIR 가 없습니다"; exit 1; }
cd "$DIR"

# compose 파일이 참조하는 변수. 개별 명령 앞에만 붙이면 뒤따르는 ps/logs 에서 빠져
# container_name 이 빈 문자열로 해석되며 검증 에러가 난다. 반드시 export 로 둔다.
export ECR_REGISTRY="$REGISTRY"
export APP_NAME="$APP"
export IMAGE_TAG="$TAG"

echo "==> ECR 로그인 ($REGISTRY)"
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY"

echo "==> $APP:$TAG 배포"
docker compose pull
docker compose up -d

echo "==> 오래된 이미지 정리"
# prune -f 는 dangling(태그 없는) 이미지만 지운다. 배포마다 커밋 SHA 태그가 새로 붙으므로
# 이전 버전들은 태그가 남아 계속 쌓인다. 이미지가 큰 앱에서는 디스크를 금방 채운다.
# -a 로 컨테이너가 참조하지 않는 이미지까지, until 로 최근 것은 롤백용으로 남긴다.
docker image prune -af --filter "until=72h"

echo "==> 현재 상태"
docker compose ps
DEPLOY
chmod +x /usr/local/bin/deploy-app

log "완료. 다음: Caddy 기동 → ECR/OIDC 설정"
