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
├── upload.py                   ← GitHub Actions 전용 (로컬 직접 실행 금지 —
│                                   단, 코드 수정 자체는 여기서 계속 함)
├── chapters.py                 ← (2026-07-26 신규) 챕터 파싱/검증/설명란 삽입
├── playlist_ops.py             ← (2026-07-26 신규) 재생목록 생성/재사용/추가
├── comment_ops.py              ← (2026-07-26 신규) 고정 댓글용 문구 작성
├── watermark_ops.py            ← (2026-07-30 신규) 채널 워터마크 등록/제거 함수
├── channel_watermark_setup.py  ← (2026-07-30 신규) 채널당 1회만 로컬에서 직접
│                                   실행하는 워터마크 등록 스크립트(자동 업로드
│                                   파이프라인과 무관, 아래 "채널 워터마크 설정"
│                                   섹션 참고)
├── 유튜브_콘텐츠_최적화_전략.md ← (2026-07-26 신규) 새 자동화 프로젝트를
│                                   만들거나 수정할 때 항상 먼저 참고할 전략 문서
│                                   (30_YouTube_View_Optimization / 29_japan_senior
│                                   _story_longform에도 동일 사본 있음)
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

## 🏷️ 채널 워터마크 설정 (채널당 1회만)

> 구독 유도 아이콘을 영상 내내 우측 하단 등에 띄우는 기능. 자동 업로드
> 파이프라인과 무관하게, 채널 브랜딩을 새로 만들거나 바꿀 때만 한 번 실행하면
> 된다.

```bash
python channel_watermark_setup.py --channel 7 --image watermark_ch7.png
```

- 워터마크 이미지는 정사각형에 가까운 PNG(투명 배경 추천, 10MB 이하)를 같은
  폴더에 준비해서 경로로 넘기면 된다.
- `--corner`로 위치 지정 가능(`topLeft`/`topRight`/`bottomLeft`/`bottomRight`,
  기본값 `bottomRight`).
- 잘못 등록했으면 `--unset`으로 제거: `python channel_watermark_setup.py --channel 7 --unset`
- 이 기능은 `youtube.upload` 스코프만으로도 동작하는 것으로 공식 문서에서
  확인됨(재생목록/댓글과 달리 스코프 재발급이 필수는 아님) — 그래도 403이
  나면 `get_youtube_token.py`로 토큰을 다시 발급해볼 것.

---

## 📊 구글 시트 컬럼 구조

| 열 | 이름 | 설명 | 예시 |
|---|---|---|---|
| A | 제목 | 영상 제목 | 고양이의 완벽한 치맥 타임 |
| B | 대본/설명 | 해시태그 포함 설명 | `#고양이 #일상 #shorts` |
| C | 영상URL | 젠스파크URL 또는 로컬파일 경로 | `C:\Users\...\video.mp4` |
| D | 드롭박스URL(또는 구글드라이브URL) | 자동 입력 (건드리지 말 것). 2026-08-09부터 `drive.google.com` 링크도 지원 — URL 패턴으로 자동 구분(아래 변경 이력 참고) | `https://www.dropbox.com/...` 또는 `https://drive.google.com/file/d/.../view` |
| E | 업로드여부 | 상태값 (아래 참조) | `기록전` |
| F | 유튜브채널 | 채널 번호 1~9 | `3` |
| G | 예약날짜 | 자동 배정 또는 수동 입력 | `2026-05-27 17:00` |
| H | YouTube링크 | 업로드 완료 후 자동 입력 | `https://youtube.com/shorts/...` |
| I~N | (이 프로젝트는 안 씀, 다른 프로젝트 예약석) | 27/28/29번 콘텐츠 생성 프로젝트가 이미 이 구간을 상태/수집일시/테마ID/생성ID/이미지폴더/테마로 쓰고 있음 — **절대 이 열들을 챕터/재생목록/댓글 용도로 재사용하지 말 것** | — |
| O | 챕터 (선택) | `시간 제목 \| 시간 제목 ...` 형식. 비우면 챕터 기능 자체를 건너뜀. 29번 시트처럼 챕터가 이미 B열(설명란)에 직접 포함돼 있으면 이 열은 비워두면 됨 | `0:00 도입부 \| 1:30 사건의 시작 \| 4:00 반전` |
| P | 재생목록 (선택) | 이 이름으로 재생목록을 찾거나 새로 만들어 영상을 추가. 비우면 건너뜀 | `家族の秘密 感動ストーリー` |
| Q | 재생목록 설명 (선택) | P열이 채워졌을 때만 사용(신규 생성 시 설명으로 들어감) | `血の繋がり、相続...` |
| R | 고정 댓글용 문구 (선택) | 댓글로 "작성"까지만 자동화됨. 비우면 건너뜀 | `皆さんはどう思いますか？` |
| S | AI 사용 공개 오버라이드 (선택) | `true`/`false`. 비우면 F열(채널번호) 기준 `CHANNEL_SYNTHETIC_MEDIA_MAP` 기본값을 씀 | `true` |

