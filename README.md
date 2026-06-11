# 📺 YouTube 자동화 관리자

> 젠스파크/로컬 영상 → 드롭박스 → YouTube 까지 원클릭 자동화

---

## 📁 파일 구성

```
5_youtube_auto_uploader/
│
├── 실행.bat                    ← ✅ 여기서 시작! 더블클릭
├── youtube_manager_ui.py       ← UI 메인 (실행.bat 이 자동 호출)
├── genspark_to_dropbox.py      ← 드롭박스 업로드 + 예약 배정 엔진
├── upload.py                   ← GitHub Actions 전용 (건드리지 말 것)
│
├── config.json                 ← 설정 저장 (UI에서 자동 생성)
├── youtube_token.json          ← YouTube OAuth 토큰 (1회 발급)
├── client_secret.json          ← YouTube OAuth 키
├── make-drive-upload-xxx.json  ← 구글 서비스 계정 키
│
└── .github/
    └── workflows/
        └── upload.yml          ← GitHub Actions 스케줄 (매시간 실행)
```

---

## 🚀 처음 설치 (최초 1회)

### 1. 라이브러리 설치

```bash
C:\Users\gichang\AppData\Local\Programs\Python\Python312\python.exe -m pip install ^
  requests gspread google-auth google-api-python-client dropbox
```

> `실행.bat` 더블클릭 시 자동으로 설치됩니다.

### 2. ⚙️ 설정 탭에서 키 입력 후 저장

| 항목 | 내용 |
|---|---|
| 서비스 계정 JSON | `make-drive-upload-xxx.json` 파일 경로 |
| 구글 시트 ID | `1VGHH_xkbNWKfzMLWIXeJRM3GHvjVEm_nvZM8FEhTK40` |
| 시트명 | `숏츠시트` |
| Dropbox App Key | `tbcj51lqb9ka0ec` |
| Dropbox App Secret | 드롭박스 앱 콘솔에서 확인 |
| Dropbox Refresh Token | `N2HVAUZx...` |

---

## 💡 사용 방법 (3가지 모드)

### 모드 A — 📅 예약 업로드 (추천)

> 유튜브 스팸 감지 방지. 하루 17:00 / 19:00 두 번씩 자동 분산 업로드.

```
실행.bat 더블클릭
→ [📅 예약 업로드] 탭
→ 영상 파일 선택
→ "구글 시트에 행 추가" 클릭
→ "드롭박스 업로드 + 예약 배정 실행" 클릭
→ 끝! GitHub Actions 가 예약 시간에 자동 YouTube 업로드
```

### 모드 B — ⚡ 즉시 드롭박스 업로드만

> YouTube 업로드는 나중에 예약으로. 드롭박스에만 먼저 올릴 때.

```
[⚡ 즉시 업로드] 탭
→ 파일 선택
→ "📦 드롭박스만 업로드" 클릭
→ D열에 드롭박스 URL 기록됨
→ E열 "업로드전" 상태로 예약 대기
```

### 모드 C — ⚡ 즉시 YouTube 업로드

> 지금 당장 바로 YouTube에 올리고 싶을 때.

```
[⚡ 즉시 업로드] 탭
→ 파일 선택
→ 채널 / 제목 / 설명 입력
→ "🚀 드롭박스 → YouTube 즉시 업로드" 클릭
→ 확인 팝업 → 예
→ 업로드 완료 후 시트에 자동 기록
```

---

## 📊 구글 시트 컬럼 구조

| 열 | 이름 | 설명 | 예시 |
|---|---|---|---|
| A | 제목 | 영상 제목 | 고양이의 완벽한 치맥 타임 |
| B | 대본/설명 | 해시태그 포함 설명 | `#고양이 #일상 #shorts` |
| C | 영상URL | 젠스파크URL 또는 로컬파일 경로 | `C:\Users\...\video.mp4` |
| D | 드롭박스URL | 자동 입력 (건드리지 말 것) | `https://www.dropbox.com/...` |
| E | 업로드여부 | 상태값 (아래 참조) | `기록전` |
| F | 유튜브채널 | 채널 번호 1~9 | `3` |
| G | 예약날짜 | 자동 배정 또는 수동 입력 | `2026-05-27 17:00` |
| H | YouTube링크 | 업로드 완료 후 자동 입력 | `https://youtube.com/shorts/...` |

### E열 상태값 의미

