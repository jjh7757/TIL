# 웹 크롤링 — BeautifulSoup과 Playwright

웹 페이지에서 필요한 데이터를 코드로 뽑아내는 두 가지 방법. **받아 온 HTML 안에 데이터가 이미 있느냐**(→ BeautifulSoup), **JavaScript가 실행돼야 나타나느냐**(→ Playwright)로 고른다.

## 1. requests + BeautifulSoup (정적 HTML)

```text
URL → requests → HTML → BeautifulSoup → 기사 제목과 링크
```

| 라이브러리 | 역할 |
|---|---|
| `requests` | 서버에 HTTP 요청을 보내고 응답을 받는다 |
| `BeautifulSoup` | 받은 HTML 문자열을 분석해 태그·속성·텍스트를 찾는다 |

BeautifulSoup은 **분석만** 한다. 사이트에 접속하지도, JavaScript를 실행하지도 않는다.

```bash
pip install requests beautifulsoup4
```

### 요청과 파싱

```python
response = requests.get(URL, timeout=15)
response.raise_for_status()          # 4xx/5xx면 예외

soup = BeautifulSoup(response.text, "html.parser")   # 파싱: 문자열 → 탐색 가능한 구조
```

- `timeout=15`: 연결·응답 대기 시간 제한. 없으면 서버가 응답하지 않을 때 무한정 기다릴 수 있다.
- `raise_for_status()`: HTTP 오류를 조용히 넘기지 않고 예외로 바꾼다. 오류 페이지의 HTML을 정상 데이터로 착각해 파싱하는 사고를 막는다.
- `html.parser`는 Python 내장 파서다.

### CSS 선택자로 요소 찾기

브라우저 개발자 도구(우클릭 → 검사)에서 제목을 담은 태그의 `class`, `href`를 확인하고 선택자를 만든다.

| 선택자 | 대상 |
|---|---|
| `a` | 모든 `a` 태그 |
| `.gPFEn` | `gPFEn` 클래스를 가진 요소 |
| `a.gPFEn` | `gPFEn` 클래스를 가진 `a` 태그 |

| 메서드 | 반환 | 못 찾았을 때 |
|---|---|---|
| `select_one()` | 첫 번째 태그 | `None` |
| `select()` | 태그 리스트 | 빈 리스트 |

못 찾았을 때 조용히 빈 결과로 넘어가지 말고 `if not articles: raise ValueError(...)`로 바로 알리는 편이 디버깅이 쉽다. **클래스 이름(`gPFEn`)은 사이트가 바꾸면 깨지는 값**이라, 결과가 0건이면 선택자부터 의심한다.

### 텍스트와 속성 읽기

- `get_text(strip=True)`: 태그 안 텍스트, 양끝 공백 제거
- `article["href"]`: 속성이 없으면 `KeyError`
- `article.get("href")`: 속성이 없으면 `None` (딕셔너리의 `get`과 같은 동작)

### 상대 주소 → 절대 주소

`href`가 `./read/...`처럼 **상대 주소**로 오는 경우가 많다. `urljoin`으로 기준 URL과 합쳐 절대 주소로 만든다.

```python
BASE_URL = urljoin(response.url, "/")      # https://news.google.com/
absolute_url = urljoin(BASE_URL, link)     # 이미 절대 주소인 링크는 그대로 유지
```

`response.url`은 리다이렉트까지 거친 **최종 주소**라서, 요청한 `URL` 변수 대신 이걸 기준으로 삼는다.

### 수집 결과 정리와 저장

기사 하나를 `{"title":..., "url":...}` 딕셔너리로 만들어 리스트에 모으고, 제목이나 링크가 빈 요소는 건너뛴다.

```python
with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["title", "url"])
    writer.writeheader(); writer.writerows(news_rows)

json_path.write_text(json.dumps(news_rows, ensure_ascii=False, indent=2), encoding="utf-8")
```

