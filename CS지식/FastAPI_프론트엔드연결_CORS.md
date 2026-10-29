# 프론트엔드 연결과 CORS

`frontend`(React + Vite)의 게시판 화면을 `fastapi_agent` 백엔드에 연결합니다. 핵심은 **출처가 다른 프론트엔드가 API 응답을 읽을 수 있게 하는 CORS**와, **JWT를 저장했다가 요청마다 보내는 흐름**입니다.

## 실행

```bash
# fastapi_agent에서
uv run fastapi dev
```

```
# frontend/.env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

```bash
# 별도 터미널
cd frontend
npm install
npm run dev
```

브라우저에서 `http://127.0.0.1:5173`에 접속합니다. Vite는 `VITE_`로 시작하는 환경변수만 프론트엔드 코드에 노출합니다.

## CORS

### 동일 출처 정책과 CORS

- **동일 출처 정책**(Same-Origin Policy): 한 출처에서 실행된 JavaScript가 **다른 출처의 응답을 자유롭게 읽지 못하게** 하는 브라우저 보안 정책. 악성 사이트가 사용자가 로그인한 다른 사이트의 데이터를 읽는 것을 막는다
- **CORS**(Cross-Origin Resource Sharing): 서버가 **응답 헤더로 허용할 출처를 알려 주어**, 브라우저가 다른 출처의 응답을 JavaScript에서 쓰도록 허락하는 방식

프론트엔드와 백엔드의 출처가 다르면 이 제한이 걸리고, 백엔드가 CORS로 프론트엔드 출처를 허용해야 화면에 API 응답을 표시할 수 있습니다.

### 출처(Origin) = 프로토콜 + 호스트 + 포트

| 주소 | 프로토콜 | 호스트 | 포트 |
|------|----------|--------|------|
| `http://127.0.0.1:5173` | http | 127.0.0.1 | 5173 |
| `http://127.0.0.1:8000` | http | 127.0.0.1 | 8000 |
| `http://localhost:5173` | http | localhost | 5173 |

- 셋 중 **하나라도 다르면** 다른 출처. 5173과 8000은 포트가 달라 다른 출처
- `localhost`와 `127.0.0.1`은 같은 컴퓨터지만 **호스트 표기가 달라** 다른 출처
- `/posts`, `/auth/login` 같은 **경로는 출처에 포함되지 않음**

### CORSMiddleware

**미들웨어**는 요청이 Router에 닿기 전과 응답이 클라이언트로 나가기 전에 **공통 처리**를 하는 구성 요소입니다 (CORS, 요청 로그 등).

