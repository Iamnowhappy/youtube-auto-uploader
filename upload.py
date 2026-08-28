"""
YouTube 자동 업로드 스크립트 v5
- E열 "업로드전" + C열 젠스파크 URL로 직접 YouTube 업로드
- 드롭박스 불필요! 젠스파크 URL → YouTube 직행
- D열 dropbox_url 있으면 드롭박스 사용, 없으면 C열 젠스파크 URL 사용
- F열 채널 번호로 채널 선택 (1=모먼트랩, 2=데일리인사이트, 3=생활정보TV)
- G열 예약날짜 있으면 예약공개, 없으면 즉시공개
- 채널별 전용 토큰 지원 (YOUTUBE_TOKEN_JSON_CH1 ~ CH9)
- 여러 시트(숏츠시트, 카툰썰시트 등) 순회 지원
"""

# ──────────────────────────────────────────
# 채널 번호 → 채널 ID 매핑
# ──────────────────────────────────────────
CHANNEL_MAP = {
    "1": "UCuyhcW0c4QCcCRtA5oeMn1w",   # 데일리인사이트
    "2": "UCMujLGISA9sRh0ki9H5xXLg",   # 모먼트랩
    "3": "UCqr08lng11l-14li4vaLc3g",   # 생활정보TV
    "4": "UC7wgb4aG0ytHl8MtOJwNBfw",   # 오늘의 회사썰
    "5": "UCjysxDKwgwejYuMx3-WDKjg",   # 행복시니어TV
    "6": "UCw8ETbGpdnXc8NJpdgmwrqw",   # 데일리AI브리핑
    "7": "UCAdzqsKoItMWxKmhoC8aSrg",   # Healthier Living Today
    "8": "UCjdqO74OEmNt9EL4H33VWUQ",   # Talk To Me In Korean
    # 2026-08-28 정정 — 이전 세션 메모(29_japan_senior_story_longform 40차)는
    # 채널9=GlobalTopTier(리브랜딩 예정)로 잘못 기록돼 있었다. 실제로 미국
    # 시니어 채널로 쓰기로 확정한 건 GlobalTopTier가 아니라 "Curious Facts"
    # 브랜드 계정이었고, 이미 유튜브 스튜디오에서 "Quiet Fortune"으로
    # 개명까지 끝난 상태였다(사용자가 Cowork 세션에서 채널 목록 스크린샷으로
    # 직접 확인해줌). GlobalTopTier는 이 프로젝트와 무관한 별개 채널이다 —
    # OAuth 토큰(YOUTUBE_TOKEN_JSON_CH9)도 이번에 Curious Facts 계정으로
    # 다시 발급받아 GitHub 시크릿을 교체했다. 채널ID는 사용자가 보여준
    # YouTube Studio 채널 콘텐츠 페이지 URL
    # (studio.youtube.com/channel/UCWULpFJH9gvGvprOli7rwiw/...)에서 확인.
    "9": "UCWULpFJH9gvGvprOli7rwiw",   # Quiet Fortune (구 Curious Facts, 미국 시니어 채널)
}

CHANNEL_NAMES = {
    "1": "데일리인사이트",
    "2": "모먼트랩",
    "3": "생활정보TV",
    "4": "오늘의회사썰",
    "5": "행복시니어TV",
    "6": "데일리AI브리핑",
    "7": "HealthierLivingToday",
    "8": "TalkToMeInKorean",
    "9": "QuietFortune",
}

# 2026-07-25 추가: defaultLanguage가 지금까지 전 채널 "ko"로 하드코딩돼
# 있었음 — 채널7(27_japan_senior_story_shorts + 29_japan_senior_story_longform,
# 대본이 전부 일본어)에는 명백히 잘못된 값이었다(YouTube가 검색/추천에서
# 언어를 매칭할 때 이 메타데이터를 쓰기 때문에, 일본어 콘텐츠에 "ko"가
# 붙어 있으면 일본 시청자에게 덜 노출될 수 있음). 여기 없는 채널은 지금까지
# 처럼 "ko"로 그대로 동작(기존 동작 100% 보존) — 실제 콘텐츠 언어가 확인된
# 채널만 여기 추가할 것.
CHANNEL_LANGUAGE_MAP = {
    "7": "ja",   # 일본 시니어 사연(쇼츠+롱폼) — 대본이 전부 일본어
    "9": "en",   # 2026-08-28 추가 — 미국 시니어 사연(Quiet Fortune, 쇼츠+롱폼) — 대본이 전부 영어
}