> ⚠️ **컬럼 배치 사고 이력**: 처음엔 이 4개 기능을 I~L열에 넣었었는데, 27/28/29번
> 프로젝트가 이미 그 자리를 상태(I)/수집일시(J)/테마ID(K)/생성ID(L)로 쓰고
> 있다는 걸 뒤늦게 발견함 — 그 상태로 뒀다면 생성ID("20260726153045" 같은
> 숫자)가 그대로 "고정 댓글 문구"로 읽혀 실제 영상에 의미 없는 댓글이 달릴
> 뻔했다. 실제 업로드가 나가기 전에 발견해서 O/P/Q/R(15~18번째 열)로 옮김.
> 새 열을 또 추가해야 한다면 **반드시 다른 프로젝트의 config.py 컬럼 상수를
> 먼저 확인**하고 그 뒤(R열 다음인 S열부터)에 이어 붙일 것.
>
> ⚠️ O~R열은 전부 **선택 입력**이다. 비어있으면 해당 기능만 조용히 건너뛰고
> 기존 A~N열 흐름은 100% 그대로 동작한다 — 기존에 A~H열만 쓰던 단순 시트/
> 스크립트(genspark_to_dropbox.py, youtube_manager_ui.py 등)도, A~N을 쓰는
> 29번 같은 시트도 수정 없이 그대로 호환됨.
>
> ⚠️ P(재생목록)/R(고정댓글)은 YouTube Data API 쓰기 권한 스코프가 필요하다.
> 지금 채널별 토큰(`youtube_token_ch*.json`)이 업로드 전용 스코프로만 발급돼
> 있었다면 403(권한 부족) 오류가 날 수 있다 — 이 경우 `get_youtube_token.py`로
> 더 넓은 스코프(`youtube.force-ssl`)로 토큰을 재발급해야 한다. 실패해도
> upload.py가 경고만 출력하고 업로드 자체는 그대로 성공 처리하도록 만들어져
> 있으니, 이 오류가 나도 영상 업로드/시트 기록에는 영향 없다.
>
> ⚠️ 엔드 화면/카드 등록, 썸네일·제목 A/B 테스트, 댓글 "고정"(pin) 자체는
> YouTube Data API가 아예 지원하지 않는 기능이라(2026년 기준 공식 문서 확인)
> 자동화 불가능 — 유튜브 스튜디오에서 직접 처리해야 한다.

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

## 📝 변경 이력

> 규칙: 이 섹션은 항상 맨 아래에 새 항목을 추가하는 방식으로만 갱신한다
> (기존 항목을 지우거나 다시 쓰지 않음).

### 2026-07-26 — 챕터/재생목록/고정댓글 자동화 추가
- 사용자가 30번 프로젝트(`30_YouTube_View_Optimization`)에서 정리한 유튜브
  알고리즘 최적화 규칙(챕터 0:00 시작/최소 3개/10초 간격, 재생목록 배치, 고정
  댓글 키워드 유도)을 실제 운영 업로더에도 반영해달라고 요청.