| 값 | 의미 | 다음 동작 |
|---|---|---|
| `기록전` | 방금 입력한 상태 | → `실행` 버튼 누르면 드롭박스 업로드 후 `업로드전`으로 변경 |
| `업로드전` | 드롭박스 업로드 완료, 예약 배정됨 | → GitHub Actions 가 예약시간에 YouTube 업로드 |
| `업로드완료` | YouTube 업로드 완료 | → H열에 링크 기록됨 |

---

## 📅 예약 슬롯 정책

- 하루 최대 **2개** : `17:00 KST` / `19:00 KST`
- 슬롯이 꽉 차면 **다음날로 자동 이월** (최대 14일 탐색)
- **수동 수정** : 구글 시트 G열에 직접 입력 가능
  - 예) `2026-05-27 21:00`

---

## 📺 채널 번호 매핑

| 번호 | 채널명 |
|---|---|
| 1 | 데일리인사이트 |
| 2 | 모먼트랩 |
| 3 | 생활정보TV |
| 4 | 오늘의회사썰 |
| 5 | 행복시니어TV |
| 6 | 데일리AI브리핑 |
| 7 | Healthier Living Today |
| 8 | Talk To Me In Korean |
| 9 | GlobalTopTier |

---

## ⚙️ GitHub Actions 설정

### Secrets 등록 현황

| Secret 이름 | 상태 | 내용 |
|---|---|---|
| `GOOGLE_SHEET_ID` | ✅ 등록됨 | 구글 시트 ID |
| `GOOGLE_SHEET_NAME` | ✅ 등록됨 | `숏츠시트` |
| `YOUTUBE_TOKEN_JSON` | ✅ 등록됨 | youtube_token.json 전체 내용 |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | ✅ 등록됨 | 서비스 계정 키 전체 내용 |
| `DROPBOX_TOKEN` | ⚠️ 교체 필요 | refresh_token 방식으로 교체 |

### DROPBOX_TOKEN 교체 방법

1. GitHub 레포 → Settings → Secrets → `DROPBOX_TOKEN` 삭제
2. `DROPBOX_REFRESH_TOKEN` 이름으로 새로 추가
3. 값: `N2HVAUZxqooAAAAAAAAAAYarp5oF4AAFeYubIsEdFeibGXLUnPcTex2d9C9-di5C`
4. `upload.py` 상단 환경변수 이름 맞게 수정 확인

### 실행 스케줄

```yaml
# .github/workflows/upload.yml
on:
  schedule:
    - cron: '0 * * * *'   # 매시간 정각 실행 (KST = UTC+9)
```

---

## 🔧 자주 있는 문제

### `ModuleNotFoundError`
```bash
# 해결: 라이브러리 재설치
C:\Users\gichang\AppData\Local\Programs\Python\Python312\python.exe -m pip install requests gspread google-auth google-api-python-client dropbox
```

### `KeyError: 'GOOGLE_SHEET_ID'`
- `upload.py` 는 GitHub Actions 전용입니다.
- **로컬에서 실행하지 마세요.** `youtube_manager_ui.py` 를 사용하세요.

### 드롭박스 토큰 만료
- Refresh Token 방식을 사용하면 만료되지 않습니다.
- 설정 탭에서 App Key / App Secret / Refresh Token 입력 후 저장.

### YouTube 토큰 만료
```bash
# 로컬에서 재발급
python get_youtube_token.py
# → youtube_token.json 새로 생성됨
# → GitHub Secrets의 YOUTUBE_TOKEN_JSON 도 업데이트 필요
```

---

## 🔄 전체 자동화 흐름 요약

```
[로컬 PC]                           [클라우드]
  │
  ├─ 캡컷/젠스파크로 영상 제작
  │
  ├─ 실행.bat 더블클릭
  │   └─ [📅 예약] 탭
  │       ├─ 파일 선택
  │       ├─ 시트에 행 추가 (E열=기록전)
  │       └─ 실행 버튼
  │           ├─ 드롭박스 업로드 → D열 URL 기록
  │           ├─ 예약 슬롯 배정 → G열 기록
  │           └─ E열 → "업로드전"
  │
  └─ 완료! 이후는 자동 ─────────────→ GitHub Actions (매시간)
                                          └─ 예약시간 도래한 행 확인
                                              └─ YouTube 업로드
                                                  └─ E열=완료, H열=링크
```

---

*마지막 수정: 2026-06-01*
