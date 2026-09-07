"""
verify_token_channel.py
발급받은 youtube_token_ch{N}.json이 실제로 어느 채널로 연결되는지
GitHub Secrets에 올리기 전에 로컬에서 미리 확인하는 스크립트.

사용법:
  python verify_token_channel.py youtube_token_ch10.json
"""
import json
import sys

from google.oauth2.credentials import Credentials as OAuthCredentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


def main():
    if len(sys.argv) < 2:
        print("사용법: python verify_token_channel.py <토큰 json 파일>")
        sys.exit(1)

    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        token_data = json.load(f)

    creds = OAuthCredentials(
        token=token_data.get("token"),
        refresh_token=token_data["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=token_data["client_id"],
        client_secret=token_data["client_secret"],
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    youtube = build("youtube", "v3", credentials=creds)
    resp = youtube.channels().list(part="snippet,id", mine=True).execute()

    items = resp.get("items", [])
    if not items:
        print("⚠️ 이 토큰으로 연결된 채널을 찾을 수 없습니다 (mine=True 결과 없음).")
        return

    print(f"\n📄 토큰 파일: {path}")
    print(f"🎯 이 토큰으로 업로드하면 실제로 올라갈 채널:\n")
    for ch in items:
        title = ch["snippet"]["title"]
        cid = ch["id"]
        print(f"   📺 {title}")
        print(f"      채널ID: {cid}")
    print()
    print("→ 위 채널이 의도한 채널(예: 천명연구소, UCQ7JqaT39C1luDelJcNVI1Q)과")
    print("   일치하는지 꼭 확인한 뒤에 GitHub Secrets에 올리세요.")


if __name__ == "__main__":
    main()
