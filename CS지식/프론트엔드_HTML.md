# 프론트엔드와 HTML

프론트엔드가 무엇인지, 웹 페이지가 화면에 표시되는 과정, 그리고 화면의 내용과 구조를 만드는 **HTML**의 요소·속성·문서 구조·주요 태그를 정리했습니다.
스타일은 [CSS 기초](프론트엔드_CSS.md), 웹 서비스 전체 구조는 [웹 서비스 구조](웹서비스구조.md), 요청·응답은 [HTTP 기초](HTTP기초.md)를 참고하세요.

## 프론트엔드

사용자가 **브라우저에서 보고 상호작용하는** 웹 애플리케이션의 영역이다. 화면의 내용, 스타일, 사용자 동작에 따른 변화를 HTML, CSS, JavaScript로 표현한다.

| 기술 | 역할 |
|------|------|
| HTML | 제목, 이미지, 링크, 입력창 등 화면의 **내용과 구조** |
| CSS | 글자 색상, 크기, 여백, 배치 등 화면의 **스타일** |
| JavaScript | 클릭·입력 등의 **동작 처리**, 화면 내용 변경 |

```
게시글 목록 화면
├── HTML       : 버튼, 게시글 목록
├── CSS        : 글자 색상, 게시글 사이의 간격, 목록의 배치
└── JavaScript : 버튼을 눌렀을 때 API에서 게시글 불러오기
```

## 웹 페이지의 동작

- **브라우저**: 웹 문서와 데이터를 받아 화면에 표시하고 사용자 동작을 처리하는 프로그램
- **서버**: 브라우저의 요청을 받아 HTML, CSS, JavaScript, 이미지, 데이터 등을 응답하는 쪽
- 웹에서는 주로 HTTP/HTTPS로 요청과 응답을 주고받는다.

```
브라우저 ── 페이지 요청 ──→ 서버
브라우저 ←─ HTML 응답 ─── 서버
```

### 화면이 표시되는 과정

1. 브라우저가 HTML을 읽고 **문서의 구조**를 만든다.
2. CSS를 적용해 요소의 **모양과 배치**를 결정하고 화면에 표시한다.
3. JavaScript가 실행되면 문서의 내용을 바꾸거나 **추가 데이터를 요청**할 수 있다.

- 파일을 불러오고 코드를 실행하는 과정은 일부 **겹쳐서** 진행될 수 있다.

## HTML(HyperText Markup Language)

- **하이퍼텍스트**: 링크를 통해 다른 문서나 페이지로 연결되는 텍스트
- **마크업 언어**: 태그로 문서의 내용과 구조를 표현하는 언어

```html
<a href="https://www.python.org/">Python 공식 사이트</a>
```

- `<a>`는 링크, `href`는 이동할 주소, `Python 공식 사이트`는 화면에 표시되는 텍스트다.

### 요소(Element)의 구조

HTML 문서를 구성하는 기본 단위다. 보통 **시작 태그 + 내용 + 종료 태그**로 이루어지고, 시작 태그에 속성을 추가할 수 있다.

```html
<p class="title">HTML 기초</p>
```

| 구성 | 예 | 설명 |
|------|-----|------|
| 태그 | `<p>`, `</p>` | 단락의 시작과 끝 |
| 속성 | `class="title"` | 요소에 `title` 클래스를 지정 |
| 내용 | `HTML 기초` | 요소 안의 텍스트 |

- `<img>`, `<input>`, `<br>`처럼 **종료 태그가 없는** 요소도 있다.

### 속성(Attribute)

요소에 **추가 정보를 제공하거나 동작을 설정**한다. 링크의 이동 주소, 이미지 파일 위치, 입력창의 종류 등을 지정한다. 시작 태그 안에 `속성이름="값"` 형태로 쓰고, 여러 속성은 공백으로 구분한다.

```html
<a href="https://www.python.org/" id="python-link">Python 공식 사이트</a>
```

- `href`는 속성 이름, `https://www.python.org/`는 속성 값이다. 클릭하면 이 주소로 이동한다.
- `id="python-link"`는 요소에 이름을 붙여 CSS·JavaScript에서 찾을 수 있게 한다.
- 같은 `<a>`라도 `href` 값을 바꾸면 이동하는 주소가 달라진다.

## HTML 문서 구조

