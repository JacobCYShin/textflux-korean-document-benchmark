#!/usr/bin/env python3
"""Create safe, generic Korean document inputs and binary masks for a TextFlux smoke test."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH, HEIGHT = 1280, 1810
PAPER = (250, 249, 246)
INK = (42, 47, 55)
RULE = (130, 138, 147)
FIELD_FILL = (255, 255, 255)

FIELDS = {
    "name": (410, 470, 1140, 570),
    "purpose": (410, 630, 1140, 730),
    "date": (410, 790, 1140, 890),
    "amount": (410, 950, 1140, 1050),
}


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def create_form(output: Path, font_path: Path) -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)
    title_font = font(font_path, 44)
    heading_font = font(font_path, 25)
    label_font = font(font_path, 30)
    note_font = font(font_path, 20)

    draw.rectangle((78, 72, WIDTH - 78, HEIGHT - 72), outline=INK, width=3)
    draw.text((WIDTH // 2, 160), "외환 거래 신청서", font=title_font, fill=INK, anchor="mm")
    draw.text(
        (WIDTH // 2, 218),
        "합성 데이터 콘텐츠 검증용 범용 서식 · 실제 금융 문서 아님",
        font=note_font,
        fill=RULE,
        anchor="mm",
    )
    draw.line((120, 270, WIDTH - 120, 270), fill=INK, width=2)

    draw.text((150, 342), "신청인 정보", font=heading_font, fill=INK)
    labels = {
        "name": "성명",
        "purpose": "거래 목적",
        "date": "거래 일자",
        "amount": "통화 및 금액",
    }
    for field_name, rectangle in FIELDS.items():
        left, top, right, bottom = rectangle
        center_y = (top + bottom) // 2
        draw.text((170, center_y), labels[field_name], font=label_font, fill=INK, anchor="lm")
        draw.rounded_rectangle(rectangle, radius=4, fill=FIELD_FILL, outline=RULE, width=2)

    draw.text((150, 1170), "확인 사항", font=heading_font, fill=INK)
    notes = [
        "• 본 이미지는 모델 입력 및 마스크 검증을 위한 예시입니다.",
        "• 금액, 날짜, 계좌·식별자 필드는 결과 문자열 전체를 검토해야 합니다.",
        "• 실제 업무 서식지와 개인정보는 이 저장소에 포함하지 않습니다.",
    ]
    for index, text in enumerate(notes):
        draw.text((175, 1230 + index * 54), text, font=note_font, fill=INK)

    draw.line((120, 1510, WIDTH - 120, 1510), fill=RULE, width=1)
    draw.text((WIDTH // 2, 1570), "TEXTFLUX KOREAN DOCUMENT BASELINE", font=note_font, fill=RULE, anchor="mm")
    image.save(output)


def create_mask(output: Path, rectangle: tuple[int, int, int, int]) -> None:
    mask = Image.new("L", (WIDTH, HEIGHT), 0)
    draw = ImageDraw.Draw(mask)
    left, top, right, bottom = rectangle
    # Leave the printed field border unmasked; only the blank writing area is editable.
    draw.rectangle((left + 10, top + 10, right - 10, bottom - 10), fill=255)
    mask.save(output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", type=Path, required=True, help="Hangul-capable TrueType or OpenType font")
    parser.add_argument("--output", type=Path, default=Path("examples/demo-inputs"))
    args = parser.parse_args()

    if not args.font.is_file():
        parser.error(f"font file not found: {args.font}")
    output_root = args.output
    forms = output_root / "forms"
    masks = output_root / "masks"
    forms.mkdir(parents=True, exist_ok=True)
    masks.mkdir(parents=True, exist_ok=True)

    create_form(forms / "demo_foreign_exchange_form.png", args.font)
    for field_name, rectangle in FIELDS.items():
        create_mask(masks / f"demo_{field_name}.png", rectangle)
    print(f"Created demo inputs under {output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
