"""
watermark_ops.py — 채널 워터마크(구독 유도 아이콘) 등록 전담 모듈

역할: YouTube Data API의 watermarks.set으로 채널에 워터마크 이미지를 등록한다.
채널 브랜딩 성격의 "1회성" 설정이라 매 업로드마다 실행되는 upload_to_youtube()
흐름과는 분리해서, channel_watermark_setup.py에서만 호출한다.

⚠️ 오해하기 쉬운 점: 이 기능은 playlist_ops.py/comment_ops.py와 달리
"youtube.upload" 스코프만으로도 동작한다(공식 문서
https://developers.google.com/youtube/v3/docs/watermarks/set 의 Authorization
표에 youtube.upload가 포함돼 있음을 확인함, 2026-07-30). 그래서 기존
youtube_token_ch*.json(업로드 전용 스코프로 발급됐을 가능성이 높음)을 그대로
써도 대부분 동작해야 한다 — 재생목록/댓글처럼 스코프 재발급이 필수는 아니다.
"""

from __future__ import annotations

import os

from googleapiclient.http import MediaFileUpload


def set_channel_watermark(
    service,
    channel_id: str,
    image_path: str,
    corner: str = "bottomRight",
    offset_ms: int = 0,
    duration_ms: int | None = None,
) -> None:
    """
    채널에 워터마크 이미지를 등록한다.

    corner: "topLeft" | "topRight" | "bottomLeft" | "bottomRight"
    offset_ms: 영상 시작 후 몇 ms 뒤에 나타날지 (기본 0 = 시작하자마자)
    duration_ms: 몇 ms 동안 보여줄지. None이면 필드 자체를 생략 —
                 공식 샘플 스크립트(youtube/api-samples/set_watermark.py)도
                 durationMs를 생략한 예시를 쓰고 있고, 이 경우 영상 내내
                 노출되는 "구독 워터마크" 방식으로 동작한다(스튜디오에서
                 기본 제공하는 워터마크와 동일한 동작).
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"워터마크 이미지 파일을 찾을 수 없음: {image_path}")

    timing = {"type": "offsetFromStart", "offsetMs": offset_ms}
    if duration_ms is not None:
        timing["durationMs"] = duration_ms

    body = {
        "position": {"type": "corner", "cornerPosition": corner},
        "timing": timing,
    }

    media = MediaFileUpload(image_path)
    service.watermarks().set(
        channelId=channel_id,
        body=body,
        media_body=media,
    ).execute()
    print(f"✅ 워터마크 등록 완료 — channel={channel_id}, image={image_path}, corner={corner}")


def unset_channel_watermark(service, channel_id: str) -> None:
    """등록된 워터마크를 제거한다(잘못 등록했을 때 되돌리는 용도)."""
    service.watermarks().unset(channelId=channel_id).execute()
    print(f"✅ 워터마크 제거 완료 — channel={channel_id}")