```html
<!DOCTYPE html>
<html lang="ko">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>게시글 목록</title>
  </head>
  <body>
    <h1>게시글 목록</h1>
    <p>게시글을 확인하세요.</p>
  </body>
</html>
```

| 요소 | 역할 |
|------|------|
| `<!DOCTYPE html>` | 브라우저가 문서를 **표준 모드**로 해석하도록 하는 선언 |
| `<html>` | 문서 전체를 감싸는 루트 요소. `lang="ko"`는 문서의 언어 |
| `<head>` | 문자 인코딩, 문서 제목, 스타일 연결 등 문서에 **관한 정보** |
| `<meta charset="UTF-8">` | 문자 인코딩 지정 |
| `<meta name="viewport" ...>` | 모바일 기기에서 화면 너비와 초기 배율 설정 |
| `<title>` | 브라우저 탭에 표시되는 문서 제목 |
| `<body>` | 페이지에 **표시할 내용** |

## 텍스트와 영역 태그

| 태그 | 설명 |
|------|------|
| `<h1>` ~ `<h6>` | 제목의 계층. `<h1>`이 가장 높은 수준 |
| `<p>` | 단락 |
| `<div>` | 여러 요소를 하나의 **영역**으로 묶음 |
| `<span>` | 문장이나 내용의 **일부**를 묶음 |
| `<ul>` | 순서 없는 목록 |
| `<li>` | 목록의 개별 항목 |

- **태그의 의미와 화면의 모양은 구분한다.** 제목의 글자 크기도 CSS로 바꿀 수 있다. 큰 글씨를 내려고 `<h1>`을 쓰는 것이 아니라, 제목이어서 `<h1>`을 쓴다.

```html
<div class="post">
  <h2>HTML 기초</h2>
  <p>작성자 : <span class="author">학습자</span></p>
  <ul>
    <li>태그와 요소</li>
    <li>문서 구조</li>
  </ul>
</div>
```

### 시맨틱 태그

내용이나 영역의 **의미**를 나타내는 태그다.

| 태그 | 의미 |
|------|------|
| `<header>` | 페이지나 영역의 머리말 |
| `<nav>` | 메뉴와 탐색 링크 |
| `<main>` | 페이지의 주요 내용 |
| `<article>` | 독립적인 글이나 콘텐츠 |
| `<footer>` | 페이지나 영역의 바닥글 |

```html
<header><h1>웹 학습 노트</h1></header>
<nav><a href="#html-note">HTML 기초</a></nav>
<main>
  <article id="html-note">
    <h2>HTML 기초</h2>
    <p>HTML은 웹 페이지의 내용과 구조를 나타낸다.</p>
  </article>
</main>
<footer>웹 기초 수업</footer>
```

## 링크와 이미지

- `<a>`: 다른 페이지나 문서의 특정 위치로 이동하는 링크
- `<img>`: 이미지 표시
- `href`: 링크의 목적지 주소 / `src`: 이미지 등 불러올 파일의 주소
- `alt`: 이미지의 의미를 전달하는 **대체 텍스트**

```html
<a href="https://www.python.org/about/">Python 소개</a>
<img src="https://www.python.org/static/img/python-logo.png" alt="Python 로고">
```

### 절대 주소와 상대 주소

- `https://www.python.org/about/`처럼 전체를 적은 것이 **절대 주소**다.
- `/about/`와 `about/`는 **상대 주소**이지만 기준 경로가 다르다.

기준 문서가 `https://example.com/docs/page.html`일 때:

| 상대 주소 | 기준 경로 | 해석된 주소 |
|-----------|-----------|-------------|
| `/about/` | 사이트 최상위 경로 | `https://example.com/about/` |
| `about/` | 현재 문서가 있는 경로 | `https://example.com/docs/about/` |

## 입력창과 버튼

- `<form>`: 입력한 값을 `action`에 지정한 주소로 전송
- `<input>`: 검색어 등 사용자가 입력할 값을 받음
- `<label>`: 입력 요소의 이름을 설명. `for` 값과 입력 요소의 `id` 값을 연결
- `<button>`: 클릭할 수 있는 버튼
- `placeholder`: 입력창이 비었을 때 보여 줄 안내 문구

```html
<form action="https://www.python.org/search/" method="get">
  <label for="search">검색어</label>
  <input id="search" name="q" type="text" placeholder="검색어를 입력하세요">
  <button type="submit">검색</button>
</form>
```