```python
# src/fastapi_agent/main.py — app = FastAPI(...) 아래
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

| 옵션 | 의미 |
|------|------|
| `allow_origins` | 응답을 읽도록 허용할 프론트엔드 출처 (`localhost`·`127.0.0.1` 둘 다 등록) |
| `allow_methods` | 허용할 HTTP 메서드 |
| `allow_headers` | JSON 본문(`Content-Type`)과 인증 토큰(`Authorization`) 헤더 |

미들웨어는 요청의 `Origin` 헤더를 보고, 허용된 출처면 응답에 `Access-Control-Allow-Origin` 등을 붙입니다. 브라우저는 이 헤더를 보고 JavaScript가 응답을 읽어도 되는지 판단합니다.

> `Authorization` 헤더나 `Content-Type: application/json`을 쓰는 요청은 브라우저가 실제 요청 전에 **`OPTIONS` 사전 요청(preflight)**을 먼저 보내 허용 여부를 확인한다. `allow_methods`·`allow_headers`는 이 사전 요청에 대한 답이다.

### CORS는 보안 장치가 아니다

CORS는 **브라우저가 적용하는 정책**이라 `curl`이나 서버 간 요청에는 적용되지 않습니다. API의 **인증·권한 검사는 별도로** 구현해야 합니다. `allow_headers`의 `Authorization`도 헤더 **전송을 허용**할 뿐, 토큰이 유효한지는 백엔드 인증 코드가 확인합니다.

---

## React 기본 개념

HTML은 화면 구조, CSS는 스타일, JavaScript는 사용자 입력과 API 호출을 담당합니다. 이 프론트엔드는 **React**로 화면을 만들고 **Vite**로 개발 서버를 실행합니다.

| 개념 | 코드에서 하는 일 |
|------|------------------|
| 컴포넌트 | `PostListPage`, `AuthPage`처럼 화면을 나누는 단위 |
| JSX | `<h1>{post.title}</h1>`처럼 JavaScript 안에서 화면을 표현하는 문법 |
| props | `<PostListPage mine />`의 `mine`처럼 컴포넌트에 전달하는 값 |
| `useState` | 게시글, 입력값, 로딩 여부 등 화면 상태 저장 |
| `useEffect` | 화면이 표시되거나 지정한 값이 바뀔 때 API 조회 등 실행 |
| React Router | `/login`, `/posts/1` 같은 주소에 맞는 화면 표시 |

- `onSubmit`은 폼 제출, `onChange`는 입력값 변경 시 실행할 함수를 연결
- `event.preventDefault()`는 폼 제출로 **페이지가 새로 열리는 기본 동작을 막고** JavaScript에서 API를 호출하게 한다

## API 요청과 응답

요청 코드는 `frontend/src/api/client.js`에 모여 있습니다.

```js
const response = await fetch(`${API_BASE_URL}/posts`)
const body = await response.json()
const posts = body.data
```

- `fetch()`: HTTP 요청, `await`: 비동기 결과 대기, `response.json()`: JSON 응답을 JavaScript 값으로
- 공통 함수 `request()`가 **성공 응답에서 `data`를 꺼내** 반환 → 화면에서는 `.data`를 다시 꺼낼 필요 없음
- 실패 응답은 `error.message`를 읽어 오류로 던지고 화면이 표시 → [공통 응답 형식](FastAPI_공통응답_예외처리.md) 덕분에 모든 API에 같은 코드가 통한다

### 응답으로 화면 그리기

```js
const [data, setData] = useState({ items: [], total: 0 })
```

`data`는 현재 값, `setData()`는 값을 바꾸는 함수입니다. `useEffect`에서 `api.posts()`를 호출하고 응답을 받으면 `setData(result)` → 상태가 바뀌면 React가 컴포넌트를 **다시 실행**해 화면에 반영합니다.

```
목록 화면 표시 → api.posts 호출 → GET /posts 응답 → setData로 상태 변경 → 게시글 목록 렌더링
```

`/posts`는 전체 배열을 반환하고, `api.posts()`가 화면의 검색·정렬·페이지 조건에 맞춰 `{ items, total }`로 변환합니다.

```jsx
<ul>
  {data.items.map((post) => (
    <li key={post.id}>
      <Link to={`/posts/${post.id}`}>{post.title}</Link>
    </li>
  ))}
</ul>
```

- JSX의 `{}` 안에는 JavaScript 표현식
- `map()`으로 게시글마다 화면 요소를 만들고, `key`는 React가 목록 항목을 구분하는 값
- 요청 중엔 `loading`, 실패하면 `error`, 성공하면 `data.items`에 따라 표시

**FastAPI는 JSON만 반환하고, 화면은 React가 그 데이터로 구성합니다.**

## 로그인과 JWT

### 로그인 후 저장

로그인 폼이 이메일·비밀번호를 JSON으로 `POST /auth/login`에 보내면, JWT는 응답의 `data.access_token`에 들어 있습니다.

```js
// frontend/src/auth/AuthContext.jsx
const result = await api.login(credentials)
const currentUser = await api.me(result.access_token)
sessionStorage.setItem(TOKEN_KEY, result.access_token)
setUser(currentUser)
setToken(result.access_token)
```

`api.login()`이 `data`를 꺼내 주므로 `result.access_token`으로 읽고, 그 토큰으로 `GET /me`를 호출해 사용자 정보를 확인한 뒤 저장합니다.

| 저장 위치 | 값과 용도 |
|-----------|-----------|
| `sessionStorage` | `access_token` 키로 JWT 저장 → **새로고침 후에도** 사용 |
| React 상태 | `token`, `user` → API 요청과 화면 표시 |

`AuthProvider`가 **Context**로 로그인 상태를 여러 컴포넌트에 공유하고, 각 화면은 `useAuth()`로 `user`, `token`, `logout()` 등을 가져옵니다. 상단 메뉴도 `user`에 따라 로그인 링크 또는 이메일+로그아웃 버튼을 표시합니다.

### JWT를 서버로 보내기

```js
const { token } = useAuth()
await api.createPost({ title, content }, token)
```

`request()`가 전달받은 토큰을 `fetch()`의 `Authorization` 헤더에 넣습니다. **`sessionStorage`에 저장했다고 자동 전송되는 것은 아니며**, 요청 코드가 헤더를 직접 붙입니다. (쿠키와 다른 점)

```
POST /posts
Content-Type: application/json
Authorization: Bearer <JWT>

