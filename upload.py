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
    "9": "UCQ7JqaT39C1IuDelJcNVI1Q",   # GlobalTopTier
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
    "9": "GlobalTopTier",
}

import os
import json
import re
import tempfile
import requests
import gspread
from datetime import datetime, timezone, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials as OAuthCredentials
from google.auth.transport.requests import Request

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
    all_rows  = sheet.get_all_values()

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

        if _uploaded_today_for_channel(all_rows, ch_num, today_str):
            print(f"   🛑 {i}행: 채널{ch_num}({CHANNEL_NAMES.get(ch_num, ch_num)})은 "
                  f"오늘({today_str}) 이미 1개 업로드 완료 → 안전장치로 건너뜀 "
                  f"(예약이 겹쳤더라도 하루 1개로 제한, 다음 실행에서 자동 재시도)")
            continue

        return i, row, scheduled

    return None, None, None


def mark_as_done(sheet, row_num, video_id):
    now_kst = datetime.now(KST)
    sheet.update_cell(row_num, 5, "업로드완료")
    # G열을 '실제 업로드된 일시'로 갱신 — 예약이 밀려서 늦게 올라간 경우에도
    # 정확한 실제 업로드 시각을 남겨야 위의 하루 1개 안전장치가 제대로 동작한다.
    sheet.update_cell(row_num, 7, now_kst.strftime("%Y-%m-%d %H:%M"))
    sheet.update_cell(row_num, 8, f"https://youtube.com/shorts/{video_id}")
    print(f"✅ 시트 업데이트: {row_num}행 → 업로드완료 (G열 = 실제 업로드 시각 {now_kst.strftime('%Y-%m-%d %H:%M')})")


# ──────────────────────────────────────────
# 영상 다운로드 (젠스파크 or 드롭박스)
# ──────────────────────────────────────────
def download_video(video_url, dropbox_url):
    """
    D열 드롭박스 URL 있으면 드롭박스 우선
    없으면 C열 젠스파크 URL 직접 다운로드
    """
    if dropbox_url:
        print(f"📦 드롭박스에서 다운로드...")
        return download_url(dropbox_url, is_dropbox=True)
    else:
        print(f"✨ 젠스파크에서 직접 다운로드...")
        return download_url(video_url, is_dropbox=False)


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


def upload_to_youtube(service, video_path, title, description, scheduled="", channel_num="1"):
    channel_id   = CHANNEL_MAP.get(str(channel_num).strip(), CHANNEL_MAP["1"])
    channel_name = CHANNEL_NAMES.get(str(channel_num).strip(), f"채널{channel_num}")
    print(f"📺 채널: {channel_name} ({channel_id})")

    # 해시태그 추출
    tags = []
    for word in description.split():
        if word.startswith("#"):
            tags.append(word.lstrip("#"))
    if "shorts" not in [t.lower() for t in tags]:
        tags.insert(0, "shorts")
    if "#shorts" not in description.lower():
        description += "\n\n#shorts"

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
            "defaultLanguage": "ko",
            "channelId": channel_id,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        }
    }
    if publish_at:
        body["status"]["publishAt"] = publish_at

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024 * 5
    )

    print(f"🎬 업로드: {title}")
    request = service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status_obj, response = request.next_chunk()
        if status_obj:
            print(f"   {int(status_obj.progress() * 100)}%...")

    video_id = response["id"]
    print(f"✅ 완료! https://youtube.com/shorts/{video_id}")
    return video_id


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

        row_num, row, scheduled = get_next_video(sheet)

        if row is None:
            print("   ⚠️  업로드할 영상 없음 (E열='업로드전' 확인)")
            continue

        title       = row[0].strip()   # A열
        script      = row[1].strip()   # B열
        video_url   = row[2].strip()   # C열 젠스파크
        dropbox_url = row[3].strip()   # D열 드롭박스
        channel_num = row[5].strip() if len(row) > 5 else "1"  # F열

        print(f"\n📋 업로드 정보:")
        print(f"   제목: {title}")
        print(f"   채널: {CHANNEL_NAMES.get(channel_num, channel_num)}")
        print(f"   소스: {'드롭박스' if dropbox_url else '젠스파크 직접'}")
        print(f"   예약: {scheduled if scheduled else '즉시공개'}")

        local_path = download_video(video_url, dropbox_url)

        try:
            yt_service = get_youtube_service(channel_num)
            video_id = upload_to_youtube(
                yt_service, local_path, title, script, scheduled, channel_num
            )
            mark_as_done(sheet, row_num, video_id)
            print(f"\n🎉 [{sheet_name}] 완료!")
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)

if __name__ == "__main__":
    main()
