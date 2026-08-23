"""
chapters.py — 설명란 챕터(타임스탬프) 파싱/검증/삽입 전담 모듈

역할: 구글 시트 I열에 사람이(또는 다른 프로젝트가) 적어둔 챕터 텍스트를 읽어서
유튜브가 실제로 챕터로 인식하는 규칙(0:00 시작 / 최소 3개 / 10초 이상 간격)을
검증하고, 통과하면 설명란 맨 끝에 이어붙인다.

I열 입력 형식 (파이프 `|`로 챕터 구분, 각 챕터는 "시간 제목" 순서):
    0:00 衝撃の告白 | 1:30 波音荘の秘密 | 4:00 届いた手紙

규칙을 어기면(예: 2개뿐, 0:00 아님, 간격 10초 미만) ValueError를 던진다.
upload.py 쪽에서는 이 예외를 잡아서 "챕터 건너뛰고 기존 설명란 그대로 업로드"로
안전하게 폴백해야 한다 — 이 모듈이 실패한다고 업로드 전체가 죽으면 안 된다.
"""

from __future__ import annotations


def _time_to_seconds(t: str) -> int:
    parts = [int(p) for p in t.strip().split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    h, m, s = parts
    return h * 3600 + m * 60 + s


def parse_chapters_cell(raw: str) -> list[dict[str, str]]:
    """'0:00 제목 | 1:30 제목2' 형식 텍스트를 [{'time':.., 'label':..}, ...]로 변환."""
    chapters = []
    for chunk in raw.split("|"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = chunk.split(maxsplit=1)
        if len(parts) != 2:
            raise ValueError(f"챕터 형식 오류(시간과 제목을 공백으로 구분해야 함): '{chunk}'")
        time_str, label = parts
        chapters.append({"time": time_str.strip(), "label": label.strip()})
    return chapters


def validate_chapters(chapters: list[dict[str, str]]) -> None:
    if len(chapters) < 3:
        raise ValueError("챕터는 최소 3개 이상이어야 유튜브가 챕터로 인식합니다.")

    if _time_to_seconds(chapters[0]["time"]) != 0:
        raise ValueError("첫 번째 챕터는 반드시 0:00 이어야 합니다.")

    prev = -1
    for ch in chapters:
        cur = _time_to_seconds(ch["time"])
        if cur <= prev:
            raise ValueError("챕터는 시간순으로 정렬되어야 합니다.")
        if prev >= 0 and (cur - prev) < 10:
            raise ValueError(f"챕터 간격은 최소 10초 이상이어야 합니다: '{ch['time']}' 앞 구간이 너무 짧습니다.")
        prev = cur


def build_description_with_chapters(description: str, chapters_raw: str) -> str:
    """
    description 끝에 검증된 챕터 블록을 붙여서 반환한다.
    chapters_raw가 비어있으면 원본 description을 그대로 반환한다.
    형식/규칙 위반이면 ValueError를 던진다 (호출부에서 잡아서 폴백할 것).
    """
    if not chapters_raw.strip():
        return description

    chapters = parse_chapters_cell(chapters_raw)
    validate_chapters(chapters)

    chapter_block = "\n".join(f"{ch['time']} {ch['label']}" for ch in chapters)
    return f"{description.rstrip()}\n\n{chapter_block}"
