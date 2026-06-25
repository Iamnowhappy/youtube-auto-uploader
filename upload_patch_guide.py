"""
upload.py 패치 가이드 — multi_uploader 연동
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
기존 upload.py에서 아래 두 곳만 수정하면 됩니다.

[1] 파일 상단 import 추가
[2] main() 함수 내 try 블록 교체

나머지 함수들 (get_client, get_sheet, get_next_video,
mark_as_done, download_video, get_youtube_service,
upload_to_youtube) 은 그대로 유지합니다.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# ──────────────────────────────────────────
# [1] 파일 상단에 추가할 import
#     (기존 import 블록 바로 아래에 추가)
# ──────────────────────────────────────────
PATCH_IMPORT = """
# ── 멀티플랫폼 업로드 모듈 ──
from multi_uploader import MultiUploader, mark_multiplatform_results
"""

# ──────────────────────────────────────────
# [2] main() 함수 내 try 블록 교체
#     기존 코드:
#         try:
#             yt_service = get_youtube_service(channel_num)
#             video_id = upload_to_youtube(...)
#             mark_as_done(sheet, row_num, video_id)
#             print(f"\n🎉 [{sheet_name}] 완료!")
#         finally:
#             if os.path.exists(local_path):
#                 os.remove(local_path)
#
#     교체 후:
# ──────────────────────────────────────────
PATCH_MAIN_TRY = '''
        try:
            yt_service = get_youtube_service(channel_num)

            # ── 멀티플랫폼 동시 업로드 ──
            uploader = MultiUploader(channel_num=channel_num)
            results = uploader.upload_all(
                video_path    = local_path,
                title         = title,
                description   = script,
                scheduled     = scheduled,
                dropbox_url   = dropbox_url,
                youtube_service = yt_service,
            )

            # ── 시트 기록 ──
            if results["youtube"]:
                mark_as_done(sheet, row_num, results["youtube"])
            mark_multiplatform_results(sheet, row_num, results)

            # ── 결과 요약 ──
            ok  = [p for p, v in results.items() if v]
            fail = [p for p, v in results.items() if v is None]
            print(f"\\n🎉 [{sheet_name}] 완료! 성공={ok}" +
                  (f" | 실패/건너뜀={fail}" if fail else ""))

        finally:
            if os.path.exists(local_path):
                os.remove(local_path)
'''

# ──────────────────────────────────────────
# 완성된 main() 전체 (복붙용)
# ──────────────────────────────────────────
COMPLETE_MAIN = '''
def main():
    print("=" * 50)
    now_kst = datetime.now(KST)
    print(f"🎬 YouTube 자동 업로드 v5 ({now_kst.strftime('%Y-%m-%d %H:%M KST')})")
    print(f"   대상 시트: {', '.join(SHEET_NAMES)}")
    print("=" * 50)

    client = get_client()

    for sheet_name in SHEET_NAMES:
        print(f"\\n📄 시트 확인: {sheet_name}")
        try:
            sheet = get_sheet(client, sheet_name)
        except Exception as e:
            print(f"   ⚠️ 시트 열기 실패: {e}")
            continue

        row_num, row, scheduled = get_next_video(sheet)

        if row is None:
            print("   ⚠️  업로드할 영상 없음 (E열=\'업로드전\' 확인)")
            continue

        title       = row[0].strip()
        script      = row[1].strip()
        video_url   = row[2].strip()
        dropbox_url = row[3].strip()
        channel_num = row[5].strip() if len(row) > 5 else "1"

        print(f"\\n📋 업로드 정보:")
        print(f"   제목: {title}")
        print(f"   채널: {CHANNEL_NAMES.get(channel_num, channel_num)}")
        print(f"   소스: {\'드롭박스\' if dropbox_url else \'젠스파크 직접\'}")
        print(f"   예약: {scheduled if scheduled else \'즉시공개\'}")

        local_path = download_video(video_url, dropbox_url)

        try:
            yt_service = get_youtube_service(channel_num)

            # ── 멀티플랫폼 동시 업로드 ──
            uploader = MultiUploader(channel_num=channel_num)
            results = uploader.upload_all(
                video_path      = local_path,
                title           = title,
                description     = script,
                scheduled       = scheduled,
                dropbox_url     = dropbox_url,
                youtube_service = yt_service,
            )

            # ── 시트 기록 ──
            if results["youtube"]:
                mark_as_done(sheet, row_num, results["youtube"])
            mark_multiplatform_results(sheet, row_num, results)

            # ── 결과 요약 ──
            ok   = [p for p, v in results.items() if v]
            fail = [p for p, v in results.items() if v is None]
            print(f"\\n🎉 [{sheet_name}] 완료! 성공={ok}" +
                  (f" | 실패/건너뜀={fail}" if fail else ""))

        finally:
            if os.path.exists(local_path):
                os.remove(local_path)


if __name__ == "__main__":
    main()
'''

if __name__ == "__main__":
    print(PATCH_IMPORT)
    print(COMPLETE_MAIN)