- 새 파일 3개 추가(코딩 컨벤션 규칙 1 — 기능별 분리): `chapters.py`(챕터
  파싱/검증/설명란 삽입), `playlist_ops.py`(재생목록 생성/재사용/추가),
  `comment_ops.py`(댓글 작성 — "고정"은 API 미지원이라 작성까지만).
- `upload.py`: 위 3개 모듈을 import해서 `upload_to_youtube()`에 `chapters_raw`/
  `playlist_name`/`playlist_description`/`pinned_comment` 4개 선택 인자 추가.
  구글 시트 I/J/K/L열(전부 선택 입력, 비우면 해당 기능만 건너뜀)에서 값을
  읽어 전달하도록 `main()`도 함께 수정. 기존 A~H열 기반 흐름·다른 스크립트는
  전혀 건드리지 않아 하위 호환 100% 유지.
- 챕터/재생목록/댓글 처리는 전부 `try/except`로 감싸서, 실패해도(형식 오류,
  API 권한 부족 등) 업로드 자체는 그대로 성공 처리되도록 설계(기존 코드베이스의
  "일부 실패해도 전체를 죽이지 않는다" 패턴을 그대로 따름).
- 검증: `py_compile`로 `upload.py`/`chapters.py`/`playlist_ops.py`/
  `comment_ops.py` 4개 파일 문법 확인. `chapters.py`는 실제 함수 호출로
  정상/비정상 케이스(간격 10초 미만, 0:00 미시작, 3개 미만, 빈 값 폴백) 전부
  단위 테스트 통과 확인.
- ⚠️ 아직 안 한 것: 실제 GitHub Actions 환경에서 채널 토큰의 쓰기 권한
  스코프가 재생목록/댓글 API를 실제로 호출할 수 있는지는 검증 못 함(토큰
  파일을 열지 않는 원칙 때문에 스코프를 코드로 확인할 방법이 없음) — 다음
  실제 업로드 때 로그에 "⚠️ 재생목록 처리 실패(권한 부족...)"가 찍히는지
  확인 필요. 찍히면 `get_youtube_token.py`로 해당 채널 토큰을
  `youtube.force-ssl` 스코프로 재발급할 것.
- ⚠️ I/J/K/L열에 실제 값을 채워 넣는 자동화(예: 29번 프로젝트의 cuts.json에서
  챕터를 뽑아 시트에 자동 기록)는 이번 범위에 포함하지 않음 — 지금은 사람이
  시트에 직접 입력하거나, 다른 프로젝트가 이 4개 열에 값을 채우도록 나중에
  연동해야 함.

### 2026-07-26 (2차) — I~L열 컬럼 충돌 긴급 수정 + 29번 실제 파이프라인과 대조
사용자 요청으로 챕터/재생목록/고정댓글 "자동화 구현"을 진행하며
`29_japan_senior_story_longform/jp_senior_longform/config.py`를 직접 열어
실제 시트 컬럼 배치를 대조하다가, 지난 항목(1차)에서 새로 만든 I/J/K/L열이
이미 27/28/29번 프로젝트의 A~N(14열) 공용 스키마와 정면으로 겹친다는 걸
발견함(I=상태, J=수집일시, K=테마ID, L=생성ID). 이 상태로 실제 운영됐다면:
- J열(수집일시, 예: "2026-07-26 15:30")이 "재생목록 이름"으로 읽혀 날짜
  문자열 이름의 재생목록이 매일 새로 생겼을 것.
- L열(생성ID, 예: "20260726153045")이 "고정 댓글 문구"로 읽혀 의미 없는
  숫자 댓글이 실제 영상에 자동으로 달렸을 것.
- 다행히 실행 전에 발견 — 아직 실제 피해는 없음.
- `upload.py`: 4개 열을 O/P/Q/R(15~18번째)로 이동, 관련 주석/로그 메시지
  전부 갱신.
