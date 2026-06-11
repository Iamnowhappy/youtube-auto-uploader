# YouTube 자동 업로드 시스템 셋업 가이드

## 📁 파일 구성
```
youtube_auto_uploader/
├── upload.py                          # 메인 업로드 스크립트
├── get_youtube_token.py               # 최초 토큰 발급 (로컬 1회만)
├── requirements.txt                   # 필요 라이브러리
└── .github/
    └── workflows/
        └── auto_upload.yml            # GitHub Actions 설정
```

---

## 🔧 STEP 1: Google Cloud Console 설정

### 1-1. 프로젝트 생성
1. https://console.cloud.google.com 접속
2. 상단 프로젝트 선택 → "새 프로젝트" → 이름: `youtube-uploader`

### 1-2. YouTube Data API 활성화
1. "API 및 서비스" → "라이브러리"
2. "YouTube Data API v3" 검색 → "사용 설정"

### 1-3. Google Sheets API 활성화
1. "API 및 서비스" → "라이브러리"
2. "Google Sheets API" 검색 → "사용 설정"

### 1-4. OAuth 2.0 클라이언트 ID 생성 (YouTube용)
1. "API 및 서비스" → "사용자 인증 정보"
2. "사용자 인증 정보 만들기" → "OAuth 클라이언트 ID"
3. 애플리케이션 유형: **데스크톱 앱**
4. 이름: `youtube-uploader`
5. 생성 후 **JSON 다운로드** → `client_secret.json`으로 저장

### 1-5. 서비스 계정 생성 (Google Sheets용)
1. "사용자 인증 정보 만들기" → "서비스 계정"
2. 이름: `sheets-reader`
3. 생성 후 해당 서비스 계정 클릭
4. "키" 탭 → "키 추가" → "새 키 만들기" → JSON 선택
5. 다운로드된 JSON 파일 내용을 보관 (나중에 GitHub Secret에 등록)

---

## 🔧 STEP 2: 구글 시트 설정

### 2-1. 시트 구조 만들기
구글 시트 새로 만들고 1행에 헤더 입력:
```
A1: 파일명
B1: 제목
C1: 설명
D1: 해시태그
E1: 상태
F1: YouTube링크
```

### 2-2. 서비스 계정 권한 부여
1. 서비스 계정 이메일 복사 (예: `sheets-reader@프로젝트.iam.gserviceaccount.com`)
2. 구글 시트 → 공유 → 해당 이메일 → "편집자" 권한 부여

### 2-3. 시트 ID 확인
URL에서 복사: `https://docs.google.com/spreadsheets/d/[여기가 시트ID]/edit`

---

## 🔧 STEP 3: 드롭박스 API 토큰 발급

1. https://www.dropbox.com/developers/apps 접속
2. "Create app" 클릭
3. API: Scoped access / Type: Full Dropbox / 이름: `youtube-uploader`
4. "Permissions" 탭 → `files.content.read` 체크
5. "Settings" 탭 → "Generate access token" 클릭
6. 발급된 토큰 복사 보관

---

## 🔧 STEP 4: YouTube OAuth 토큰 발급 (로컬 PC에서 1회)

로컬 PC에서 실행:
```bash
# 라이브러리 설치
pip install google-auth-oauthlib google-api-python-client

# client_secret.json을 같은 폴더에 놓고 실행
python get_youtube_token.py
```
→ 브라우저 열리면 YouTube 채널 계정으로 로그인
→ `youtube_token.json` 파일 생성됨
→ 파일 내용 전체 복사 (GitHub Secret에 등록)

---

## 🔧 STEP 5: GitHub 레포 생성 및 Secrets 등록

### 5-1. GitHub 레포 생성
1. https://github.com/new
2. 레포 이름: `youtube-auto-uploader`
3. Private으로 생성 (토큰 보안)

### 5-2. 파일 업로드
레포에 아래 파일들 업로드:
- `upload.py`
- `requirements.txt`
- `.github/workflows/auto_upload.yml`

### 5-3. GitHub Secrets 등록
레포 → Settings → Secrets and variables → Actions → "New repository secret"

| Secret 이름 | 값 |
|---|---|
| `DROPBOX_TOKEN` | 드롭박스 액세스 토큰 |
| `DROPBOX_FOLDER` | `/youtube_videos` (드롭박스 폴더 경로) |
| `GOOGLE_SHEET_ID` | 구글 시트 ID |
| `GOOGLE_SHEET_NAME` | `Sheet1` (시트 탭 이름) |
| `YOUTUBE_TOKEN_JSON` | youtube_token.json 파일 내용 전체 |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | 서비스 계정 JSON 파일 내용 전체 |

---

## 🔧 STEP 6: 드롭박스 폴더 & 시트 데이터 준비

### 드롭박스
- `/youtube_videos/` 폴더 생성
- 영상 파일 업로드 (파일명 = 구글 시트 A열과 동일해야 함)

### 구글 시트 데이터 예시
```
파일명          | 제목              | 설명              | 해시태그              | 상태
video_001.mp4  | 우주의 크기는?    | 우주에 대한 놀...  | #shorts #우주 #과학  | 대기중
video_002.mp4  | 블랙홀 진실       | 블랙홀에 들어...   | #shorts #블랙홀      | 대기중
```

---

## ✅ 테스트

GitHub 레포 → Actions 탭 → "YouTube 자동 업로드" → "Run workflow" 클릭

정상 작동하면:
- 구글 시트 첫 번째 "대기중" 영상이 YouTube에 업로드됨
- 시트 E열이 "완료"로 변경
- F열에 YouTube 링크 기록

---

## ⏰ 자동 실행 시간 변경

`auto_upload.yml`에서 cron 수정:
```yaml
# 매일 오전 9시 (한국시간)
- cron: "0 0 * * *"

# 매일 오후 7시 (한국시간)
- cron: "0 10 * * *"

# 매일 정오 (한국시간)
- cron: "0 3 * * *"
```

---

## ⚠️ 주의사항

1. **YouTube API 할당량**: 하루 10,000 유닛. 업로드 1회 = 약 1,600 유닛. 하루 6개까지 가능하지만 **하루 1개만** 올리는 게 알고리즘에 유리!
2. **refresh_token 만료**: 6개월간 미사용 시 만료됨. STEP 4를 다시 실행하면 됨.
3. **드롭박스 토큰**: Short-lived token은 4시간 후 만료. 발급 시 "No expiration" 선택할 것.

---

## 🆘 문제 발생 시

GitHub → Actions 탭 → 해당 워크플로우 클릭 → 로그 확인
