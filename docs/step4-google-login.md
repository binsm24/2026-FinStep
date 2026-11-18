# 4단계: 구글 로그인과 사용자별 진단 결과 보관함

## 구현 상태

- Google Identity Services 로그인 버튼과 서버의 Google ID 토큰 검증을 연결했다. 사용자 식별에는 이메일 대신 Google `sub`를 사용한다.
- 로그인 세션은 HttpOnly 쿠키로 전달하고, 서버에는 세션 토큰의 해시를 보관한다. 로그인 nonce와 Origin 검증으로 재사용 및 교차 사이트 요청을 방어한다.
- 완료된 진단 화면에서 저장 버튼을 누르면 로그인한 사용자의 보관함에 저장된다. 로그인 전에 완료한 진단도 같은 브라우저에서 로그인한 뒤 저장할 수 있다. 자동 저장은 하지 않는다.
- 목록 및 상세 조회는 해당 사용자에게만 허용된다. 점수와 진단 내용은 서버 결과를 저장하며 클라이언트에서 전달한 점수를 신뢰하지 않는다.
- 기본 저장소는 `backend/storage/finstep.db`이다. 저장된 결과와 로그인 정보는 서버 재시작 후에도 유지된다. 진행 중인 시뮬레이션은 메모리에 있어 재시작 시 사라진다.
- OAuth 클라이언트 ID가 없으면 로그인 준비 중 안내를 표시한다. 비회원 학습과 시뮬레이션은 이용할 수 있다.

## 사용자가 완료할 Google 설정

1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트를 선택하거나 생성한다.
2. Google Auth Platform에서 앱 이름, 지원 이메일, 대상 사용자 등 필요한 동의 화면 설정을 완료한다. 테스트 모드에서 테스트 사용자를 요구하면 사용할 Google 계정을 등록한다.
3. OAuth 클라이언트를 만들고 애플리케이션 유형을 **웹 애플리케이션**으로 선택한다.
4. 승인된 JavaScript 원본에 `http://localhost`와 `http://localhost:5173`을 추가한다. 개발 중에는 `http://localhost:5173` 주소로 일관되게 접속한다.
5. 생성된 `…apps.googleusercontent.com` 형식의 클라이언트 ID를 기존 `backend/.env`에 아래와 같이 추가한다. 기존 Gemini 설정은 유지한다.

```dotenv
GOOGLE_CLIENT_ID=발급받은_ID.apps.googleusercontent.com
FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
COOKIE_SECURE=false
```

현재 구현은 팝업의 JavaScript 콜백으로 ID 토큰을 받으므로 리디렉션 URI나 클라이언트 보안 비밀번호는 필요하지 않다. 프론트엔드에 별도 클라이언트 ID를 넣을 필요도 없다.

## 실행과 실제 로그인 확인

백엔드 폴더에서:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

프론트엔드 폴더의 별도 터미널에서:

```powershell
npm.cmd run dev -- --host 127.0.0.1
```

환경 변수 변경 후에는 백엔드를 재시작한다. `http://localhost:5173`에서 로그인, 진단 완료, 결과 저장, 보관함 조회 순서로 확인한다. 로그아웃 후 다른 계정으로 로그인했을 때 이전 계정의 결과가 보이지 않는지도 확인한다.

## 검증 결과와 남은 범위

- 백엔드 자동 테스트 39개 통과: 인증, 결과 소유권, 저장 지속성, 시나리오 분기, 학습 데이터 포함.
- 프론트엔드 린트와 프로덕션 빌드 통과.
- 인증 테스트는 테스트용 RSA 키로 서명한 토큰과 격리된 SQLite DB를 사용한다. 실제 Google 계정 로그인은 클라이언트 ID가 아직 없어 검증하지 못했다.
- 개발 서버 실행 및 브라우저 화면 검증은 최종 완료되지 않았다. 실행 명령 자체가 상시 서버 운영을 의미하지는 않는다.
- 5단계 PC·반응형 UI 개편과 6단계 배포는 진행하지 않았다.

배포 시에는 HTTPS에서 `COOKIE_SECURE=true`를 사용하고 실제 원본을 Google 콘솔과 `FRONTEND_ORIGINS`에 등록해야 한다. 현재 개발 서버는 `/api`를 백엔드로 프록시한다. 운영에서도 같은 사이트에서 API를 제공하는 구성을 준비해야 하며, 서로 다른 사이트에 프론트엔드와 API를 단순히 분리하면 현재 쿠키 설정으로 로그인 유지가 안 될 수 있다. PostgreSQL 연결 설정은 지원하지만 실제 PostgreSQL 서버 연결은 아직 검증하지 않았다.

공식 참고: [클라이언트 ID 생성](https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid), [서버의 ID 토큰 검증](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token), [JavaScript API](https://developers.google.com/identity/gsi/web/reference/js-reference).
