FROM python:3.12-alpine

WORKDIR /app
COPY app.py .

# 빌드 시점에 커밋 SHA를 심어 배포가 실제로 갱신됐는지 눈으로 확인한다
ARG GIT_SHA=unknown
ENV GIT_SHA=$GIT_SHA

EXPOSE 3000
CMD ["python", "app.py"]
