# RSS 기초

RSS(Really Simple Syndication)는 웹사이트의 새 글·업데이트를 표준화된 XML 형식으로 배포하는 방식입니다. 블로그·뉴스 사이트가 `/feed`, `/rss.xml` 같은 경로에 이 파일을 두면, RSS 리더가 주기적으로 가져와 새 글 여부를 확인합니다.

## 동작 방식

1. 사이트가 `<rss>`(또는 Atom의 `<feed>`) 루트 아래 `<item>`(글) 목록을 XML로 제공
2. 각 `<item>`에 제목, 링크, 요약/본문, 발행일 등이 들어있음
3. 리더 앱(Feedly, Inoreader 등)이나 자동화 툴이 이 URL을 주기적으로 폴링해서 새 항목만 골라 보여줌

## 예시 구조

```xml
<rss version="2.0">
  <channel>
    <title>내 블로그</title>
    <link>https://example.com</link>
    <item>
      <title>글 제목</title>
      <link>https://example.com/post/1</link>
      <pubDate>Tue, 04 Aug 2026 10:00:00 +0900</pubDate>
      <description>요약 내용</description>
    </item>
  </channel>
</rss>
```

## 왜 아직도 쓰이는가

| 특징 | 설명 |
|---|---|
| 알고리즘 없음 | 구독한 순서·시간순 그대로 받아볼 수 있음 (플랫폼 추천 알고리즘에 의존하지 않음) |
| 인증 불필요 | [API 키](API기초.md) 없이 공개 URL만으로 구독 가능 |
| 자동화 연계 | [n8n](../n8n실습/n8n.md) 같은 툴의 RSS Trigger 노드로 새 글 감지 → 요약 → 알림 같은 워크플로우를 만들 수 있음 |

## 관련 개념

- **Atom**: RSS와 목적은 같은 경쟁 규격 (더 엄격한 XML 스펙)
- **웹훅(Webhook)과의 차이**: RSS는 구독자가 주기적으로 가져오는(pull) 방식이고, 웹훅은 서버가 이벤트 발생 시 바로 보내주는(push) 방식

## 참고

- [API 기초](API기초.md)
- [n8n](../n8n실습/n8n.md)