{"title": "제목", "content": "본문"}
```

백엔드의 `get_current_user()`가 헤더에서 토큰을 읽고 **서명·만료를 검증**한 뒤 토큰의 사용자 ID로 회원을 조회하고, 그 사용자를 게시글 작성자로 지정합니다.

### 새로고침·로그아웃·만료

| 상황 | 처리 |
|------|------|
| 새로고침 | `sessionStorage`에서 토큰을 읽고 `/me`를 호출해 사용자 정보 복원 |
| 로그아웃 | 저장된 토큰 삭제, React의 `token`·`user` 비우기 |
| 탭 닫기 | 탭 세션 종료와 함께 `sessionStorage`도 삭제 |
| 인증 실패 | 저장된 토큰으로 보낸 요청이 401 → 로그인 상태 지우고 재로그인 안내 |

토큰 **자동 갱신은 없으므로** 만료되면 다시 로그인합니다. 인증이 필요한 화면은 `RequireAuth`가 감싸, 로그인 상태가 없으면 로그인 화면으로 보냅니다.

## 입력 폼과 게시글 등록

### 입력값을 상태로 관리

```jsx
const [title, setTitle] = useState('')
const [content, setContent] = useState('')

<form onSubmit={submit}>
  <input value={title} onChange={(event) => setTitle(event.target.value)} />
  <textarea value={content} onChange={(event) => setContent(event.target.value)} />
  <button type="submit">등록</button>
</form>
```

`value`는 입력란에 표시할 값, `onChange`는 입력할 때마다 `event.target.value`로 현재 값을 읽어 상태에 저장합니다.

### 요청 중·성공·실패 처리

```js
const [pending, setPending] = useState(false)
const [error, setError] = useState('')
const { token } = useAuth()
const navigate = useNavigate()

async function submit(event) {
  event.preventDefault()
  if (pending) return               // 중복 제출 방지

  setPending(true)
  setError('')

  try {
    const post = await api.createPost({ title, content }, token)
    navigate(`/posts/${post.id}`, { replace: true })   // 생성된 글 상세로 이동
  } catch (reason) {
    setError(reason.message)        // 백엔드의 error.message
  } finally {
    setPending(false)               // 성공·실패와 관계없이 해제
  }
}
```

```jsx
<button type="submit" disabled={pending}>
  {pending ? '등록 중…' : '등록'}
</button>
{error && <p role="alert">{error}</p>}
```

| 상황 | 화면 처리 |
|------|-----------|
| 요청 중 | 버튼 비활성화로 반복 제출 방지 |
| 성공 | 생성된 게시글 상세 화면으로 이동 (`replace: true` → 뒤로가기로 작성 폼에 돌아가지 않음) |
| 실패 | 오류 표시, **입력값 유지** → 다시 제출 가능 |

인증 만료로 로그인 화면으로 이동하면 입력값은 유지되지 않습니다.

## 연결 확인

회원가입 → 로그인 → 글쓰기 → 게시글 상세 → 댓글 작성 순서로 확인합니다. 개발자 도구에서:

| 탭 | 확인 |
|----|------|
| Application → Session Storage | 로그인 후 `access_token` 저장 |
| Network | `/auth/login` 응답의 `data.access_token`, `/me`·글쓰기 요청의 `Authorization` 헤더 |
| Network | `/posts` 응답의 게시글이 화면 목록에 표시 |
| Network → Payload | `POST /posts`에 입력한 `title`, `content`가 JSON으로 전달 |

- 글 등록 후 응답의 게시글 ID 상세 화면으로 이동하는지
- 새로고침 후 로그인 상태가 복원되는지, 로그아웃 후 토큰이 삭제되는지
