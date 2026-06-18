"""
YouTube OAuth 토큰 최초 발급 스크립트
- 이 스크립트는 로컬 PC에서 딱 한 번만 실행합니다
- 실행하면 브라우저가 열리고 YouTube 로그인 후 토큰을 발급받습니다
- 발급된 토큰 JSON을 GitHub Secrets에 등록하면 됩니다

사전 준비:
  pip install google-auth-oauthlib google-api-python-client
"""

import json
import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# YouTube 업로드 권한
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_token(ch: str = None):
    """
    Google Cloud Console에서 다운받은 client_secret.json 파일로
    OAuth 토큰을 발급받습니다.
    ch가 주어지면 youtube_token_ch{ch}.json으로 바로 저장 (채널별 전용 토큰).
    ch가 없으면 예전처럼 youtube_token.json으로 저장.
    """
    
    # client_secret.json 파일이 같은 폴더에 있어야 합니다
    if not os.path.exists("client_secret.json"):
        print("❌ client_secret.json 파일이 없습니다!")
        print("   Google Cloud Console → API 및 서비스 → 사용자 인증 정보")
        print("   → OAuth 2.0 클라이언트 ID → JSON 다운로드")
        return
    
    flow = InstalledAppFlow.from_client_secrets_file(
        "client_secret.json",
        SCOPES
    )
    
    # 브라우저 열어서 로그인
    out_name = f"youtube_token_ch{ch}.json" if ch else "youtube_token.json"
    print("🌐 브라우저가 열립니다.")
    if ch:
        print(f"⚠️  반드시 채널 {ch}번을 관리하는 구글 계정으로 로그인하세요!")
        print(f"   (브랜드 계정으로 여러 채널을 한 계정에서 관리 중이라면,")
        print(f"    동의 화면에서 계정/채널을 잘못 고르지 않게 특히 주의하세요.)")
    else:
        print("🌐 YouTube 채널 계정으로 로그인하세요.")
    creds = flow.run_local_server(port=8080)
    
    # 토큰 정보 출력
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
    }
    
    # 파일로 저장
    with open(out_name, "w") as f:
        json.dump(token_data, f, indent=2)
    
    print("\n✅ 토큰 발급 완료!")
    print(f"📄 {out_name} 파일이 생성되었습니다.")
    if ch:
        print(f"   → 이 파일을 C:\\Projects\\5_youtube_auto_uploader\\ 안에 그대로 두세요.")
    else:
        print("\n⚠️  이 파일 내용을 GitHub Secrets에 등록하세요:")
        print("   Secret 이름: YOUTUBE_TOKEN_JSON")
        print("   Secret 값: (파일 내용 전체)")
    print("\n토큰 내용:")
    print(json.dumps(token_data, indent=2))


if __name__ == "__main__":
    ch_arg = sys.argv[1] if len(sys.argv) > 1 else None
    get_token(ch_arg)
