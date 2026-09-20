"""유튜브 업로드 성공 직후 같은 영상을 인스타그램 릴스에도 자동 게시.

2026-09-13 추가 — 기존 uploaders/instagram.py(35_multi_channel_uploader,
수동 CLI용으로 이미 완성되어 있던 코드)를 그대로 재사용. 새로 구현하지 않고
sys.path로 그 프로젝트를 가져다 쓴다. .env에 IG_USER_ID/IG_ACCESS_TOKEN이
없으면(Meta 앱 설정 전) 조용히 건너뛴다 — 다른 플랫폼과 마찬가지로 준비된
것만 동작하는 구조.
"""
import sys
from pathlib import Path

_UPLOADER_DIR = Path(r"C:\Projects\35_multi_channel_uploader")
if str(_UPLOADER_DIR) not in sys.path:
    sys.path.insert(0, str(_UPLOADER_DIR))


def _log(msg: str) -> None:
    """Windows cp949 콘솔에서 이모지 print가 죽는 고질적 문제 방지
    (이 프로젝트 다른 곳들과 동일한 패턴)."""
    try:
        print(msg)
    except Exception:
        pass


def repost_to_instagram(local_path: str, title: str, description: str) -> None:
    """실패해도 이미 끝난 유튜브 업로드는 절대 되돌리지 않는다 — 항상 예외를 삼킴."""
    try:
        from uploaders.instagram import InstagramUploader
        from uploaders.base import UploadRequest

        uploader = InstagramUploader()
        if not uploader.is_configured():
            _log("   [SKIP] 인스타그램 미설정(IG_USER_ID/IG_ACCESS_TOKEN 없음) → 건너뜀"
                 " — 35_multi_channel_uploader/SETUP_GUIDE.md 3번 참고")
            return

        req = UploadRequest(video_path=Path(local_path), title=title, description=description)
        result = uploader.upload(req)
        if result.success:
            _log(f"   [OK] 인스타그램 릴스 게시 완료: {result.post_url}")
        else:
            _log(f"   [FAIL] 인스타그램 게시 실패(유튜브 업로드는 정상 완료됨): {result.message}")
    except Exception as e:
        _log(f"   [FAIL] 인스타그램 게시 중 예상치 못한 오류(유튜브 업로드는 정상 완료됨): {e}")
