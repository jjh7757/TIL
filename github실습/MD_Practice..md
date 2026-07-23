# Git 기본 사용 흐름

Git은 파일의 변경 사항을 기록하고, GitHub와 같은 원격 저장소에 저장할 수 있도록 도와주는 버전 관리 시스템입니다.

---

## 전체 흐름

```text
일반 폴더
    │
    │ git init
    ▼
로컬 Git 저장소

Working Directory
    │
    │ git add
    ▼
Staging Area
    │
    │ git commit
    ▼
Commits
    │
    │ git push
    ▼
GitHub 원격 저장소
```

---

# 1. Git 저장소 생성

현재 폴더를 Git 저장소로 초기화합니다.

```bash
git init
```

---

# 2. 현재 상태 확인

변경된 파일이나 추적되지 않는 파일을 확인합니다.

```bash
git status
```

---

# 3. 변경 사항 스테이징

커밋할 파일을 선택합니다.

모든 변경 사항 추가

```bash
git add .
```

특정 파일만 추가

```bash
git add 파일이름
```

---

# 4. 커밋 생성

스테이징된 변경 사항을 하나의 버전으로 저장합니다.

```bash
git commit -m "커밋 메시지"
```

예시

```bash
git commit -m "회원가입 기능 추가"
```

---

# 5. 커밋 이력 확인

지금까지의 커밋 기록을 확인합니다.

```bash
git log --oneline
```

---

# 6. GitHub 원격 저장소 연결

GitHub 저장소를 로컬 저장소와 연결합니다.

```bash
git remote add origin [원격 저장소 URL]
```

예시

```bash
git remote add origin https://github.com/username/project.git
```

---

# 7. GitHub로 업로드

로컬 커밋을 원격 저장소로 전송합니다.

처음 한 번만

```bash
git push -u origin main
```

이후에는

```bash
git push
```

만 입력하면 됩니다.

---

# 프로젝트를 처음 설정할 때

프로젝트를 처음 Git으로 관리할 때는 아래 명령을 순서대로 실행합니다.

```bash
git init

git remote add origin [원격 저장소 URL]

git push -u origin main
```

---

# 파일을 수정할 때마다 반복하는 흐름

작업 후에는 아래 과정을 반복합니다.

```bash
git status

git add .

git commit -m "변경 내용 설명"

git push
```

---

# Git 명령어 요약

| 명령어 | 설명 |
|---------|------|
| `git init` | Git 저장소 생성 |
| `git status` | 현재 변경 사항 확인 |
| `git add .` | 모든 변경 사항 스테이징 |
| `git commit -m "메시지"` | 변경 사항 저장 |
| `git log --oneline` | 커밋 기록 확인 |
| `git remote add origin URL` | GitHub 저장소 연결 |
| `git push -u origin main` | 첫 업로드 |
| `git push` | 변경 사항 업로드 |

---

# 핵심 흐름 한눈에 보기

```text
파일 수정
    │
    ▼
git status
    │
    ▼
git add .
    │
    ▼
git commit -m "메시지"
    │
    ▼
git push
```

> 💡 **Tip**
>
> - `git init`과 `git remote add origin`은 프로젝트를 처음 만들 때 대부분 한 번만 실행합니다.
> - 이후에는 **`git add → git commit → git push`** 과정을 반복하면서 버전을 관리합니다.