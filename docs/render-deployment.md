# Render 배포

## 구성

저장소 루트의 `render.yaml`은 Docker 웹 서비스와 PostgreSQL을 생성한다.
Docker 빌드에서 React를 빌드하고 FastAPI가 정적 파일과 API를 같은 HTTPS 주소에서 제공한다.
`/archive` 등 페이지 새로고침을 지원하며, 없는 API와 정적 파일은 404를 반환한다.
로그인과 진단 결과는 PostgreSQL에 저장된다. 로컬 SQLite 파일은 업로드하지 않는다.
진행 중 시뮬레이션은 메모리에 있으므로 서버 재시작 시 초기화된다. 워커와 서비스 인스턴스는 각각 하나로 유지한다.

## 배포 순서

1. 배포할 기능과 배포 파일을 GitHub `binsm24/2026-FinStep` 저장소에 커밋·푸시한다. 현재 작업 브랜치는 `feature/economic-learning`이다. 로컬 파일만 변경하면 Render에 반영되지 않는다.
2. Render 대시보드에서 **New → Blueprint**로 저장소와 실제 푸시한 브랜치를 선택한다. Blueprint 경로는 `render.yaml`, Root Directory는 비워 둔다.
3. 생성 리소스와 요금제를 확인한다. 기본 파일은 웹 서비스와 DB 모두 `free`이다.
4. `GEMINI_API_KEY`와 `GOOGLE_CLIENT_ID`를 Render 환경 변수에 입력한다. 비밀 키를 GitHub, Dockerfile, 프론트엔드에 넣지 않는다. Google ID가 아직 없으면 빈 문자열로 두며 로그인은 비활성화된다. Dashboard가 빈 값을 허용하지 않으면 해당 sync 항목을 제거한 후 나중에 Environment에서 추가한다.
5. Blueprint를 배포하고 웹 서비스가 **Live**가 될 때까지 로그를 확인한다. 실제 서비스 주소는 Dashboard에서 복사한다.
6. Google Cloud OAuth 웹 클라이언트의 **승인된 JavaScript 원본**에 실제 `https://…onrender.com` 주소를 추가한다. 경로나 마지막 `/`는 넣지 않는다. 현재 로그인 방식에는 리디렉션 URI와 client secret이 필요하지 않다.
7. 홈페이지, `/health`, `/api/auth/me`, 학습, 시뮬레이션, 로그인, 결과 저장과 보관함 새로고침을 확인한다. 재배포 후에도 저장 결과가 남는지 확인한다.

## 환경 변수

| 이름 | 설정 |
| --- | --- |
| `DATABASE_URL` | Blueprint가 PostgreSQL 내부 연결 문자열을 연결 |
| `COOKIE_SECURE` | `true` |
| `FRONTEND_ORIGINS` | 기본은 빈 문자열. Render의 `RENDER_EXTERNAL_URL`을 코드가 자동 허용. 사용자 도메인은 여기에 HTTPS 원본을 쉼표로 추가 |
| `GEMINI_API_KEY` | Render에서 직접 입력 |
| `GEMINI_MODEL` | 기본 `gemini-2.5-flash`; 계정에서 사용할 수 있는 모델로 변경 가능 |
| `GOOGLE_CLIENT_ID` | Google OAuth 웹 클라이언트의 공개 ID |
| `FRONTEND_DIST` | Docker 이미지에서 `/app/frontend/dist` 설정 |

`VITE_API_BASE_URL`은 설정하지 않는다. 프론트엔드는 같은 주소의 `/api`를 호출한다.
로컬 개발은 기존 Vite 프록시와 FastAPI 실행 방식을 그대로 사용한다.

## 무료 구성의 제약

무료 웹 서비스는 15분 동안 요청이 없으면 중지되며 첫 접속 시 기동 시간이 필요하다.
무료 PostgreSQL은 생성 후 30일에 만료되며 워크스페이스당 하나만 생성할 수 있다.
만료 뒤 14일의 유예 기간이 지나면 DB 데이터가 삭제된다. 장기 운영 전에는 유료 DB 전환이나 데이터 이전이 필요하다.
요금제 변경은 사용자 선택 후 진행한다. 기존 무료 DB가 있으면 새 DB 생성 대신 연결 구성을 변경해야 한다.

공식 문서: [Blueprint 설정](https://render.com/docs/blueprint-spec), [무료 구성 제약](https://render.com/docs/free), [배포 동작](https://render.com/docs/deploys).

## 로컬 컨테이너 확인

Docker Desktop의 Linux 엔진을 실행한 뒤 저장소 루트에서:

```powershell
docker build -t finstep .
docker run --rm -p 10000:10000 --env-file backend/.env -e FRONTEND_ORIGINS=http://localhost:10000 -e COOKIE_SECURE=false finstep
```

`http://localhost:10000`에서 확인한다. 이 임시 컨테이너에서 기본 SQLite로 저장한 데이터는 컨테이너 제거 시 사라진다.