# 2026-07-30 추가: 유튜브 스튜디오에서 "AI 사용" 공개 질문(실제 인물처럼
# 보이는 것을 AI로 만들었는지 등)에 매번 사람이 직접 "예"를 눌러야 했음
# (자동화로 업로드되니 아무도 이 질문에 답을 안 넣은 채로 올라갔었고,
# 이후 유튜브가 자체 감지로 라벨을 뒤늦게 붙이는 걸 사용자가 발견함).
# YouTube Data API의 status.containsSyntheticMedia 필드(2024-10-30 API에
# 추가됨, videos.insert/update에서 설정 가능)로 업로드 시점에 바로 선언하면
# 스튜디오에서 나중에 따로 체크할 필요가 없다.
#
# ⚠️ 전 채널에 무조건 True를 넣지 않는다 — 유튜브 disclosure 기준은
# "사실적으로 보이는 인물/장면을 AI로 생성/변경"한 경우에만 해당하고,
# 단순 TTS 내레이션이나 만화/일러스트 스타일 이미지, 대본 생성 보조 정도는
# 대상이 아니다(과잉 신고도 정책 위반은 아니지만 불필요한 라벨을 늘릴
# 이유가 없음). 채널7(일본 시니어 사연, 27/29번 프로젝트 — 사실적인 AI
# 생성 인물 이미지 + AI 음성 내레이션)만 확실히 해당되는 걸 확인해서
# True로 등록. 다른 채널도 사실적인 AI 생성 인물/장면을 쓴다면 여기에
# 추가할 것.
CHANNEL_SYNTHETIC_MEDIA_MAP = {
    "7": True,   # 일본 시니어 사연(쇼츠+롱폼) — 사실적 AI 생성 인물 이미지 + AI 내레이션
    "9": True,   # 2026-08-28 추가 — 미국 시니어 사연(Quiet Fortune, 쇼츠+롱폼) — 채널7과 동일한 이유(사실적 AI 생성 인물 이미지 + AI 내레이션)
}

# 2026-08-29 추가 — 사용자 요청: "아.. 영어 시니어만 구독피드게시 구독자
# 알림전송을 꺼야 되는데...." (YouTube 스튜디오 업로드 화면의 '구독 피드에
# 게시하고 구독자에게 알림 전송' 체크박스와 동일한 설정 — YouTube Data API
# videos.insert()의 notifySubscribers 쿼리 파라미터, 기본값 True).
# 채널9(Quiet Fortune, 미국 시니어)만 False로 꺼서 업로드하고, 나머지
# 채널은 지금까지처럼 기본 True(=구독자에게 알림 전송, 기존 동작 100%
# 유지)로 둔다. 왜 채널9만 끄는지는 사용자 판단 영역이라 여기선 그대로
# 반영만 함 — 매핑에 없는 채널은 True로 폴백(안전한 기본값, 새 채널
# 추가돼도 실수로 알림이 꺼지는 일 없음).
CHANNEL_NOTIFY_SUBSCRIBERS_MAP = {
    "9": False,  # 미국 시니어(Quiet Fortune) — 구독 피드 게시/알림 끔
}

import os
import json
import re
import tempfile
import time
import requests
import gspread
from datetime import datetime, timezone, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials as OAuthCredentials
from google.auth.transport.requests import Request

# 2026-07-26 추가: 챕터/재생목록/고정댓글 자동화 — 각 기능을 별도 파일로 분리
# (코딩 컨벤션 규칙 1). 이 세 모듈은 전부 "실패해도 업로드 자체는 죽지 않게"
# 설계되어 있고, upload_to_youtube()/main()에서 항상 try/except로 감싸 호출한다.
from chapters import build_description_with_chapters
from playlist_ops import ensure_playlist, add_to_playlist
from comment_ops import post_comment_candidate

KST = timezone(timedelta(hours=9))

# ──────────────────────────────────────────
# 환경변수 로드
# ──────────────────────────────────────────
DROPBOX_TOKEN      = os.environ.get("DROPBOX_TOKEN", "")
GOOGLE_SHEET_ID    = os.environ["GOOGLE_SHEET_ID"]
YOUTUBE_TOKEN_JSON = os.environ["YOUTUBE_TOKEN_JSON"]
GOOGLE_SA_JSON     = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]

# 처리할 시트 이름 목록
# GOOGLE_SHEET_NAMES="숏츠시트,카툰썰시트" 처럼 쉼표로 여러 개 지정 가능
# 미지정 시 기존 동작 유지를 위해 GOOGLE_SHEET_NAME(단일, 기본값 "숏츠시트")도 함께 확인
_sheet_names_env = os.environ.get("GOOGLE_SHEET_NAMES", "")
if _sheet_names_env.strip():
    SHEET_NAMES = [s.strip() for s in _sheet_names_env.split(",") if s.strip()]
else:
    SHEET_NAMES = [os.environ.get("GOOGLE_SHEET_NAME", "숏츠시트")]


# ──────────────────────────────────────────
# 구글 시트 연결
# ──────────────────────────────────────────
def get_client():
    creds_dict = json.loads(GOOGLE_SA_JSON)
    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)


def get_sheet(client, sheet_name):
    return client.open_by_key(GOOGLE_SHEET_ID).worksheet(sheet_name)


