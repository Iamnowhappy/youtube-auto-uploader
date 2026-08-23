"""
comment_ops.py — 고정 댓글용 문구 작성 전담 모듈

역할: commentThreads.insert로 댓글 "작성"까지만 자동화한다. YouTube Data API에는
댓글 "고정(pin)" 전용 엔드포인트가 없으므로(2026년 기준 공식 문서 확인 완료),
작성 후 스튜디오에서 직접 고정하라는 안내를 출력한다.

⚠️ 이 함수도 playlist_ops.py와 마찬가지로 쓰기 권한 스코프가 필요하다.
"""

from __future__ import annotations


def post_comment_candidate(service, video_id: str, text: str) -> None:
    if not text.strip():
        return
    service.commentThreads().insert(
        part="snippet",
        body={
            "snippet": {
                "videoId": video_id,
                "topLevelComment": {"snippet": {"textOriginal": text}},
            }
        },
    ).execute()
    print(
        "   [댓글] 작성 완료. ※ '고정(pin)'은 API 미지원 — "
        f"https://studio.youtube.com/video/{video_id}/comments 에서 직접 상단 고정할 것"
    )
