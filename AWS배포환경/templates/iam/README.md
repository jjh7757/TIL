# IAM 설정

계정 ID(`403187831140`)는 이미 채워져 있다.
남은 `REPO_NAME`(GitHub 저장소 이름)과 `INSTANCE_ID`(EC2 인스턴스 ID)를 치환한 뒤 사용한다.

## 1. GitHub OIDC 자격증명 공급자 등록 (계정당 한 번)

IAM → Identity providers → Add provider → OpenID Connect

- Provider URL: `https://token.actions.githubusercontent.com`
- Audience: `sts.amazonaws.com`

## 2. Actions용 역할 — `github-actions-deploy`

- 신뢰 정책: [`github-actions-trust-policy.json`](github-actions-trust-policy.json)
- 권한 정책: [`github-actions-permissions.json`](github-actions-permissions.json)

### GitHub의 `sub` 클레임은 ID를 포함한다 — 콘솔 마법사를 믿지 말 것

AWS 콘솔의 "웹 자격 증명" 마법사는 `repo:<owner>/<repo>:*` 형식을 생성하지만,
**GitHub이 실제로 보내는 값에는 숫자 ID가 붙어 있다.**

```
repo:jjh7757@307797437/deploy-test@1365988315:ref:refs/heads/master
     ^^^^^^^ ^^^^^^^^^ ^^^^^^^^^^^ ^^^^^^^^^^
     소유자  소유자 ID   저장소       저장소 ID
```

이름이 바뀌거나 남이 그 이름을 차지해도 ID는 변하지 않으므로 보안상 더 강한 형식이다.
하지만 마법사가 만든 구형식 패턴과는 매칭되지 않아, **신뢰 정책이 완벽해 보이는데도
`Not authorized to perform sts:AssumeRoleWithWebIdentity`로 계속 거절당한다.**
AWS는 "역할 없음"과 "신뢰 정책 불일치"를 같은 메시지로 응답해서 원인 파악이 더 어렵다.

그래서 템플릿은 두 형식을 모두 넣어뒀다. ID는 다음으로 확인한다.

```bash
gh api repos/<owner>/<repo> --jq '{owner_id:.owner.id, repo_id:.id}'
```

값이 의심스러우면 워크플로에서 실제 클레임을 찍어보는 게 가장 빠르다
(`ACTIONS_ID_TOKEN_REQUEST_URL`로 토큰을 받아 payload를 디코드).

**신뢰 정책의 `sub` 조건이 보안의 핵심이다.** `repo:jjh7757/REPO_NAME:*`로 저장소를 특정하지
않고 와일드카드로 열어두면 **다른 사람의 GitHub 저장소에서도 이 역할을 가져다 쓸 수 있다.**
저장소마다 역할을 따로 만들거나, 한 역할을 공유하려면 `sub` 조건에 저장소를 나열한다.

배포 대상 인스턴스도 ARN으로 고정했다. 이 역할이 탈취돼도 다른 인스턴스에는 명령을 못 보낸다.

## 3. EC2 인스턴스 프로파일 — `ec2-deploy-target`

- AWS 관리형 정책 `AmazonSSMManagedInstanceCore` 연결 (SSM 접속에 필요)
- 추가 인라인 정책: [`ec2-instance-profile-permissions.json`](ec2-instance-profile-permissions.json)

서버는 이미지를 **받기만** 하면 되므로 ECR 푸시 권한을 주지 않는다.

`deploy-app` 스크립트가 쓰는 `sts:GetCallerIdentity`는 IAM 권한이 필요 없는 호출이라
정책에 넣지 않았다.

## 확인

```bash
# 인스턴스에서 — SSM 등록 여부
aws ssm describe-instance-information --region ap-northeast-2

# 인스턴스에서 — ECR 로그인 가능 여부
aws ecr get-login-password --region ap-northeast-2 | head -c 20
```
