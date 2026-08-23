"""
playlist_ops.py — 재생목록 생성/재사용 + 영상 추가 전담 모듈

역할: 같은 이름의 재생목록이 채널에 이미 있으면 재사용하고, 없으면 새로 만든다.
이미 그 재생목록에 들어있는 영상이면 중복 추가하지 않는다.

⚠️ 주의: 이 파일의 함수들은 playlists.insert / playlistItems.insert 쓰기 권한이
필요하다. 기존 youtube_token_ch*.json이 업로드(youtube.upload) 스코프로만
발급됐다면 403(insufficientPermissions) 오류가 날 수 있다 — 이 경우
get_youtube_token.py로 더 넓은 스코프(youtube.force-ssl 또는 youtube)로 토큰을
재발급해야 한다. upload.py 쪽에서 이 오류를 잡아 경고만 출력하고 업로드 자체는
계속 진행하도록 감싸져 있다.
"""

from __future__ import annotations


def ensure_playlist(service, title: str, description: str) -> str:
    channels = service.channels().list(part="id", mine=True).execute()
    channel_id = channels["items"][0]["id"]

    existing = service.playlists().list(part="snippet", mine=True, maxResults=50).execute()
    for pl in existing.get("items", []):
        if pl["snippet"]["title"] == title:
            print(f"   [재생목록] 기존 재생목록 재사용: {title}")
            return pl["id"]

    created = service.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {"title": title, "description": description, "channelId": channel_id},
            "status": {"privacyStatus": "public"},
        },
    ).execute()
    print(f"   [재생목록] 신규 생성: {title}")
    return created["id"]


def add_to_playlist(service, playlist_id: str, video_id: str) -> None:
    items = service.playlistItems().list(
        part="contentDetails", playlistId=playlist_id, maxResults=50
    ).execute()
    for it in items.get("items", []):
        if it["contentDetails"]["videoId"] == video_id:
            print("   [재생목록] 이미 포함된 영상 — 중복 추가 건너뜀")
            return

    service.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {"kind": "youtube#video", "videoId": video_id},
            }
        },
    ).execute()
    print("   [재생목록] 영상 추가 완료")