# 2026-08-16 추가 — 실사용 중 GitHub Actions 실행이
# "gspread.exceptions.APIError: [503]: The service is currently unavailable."
# (구글 시트 API 쪽의 일시적 장애 — 우리 코드/OAuth 드라이브 변경과는 무관함)
# 하나로 전체가 죽어버리는 문제 발견. get_next_video()의 sheet.get_all_values()
# 호출 시점에서 터졌는데, 그 호출 하나가 예외를 던지면 main()의 for 루프가
# 통째로 중단돼서 그 뒤에 나오는 다른 시트(다른 채널)들은 아예 시도조차
# 안 되는 게 더 큰 문제였다(30분마다 도는 자동화라 개별 요청이 가끔
# 503/500/429로 실패하는 건 정상 범위 — 재시도 없이 그대로 죽게 두면 안 됨).
def _retry_gspread_call(fn, *args, retries=3, base_delay=5, **kwargs):
    """일시적인 구글 API 오류(503/500/429)로 보이면 지수 백오프로 재시도한다.
    그 외 오류(권한 문제 등 재시도해도 똑같이 실패할 오류)는 즉시 그대로
    올린다."""
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            return fn(*args, **kwargs)
        except gspread.exceptions.APIError as e:
            msg = str(e)
            transient = any(code in msg for code in ("[503]", "[500]", "[429]"))
            last_err = e
            if not transient or attempt >= retries:
                raise
            delay = base_delay * (2 ** (attempt - 1))
            print(f"   ⚠️ 구글 시트 API 일시 오류({e}) — {delay}초 후 재시도 "
                  f"({attempt}/{retries})")
            time.sleep(delay)
    raise last_err


def _uploaded_today_for_channel(all_rows, channel_num, today_str):
    """같은 채널로 오늘 이미 업로드 완료된 행이 있는지 확인.
    mark_as_done()이 G열을 '실제 업로드 일시'로 갱신해두기 때문에,
    예약이 잘못 겹쳐도 이 체크가 하루 1개를 보장하는 마지막 안전장치다."""
    for row in all_rows[1:]:
        while len(row) < 7:
            row.append("")
        status = row[4].strip()
        ch     = row[5].strip() if len(row) > 5 else ""
        sched  = row[6].strip()
        if status == "업로드완료" and ch == str(channel_num).strip() and sched[:10] == today_str:
            return True
    return False


def get_next_video(sheet):
    """
    E열이 '업로드전'인 행 반환
    - G열 예약시간이 현재보다 과거이거나 같으면 → 업로드
    - G열 비어있으면 → 즉시 업로드
    - 안전장치: 같은 채널이 오늘 이미 1개 업로드됐으면, 그 채널의 다른 행은
      예약시간이 지났어도 건너뛴다 (시트에 같은 날짜로 두 개가 겹쳐 잡혀도
      하루 1개 업로드 원칙이 코드 레벨에서 강제됨)
    """
    now_kst   = datetime.now(KST)
    today_str = now_kst.strftime("%Y-%m-%d")
    all_rows  = _retry_gspread_call(sheet.get_all_values)

    for i, row in enumerate(all_rows[1:], start=2):
        while len(row) < 7:
            row.append("")
        status    = row[4].strip()
        ch_num    = row[5].strip() if len(row) > 5 else "1"
        scheduled = row[6].strip()
        video_url = row[2].strip()
        dropbox   = row[3].strip()

        if status != "업로드전":
            continue
        if not video_url and not dropbox:
            continue

        is_due = False
        if not scheduled:
            # G열 비어있으면 즉시 업로드
            is_due = True
        else:
            # G열 있으면 예약시간 체크 (과거 포함 모두 업로드 대상)
            try:
                s = scheduled.strip()
                if len(s) == 10:
                    s += " 00:00"
                sched_dt = datetime.strptime(s, "%Y-%m-%d %H:%M")
                sched_kst = sched_dt.replace(tzinfo=KST)
                if now_kst >= sched_kst:
                    is_due = True
                else:
                    print(f"   ⏰ {i}행 예약 대기: {scheduled} (아직 {int((sched_kst-now_kst).total_seconds()//3600)}시간 남음)")
            except Exception as e:
                print(f"   ⚠️ {i}행 날짜 파싱 오류: {e}")
                continue

        if not is_due:
            continue

       # if _uploaded_today_for_channel(all_rows, ch_num, today_str):
       #      print(f"   🛑 {i}행: 채널{ch_num}({CHANNEL_NAMES.get(ch_num, ch_num)})은 "
       #           f"오늘({today_str}) 이미 1개 업로드 완료 → 안전장치로 건너뜀 "
       #         f"(예약이 겹쳤더라도 하루 1개로 제한, 다음 실행에서 자동 재시도)")
       #   continue

        return i, row, scheduled

    return None, None, None


