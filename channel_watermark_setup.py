"""
channel_watermark_setup.py — 채널 워터마크 1회 설정용 로컬 실행 스크립트

이 스크립트는 GitHub Actions(upload.py)와 무관하게, 채널당 딱 한 번만 로컬
PC에서 직접 실행하면 되는 "채널 브랜딩" 설정이다. 자동 업로드 파이프라인의
일부가 아니므로 매 업로드마다 실행되지 않는다.

사전 준비물:
  1. 정사각형에 가까운 워터마크 이미지 (PNG 권장, 투명 배경 추천, 10MB 이하)
     — 보통 "구독" 문구가 적힌 작은 아이콘을 씀. 예: watermark_ch7.png
  2. 해당 채널의 로컬 토큰 파일 youtube_token_ch{N}.json
     (get_youtube_token.py {N} 으로 이미 발급돼 있어야 함)

사용법 (같은 폴더에서 실행):
  python channel_watermark_setup.py --channel 7 --image watermark_ch7.png

옵션:
  --corner   topLeft | topRight | bottomLeft | bottomRight (기본 bottomRight)
  --unset    워터마크를 등록 대신 제거하고 싶을 때 (--image 불필요)

⚠️ 이 스크립트는 로컬 토큰 파일을 코드가 "실행 시점"에 읽어서 인증하는 방식이다
(민감 파일 자체를 이 대화에서 직접 열람하지 않는다는 원칙과 별개로, 스크립트
실행은 사용자 PC에서 사용자가 직접 함 — get_youtube_token.py와 동일한 패턴).
403 오류가 나면 watermarks.set에 필요한 스코프(youtube.upload로 충분함,
공식 문서 확인 완료)가 토큰에 있는지만 확인하면 된다.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as OAuthCredentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from watermark_ops import set_channel_watermark, unset_channel_watermark


def _load_local_credentials(channel_num: str) -> OAuthCredentials:
    token_path = f"youtube_token_ch{channel_num}.json"
    if not os.path.exists(token_path):
        print(f"❌ {token_path} 없음.")
        print(f"   → 먼저 실행: python get_youtube_token.py {channel_num}")
        sys.exit(1)

    with open(token_path, "r", encoding="utf-8") as f:
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
    return creds


def main() -> None:
    parser = argparse.ArgumentParser(description="채널 워터마크 1회 등록/제거")
    parser.add_argument("--channel", required=True, help="채널 번호 (1~9, CHANNEL_MAP 기준)")
    parser.add_argument("--image", help="워터마크 이미지 경로 (등록 시 필수)")
    parser.add_argument(
        "--corner",
        default="bottomRight",
        choices=["topLeft", "topRight", "bottomLeft", "bottomRight"],
    )
    parser.add_argument("--unset", action="store_true", help="워터마크 제거만 실행")
    args = parser.parse_args()

    if not args.unset and not args.image:
        parser.error("--image가 필요합니다 (또는 제거하려면 --unset 사용)")

    creds = _load_local_credentials(args.channel)
    service = build("youtube", "v3", credentials=creds)

    channels = service.channels().list(part="id", mine=True).execute()
    items = channels.get("items", [])
    if not items:
        print("❌ 이 토큰으로 조회되는 채널이 없음 — 올바른 계정으로 로그인했는지 확인.")
        sys.exit(1)
    channel_id = items[0]["id"]

    try:
        if args.unset:
            unset_channel_watermark(service, channel_id)
        else:
            set_channel_watermark(service, channel_id, args.image, corner=args.corner)
    except HttpError as e:
        print(f"❌ 워터마크 처리 실패: {e}")
        print("   → 403이면 get_youtube_token.py로 토큰을 다시 발급해보세요"
              "(youtube.upload 스코프면 충분한 것으로 확인됨).")
        sys.exit(1)


if __name__ == "__main__":
    main()
