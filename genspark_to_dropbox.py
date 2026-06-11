"""
YouTube 자동화 통합 관리 스크립트 v3
- 로컬 영상 / 젠스파크 URL → 드롭박스 업로드
- 드롭박스 URL 생성 후 구글 시트 D열 자동 기록
- 채널당 하루 최대 2개 기준으로 예약날짜 자동 배정
  (17:00 / 19:00 슬롯, 초과 시 다음날로 이월)
- E열 "업로드전" 자동 설정
"""

import os
import re
import sys
import json
import time
import threading
import requests
import gspread
import dropbox
from datetime import datetime, timedelta, timezone
from pathlib import Path
from google.oauth2.service_account import Credentials

# ── KST ──────────────────────────────────
KST = timezone(timedelta(hours=9))

# ── 채널 정보 ─────────────────────────────
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

# ── 드롭박스 슬롯 (하루 2개: 17:00, 19:00) ──
DAILY_SLOTS = ["17:00", "19:00"]
MAX_PER_DAY = 2


# ══════════════════════════════════════════
# 설정 로드 / 저장
# ══════════════════════════════════════════
CONFIG_PATH = Path(__file__).parent / "config.json"

def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════
# 구글 시트 연결
# ══════════════════════════════════════════
def get_sheet(cfg: dict):
    sa_path = cfg.get("google_sa_path", "")
    sheet_id   = cfg.get("sheet_id", "")
    sheet_name = cfg.get("sheet_name", "숏츠시트")

    if not sa_path or not os.path.exists(sa_path):
        raise FileNotFoundError(f"서비스 계정 키 파일 없음: {sa_path}")

    with open(sa_path, "r", encoding="utf-8") as f:
        creds_dict = json.load(f)

    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds  = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(sheet_id).worksheet(sheet_name)


# ══════════════════════════════════════════
# 드롭박스 연결
# ══════════════════════════════════════════
def get_dropbox(cfg: dict):
    app_key      = cfg.get("dropbox_app_key", "")
    app_secret   = cfg.get("dropbox_app_secret", "")
    refresh_token= cfg.get("dropbox_refresh_token", "")

    if not all([app_key, app_secret, refresh_token]):
        raise ValueError("드롭박스 설정 누락 (app_key / app_secret / refresh_token)")

    return dropbox.Dropbox(
        oauth2_refresh_token=refresh_token,
        app_key=app_key,
        app_secret=app_secret
    )


# ══════════════════════════════════════════
# 예약 슬롯 자동 배정
# ══════════════════════════════════════════
def get_next_slot(sheet) -> str:
    """
    구글 시트 G열을 스캔해서
    오늘/내일 기준으로 비어있는 슬롯(17:00, 19:00) 반환
    채널 구분 없이 전체 기준 하루 MAX_PER_DAY개 제한
    """
    all_rows = sheet.get_all_values()
    now_kst  = datetime.now(KST)

    # 기존 예약 슬롯 수집
    booked = {}   # "2026-05-26 17:00" : count
    for row in all_rows[1:]:
        while len(row) < 7:
            row.append("")
        g = row[6].strip()
        e = row[4].strip()
        if g and e in ("업로드전", "업로드완료"):
            booked[g] = booked.get(g, 0) + 1

    # 오늘부터 최대 14일 후까지 탐색
    for day_offset in range(14):
        target_date = now_kst + timedelta(days=day_offset)
        date_str    = target_date.strftime("%Y-%m-%d")

        for slot_time in DAILY_SLOTS:
            slot_key = f"{date_str} {slot_time}"

            # 과거 슬롯 스킵
            slot_dt = datetime.strptime(slot_key, "%Y-%m-%d %H:%M").replace(tzinfo=KST)
            if slot_dt <= now_kst:
                continue

            # 해당 슬롯 예약 수 확인
            if booked.get(slot_key, 0) < 1:   # 슬롯당 1개
                return slot_key

    return ""   # 14일 모두 꽉 찬 경우 (거의 없음)