def mark_as_done(sheet, row_num, video_id, is_short=True):
    now_kst = datetime.now(KST)
    sheet.update_cell(row_num, 5, "업로드완료")
    # G열을 '실제 업로드된 일시'로 갱신 — 예약이 밀려서 늦게 올라간 경우에도
    # 정확한 실제 업로드 시각을 남겨야 위의 하루 1개 안전장치가 제대로 동작한다.
    sheet.update_cell(row_num, 7, now_kst.strftime("%Y-%m-%d %H:%M"))
    # 2026-07-25 수정: 예전엔 롱폼이어도 무조건 /shorts/ 링크를 시트에
    # 기록했음. is_short 판정에 맞춰 링크 형식을 바꾼다(upload_to_youtube 참고).
    final_url = f"https://youtube.com/shorts/{video_id}" if is_short else f"https://youtu.be/{video_id}"
    sheet.update_cell(row_num, 8, final_url)
    print(f"✅ 시트 업데이트: {row_num}행 → 업로드완료 (G열 = 실제 업로드 시각 {now_kst.strftime('%Y-%m-%d %H:%M')})")


# ──────────────────────────────────────────
# 영상 다운로드 (젠스파크 or 드롭박스 or 구글드라이브)
# ──────────────────────────────────────────
# 2026-08-09 추가 — 29_japan_senior_story_longform이 Dropbox 무료 용량
# (2GB) 부족 문제로 "구글 드라이브도 업로드 대상으로 고를 수 있게" 요청함
# (그 프로젝트의 tts_dropbox.upload_to_gdrive() 참고). D열은 그대로 두고
# (스키마 변경 없음), 값이 Dropbox 링크냐 구글드라이브 링크냐만 URL 패턴으로
# 구분한다 — 기존 D열=Dropbox 전용이라는 전제였던 곳(예: 다른 시트/
# genspark_to_dropbox.py 등)은 계속 Dropbox 링크만 넣을 것이므로 영향 없음.
def download_video(video_url, dropbox_url):
    """
    D열에 구글드라이브 링크가 있으면 구글드라이브
    D열에 그 외 링크(Dropbox 등)가 있으면 기존 방식(드롭박스 우선)
    D열이 비어있으면 C열 젠스파크 URL 직접 다운로드
    """
    if dropbox_url:
        if "drive.google.com" in dropbox_url:
            print(f"📦 구글 드라이브에서 다운로드...")
            return download_gdrive(dropbox_url)
        print(f"📦 드롭박스에서 다운로드...")
        return download_url(dropbox_url, is_dropbox=True)
    else:
        print(f"✨ 젠스파크에서 직접 다운로드...")
        return download_url(video_url, is_dropbox=False)


def _extract_gdrive_file_id(url):
    """https://drive.google.com/file/d/<ID>/view... 또는
    https://drive.google.com/uc?id=<ID>... 형태 둘 다 지원."""
    m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
    if m:
        return m.group(1)
    m = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", url)
    if m:
        return m.group(1)
    return None


def _get_drive_service():
    """Sheets 연결에 이미 쓰는 서비스 계정(GOOGLE_SERVICE_ACCOUNT_JSON)을
    그대로 재사용해 Drive API 클라이언트를 만든다."""
    creds_dict = json.loads(GOOGLE_SA_JSON)
    creds = Credentials.from_service_account_info(
        creds_dict, scopes=["https://www.googleapis.com/auth/drive"])
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def download_gdrive(url):
    """구글드라이브 링크에서 영상을 내려받는다. 익명 공개링크로 그냥
    requests.get을 하면 대용량 파일에서 구글이 '바이러스 검사를 할 수
    없습니다' 확인 페이지(HTML)를 대신 돌려줘서 실패하므로, 이미 쓰고 있는
    서비스 계정으로 인증된 Drive API(files().get_media)를 통해 내려받는다
    — 인증 API 호출은 그 확인 페이지를 거치지 않는다."""
    file_id = _extract_gdrive_file_id(url)
    if not file_id:
        raise RuntimeError(f"구글 드라이브 URL에서 파일 ID를 추출하지 못했습니다: {url}")

    service = _get_drive_service()
    request = service.files().get_media(fileId=file_id)

    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    try:
        downloader = MediaIoBaseDownload(tmp, request, chunksize=50 * 1024 * 1024)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"   다운로드 중... {int(status.progress() * 100)}%")
    finally:
        tmp.close()

    size = os.path.getsize(tmp.name)
    print(f"✅ 다운로드 완료: {size / 1024 / 1024:.1f}MB")
    return tmp.name


def download_url(url, is_dropbox=False):
    if is_dropbox:
        # 드롭박스 st= 파라미터 제거
        url = re.sub(r'&st=[^&]*', '', url)
        url = re.sub(r'\?st=[^&]*&', '?', url)
        url = re.sub(r'\?st=[^&]*$', '', url)
        if "dl=0" in url:
            url = url.replace("dl=0", "dl=1")
        elif "dl=1" not in url:
            url += "&dl=1" if "?" in url else "?dl=1"

    print(f"   URL: {url[:80]}...")
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, stream=True, allow_redirects=True)
    response.raise_for_status()

    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    total = 0
    for chunk in response.iter_content(chunk_size=1024 * 1024):
        tmp.write(chunk)
        total += len(chunk)
    tmp.flush()
    tmp.close()
    print(f"✅ 다운로드 완료: {total / 1024 / 1024:.1f}MB")
    return tmp.name