- README 컬럼 표에 "I~N열은 다른 프로젝트 예약석" 경고 추가.
- 교훈: 여러 프로젝트가 같은 구글 스프레드시트를 공유할 때 새 컬럼을 추가하기
  전엔 반드시 그 시트를 쓰는 다른 프로젝트의 컬럼 상수(`config.py`의
  `COL_*`)를 먼저 확인할 것 — `유튜브_콘텐츠_최적화_전략.md`에도 이 교훈을
  추가함.
- 검증: py_compile 통과. 실제 Sheets/YouTube API 호출 없이는(샌드박스에
  자격 증명 없음) O/P/Q/R 값이 실제로 올바르게 읽히는지 런타임 검증은 아직
  못 함 — 다음 실제 실행 시 로그의 "재생목록(P열)"/"고정댓글(R열)" 출력이
  기대한 값과 일치하는지 확인 필요.

### 2026-07-30 — AI 사용(합성 콘텐츠) 공개를 업로드 시점에 자동 선언
사용자가 유튜브 스튜디오에서 일부 영상에만 "AI 라벨" 알림이 붙어 있고
어떤 영상엔 없는 걸 발견 — 확인해보니 스튜디오의 "AI 사용" 공개 질문에
"예"가 체크된 영상에만 라벨이 붙는 것이었고, 지금까지는 자동 업로드
과정에서 아무도 이 질문에 답을 넣지 않았다(유튜브가 나중에 자체 감지로
뒤늦게 라벨을 붙인 것으로 보임). YouTube Data API가 2024-10-30부터
`status.containsSyntheticMedia`(bool) 필드를 `videos.insert`/`videos.update`
에서 지원하는 걸 확인하고 업로드 시점에 바로 선언하도록 수정.
- `CHANNEL_SYNTHETIC_MEDIA_MAP` 신설(`CHANNEL_LANGUAGE_MAP`과 동일 패턴) —
  채널7(일본 시니어 사연, 사실적인 AI 생성 인물 이미지 + AI 내레이션이
  확실히 해당)만 `True`로 등록, 나머지 채널은 등록 안 하면 필드 자체를
  안 보내서 기존 동작(스튜디오 기본값/자동감지) 그대로 유지.
- ⚠️ 전 채널에 무조건 True를 넣지 않음 — 유튜브 disclosure 기준은 "사실적인
  인물/장면을 AI로 생성·변경"한 경우만 해당하고, 단순 TTS 내레이션이나
  일러스트풍 이미지, 대본 생성 보조 정도는 대상이 아니기 때문. 다른 채널도
  사실적인 AI 생성 인물/장면을 쓴다면 이 맵에 추가할 것.
- S열(선택) 신설 — 특정 영상 하나만 채널 기본값과 다르게 강제하고 싶을 때
  `true`/`false`로 오버라이드. 비어있으면 채널 기본값을 그대로 씀.
- 29번(콘텐츠 생성) 프로젝트는 수정 불필요 — 채널 번호는 이미 F열로 흘러
  들어오므로 `upload.py` 한 파일만 고치면 된다.
- 검증: py_compile 통과. 채널7/override 조합별로 최종 값이 올바르게
  해석되는지(override 우선 → 채널 맵 → None) 파이썬으로 직접 호출해 확인.
  ⚠️ 실제 YouTube API 호출로 `containsSyntheticMedia`가 정상적으로 저장되고
  스튜디오 UI에 "예"로 반영되는지는 이 샌드박스에 자격 증명이 없어 검증
  못 함 — 다음 실제 업로드 후 스튜디오에서 확인 필요.

### 2026-07-30 (2차) — 유튜브 성장 강의 18가지 업로드 세팅 팁 반영 + 워터마크 자동화
사용자가 구독자 11만 유튜버의 "업로드 세팅 18가지" 강의 대본 전체를 붙여넣고
"체크리스트 또는 자동화 구현해줘" 요청. 18개 항목을 하나씩 대조한 결과:
- 재생목록 자동 배정, 챕터 수동 입력(자동챕터 대신 타임스탬프 직접 삽입),
  카테고리 지정, 설명란 SEO 원칙, 고정 댓글 자동 작성은 **이미 이 프로젝트에
  구현돼 있음**을 재확인(신규 작업 불필요).