- `name="q"`는 서버로 전송할 데이터의 **키**를 지정한다.
- `method="get"`은 입력값을 **URL에 붙여** 전송한다. `python`을 검색하면 요청 주소가 `https://www.python.org/search/?q=python`이 된다. (→ [URL 구조](URL구조.md)의 쿼리 스트링)

## id와 class 속성

### id

- 요소에 **고유한** 식별자를 부여한다. 같은 문서 안에서 중복되지 않게 쓴다.
- CSS·JavaScript에서 특정 요소 하나를 찾을 때 쓴다.

```html
<h1 id="page-title">게시글 목록</h1>
```

### class

- 여러 요소에 **공통된 이름**을 부여한다. 같은 클래스를 여러 요소에 지정할 수 있고, 한 요소에 여러 클래스를 공백으로 구분해 지정할 수 있다.
- CSS에서 공통 스타일을 적용하거나 JavaScript에서 여러 요소를 찾을 때 쓴다.

```html
<p class="title">HTML 기초</p>
<p class="title featured">CSS 선택자</p>
```

- 두 요소 모두 `title` 클래스를 가지고, 두 번째는 `title`과 `featured`를 함께 가진다.
- **클래스 이름만 지정한다고 모양이 자동으로 바뀌지는 않는다.** 해당 클래스에 적용할 CSS가 필요하다.

## 요소 중첩과 관계

요소 안에 다른 요소를 넣어 문서 구조를 표현한다.

| 관계 | 설명 |
|------|------|
| 부모 | 바로 바깥의 요소 |
| 자식 | 바로 안쪽의 요소 |
| 형제 | 같은 부모를 가진 요소들 |
| 자손 | 안쪽에 포함된 **모든 단계**의 요소 |

```html
<ul id="post-list">
  <li id="post-1" class="post">
    <a class="title featured" href="#post-1">HTML 기초</a>
    <div class="details">
      <p class="body">HTML은 웹 페이지의 내용과 구조를 나타낸다.</p>
    </div>
  </li>
  <li id="post-2" class="post">
    <a class="title" href="#post-2">CSS 선택자</a>
    <div class="details">
      <p class="body">CSS 선택자로 스타일을 적용할 요소를 찾는다.</p>
    </div>
  </li>
</ul>
```

- `<ul>`의 자식은 두 `<li>`, 각 `<li>`의 자식은 `<a>`와 `<div>`다.
- `<p>`는 `<div>`의 **자식**이자 `<li>`의 **자손**이다.
- 반복되는 게시글은 같은 구조와 클래스를 쓰고 제목·본문만 다르다.
- `href="#post-1"`은 같은 문서에서 `id="post-1"`인 위치로 이동한다.

## HTML 주석

```html
<!-- 게시글 목록 영역 -->
<ul id="post-list"></ul>
```

- 화면에는 표시되지 않지만 HTML 소스와 개발자 도구에서는 **누구나 볼 수 있다.** 비밀 정보를 적지 않는다.

## 브라우저 개발자 도구

웹 페이지의 HTML, 스타일, 네트워크 등을 분석하는 도구다. 브라우저에 내장되어 있고 `F12` 또는 `Ctrl + Shift + I`로 연다.

- **요소(Elements)**: HTML 구조와 CSS 스타일을 실시간으로 분석·수정한다. 왼쪽 상단의 **검사 요소 선택** 버튼으로 화면의 특정 요소를 골라 볼 수 있다.
- **콘솔(Console)**: JavaScript 코드를 실행하고 결과를 확인한다. 오류와 경고를 보고 버그를 추적한다.

## 정리

- 프론트엔드는 HTML(내용·구조) + CSS(스타일) + JavaScript(동작)로 이루어진다.
- 브라우저는 HTML을 읽어 구조를 만들고, CSS를 입히고, JavaScript로 변경·추가 요청을 한다.
- 요소 = 태그 + 속성 + 내용. 속성(`href`, `src`, `id`, `class` 등)이 요소의 동작과 식별을 정한다.
- 태그는 **모양이 아니라 의미**로 고른다. 시맨틱 태그와 `alt` 같은 속성은 구조와 접근성을 위한 것이다.
- `id`는 하나만, `class`는 여러 요소에 공통으로. 둘 다 CSS·JavaScript가 요소를 찾는 손잡이다.
