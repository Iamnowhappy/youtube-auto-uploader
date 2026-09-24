"""
localization_ops.py — 다국어 제목/설명(localizations) 파싱 전담 모듈

2026-09-25 추가 — Made on YouTube 2026에서 자동 더빙/다국어 도달이 강조됨.
U열에 {"en": {"title": "...", "description": "..."}, "ko": {...}} 형태 JSON을
넣으면 videos.insert의 localizations로 함께 올린다(시청자 언어 설정에 맞춰
제목/설명이 번역돼 보임). 22/40번 생성기가 만드는 upload_meta.json의
"localizations" 값을 그대로 복사해 넣으면 된다.

형식이 틀리면 빈 dict를 돌려줘서 "다국어 없이 기존대로 업로드"로 폴백한다.
"""

from __future__ import annotations

import json


def parse_localizations(raw: str, default_language: str) -> dict:
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"   ⚠️ U열 다국어 JSON 형식 오류 — 다국어 없이 업로드: {e}")
        return {}
    if not isinstance(data, dict):
        return {}

    result = {}
    for lang, loc in data.items():
        # 기본 언어와 같은 키는 snippet 제목/설명과 중복이라 뺀다.
        if lang == default_language or not isinstance(loc, dict):
            continue
        title = str(loc.get("title", "")).strip()
        if not title:
            continue
        result[lang] = {
            "title": title[:100],
            "description": str(loc.get("description", "")).strip()[:5000],
        }
    return result


if __name__ == "__main__":
    raw = '{"en": {"title": "Hi", "description": "d"}, "ko": {"title": "안녕"}, "ja": {"title": ""}}'
    assert parse_localizations(raw, "ko") == {"en": {"title": "Hi", "description": "d"}}
    assert parse_localizations("not json", "ko") == {}
    assert parse_localizations("", "ko") == {}
    print("ok")
