"""
multi_uploader.py — 멀티플랫폼 동시 업로드 공통 모듈 v1.0
────────────────────────────────────────────────────────
지원 플랫폼:
  - YouTube  : 기존 upload.py 로직 그대로 흡수
  - Instagram: Graph API (Reels) — Dropbox 공개 URL 활용
  - TikTok   : Content Posting API — 파일 직접 업로드

사용법 (upload.py에서 호출):
    from multi_uploader import MultiUploader
    uploader = MultiUploader(channel_num="4")
    results = uploader.upload_all(
        video_path   = "/tmp/video.mp4",
        title        = "제목",
        description  = "설명 #shorts",
        scheduled    = "2025-07-01 09:00",   # 없으면 ""
        dropbox_url  = "https://dl.dropbox..."  # Instagram용
    )
    # results = {"youtube": "VIDEO_ID", "instagram": "MEDIA_ID", "tiktok": "PUBLISH_ID"}

환경변수 (.env / GitHub Secrets):
    # 기존 (YouTube)
    YOUTUBE_TOKEN_JSON_CH1 ~ CH9
    GOOGLE_SERVICE_ACCOUNT_JSON
    GOOGLE_SHEET_ID

    # Instagram (신규)
    INSTAGRAM_ACCESS_TOKEN_CH{N}   # 채널별 Graph API 토큰
    INSTAGRAM_USER_ID_CH{N}        # 채널별 IG 비즈니스 계정 ID

    # TikTok (신규, API 승인 후 활성화)
    TIKTOK_ACCESS_TOKEN_CH{N}      # 채널별 TikTok 토큰

Google Sheet 열 구조 (기존 + 신규):
    A: 제목      B: 스크립트   C: 젠스파크URL  D: 드롭박스URL
    E: 상태      F: 채널번호   G: 예약일시
    H: YouTube URL (기존 mark_as_done이 기록)
    I: Instagram URL (신규)
    J: TikTok URL   (신규)
"""

import os
import json
import time
import requests
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

# ──────────────────────────────────────────────────────────
# 채널번호 → 플랫폼별 설정 매핑
# ──────────────────────────────────────────────────────────
# 각 채널이 어느 플랫폼에 업로드할지 제어
# True = 업로드, False = 건너뜀
CHANNEL_PLATFORM_MAP = {
    #  채널번호: {youtube, instagram, tiktok}
    "1": {"youtube": True,  "instagram": False, "tiktok": False},  # 데일리인사이트
    "2": {"youtube": True,  "instagram": False, "tiktok": False},  # 모먼트랩
    "3": {"youtube": True,  "instagram": False, "tiktok": False},  # 생활정보TV
    "4": {"youtube": True,  "instagram": True,  "tiktok": True },  # 오늘의회사썰 (카툰썰)
    "5": {"youtube": True,  "instagram": False, "tiktok": False},  # 행복시니어TV
    "6": {"youtube": True,  "instagram": False, "tiktok": False},  # 데일리AI브리핑
    "7": {"youtube": True,  "instagram": False, "tiktok": False},  # HealthierLivingToday
    "8": {"youtube": True,  "instagram": False, "tiktok": False},  # TalkToMeInKorean
    "9": {"youtube": True,  "instagram": False, "tiktok": False},  # GlobalTopTier
    "10": {"youtube": True, "instagram": True,  "tiktok": True },  # MindShift English (신규)
}

# 채널번호 → Instagram 콘텐츠 언어 (해시태그 자동 추가용)
CHANNEL_LANGUAGE = {
    "1": "ko", "2": "ko", "3": "ko", "4": "ko", "5": "ko",
    "6": "ko", "7": "en", "8": "en", "9": "en", "10": "en",
}


