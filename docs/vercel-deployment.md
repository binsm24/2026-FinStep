# Vercel + Neon 배포

## 구성

- 저장소 루트를 Vercel 프로젝트 Root Directory로 사용한다. Framework Preset은 Other이다.
- `vercel.json`에서 frontend의 설치·빌드 및 `frontend/dist` 출력을 설정한다.
- `/api/*`와 `/health`는 `api/index.py`의 FastAPI 함수로 연결한다. 정적 파일과 SPA 페이지는 Vercel CDN에서 제공한다.
- 시뮬레이션 상태, 로그인 세션, 결과를 모두 Neon PostgreSQL에 저장한다. 요청 간 메모리 유지에 의존하지 않는다.
- 같은 답변의 재시도는 저장한 결과를 반환하고, 동시 변경은 DB 버전 검사로 중복 진행을 방지한다.
- Vercel에서 DATABASE_URL이 없으면 시작을 실패시켜 임시 SQLite에 결과가 저장되는 일을 방지한다.

## 계정 설정 및 배포

1. Neon Free 프로젝트를 생성하고 Connect에서 pooling이 켜진 PostgreSQL 연결 문자열을 복사한다. `sslmode=require`를 유지한다.
2. Vercel에서 GitHub 저장소 `binsm24/2026-FinStep`을 가져온다. 배포 변경이 포함된 브랜치를 선택한다.
3. 아래 환경 변수를 설정한다. DB 비밀번호와 Gemini 키는 Git 저장소에 넣지 않는다.
4. 배포가 Ready가 되면 `/health`, `/api/auth/me`, 학습 화면, 시뮬레이션을 확인한다.
5. Google Cloud OAuth 웹 클라이언트의 승인된 JavaScript 원본에 실제 운영 HTTPS 주소를 추가한다. 리디렉션 URI와 client secret은 현재 로그인 방식에 필요하지 않다.
6. 실제 Google 계정으로 로그인하고 결과 저장·보관함·로그아웃을 확인한다.

| 환경 변수 | 값 |
| --- | --- |
| `DATABASE_URL` | Neon pooled 연결 문자열 |
| `COOKIE_SECURE` | `true` |
| `FRONTEND_ORIGINS` | 실제 운영 원본 `https://프로젝트.vercel.app`; 커스텀 도메인은 쉼표로 추가 |
| `GEMINI_API_KEY` | Gemini API 키 |
| `GEMINI_MODEL` | 계정에서 사용 가능한 모델, 예: `gemini-2.5-flash` |
| `GOOGLE_CLIENT_ID` | Google OAuth 웹 클라이언트 공개 ID |

`VERCEL_URL`과 `VERCEL_PROJECT_PRODUCTION_URL`은 서버에서 신뢰할 원본으로 자동 추가한다.
`FRONTEND_DIST`와 `VITE_API_BASE_URL`은 Vercel에서 설정하지 않는다.
운영 DB 자격 증명을 신뢰하지 않는 Preview 브랜치에 공유하지 않는다.

## 검증 명령

```powershell
cd backend
.\.venv\Scripts\python.exe -m unittest discover -p 'test_*.py'
cd ../frontend
npm.cmd run lint
npm.cmd run build
node --test tests/quiz.test.mjs
```

`backend/test_gemini.py`는 직접 실행할 때만 실제 Gemini API를 호출한다.
일반 테스트는 외부 API 없이 격리된 SQLite를 사용하며 실제 Neon 연결 및 Vercel 실행은 배포 후 별도로 확인한다.

## 운영 범위

Neon 무료 사용량을 대시보드에서 확인한다. 휴면 DB는 다음 요청에서 자동 재개되므로 첫 요청이 느려질 수 있다.
저장된 시뮬레이션은 자동 삭제하지 않으므로 사용량 증가 시 보관 기간과 정리 정책을 추가해야 한다.
현재 스키마는 최초 시작 시 생성하며 기존 테이블의 구조 변경을 자동 마이그레이션하지 않는다.

참고: [Vercel Python](https://vercel.com/docs/functions/runtimes/python), [Vercel 설정](https://vercel.com/docs/project-configuration/vercel-json), [Neon 연결](https://neon.com/docs/connect/connect-from-any-app).