# ══════════════════════════════════════════
# 드롭박스 업로드 (로컬 파일)
# ══════════════════════════════════════════
def upload_local_to_dropbox(local_path: str, dbx, log_fn=print) -> str:
    """로컬 mp4 → 드롭박스 /genspark/ → 공유 URL 반환"""
    filename     = Path(local_path).name
    dropbox_path = f"/genspark/{filename}"
    file_size    = os.path.getsize(local_path)
    CHUNK        = 50 * 1024 * 1024   # 50MB

    log_fn(f"  📤 업로드 시작: {filename} ({file_size/1024/1024:.1f}MB)")

    with open(local_path, "rb") as f:
        if file_size <= CHUNK:
            dbx.files_upload(
                f.read(), dropbox_path,
                mode=dropbox.files.WriteMode.overwrite
            )
        else:
            # 청크 업로드
            session = dbx.files_upload_session_start(f.read(CHUNK))
            cursor  = dropbox.files.UploadSessionCursor(
                session_id=session.session_id, offset=f.tell()
            )
            while f.tell() < file_size:
                remaining = file_size - f.tell()
                chunk     = f.read(CHUNK)
                if remaining <= CHUNK:
                    dbx.files_upload_session_finish(
                        chunk, cursor,
                        dropbox.files.CommitInfo(dropbox_path,
                            mode=dropbox.files.WriteMode.overwrite)
                    )
                else:
                    dbx.files_upload_session_append_v2(chunk, cursor)
                    cursor.offset = f.tell()
                pct = int(f.tell() / file_size * 100)
                log_fn(f"  ⬆️  {pct}%...")

    # 공유 링크 생성 (이미 있으면 기존 것 사용)
    try:
        link_meta = dbx.sharing_create_shared_link_with_settings(dropbox_path)
        dl_url = link_meta.url.replace("?dl=0", "?dl=1")
    except dropbox.exceptions.ApiError as e:
        if "shared_link_already_exists" in str(e):
            links  = dbx.sharing_list_shared_links(path=dropbox_path).links
            dl_url = links[0].url.replace("?dl=0", "?dl=1")
        else:
            raise

    log_fn(f"  ✅ 드롭박스 URL: {dl_url[:60]}...")
    return dl_url


# ══════════════════════════════════════════
# 젠스파크 URL → 드롭박스
# ══════════════════════════════════════════
def download_genspark(url: str, log_fn=print) -> str:
    """젠스파크 URL → 임시 파일 다운로드 → 경로 반환"""
    log_fn(f"  🌐 젠스파크 다운로드 중...")
    headers  = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, stream=True,
                            allow_redirects=True, timeout=120)
    response.raise_for_status()

    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    total = 0
    for chunk in response.iter_content(chunk_size=1024 * 1024):
        tmp.write(chunk)
        total += len(chunk)
    tmp.flush()
    tmp.close()
    log_fn(f"  ✅ 다운로드 완료: {total/1024/1024:.1f}MB")
    return tmp.name