# ──────────────────────────────────────────
# YouTube 업로드
# ──────────────────────────────────────────
def get_youtube_service(channel_num="1"):
    # 채널별 전용 토큰 우선 사용, 없으면 기본 토큰
    token_env_key = f"YOUTUBE_TOKEN_JSON_CH{channel_num}"
    token_json = os.environ.get(token_env_key)

    if token_json:
        print(f"✅ {token_env_key} 토큰 사용")
    else:
        print(f"⚠️ {token_env_key} 없음 → 기본 YOUTUBE_TOKEN_JSON 사용")
        token_json = os.environ["YOUTUBE_TOKEN_JSON"]

    token_data = json.loads(token_json)
    creds = OAuthCredentials(
        token=token_data.get("token"),
        refresh_token=token_data["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=token_data["client_id"],
        client_secret=token_data["client_secret"],
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)


def _get_video_duration_seconds(video_path):
    """ffprobe로 실제 영상 길이(초)를 잰다. ffprobe가 없거나 실패하면 None을
    반환한다(호출부가 "판정 불가 시 기존 동작 유지"로 안전하게 폴백하기 위함).

    2026-07-25 신설 — 아래 SHORTS_MAX_SECONDS 판정에 쓰인다. GitHub Actions
    ubuntu-latest 러너에는 ffmpeg/ffprobe가 기본 설치돼 있다."""
    try:
        import subprocess
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True, timeout=30,
        )
        return float(result.stdout.strip())
    except Exception as e:
        print(f"   ⚠️ 영상 길이 확인 실패({e}) — 길이 기반 판정을 건너뜁니다")
        return None


# YouTube Shorts 최대 길이(2024-10부터 3분, 2026-07 기준 확인). 약간의
# 여유(3초)를 둬서 3:00.x 처럼 근소하게 넘는 영상을 실수로 숏츠 취급하지
# 않게 한다.
SHORTS_MAX_SECONDS = 183


