from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont


OUTPUT_DIR = Path(__file__).resolve().parent

NAVY = "#0C171F"
GREEN = "#00F700"
TRANSPARENT = (255, 255, 255, 0)
FONT_REGULAR = r"C:\Windows\Fonts\GOTHIC.TTF"
FONT_BOLD = r"C:\Windows\Fonts\GOTHICB.TTF"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size)


def wrapped_lines(draw, text, box_width, text_font, max_lines=3):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if draw.textlength(candidate, font=text_font) <= box_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines[:max_lines]


def draw_cell_text(draw, text, bounds, text_font, *, bold=False, align="left"):
    x0, y0, x1, y1 = bounds
    inset_x = 24
    available_width = x1 - x0 - 2 * inset_x
    active_font = font(text_font.size, bold=bold)
    lines = wrapped_lines(draw, text, available_width, active_font)
    spacing = 10
    line_heights = [draw.textbbox((0, 0), line, font=active_font)[3] for line in lines]
    block_height = sum(line_heights) + spacing * max(0, len(lines) - 1)
    y = y0 + (y1 - y0 - block_height) / 2
    for line, line_height in zip(lines, line_heights):
        if align == "center":
            width = draw.textlength(line, font=active_font)
            x = x0 + (x1 - x0 - width) / 2
        else:
            x = x0 + inset_x
        draw.text((x, y), line, fill=NAVY, font=active_font)
        y += line_height + spacing


def render_table(filename, headers, rows, column_widths, selected_index):
    width = sum(column_widths)
    header_height = 110
    row_height = 154
    height = header_height + row_height * len(rows) + 12
    image = Image.new("RGBA", (width, height), TRANSPARENT)
    draw = ImageDraw.Draw(image)

    x_positions = [0]
    for column_width in column_widths:
        x_positions.append(x_positions[-1] + column_width)

    # Minimal rules: strong header baseline, light row dividers, no filled cells.
    draw.line((0, header_height, width, header_height), fill=NAVY, width=4)
    for row_index in range(1, len(rows) + 1):
        y = header_height + row_index * row_height
        draw.line((0, y, width, y), fill=(12, 23, 31, 85), width=2)
    for x in x_positions[1:-1]:
        draw.line((x, 12, x, header_height + row_height * len(rows)), fill=(12, 23, 31, 55), width=2)

    header_font = font(34, bold=True)
    body_font = font(31)
    for column_index, header in enumerate(headers):
        bounds = (x_positions[column_index], 0, x_positions[column_index + 1], header_height)
        draw_cell_text(draw, header, bounds, header_font, bold=True,
                       align="center" if column_index in (1, 2, 3, 4, 5) else "left")

    for row_index, row in enumerate(rows):
        y0 = header_height + row_index * row_height
        y1 = y0 + row_height
        for column_index, value in enumerate(row):
            bounds = (x_positions[column_index], y0, x_positions[column_index + 1], y1)
            draw_cell_text(
                draw,
                value,
                bounds,
                body_font,
                bold=(row_index == selected_index and column_index == 0),
                align="center" if column_index in (1, 2, 3, 4, 5) else "left",
            )

    image.save(OUTPUT_DIR / filename, dpi=(300, 300))


def main():
    render_table(
        "appendix_reward_formulations_transparent.png",
        ["Reward formulation", "Spearman", "1 - MSE", "Top-25% overlap", "Validation reward"],
        [
            ["Rank-dominant (selected)", "70%", "30%", "—", "0.7081"],
            ["Stronger-rank", "85%", "15%", "—", "0.6875"],
            ["Pure-rank", "100%", "—", "—", "0.6815"],
            ["Balanced rank-score", "50%", "50%", "—", "0.6848"],
            ["Tail-aware", "60%", "20%", "20%", "0.7012"],
        ],
        [600, 270, 270, 360, 900],
        selected_index=0,
    )

    render_table(
        "appendix_bucket_mappings_transparent.png",
        ["Selection approach", "Conservative", "Balanced", "Aggressive", "Monthly risk ordering", "High-low risk spread"],
        [
            ["Selective overlapping tails (selected)", "0–30%", "20–80%", "70–100%", "11/11", "0.449"],
            ["Non-overlapping thirds", "0–33%", "33–67%", "67–100%", "10/11", "0.426"],
            ["Broad overlapping", "0–40%", "25–75%", "60–100%", "11/11", "0.356"],
            ["Wide overlapping", "0–50%", "20–80%", "50–100%", "11/11", "0.317"],
        ],
        [600, 280, 280, 280, 480, 480],
        selected_index=0,
    )


if __name__ == "__main__":
    main()