- **워터마크 등록을 새로 자동화함**: `유튜브_콘텐츠_최적화_전략.md` 4번
  섹션에 "채널 자동 챕터 on/off 토글, 쇼츠 리믹스 허용 토글, 워터마크 등록은
  API 미지원"이라고 적어뒀던 게 **워터마크에 한해서는 틀린 정보**였음을
  공식 문서(`developers.google.com/youtube/v3/docs/watermarks/set`)로 확인—
  `watermarks.set`/`watermarks.unset` 엔드포인트가 실제로 존재하고,
  `youtube.upload` 스코프만으로도 동작한다(재생목록/댓글과 달리 스코프
  재발급 불필요). `watermark_ops.py`(등록/제거 함수)와
  `channel_watermark_setup.py`(채널당 1회 실행하는 CLI, 자동 업로드
  파이프라인과 분리)를 신규 작성.
- **자동화 불가능으로 남는 항목(스튜디오 수동 처리 확정)**: 엔드스크린 연관
  영상 연결, 썸네일·제목 3안 A/B 테스트 등록, 자동 챕터 on/off 토글, 쇼츠
  리믹스 허용 여부 — 전부 API 미지원 확인됨(리믹스는 공식 문서에서 별도
  필드를 찾지 못해 "미확인"으로 분류, 추가 확인 필요시 재검토).
- **채널당 1회만 사람이 직접 해야 하는 항목**(코드 자동화 범위 밖, 계정/보안
  설정 성격): 채널 키워드, 채널 설명 첫 문장 키워드, 비즈니스 문의 이메일
  등록, 기능 사용 자격요건(중급/고급) 인증, 구독 정보 비공개, 2단계 인증,
  업로드 기본값(기본 공개상태 등). `유튜브_콘텐츠_최적화_전략.md`에 "8.
  채널 최초 1회 설정 체크리스트" 섹션을 신설해 18개 항목 전체를 정리.
- 검증: `py_compile watermark_ops.py channel_watermark_setup.py` 통과.
  ⚠️ 실제 `watermarks.set` API 호출로 채널에 워터마크가 정상 등록되고
  스튜디오/실제 재생화면에 노출되는지는 이 샌드박스에 자격 증명이 없어
  검증 못 함 — 사용자가 로컬에서 실제 이미지 파일로 최초 실행해서 확인 필요.

### 2026-08-09 — D열에 구글드라이브 링크도 지원 (Dropbox 경로는 완전히 그대로)
29_japan_senior_story_longform 쪽에서 Dropbox 무료 용량(2GB)이 자주 꽉 차는
문제로 "Dropbox 또는 구글드라이브를 사용자가 고를 수 있게 해달라"는 요청이
들어옴 — 그 프로젝트가 올리는 쪽(`tts_dropbox.upload_to_gdrive()`)을 새로
만들면서, 이 프로젝트(다운받아서 실제 유튜브에 올리는 쪽)도 구글드라이브
링크를 처리할 수 있어야 파이프라인이 완성된다는 게 확인돼 사용자가 이 폴더도
함께 연결해서 같이 수정함.

- `upload.py`의 `download_video()`에 분기 추가 — D열 값에 `drive.google.com`
  이 포함되면 신규 `download_gdrive()`로, 그 외(기존 Dropbox 링크 등)는
  **기존 `download_url(is_dropbox=True)` 그대로**, D열이 비어있으면 **기존
  젠스파크 직접 다운로드 그대로**. 기존 두 경로는 단 한 줄도 수정하지 않음
  (URL 패턴으로만 새 분기를 추가한 것이라 다른 프로젝트가 계속 Dropbox
  링크만 D열에 넣는다면 이번 변경의 영향을 전혀 받지 않는다).