def upload_to_youtube(service, video_path, title, description, scheduled="", channel_num="1",
                       chapters_raw="", playlist_name="", playlist_description="", pinned_comment="",
                       contains_synthetic_media=None, sheet_name=""):
    channel_id   = CHANNEL_MAP.get(str(channel_num).strip(), CHANNEL_MAP["1"])
    channel_name = CHANNEL_NAMES.get(str(channel_num).strip(), f"채널{channel_num}")
    print(f"📺 채널: {channel_name} ({channel_id})")

    # 2026-07-25 수정: 지금까지는 영상 길이와 무관하게 무조건 tags에
    # "shorts"를 넣고 description에 "#shorts"를 붙였음 — 채널7의
    # 29_japan_senior_story_longform(16분대 장편)에 이 로직이 그대로
    # 적용되면서, 장편 영상에 "shorts" 태그 + "#shorts" 해시태그가 붙는
    # 실제 사고가 발생함(조회수가 쇼츠 대비 극단적으로 저조했던 원인 중
    # 하나로 의심됨). 이제 실제 영상 길이를 재서 3분(SHORTS_MAX_SECONDS)
    # 이하일 때만 숏츠로 취급한다. 길이 판정이 안 되면(ffprobe 실패 등)
    # 기존 동작(숏츠로 간주)으로 안전하게 폴백한다 — 판정 불가로 장편에
    # 실수로 태그를 안 붙이는 것보다야, 원래도 대부분 숏츠였던 채널들
    # 기준으로는 폴백이 안전한 방향이라 판단.
    duration = _get_video_duration_seconds(video_path)
    if duration is not None:
        is_short = duration <= SHORTS_MAX_SECONDS
        print(f"   ⏱️ 영상 길이: {duration:.1f}초 → {'숏츠' if is_short else '롱폼'}으로 판정")
    else:
        # 2026-08-13 수정: 길이 판정이 안 될 때 예전엔 무조건 "숏츠"로
        # 폴백했음(대부분 채널이 숏츠 전용이던 시절엔 안전한 선택이었음).
        # 그런데 채널7은 이제 숏츠(27_japan_senior_story_shorts, 숏츠시트)와
        # 롱폼(29_japan_senior_story_longform, 일본시니어롱폼시트)을 같은
        # 채널에 함께 올리므로, 길이 판정 불가 시 무조건 숏츠로 찍으면 롱폼
        # 시트에서 온 영상에 "shorts" 태그/"#shorts"가 잘못 붙는 사고가 재발할
        # 수 있다(실제로 반복돼 온 문제). 어느 시트에서 온 행인지(sheet_name)를
        # 넘겨받으면 그 시트 이름으로 더 안전하게 폴백한다 — sheet_name이
        # 없거나 "롱폼"을 포함하지 않으면 기존 동작(숏츠로 간주) 그대로 유지.
        if "롱폼" in sheet_name:
            is_short = False
            print(f"   ⚠️ 영상 길이 판정 실패 — 시트명('{sheet_name}'에 '롱폼' 포함)을 "
                  f"근거로 롱폼으로 폴백")
        else:
            is_short = True
            print(f"   ⚠️ 영상 길이 판정 실패 — 숏츠로 폴백(기존 동작 유지)")

    # 해시태그 추출
    tags = []
    for word in description.split():
        if word.startswith("#"):
            tags.append(word.lstrip("#"))
    if is_short:
        if "shorts" not in [t.lower() for t in tags]:
            tags.insert(0, "shorts")
        if "#shorts" not in description.lower():
            description += "\n\n#shorts"
    else:
        # 롱폼인데 예전에 실수로 붙었던 shorts/#shorts가 (예: 대본에 우연히
        # 포함되는 등) 섞여 들어오면 걸러낸다.
        tags = [t for t in tags if t.lower() != "shorts"]

    # 2026-07-26 추가: I열에 챕터 텍스트("0:00 제목 | 1:30 제목2 | ...")가 있으면
    # 검증 후 설명란 끝에 붙인다. 형식/규칙(0:00 시작, 최소 3개, 10초 이상 간격)을
    # 어기면 chapters.py가 ValueError를 던지는데, 여기서 잡아서 "챕터 없이 기존
    # 설명란 그대로 업로드"로 안전하게 폴백한다 — 챕터 문제로 업로드 전체가
    # 죽으면 안 되기 때문.
    if chapters_raw.strip():
        try:
            description = build_description_with_chapters(description, chapters_raw)
            print("   [챕터] 설명란에 추가 완료")
        except ValueError as e:
            print(f"   ⚠️ 챕터 형식/규칙 오류 — 챕터 없이 업로드 진행: {e}")

    # 2026-07-25 추가: defaultLanguage 채널별 매핑(위 CHANNEL_LANGUAGE_MAP).
    # 매핑에 없는 채널은 기존과 동일하게 "ko".
    default_language = CHANNEL_LANGUAGE_MAP.get(str(channel_num).strip(), "ko")

    # 공개 상태
    now_kst = datetime.now(KST)
    if scheduled:
        try:
            if len(scheduled) == 10:
                scheduled += " 09:00"
            sched_dt  = datetime.strptime(scheduled, "%Y-%m-%d %H:%M")
            sched_kst = sched_dt.replace(tzinfo=KST)
            # 예약시간이 미래면 예약공개, 과거면 즉시공개
            if sched_kst > now_kst:
                sched_utc  = sched_kst.astimezone(timezone.utc)
                publish_at = sched_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")
                privacy    = "private"
                print(f"⏰ 예약공개: {scheduled} KST")
            else:
                publish_at = None
                privacy    = "public"
                print(f"🚀 즉시공개 (예약시간 {scheduled} 이미 지남)")
        except Exception as e:
            print(f"⚠️ 날짜 파싱 실패({e}), 즉시공개")
            publish_at = None
            privacy    = "public"
    else:
        publish_at = None
        privacy    = "public"
        print("🚀 즉시 공개")

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:500],
            "categoryId": "22",
            "defaultLanguage": default_language,
            "defaultAudioLanguage": default_language,
            "channelId": channel_id,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        }
    }
    if publish_at:
        body["status"]["publishAt"] = publish_at

    # 2026-07-30 추가: AI 사용(사실적 합성/변경 콘텐츠) 공개를 업로드 시점에
    # API로 바로 선언. None이면(채널 매핑에도 없고 시트 오버라이드도 없으면)
    # 아예 필드를 안 보내서 기존 동작(유튜브 스튜디오 기본값/자동감지에 맡김)
    # 그대로 유지 — 잘못된 값을 강제로 넣는 것보다 안전하다.
    if contains_synthetic_media is not None:
        body["status"]["containsSyntheticMedia"] = bool(contains_synthetic_media)
        print(f"   🤖 AI 사용(합성 콘텐츠) 공개: {bool(contains_synthetic_media)}")

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024 * 5
    )

    # 2026-08-29 추가 — 위 CHANNEL_NOTIFY_SUBSCRIBERS_MAP 참고. notifySubscribers는
    # body(snippet/status)가 아니라 insert() 메서드 자체의 쿼리 파라미터다.
    notify_subscribers = CHANNEL_NOTIFY_SUBSCRIBERS_MAP.get(str(channel_num).strip(), True)
    print(f"   🔔 구독자 알림 전송: {notify_subscribers}")

    print(f"🎬 업로드: {title}")
    request = service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
        notifySubscribers=notify_subscribers,
    )

    response = None
    while response is None:
        status_obj, response = request.next_chunk()
        if status_obj:
            print(f"   {int(status_obj.progress() * 100)}%...")

    video_id = response["id"]
    # 2026-07-25 수정: 링크도 실제 판정(is_short)에 맞춰 /shorts/ 또는
    # /watch?v= 형태로 출력 — 예전엔 롱폼이어도 무조건 /shorts/ 링크였음.
    final_url = f"https://youtube.com/shorts/{video_id}" if is_short else f"https://youtu.be/{video_id}"
    print(f"✅ 완료! {final_url}")

    # 2026-07-26 추가: 재생목록/고정댓글 자동화. 둘 다 영상 업로드 자체가 이미
    # 끝난 뒤에 실행되므로, 여기서 실패해도(권한 부족 403 등) 업로드 성공
    # 자체는 절대 되돌리지 않는다 — 경고만 출력하고 넘어간다.
    if playlist_name.strip():
        try:
            playlist_id = ensure_playlist(service, playlist_name.strip(), playlist_description.strip())
            add_to_playlist(service, playlist_id, video_id)
        except HttpError as e:
            print(f"   ⚠️ 재생목록 처리 실패(권한 부족일 수 있음, get_youtube_token.py로 "
                  f"스코프 재발급 필요할 수 있음): {e}")
        except Exception as e:
            print(f"   ⚠️ 재생목록 처리 중 예상치 못한 오류: {e}")

    if pinned_comment.strip():
        try:
            post_comment_candidate(service, video_id, pinned_comment.strip())
        except HttpError as e:
            print(f"   ⚠️ 댓글 작성 실패(권한 부족일 수 있음): {e}")
        except Exception as e:
            print(f"   ⚠️ 댓글 작성 중 예상치 못한 오류: {e}")

    return video_id, is_short