| 옵션 | 이유 |
|---|---|
| `utf-8-sig` | Excel에서 CSV를 열 때 한글이 깨지지 않게 BOM을 붙인다 |
| `newline=""` | CSV 모듈이 줄바꿈을 직접 처리하게 해서 Windows에서 빈 줄이 끼는 것을 막는다 |
| `ensure_ascii=False` | JSON에 한글을 `\uXXXX`가 아니라 그대로 기록 |
| `indent=2` | 사람이 읽기 좋은 들여쓰기 |

## 2. 응답 HTML ≠ 브라우저 화면

브라우저는 HTML을 받은 뒤 **JavaScript를 실행해 화면을 바꾼다.** `requests`로 받은 HTML에는 그 실행 결과가 없다.

> 브라우저에서 보이는 데이터를 BeautifulSoup으로 못 찾으면, 먼저 `response.text`에 그 데이터가 있는지 확인한다.

없다면 JS가 나중에 채우는 데이터이므로 브라우저를 직접 제어하는 Playwright가 필요하다.

## 3. Playwright (JavaScript가 그린 화면)

```text
브라우저 실행 → 페이지 이동 → 제목 요소 대기 → 제목 수집 → 브라우저 종료
```

```bash
pip install playwright
python -m playwright install chromium     # 브라우저 본체를 따로 설치
```

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(URL, wait_until="domcontentloaded")

    title_locator = page.locator(".ContentTitle__title--e3qXt")
    title_locator.first.wait_for(state="visible", timeout=15000)   # 요소가 나타날 때까지 대기

    for title in title_locator.all():
        text = title.text_content()
        if text and text.strip():
            print(text.strip())
    browser.close()
```

| 요소 | 설명 |
|---|---|
| `headless=False/True` | 창을 보이게 / 숨기게. 화면 없는 서버에서는 `True` |
| `wait_until="domcontentloaded"` | 초기 HTML 문서가 준비될 때까지만 기다림. JS가 나중에 채우는 데이터는 별도로 기다려야 함 |
| `page.locator(css)` | 요소를 찾는 **Locator 객체**를 만든다. 만드는 것만으로는 기다리지 않는다 |
| `wait_for(state="visible", timeout=...)` | 요소가 보일 때까지 대기. 먼저 나타나면 바로 진행, 시간 안에 안 나타나면 오류 |
| `all()` | 현재 DOM에서 일치하는 Locator 전체. **대기하지 않는다** |
| `wait_for_timeout(ms)` | 단순 시간 대기(밀리초). 수업 중 화면을 보려는 용도이고 수집 조건으로 쓰면 안 됨 |

### 가장 중요한 규칙: 데이터가 나타날 때까지 기다린 뒤 읽기

> 페이지가 열렸다고 해서 수집할 데이터까지 준비된 것은 아니다.

`goto()`가 끝난 직후에 목록을 읽으면 JS가 아직 데이터를 안 그렸을 수 있어 **빈 결과**가 나온다. `wait_for`로 **첫 요소가 보이는 것을 확인한 뒤** `all()`로 읽는다. 스크롤하면 더 로딩되는 목록은 별도의 대기 조건이 필요하다.

실행 파일에서는 수집 코드를 `try`에 두고 `finally`에서 `browser.close()`를 호출해 오류가 나도 브라우저가 남지 않게 정리한다.

## 4. 어떤 걸 쓸까

| | requests + BeautifulSoup | Playwright |
|---|---|---|
| 동작 | HTML 문자열만 받아 분석 | 실제 브라우저를 띄워 JS까지 실행 |
| 속도·자원 | 빠르고 가벼움 | 느리고 무거움 (브라우저 필요) |
| 적합 | 정적 HTML, 응답에 데이터가 이미 있는 페이지 | JS로 그려지는 화면, 클릭·스크롤 등 상호작용 |
| 선택 순서 | **먼저 시도** | `response.text`에 데이터가 없을 때 |

공통 주의: 선택자(클래스 이름)는 사이트가 바뀌면 깨지고, 크롤링은 사이트의 이용 약관과 `robots.txt`, 요청 빈도(과도한 요청 금지, `time.sleep`)를 지켜야 한다.