class MultiUploader:
    """
    YouTube + Instagram + TikTok 동시 업로드 클래스
    채널번호로 초기화하면 해당 채널의 플랫폼 설정을 자동으로 적용
    """

    def __init__(self, channel_num: str = "1"):
        self.channel_num = str(channel_num).strip()
        self.platform_config = CHANNEL_PLATFORM_MAP.get(
            self.channel_num,
            {"youtube": True, "instagram": False, "tiktok": False}
        )
        self.language = CHANNEL_LANGUAGE.get(self.channel_num, "ko")
        print(f"📡 MultiUploader 초기화: 채널{self.channel_num} | "
              f"YT={self.platform_config['youtube']} "
              f"IG={self.platform_config['instagram']} "
              f"TT={self.platform_config['tiktok']}")

    # ──────────────────────────────────────────────────────
    # 메인: 전체 플랫폼 동시 업로드
    # ──────────────────────────────────────────────────────
    def upload_all(
        self,
        video_path: str,
        title: str,
        description: str,
        scheduled: str = "",
        dropbox_url: str = "",
        youtube_service=None,        # 기존 upload.py의 get_youtube_service() 결과
    ) -> dict:
        """
        설정된 모든 플랫폼에 업로드 후 결과 dict 반환
        결과: {"youtube": "id or None", "instagram": "id or None", "tiktok": "id or None"}
        """
        results = {"youtube": None, "instagram": None, "tiktok": None}

        # ── YouTube ──
        if self.platform_config["youtube"] and youtube_service:
            try:
                from upload import upload_to_youtube  # 기존 함수 재사용
                # 2026-07-25: upload_to_youtube()가 이제 (video_id, is_short)
                # 튜플을 반환하도록 바뀜(영상 길이 기반 숏츠 판정 추가 — upload.py
                # 참고). 링크 형식도 그에 맞춰 표시한다.
                video_id, is_short = upload_to_youtube(
                    youtube_service, video_path, title,
                    description, scheduled, self.channel_num
                )
                results["youtube"] = video_id
                final_url = f"https://youtube.com/shorts/{video_id}" if is_short else f"https://youtu.be/{video_id}"
                print(f"✅ YouTube 완료: {final_url}")
            except Exception as e:
                print(f"❌ YouTube 실패: {e}")

        # ── Instagram ──
        if self.platform_config["instagram"]:
            if not dropbox_url:
                print("⚠️ Instagram 건너뜀: Dropbox URL 없음 (공개 URL 필요)")
            else:
                try:
                    ig_id = self._upload_instagram(
                        dropbox_url=dropbox_url,
                        caption=self._build_ig_caption(title, description),
                    )
                    results["instagram"] = ig_id
                    print(f"✅ Instagram 완료: media_id={ig_id}")
                except Exception as e:
                    print(f"❌ Instagram 실패: {e}")

        # ── TikTok ──
        if self.platform_config["tiktok"]:
            try:
                tt_id = self._upload_tiktok(
                    video_path=video_path,
                    title=title,
                    description=description,
                )
                results["tiktok"] = tt_id
                print(f"✅ TikTok 완료: publish_id={tt_id}")
            except NotImplementedError:
                print("⏸️ TikTok: API 승인 대기 중 (환경변수 설정 후 활성화)")
            except Exception as e:
                print(f"❌ TikTok 실패: {e}")

        return results

    # ──────────────────────────────────────────────────────
    # Instagram Reels 업로드 (Graph API)
    # ──────────────────────────────────────────────────────
    def _upload_instagram(self, dropbox_url: str, caption: str) -> str:
        """
        Instagram Graph API로 Reels 업로드
        필요 환경변수:
            INSTAGRAM_ACCESS_TOKEN_CH{N}
            INSTAGRAM_USER_ID_CH{N}

        흐름:
            1) 미디어 컨테이너 생성 (video_url = Dropbox 공개 URL)
            2) 처리 완료 대기 (폴링)
            3) 게시 (publish)
        """
        token   = self._get_env(f"INSTAGRAM_ACCESS_TOKEN_CH{self.channel_num}")
        user_id = self._get_env(f"INSTAGRAM_USER_ID_CH{self.channel_num}")

        # Dropbox URL을 직접 다운로드 가능한 형태로 변환
        video_url = self._to_dropbox_direct(dropbox_url)
        print(f"📸 Instagram 업로드 시작...")

        # ── Step 1: 컨테이너 생성 ──
        container_res = requests.post(
            f"https://graph.facebook.com/v19.0/{user_id}/media",
            data={
                "media_type": "REELS",
                "video_url":  video_url,
                "caption":    caption[:2200],   # IG 캡션 최대 2200자
                "access_token": token,
            },
            timeout=60,
        )
        container_res.raise_for_status()
        container_data = container_res.json()

        if "error" in container_data:
            raise Exception(f"컨테이너 생성 실패: {container_data['error']}")

        creation_id = container_data["id"]
        print(f"   컨테이너 생성: {creation_id}")

        # ── Step 2: 처리 완료 대기 (최대 5분) ──
        self._wait_for_ig_container(creation_id, token)

        # ── Step 3: 게시 ──
        publish_res = requests.post(
            f"https://graph.facebook.com/v19.0/{user_id}/media_publish",
            data={
                "creation_id":  creation_id,
                "access_token": token,
            },
            timeout=30,
        )
        publish_res.raise_for_status()
        publish_data = publish_res.json()

        if "error" in publish_data:
            raise Exception(f"게시 실패: {publish_data['error']}")

        return publish_data["id"]

    def _wait_for_ig_container(self, creation_id: str, token: str, max_wait: int = 300):
        """Instagram 미디어 처리 완료까지 폴링 (최대 max_wait초)"""
        print(f"   IG 처리 대기 중...", end="", flush=True)
        elapsed = 0
        interval = 10
        while elapsed < max_wait:
            time.sleep(interval)
            elapsed += interval
            res = requests.get(
                f"https://graph.facebook.com/v19.0/{creation_id}",
                params={"fields": "status_code", "access_token": token},
                timeout=15,
            )
            status = res.json().get("status_code", "")
            print(f" {status}({elapsed}s)...", end="", flush=True)
            if status == "FINISHED":
                print(" ✅")
                return
            elif status == "ERROR":
                raise Exception("Instagram 미디어 처리 오류")
        raise TimeoutError("Instagram 처리 시간 초과 (5분)")

    # ──────────────────────────────────────────────────────
    # TikTok 업로드 (Content Posting API)
    # ──────────────────────────────────────────────────────
    def _upload_tiktok(self, video_path: str, title: str, description: str) -> str:
        """
        TikTok Content Posting API로 업로드
        필요 환경변수:
            TIKTOK_ACCESS_TOKEN_CH{N}

        ※ TikTok Developer 계정 + Content Posting API 승인 필요
          승인 전까지는 NotImplementedError 발생 → upload_all에서 graceful skip
        """
        token = os.environ.get(f"TIKTOK_ACCESS_TOKEN_CH{self.channel_num}")
        if not token:
            raise NotImplementedError("TikTok 토큰 없음 — API 승인 후 환경변수 설정 필요")

        video_size = os.path.getsize(video_path)
        print(f"🎵 TikTok 업로드 시작 ({video_size / 1024 / 1024:.1f}MB)...")

        # ── Step 1: 업로드 초기화 ──
        init_res = requests.post(
            "https://open.tiktokapis.com/v2/post/publish/video/init/",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json; charset=UTF-8",
            },
            json={
                "post_info": {
                    "title":               title[:150],
                    "privacy_level":       "PUBLIC_TO_EVERYONE",
                    "disable_duet":        False,
                    "disable_comment":     False,
                    "disable_stitch":      False,
                    "video_cover_timestamp_ms": 1000,
                },
                "source_info": {
                    "source":            "FILE_UPLOAD",
                    "video_size":        video_size,
                    "chunk_size":        video_size,
                    "total_chunk_count": 1,
                },
            },
            timeout=30,
        )
        init_res.raise_for_status()
        init_data = init_res.json()

        if init_data.get("error", {}).get("code") != "ok":
            raise Exception(f"TikTok 초기화 실패: {init_data.get('error')}")

        upload_url  = init_data["data"]["upload_url"]
        publish_id  = init_data["data"]["publish_id"]
        print(f"   publish_id: {publish_id}")

        # ── Step 2: 영상 업로드 ──
        with open(video_path, "rb") as f:
            video_data = f.read()

        put_res = requests.put(
            upload_url,
            headers={
                "Content-Type":  "video/mp4",
                "Content-Length": str(video_size),
                "Content-Range": f"bytes 0-{video_size - 1}/{video_size}",
            },
            data=video_data,
            timeout=300,
        )
        put_res.raise_for_status()
        print(f"   TikTok 영상 전송 완료")

        return publish_id

    # ──────────────────────────────────────────────────────
    # 유틸리티
    # ──────────────────────────────────────────────────────
    def _get_env(self, key: str) -> str:
        """환경변수 필수 조회 — 없으면 명확한 오류"""
        val = os.environ.get(key)
        if not val:
            raise EnvironmentError(
                f"환경변수 누락: {key}\n"
                f"  → .env 또는 GitHub Secrets에 추가 필요"
            )
        return val

    def _to_dropbox_direct(self, url: str) -> str:
        """Dropbox URL을 직접 다운로드 가능한 형태로 변환"""
        import re
        url = re.sub(r'&st=[^&]*', '', url)
        url = re.sub(r'\?st=[^&]*&', '?', url)
        url = re.sub(r'\?st=[^&]*$', '', url)
        if "dl=0" in url:
            return url.replace("dl=0", "dl=1")
        elif "dl=1" not in url:
            return url + ("&dl=1" if "?" in url else "?dl=1")
        return url

    def _build_ig_caption(self, title: str, description: str) -> str:
        """Instagram 캡션 생성 (제목 + 설명 + 해시태그)"""
        # 기존 설명에서 해시태그 추출
        existing_tags = [w for w in description.split() if w.startswith("#")]

        # 언어별 기본 해시태그 추가
        if self.language == "ko":
            default_tags = ["#shorts", "#shortvideo", "#유튜브쇼츠"]
        else:
            default_tags = ["#shorts", "#shortvideo", "#reels"]

        all_tags = existing_tags.copy()
        for tag in default_tags:
            if tag.lower() not in [t.lower() for t in all_tags]:
                all_tags.append(tag)

        # 캡션 조합
        caption = title
        if description:
            # 해시태그 제거한 본문만 추출
            body = " ".join(w for w in description.split() if not w.startswith("#"))
            if body:
                caption += f"\n\n{body}"
        if all_tags:
            caption += "\n\n" + " ".join(all_tags)

        return caption