- `download_gdrive()`/`_extract_gdrive_file_id()`/`_get_drive_service()`
  신설 — 공개 공유링크를 그냥 `requests.get`으로 받으면 대용량 파일에서
  구글이 "바이러스 검사를 할 수 없습니다" 확인 페이지(HTML)를 대신
  돌려줘서 실패하는 잘 알려진 문제가 있어, 이미 Sheets 연결에 쓰고 있는
  서비스 계정(`GOOGLE_SERVICE_ACCOUNT_JSON`)으로 인증된 Drive API
  (`files().get_media` + `MediaIoBaseDownload`)로 내려받는다 — 인증 API
  호출은 그 확인 페이지를 거치지 않는다. 새 패키지 의존성 없음
  (`googleapiclient`/`google-auth`는 이미 requirements에 있던 것 재사용,
  `MediaIoBaseDownload`만 기존 import 줄에 추가).
- 검증: `_extract_gdrive_file_id()`를 `/file/d/<id>/view`, `?id=<id>`,
  Dropbox URL(→None 반환 확인) 세 가지로 테스트. `download_video()`도
  `download_url`/`download_gdrive`를 몽키패치해서 ①D열 비어있음→기존
  젠스파크 경로 ②D열=Dropbox 링크→기존 경로(변경 없음 확인) ③D열=
  구글드라이브 링크→신규 경로로 정확히 분기되는지 assert로 확인. 실제
  `google-api-python-client`/`google-auth` 패키지를 설치해서 `upload.py`
  py_compile 통과.
- ⚠️ 실제 GitHub Actions 환경에서 구글드라이브 링크가 든 행을 실제로
  처리해서 다운로드→유튜브 업로드까지 끝까지 되는지는 이 샌드박스에서
  검증 못 함(자격 증명·네트워크 제약) — 29번 프로젝트 쪽에서
  `google_drive_folder_id` 최초 설정(서비스 계정과 사람 드라이브 폴더 공유)
  후 실제로 한 번 돌려서 확인 필요.

### 2026-08-16 — 시트 API 일시 오류(503) 하나로 자동화 전체가 죽는 문제 수정
사용자가 "구글드라이브에는 잘 올라가는데 유튜브 업로드가 실패했다"고 신고
해서 GitHub Actions 실행 로그(Actions 탭)를 직접 확인 — 실제 트레이스백은
`gspread.exceptions.APIError: [503]: The service is currently unavailable.`이
`get_next_video()`의 `sheet.get_all_values()` 호출에서 발생한 것이었다. 즉
Drive 다운로드나 유튜브 업로드는 아예 시도되기도 전에, 시트 API 자체의
일시적 장애(우리 코드/29번의 OAuth Drive 전환과는 무관한 구글 쪽 문제)로
전체 스크립트가 죽어버린 것 — 이 오류 하나로 `main()`의 for 루프 전체가
중단돼서, 실패한 시트 뒤에 나열된 다른 채널 시트들(예: 일본시니어롱폼시트)은
아예 시도조차 못 됐다. 30분마다 자동으로 도는 무인 배치라 이런 일시적
API 오류는 정상적으로 발생할 수 있는 범위인데, 재시도 없이 그대로
죽게 두면 안 된다고 판단해서 고침.

- `_retry_gspread_call(fn, *args, retries=3, base_delay=5, **kwargs)` 신규
  추가 — `gspread.exceptions.APIError`의 메시지에 `[503]`/`[500]`/`[429]`
  (일시적 오류로 흔히 보는 코드)가 포함돼 있으면 5초→10초→20초 지수
  백오프로 최대 3회 재시도. 그 외 오류(예: `[403]` 권한 문제처럼 재시도해도
  똑같이 실패할 오류)는 재시도 없이 즉시 그대로 올린다.
- `get_next_video()`의 `sheet.get_all_values()` 호출을 이 재시도 헬퍼로
  감싸서, 이 지점에서 터지는 일시적 오류는 대부분 자동으로 회복되게 함.
- `main()`의 `get_next_video(sheet)` 호출부에도 try/except를 추가(기존
  `get_sheet()` 호출부와 동일한 패턴) — 재시도까지 다 실패한 지속적인
  오류라도, 그 시트 하나만 건너뛰고 나머지 시트(다른 채널)는 계속
  처리하도록 변경. 예전엔 여기서 예외 하나가 전체 프로세스를 죽여서
  뒤 시트들이 아예 처리되지 않았다.