# ══════════════════════════════════════════
# 메인 처리 함수
# ══════════════════════════════════════════
def process_pending_rows(cfg: dict, log_fn=print, manual_slot: str = "") -> dict:
    """
    구글 시트에서 처리 대상 행 탐색 후 실행
    대상: E열="기록전" 이고 (C열 젠스파크URL 또는 로컬경로) 있는 행
    manual_slot: "2026-06-08 19:00" 형식 — 입력 시 자동 슬롯 무시하고 이 시간으로 고정
    반환: {"success": n, "skip": n, "error": n}
    """
    result = {"success": 0, "skip": 0, "error": 0}

    log_fn("📊 구글 시트 연결 중...")
    sheet = get_sheet(cfg)
    log_fn("☁️  드롭박스 연결 중...")
    dbx   = get_dropbox(cfg)

    all_rows = sheet.get_all_values()
    log_fn(f"📋 전체 {len(all_rows)-1}행 스캔 중...\n")

    for i, row in enumerate(all_rows[1:], start=2):
        while len(row) < 8:
            row.append("")

        title    = row[0].strip()   # A열
        status   = row[4].strip()   # E열
        ch_num   = row[5].strip()   # F열
        g_col    = row[6].strip()   # G열 (예약날짜)
        c_col    = row[2].strip()   # C열 (젠스파크URL or 로컬경로)
        d_col    = row[3].strip()   # D열 (드롭박스URL)

        # 처리 대상: E열 "기록전" + D열 비어있음 + C열 있음
        if status != "기록전":
            continue
        if d_col:
            log_fn(f"  [{i}행] {title[:20]} → 드롭박스URL 이미 있음, 건너뜀")
            result["skip"] += 1
            continue
        if not c_col:
            log_fn(f"  [{i}행] {title[:20]} → C열 비어있음, 건너뜀")
            result["skip"] += 1
            continue

        log_fn(f"\n[{i}행] 처리 시작: {title[:30]}")
        log_fn(f"  채널: {CHANNEL_NAMES.get(ch_num, ch_num)}")

        try:
            # ① 로컬파일 vs 젠스파크 URL 판별
            #    http로 시작하면 URL, 아니면 로컬 경로로 간주
            is_url = c_col.lower().startswith("http://") or \
                     c_col.lower().startswith("https://")

            if not is_url:
                # 로컬 파일 경로
                norm_path = os.path.normpath(c_col)
                log_fn(f"  📁 로컬 파일 경로: {norm_path}")
                if not os.path.exists(norm_path):
                    log_fn(f"  ❌ 파일을 찾을 수 없음!")
                    log_fn(f"     입력 경로: {c_col}")
                    log_fn(f"     변환 경로: {norm_path}")
                    log_fn(f"     → 경로/파일명을 확인하세요 (오타, 확장자 등)")
                    result["error"] += 1
                    continue
                dl_url = upload_local_to_dropbox(norm_path, dbx, log_fn)
            else:
                log_fn(f"  🌐 젠스파크 URL 감지")
                tmp_path = download_genspark(c_col, log_fn)
                try:
                    dl_url = upload_local_to_dropbox(tmp_path, dbx, log_fn)
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)

            # ② 예약 슬롯 배정
            if g_col:
                # G열에 이미 날짜 입력됨 → 유지
                slot = g_col
                log_fn(f"  📅 기존 예약 유지: {slot}")
            elif manual_slot:
                # UI에서 수동 입력한 시간 → 전체 행에 동일 적용
                slot = manual_slot
                log_fn(f"  📅 수동 지정 시간 적용: {slot} KST")
            else:
                # 자동 슬롯 배정 (17:00 / 19:00)
                slot = get_next_slot(sheet)
                log_fn(f"  📅 예약 슬롯 자동 배정: {slot}")

            # ③ 시트 업데이트
            #    드롭박스 업로드는 지금 즉시 완료됨 (위 ①에서)
            #    YouTube 업로드만 G열 예약시간에 GitHub Actions가 처리
            sheet.update_cell(i, 4, dl_url)    # D열 드롭박스URL (즉시 기록)
            sheet.update_cell(i, 5, "업로드전") # E열 (예약 대기 상태)
            if slot:
                sheet.update_cell(i, 7, slot)  # G열 예약날짜 (자동/수동 모두 기록)

            log_fn(f"  ✅ 완료! 예약: {slot}")
            result["success"] += 1
            time.sleep(1)   # API 과호출 방지

        except Exception as e:
            import traceback
            log_fn(f"  ❌ 오류: {type(e).__name__}: {e}")
            log_fn(f"     {traceback.format_exc().splitlines()[-3] if len(traceback.format_exc().splitlines())>=3 else ''}")
            result["error"] += 1

    log_fn(f"\n{'='*40}")
    log_fn(f"🎉 처리 완료: 성공 {result['success']} / 건너뜀 {result['skip']} / 오류 {result['error']}")
    return result


# ══════════════════════════════════════════
# 단독 실행
# ══════════════════════════════════════════
if __name__ == "__main__":
    cfg = load_config()
    if not cfg:
        print("❌ config.json 없음. UI를 통해 먼저 설정하세요.")
        sys.exit(1)
    process_pending_rows(cfg)
