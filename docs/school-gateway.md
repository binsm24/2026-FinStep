# 학교 Gateway 연결

FinStep의 기본 AI 연결은 학교 BAZE Gateway입니다. EasyView와 같은 Chat Completions 방식이며, 행동 추출과 승인된 대사 선택에만 사용합니다. 분기·종료 판정, 원문 근거 및 JSON 구조 검증, 오류 시 기존 대체 처리는 유지합니다. Google 직접 API로 자동 재시도하지 않습니다.

## 필요한 설정

기존 `backend/.env`의 로그인·DB 설정을 유지하면서 아래 항목을 추가합니다. 키는 학교 개발자 페이지에서 발급받아 직접 입력하며 프론트엔드나 Git에 넣지 않습니다. EasyView의 키는 자동 복사하지 않습니다.

```dotenv
LLM_PROVIDER=gateway
BAZE_API_KEY=학교에서_발급받은_키
BAZE_BASE_URL=https://factchat-cloud.mindlogic.ai/v1/gateway
BAZE_MODEL=gemini-3.8-flash
```

학교 문서에 명시된 Gemini 3.8 Flash ID는 `gemini-3.8-flash`입니다. 실제 사용 가능 여부는 계정의 모델 목록으로 확인합니다. 설정 변경 후 백엔드를 재시작하세요. 새 패키지 설치는 필요하지 않습니다(`httpx`는 기존 의존성).

## 수동 연결 확인

프로젝트 루트에서 실행합니다. 첫 명령은 모델 목록만 조회하며, 두 번째는 짧은 테스트 답변을 학교 API로 전송하므로 이용량이 발생할 수 있습니다. 키나 실제 사용자 대화는 출력하지 않습니다.

```powershell
.\backend\.venv\Scripts\python.exe backend/check_gateway.py --list-models
.\backend\.venv\Scripts\python.exe backend/check_gateway.py
```

이후 브라우저에서 보이스피싱 시나리오에 다음을 순서대로 입력하여 다음 상황과 결과를 확인합니다.

1. `개인정보를 제공하지 않는다. 송금하지 않는다. 공식 기관에 확인한다.`
2. `전화를 끊는다.`

네트워크·인증·모델·형식 오류에서는 응답을 임의로 신뢰하지 않고 기존 규칙 기반 대체 처리로 돌아갑니다. 모호한 답변은 분석 불가 또는 재질문이 될 수 있습니다. 자동 테스트는 모의 Gateway 응답으로 실행되며 실제 서비스 품질과 지연시간 검증은 별도입니다.

## 배포

Vercel 프로젝트 Settings → Environment Variables에 위 네 항목을 등록하고 해당 환경을 재배포합니다. 로컬 `.env`만 바꿔서는 배포 사이트에 적용되지 않습니다. 기존 Neon 데이터베이스의 `DATABASE_URL`은 유지합니다.

Google 로그인용 `GOOGLE_CLIENT_ID`와 DB·쿠키 설정은 그대로 유지합니다. 기존 `GEMINI_API_KEY`는 `LLM_PROVIDER=gateway`일 때 사용하지 않습니다.

## Google 직접 API로 전환

`LLM_PROVIDER=gemini`, `GEMINI_API_KEY`, `GEMINI_MODEL`을 설정하고 재시작/재배포합니다. 학교 키를 Google 직접 API 키로 사용하면 안 됩니다.

## 참고

- [학교 모델 목록](https://docs.mindlogic.ai/docs/sookmyung/api-gateway/getting-started/models)
- [학교 Chat Completions 및 JSON Schema](https://docs.mindlogic.ai/docs/sookmyung/api-gateway/reference/chat-completions)