- 검증: 가짜 `gspread.exceptions.APIError`(진짜 gspread 예외 클래스를
  가짜 응답 객체로 생성)로 ①503이 두 번 실패하다 세 번째에 성공하는
  경우 ②403처럼 재시도 대상이 아닌 오류는 즉시 그대로 올라가는지
  ③재시도를 다 써도 안 되면 결국 예외가 올라가는지 ④`get_next_video()`가
  실제로 이 재시도 헬퍼를 거쳐 일시적 실패를 극복하고 정상적으로 행을
  찾아내는지, 총 4개 시나리오를 실제로 돌려서 assert로 확인. `python3 -m
  py_compile` 통과.
- ⚠️ 사용자가 삭제했다고 한 "유튜브 업로드 실패" 영상은 이번 로그를 보면
  실제로는 유튜브 API까지 도달하지도 못했다(시트 읽기 단계에서 이미
  죽음) — 즉 유튜브에 부분적으로라도 뭔가 올라갔을 가능성은 낮고, 다음
  30분 주기 자동 실행(또는 수동 재실행)에서 정상적으로 다시 시도될
  것으로 보인다. 다만 이번 수정 이후 실제로 다음 예약 슬롯이 정상
  업로드되는지는 다음 실행 결과로 확인 필요.

### 2026-08-29 — 채널9(미국 시니어) 업로드 시 구독자 알림/구독피드 게시 끄기
사용자 요청: "아.. 영어 시니어만 구독피드게시 구독자 알림전송을 꺼야
되는데...." (유튜브 스튜디오 업로드 화면 '더보기 > 라이선스'의 '구독
피드에 게시하고 구독자에게 알림 전송' 체크박스와 동일한 설정 — API로는
`videos.insert()`의 `notifySubscribers` 쿼리 파라미터, 기본값 True).
- `CHANNEL_NOTIFY_SUBSCRIBERS_MAP = {"9": False}` 신설(`CHANNEL_LANGUAGE_
  MAP`/`CHANNEL_SYNTHETIC_MEDIA_MAP`과 동일한 채널별 매핑 패턴). 매핑에
  없는 채널은 `True`로 폴백 — 지금까지처럼 구독자에게 정상적으로 알림이
  가는 기존 동작을 그대로 유지한다(채널9만 예외).
- `upload_to_youtube()`의 `service.videos().insert(...)` 호출에
  `notifySubscribers=notify_subscribers` 인자 추가. 이 값은 body(snippet/
  status) 안이 아니라 insert 메서드 자체의 쿼리 파라미터라 body 구성
  로직은 건드리지 않았다.
- 같은 화면에서 사용자가 함께 지적한 나머지 3가지(① 태그에 일본어가
  섞여 있음 ② AI 사용 공개가 "예"로 안 돼 있음 ③ 동영상/제목·설명 언어가
  영어가 아님)는 확인 결과 이 프로젝트 코드에는 이미 반영돼 있었다 — ①은
  `27_japan_senior_story_shorts` 2026-08-29(19차)에서 시트 해시태그 자체를
  마켓별로 고쳤고(태그는 description의 "#단어"를 그대로 추출하므로 자동
  반영), ②③은 `CHANNEL_SYNTHETIC_MEDIA_MAP["9"]=True`/`CHANNEL_LANGUAGE_
  MAP["9"]="en"`이 2026-08-28에 이미 추가돼 있었다. 사용자가 스크린샷으로
  보여준 그 영상은 이 수정들이 반영되기 전(또는 수동 업로드 경로)에 이미
  올라간 것으로 보이며, 그 영상 자체는 유튜브 스튜디오에서 직접 고쳐야
  한다(자동화 코드 수정으로는 이미 올라간 영상에 소급 적용 안 됨).
- 검증: `python3 -m py_compile upload.py` 통과. `videos().insert(` 호출부가
  파일 전체에서 한 곳뿐임을 grep으로 확인.

---

*마지막 수정: 2026-08-29*