# ──────────────────────────────────────────────────────────
# Google Sheet 결과 기록 헬퍼
# (upload.py의 mark_as_done에 추가로 호출)
# ──────────────────────────────────────────────────────────
def mark_multiplatform_results(sheet, row_num: int, results: dict):
    """
    upload_all() 결과를 시트 I열(Instagram), J열(TikTok)에 기록
    H열(YouTube URL)은 기존 mark_as_done()이 처리
    """
    if results.get("instagram"):
        ig_url = f"https://www.instagram.com/p/{results['instagram']}/"
        sheet.update_cell(row_num, 9, ig_url)    # I열
        print(f"   📸 Instagram URL → I열: {ig_url}")

    if results.get("tiktok"):
        # TikTok은 publish_id만 있고 최종 URL은 처리 후 조회 필요
        sheet.update_cell(row_num, 10, f"TT:{results['tiktok']}")  # J열
        print(f"   🎵 TikTok publish_id → J열: {results['tiktok']}")


# ──────────────────────────────────────────────────────────
# 단독 실행 테스트
# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== MultiUploader 단독 테스트 ===")
    print()

    # 환경변수 체크
    required = ["GOOGLE_SHEET_ID", "GOOGLE_SERVICE_ACCOUNT_JSON"]
    optional = [
        "INSTAGRAM_ACCESS_TOKEN_CH4", "INSTAGRAM_USER_ID_CH4",
        "TIKTOK_ACCESS_TOKEN_CH4",
    ]

    print("[ 필수 환경변수 ]")
    for k in required:
        v = os.environ.get(k)
        print(f"  {'✅' if v else '❌'} {k}")

    print()
    print("[ 선택 환경변수 (Instagram/TikTok) ]")
    for k in optional:
        v = os.environ.get(k)
        print(f"  {'✅' if v else '⚠️ 미설정'} {k}")

    print()
    print("[ 채널별 플랫폼 설정 ]")
    for ch, cfg in CHANNEL_PLATFORM_MAP.items():
        flags = []
        if cfg["youtube"]:   flags.append("YouTube")
        if cfg["instagram"]: flags.append("Instagram")
        if cfg["tiktok"]:    flags.append("TikTok")
        print(f"  채널{ch}: {', '.join(flags)}")

    print()
    print("사용 방법:")
    print("  from multi_uploader import MultiUploader, mark_multiplatform_results")
    print("  uploader = MultiUploader(channel_num='4')")
    print("  results = uploader.upload_all(video_path, title, desc, scheduled, dropbox_url, yt_service)")
    print("  mark_multiplatform_results(sheet, row_num, results)")
