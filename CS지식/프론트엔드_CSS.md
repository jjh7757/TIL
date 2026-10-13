# CSS 기초

HTML 요소의 색상, 글자 크기, 여백, 배치 등을 지정하는 스타일 언어 **CSS(Cascading Style Sheets)**의 기본 구조, 박스 모델, 선택자, 적용 방법을 정리했습니다.
요소·속성·`id`/`class` 등 HTML 쪽 개념은 [프론트엔드와 HTML](프론트엔드_HTML.md)을 참고하세요.

- **선택자**로 적용할 요소를 고르고, **속성과 값**으로 스타일을 지정한다.

## 기본 구조

```none
선택자 {
  속성: 값;
  속성: 값;
}
```

```css
.body {
  color: blue;
  font-size: 20px;
}
```

- `.body`는 선택자로, `body` 클래스를 가진 요소를 고른다.
- `{ }` 안에 선택한 요소에 적용할 스타일을 쓴다.
- `color`, `font-size`는 속성이고 `blue`, `20px`는 각 속성의 값이다.
- 속성과 값은 `:`으로 구분하고 각 선언은 `;`으로 끝낸다.
- `class="body"`는 **HTML 속성**이고, `color`·`font-size`는 **CSS 속성**이다. 이름이 같은 `body`가 나와도 서로 다른 층위다.

## 색상과 여백, 박스 모델

```css
.post {
  background-color: #f5f5f5;
  border: 1px solid #cccccc;
  padding: 16px;
  margin: 12px;
}
```

| 속성 | 설명 |
|------|------|
| `background-color` | 배경색 |
| `border` | 테두리 |
| `padding` | 내용과 테두리 사이의 **안쪽** 여백 |
| `margin` | 테두리 **바깥쪽** 여백 |

요소의 영역을 **내용 → 안쪽 여백(padding) → 테두리(border) → 바깥쪽 여백(margin)**으로 구분하는 방식을 **박스 모델(Box Model)**이라고 한다.

## 기본 선택자

| 선택자 | 표기 | 설명 |
|--------|------|------|
| 태그 | `a` | 모든 `<a>` 요소 |
| 클래스 | `.body` | `body` 클래스를 가진 요소 (앞에 `.`) |
| 아이디 | `#post-list` | 해당 아이디를 가진 요소 (앞에 `#`) |
| 속성 | `button[type="button"]` | `type`이 `button`인 `<button>` |

```css
a {
  color: navy;
}

.body {
  font-weight: bold;
}

#post-list {
  padding: 16px;
}

button[type="button"] {
  border: 1px solid gray;
}
```

클래스 선택자를 **공백 없이** 이어 쓰면 두 클래스를 **모두** 가진 요소만 고른다.

```css
.title.featured {
  color: #b42318;
}
```

## 자손 선택자와 자식 선택자

게시글 하나의 구조:

```html
<li id="post-1" class="post">
  <a class="title" href="#post-1">HTML 기초</a>
  <div class="details">
    <p class="body">HTML은 웹 페이지의 내용과 구조를 나타낸다.</p>
  </div>
</li>
```

```
li.post
├── a.title
└── div.details
    └── p.body
```

- **자손 선택자**: 공백으로 연결. 안쪽의 **모든 단계**에서 조건에 맞는 요소를 고른다.
- **자식 선택자**: `>`로 연결. **바로 아래 단계**에서만 고른다.

```css
.post .body {
  color: blue;
}

.post > .title {
  font-weight: bold;
}
```

- `.post .body`: 각 게시글 안의 본문 요소를 고른다. (`.details` 안에 있어도 자손이므로 선택됨)
- `.post > .title`: 각 게시글 **바로 아래**의 제목 링크를 고른다.
- `.post > .body`는 **선택되는 요소가 없다.** 본문이 `.details` 안에 있어 `.post`의 자식이 아니라 자손이기 때문이다.

## CSS 적용 방법

| 방법 | 위치 | 예 |
|------|------|-----|
| 인라인 스타일 | 요소의 `style` 속성 | `<p style="color: blue;">...</p>` |
| 내부 스타일 | `<head>` 안의 `<style>` | 아래 |
| 외부 스타일 | 별도 CSS 파일을 `<link>`로 연결 | 아래 |

```html
<!-- 내부 스타일 -->
<style>
  .body {
    color: blue;
  }
</style>

<!-- 외부 스타일 -->
<link rel="stylesheet" href="posts.css">
```

- 공통 예제는 외부 스타일을 쓰며, `posts.html`에서 `posts.css`를 연결한다.
- 외부 스타일은 CSS를 HTML과 분리해 여러 페이지에서 재사용하고 관리하기 쉽다.

## 정리

- CSS는 `선택자 { 속성: 값; }` 구조다. 먼저 **누구에게** 적용할지 고르고, **무엇을** 바꿀지 쓴다.
- 박스 모델: 내용 → `padding` → `border` → `margin`.
- 선택자: 태그, `.클래스`, `#아이디`, `[속성]`. 공백은 자손, `>`는 자식, 이어 쓰면 "모두 가진" 요소.
- 적용은 인라인 / 내부 / 외부 세 가지이고, 외부 CSS 파일 연결이 기본이다.