# ──────────────────────────────────────────
# 메인
# ──────────────────────────────────────────
def main():
    print("=" * 50)
    now_kst = datetime.now(KST)
    print(f"🎬 YouTube 자동 업로드 v5 ({now_kst.strftime('%Y-%m-%d %H:%M KST')})")
    print(f"   대상 시트: {', '.join(SHEET_NAMES)}")
    print("=" * 50)

    client = get_client()

    # 여러 시트를 순회하며 업로드할 영상 탐색
    # 시트별로 하나씩 처리(한 번 실행에 시트당 최대 1개 업로드)
    for sheet_name in SHEET_NAMES:
        print(f"\n📄 시트 확인: {sheet_name}")
        try:
            sheet = get_sheet(client, sheet_name)
        except Exception as e:
            print(f"   ⚠️ 시트 열기 실패: {e}")
            continue

        # 2026-08-16 추가 — get_all_values() 재시도(_retry_gspread_call)로도
        # 못 넘긴 지속적인 오류(또는 재시도 대상이 아닌 오류)라면, 이 시트만
        # 건너뛰고 나머지 시트는 계속 처리한다 — 예전엔 여기서 예외가 나면
        # main()의 for 루프 전체가 죽어서 뒤에 있는 다른 채널 시트들은
        # 아예 시도조차 안 됐다.
        try:
            row_num, row, scheduled = get_next_video(sheet)
        except Exception as e:
            print(f"   ⚠️ {sheet_name} 시트 확인 실패(다음 시트로 계속 진행): {e}")
            continue

        if row is None:
            print("   ⚠️  업로드할 영상 없음 (E열='업로드전' 확인)")
            continue

        title       = row[0].strip()   # A열
        script      = row[1].strip()   # B열
        video_url   = row[2].strip()   # C열 젠스파크
        dropbox_url = row[3].strip()   # D열 드롭박스
        channel_num = row[5].strip() if len(row) > 5 else "1"  # F열

        # 2026-07-26 추가, 2026-07-26 컬럼 위치 수정: 처음엔 I/J/K/L열을 썼으나,
        # 27/28/29번 콘텐츠 생성 프로젝트가 이미 A~N(14열) 스키마를 공유하고
        # 있다는 게 뒤늦게 확인됨(I=상태, J=수집일시, K=테마ID, L=생성ID —
        # 전부 이미 다른 용도로 쓰이고 있었음). 그 상태로 뒀다면 예를 들어
        # L열(생성ID, "20260726153045" 같은 숫자 문자열)이 "고정 댓글 문구"로
        # 그대로 읽혀서 실제 영상에 의미 없는 숫자 댓글이 자동으로 달릴
        # 뻔했다 — 실사고로 이어지기 전에 발견해서 기존 스키마와 절대
        # 겹치지 않는 O/P/Q/R(15~18번째 열)로 옮김. O/P/Q/R은 전부 선택
        # 입력(없으면 기존과 100% 동일하게 동작 — 챕터/재생목록/댓글 기능
        # 자체를 건너뜀). 기존 A~N열 구조는 전혀 건드리지 않아 A~H만 쓰는
        # 단순 시트(genspark_to_dropbox.py, youtube_manager_ui.py 등)와
        # A~N을 쓰는 29번 같은 시트 모두 수정 없이 그대로 호환된다.
        #
        # ⚠️ 29번 프로젝트는 챕터를 이 O열이 아니라 B열(설명란)에 직접
        # 이어붙이는 별도 메커니즘(storage.append_chapters_to_sheet_description)을
        # 이미 쓰고 있으므로, 29번 시트에서는 O열이 항상 비어있는 게 정상이다
        # — 그래도 chapters_raw가 비어있으면 조용히 건너뛰므로 문제없다.
        chapters_raw         = row[14].strip() if len(row) > 14 else ""  # O열: "0:00 제목 | 1:30 제목2 | ..."
        playlist_name        = row[15].strip() if len(row) > 15 else ""  # P열: 재생목록 이름
        playlist_description = row[16].strip() if len(row) > 16 else ""  # Q열: 재생목록 설명
        pinned_comment       = row[17].strip() if len(row) > 17 else ""  # R열: 고정 댓글용 문구

        # 2026-07-30 추가: S열은 "이 영상 하나만" AI 공개 여부를 채널 기본값과
        # 다르게 강제하고 싶을 때만 쓰는 선택 오버라이드. 비어있으면(대부분의
        # 경우) 아래에서 CHANNEL_SYNTHETIC_MEDIA_MAP의 채널 기본값을 그대로 씀.
        synthetic_override_raw = row[18].strip().lower() if len(row) > 18 else ""  # S열: true/false, 비우면 채널 기본값
        if synthetic_override_raw in ("true", "1", "yes", "예"):
            contains_synthetic_media = True
        elif synthetic_override_raw in ("false", "0", "no", "아니요"):
            contains_synthetic_media = False
        else:
            contains_synthetic_media = CHANNEL_SYNTHETIC_MEDIA_MAP.get(str(channel_num).strip())

        print(f"\n📋 업로드 정보:")
        print(f"   제목: {title}")
        print(f"   채널: {CHANNEL_NAMES.get(channel_num, channel_num)}")
        if dropbox_url and "drive.google.com" in dropbox_url:
            _source_label = "구글드라이브"
        elif dropbox_url:
            _source_label = "드롭박스"
        else:
            _source_label = "젠스파크 직접"
        print(f"   소스: {_source_label}")
        print(f"   예약: {scheduled if scheduled else '즉시공개'}")
        print(f"   챕터(O열): {'있음' if chapters_raw else '없음(29번처럼 B열에 직접 포함됐을 수 있음)'}")
        print(f"   재생목록(P열): {playlist_name if playlist_name else '없음(P열 비어있음)'}")
        print(f"   고정댓글(R열): {'있음' if pinned_comment else '없음(R열 비어있음)'}")
        print(f"   AI 사용 공개(S열/채널기본값): {contains_synthetic_media if contains_synthetic_media is not None else '미지정(스튜디오 기본값/자동감지에 맡김)'}")

        # 2026-08-23 추가 — 사용자 리포트: 같은 영상이 하루에 3~4번씩
        # 중복 업로드됨(그중 2건은 "처리 중단됨"). 원인: get_next_video()가
        # 행을 고른 시점부터 mark_as_done()으로 E열이 "업로드완료"로 바뀌는
        # 시점 사이에 다운로드+업로드하는 시간(긴 영상은 30분 스케줄
        # 주기보다 오래 걸릴 수 있음)이 걸리는데, 그 사이에 겹쳐서 실행된
        # 다른 실행이 같은 행을 또 "업로드전"으로 보고 집어버림. 워크플로
        # 차원의 근본 해결(auto_upload.yml의 concurrency 설정)과 별개로,
        # 여기서도 다운로드 시작 전에 바로 E열을 "업로드중"으로 찜해서
        # (get_next_video()는 정확히 "업로드전"인 행만 고르므로 "업로드중"은
        # 자동으로 건너뛰어짐) concurrency로 못 막는 경우(예: 사람이 로컬
        # 에서 upload.py를 직접 실행)에도 중복 픽업을 막는다. 다운로드/
        # 업로드가 실패하면 except에서 "업로드전"으로 되돌려서 다음 실행
        # 때 정상적으로 재시도되게 한다("업로드중"에 영영 갇히는 것 방지).
        sheet.update_cell(row_num, 5, "업로드중")

        try:
            local_path = download_video(video_url, dropbox_url)
        except Exception as e:
            sheet.update_cell(row_num, 5, "업로드전")
            print(f"   ❌ [{sheet_name}] 다운로드 실패 — '업로드전'으로 되돌림, 다음 실행에서 재시도: {e}")
            continue

        try:
            yt_service = get_youtube_service(channel_num)
            video_id, is_short = upload_to_youtube(
                yt_service, local_path, title, script, scheduled, channel_num,
                chapters_raw=chapters_raw,
                playlist_name=playlist_name,
                playlist_description=playlist_description,
                pinned_comment=pinned_comment,
                contains_synthetic_media=contains_synthetic_media,
                sheet_name=sheet_name,
            )
            mark_as_done(sheet, row_num, video_id, is_short)
            print(f"\n🎉 [{sheet_name}] 완료!")
        except Exception as e:
            sheet.update_cell(row_num, 5, "업로드전")
            print(f"   ❌ [{sheet_name}] 업로드 실패 — '업로드전'으로 되돌림, 다음 실행에서 재시도: {e}")
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)

if __name__ == "__main__":
    main()