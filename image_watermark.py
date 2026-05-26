#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import os
import platform
from pathlib import Path
from typing import Iterable

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_IMPORT_ERROR: Exception | None = None
except ImportError as exc:
    Image = ImageDraw = ImageFont = None
    PIL_IMPORT_ERROR = exc

DEFAULT_WATERMARK_TEXT = "点击本图->长按加群！"
DEFAULT_BOTTOM_MARGIN = 40
DEFAULT_SIDE_PADDING = 40
DEFAULT_FILL = "#FF2D2D"
DEFAULT_STROKE_FILL = "#FFEA00"
DEFAULT_STROKE_RATIO = 0.06
DEFAULT_BOLD_RATIO = 0.03
MIN_FONT_SIZE = 12
MAX_OUTPUT_SCALE = 1.2
MAX_JPEG_QUALITY = 95
MIN_JPEG_QUALITY = 35
FALLBACK_SCALE_STEPS = (0.98, 0.96, 0.94, 0.92, 0.9, 0.88, 0.85, 0.82, 0.8, 0.75)

MAC_FONT_CANDIDATES = (
    "/System/Library/Fonts/Supplemental/PingFang SC Semibold.ttf",
    "/System/Library/Fonts/Supplemental/PingFang SC Bold.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
)

WINDOWS_FONT_CANDIDATES = (
    "{WINDIR}/Fonts/msyhbd.ttc",
    "{WINDIR}/Fonts/msyh.ttc",
    "{WINDIR}/Fonts/simhei.ttf",
    "{WINDIR}/Fonts/simsun.ttc",
    "{LOCALAPPDATA}/Microsoft/Windows/Fonts/msyhbd.ttc",
)

OTHER_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="给图片底部添加自适应水印。")
    parser.add_argument("image", nargs="?", help="输入图片路径，例如 images/group-qr-code.png")
    parser.add_argument(
        "-o",
        "--output",
        help="输出图片路径，默认在原文件名后追加 _watermarked",
    )
    parser.add_argument(
        "-t",
        "--text",
        default=DEFAULT_WATERMARK_TEXT,
        help=f"水印内容，默认: {DEFAULT_WATERMARK_TEXT}",
    )
    parser.add_argument(
        "--font",
        help="可选字体文件路径，建议传入支持中文的粗体字体",
    )
    parser.add_argument(
        "--bottom-margin",
        type=int,
        default=DEFAULT_BOTTOM_MARGIN,
        help=f"文字距离底部的像素值，默认 {DEFAULT_BOTTOM_MARGIN}",
    )
    parser.add_argument(
        "--side-padding",
        type=int,
        default=DEFAULT_SIDE_PADDING,
        help=f"左右留白像素值，默认 {DEFAULT_SIDE_PADDING}",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="打开图形界面",
    )
    return parser.parse_args()


def resolve_output_path(image_path: Path, output: str | None) -> Path:
    if output:
        return Path(output)
    return image_path.with_name(f"{image_path.stem}_watermarked{image_path.suffix}")


def ensure_pillow_available(use_gui: bool = False) -> None:
    if PIL_IMPORT_ERROR is None:
        return

    message = (
        "未检测到 Pillow，请先安装依赖：\n"
        "macOS: python3 -m pip install pillow\n"
        "Windows: python -m pip install pillow"
    )
    if use_gui:
        try:
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("缺少依赖", message)
            root.destroy()
        except Exception:
            pass
    raise SystemExit(message)


def expand_font_path(raw_path: str) -> Path:
    env_mapping = {
        "WINDIR": os.environ.get("WINDIR", "C:/Windows"),
        "LOCALAPPDATA": os.environ.get("LOCALAPPDATA", ""),
    }
    if "{LOCALAPPDATA}" in raw_path and not env_mapping["LOCALAPPDATA"]:
        return Path()
    return Path(raw_path.format(**env_mapping)).expanduser()


def iter_font_candidates(user_font: str | None) -> Iterable[Path]:
    if user_font:
        yield Path(user_font)
    system_name = platform.system().lower()
    if system_name == "windows":
        font_candidates = WINDOWS_FONT_CANDIDATES
    elif system_name == "darwin":
        font_candidates = MAC_FONT_CANDIDATES
    else:
        font_candidates = OTHER_FONT_CANDIDATES

    seen: set[Path] = set()
    for raw_path in (*font_candidates, *MAC_FONT_CANDIDATES, *WINDOWS_FONT_CANDIDATES, *OTHER_FONT_CANDIDATES):
        expanded = expand_font_path(raw_path)
        if not str(expanded) or str(expanded) == ".":
            continue
        if expanded not in seen:
            seen.add(expanded)
            yield expanded


def load_font(font_path: str | None, size: int) -> ImageFont.FreeTypeFont:
    for candidate in iter_font_candidates(font_path):
        if candidate.exists():
            try:
                return ImageFont.truetype(str(candidate), size=size, index=0)
            except OSError:
                continue
    raise FileNotFoundError(
        "未找到可用的中文粗体字体，请通过 --font 指定字体文件路径。"
    )


def get_text_style(size: int) -> tuple[int, int]:
    stroke_width = max(1, round(size * DEFAULT_STROKE_RATIO))
    bold_offset = max(1, round(size * DEFAULT_BOLD_RATIO))
    return stroke_width, bold_offset


def measure_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    stroke_width: int,
    bold_offset: int,
) -> tuple[int, int, int, int]:
    left, top, right, bottom = draw.textbbox(
        (0, 0),
        text,
        font=font,
        stroke_width=stroke_width,
    )
    return left - bold_offset, top - bold_offset, right + bold_offset, bottom + bold_offset


def draw_bold_text(
    draw: ImageDraw.ImageDraw,
    position: tuple[float, float],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: str,
    stroke_width: int,
    stroke_fill: str,
    bold_offset: int,
) -> None:
    x, y = position
    for dx in range(-bold_offset, bold_offset + 1):
        for dy in range(-bold_offset, bold_offset + 1):
            if dx == 0 and dy == 0:
                continue
            if abs(dx) + abs(dy) > bold_offset:
                continue
            draw.text(
                (x + dx, y + dy),
                text,
                font=font,
                fill=fill,
            )

    draw.text(
        position,
        text,
        font=font,
        fill=fill,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )


def pick_font_size(
    image: Image.Image,
    text: str,
    font_path: str | None,
    side_padding: int,
    bottom_margin: int,
) -> tuple[ImageFont.FreeTypeFont, int, int]:
    draw = ImageDraw.Draw(image)
    max_width = max(1, image.width - side_padding * 2)
    max_height = max(1, image.height - bottom_margin)

    upper = max(MIN_FONT_SIZE, min(image.width, image.height))
    lower = MIN_FONT_SIZE
    chosen_font: ImageFont.FreeTypeFont | None = None
    chosen_stroke = 0
    chosen_height = 0

    while lower <= upper:
        size = (lower + upper) // 2
        stroke_width, bold_offset = get_text_style(size)
        font = load_font(font_path, size)
        left, top, right, bottom = measure_text(draw, text, font, stroke_width, bold_offset)
        text_width = right - left
        text_height = bottom - top

        if text_width <= max_width and text_height <= max_height:
            chosen_font = font
            chosen_stroke = stroke_width
            chosen_height = text_height
            lower = size + 1
        else:
            upper = size - 1

    if chosen_font is None:
        raise ValueError("水印文字过长，当前图片无法容纳，请缩短文字后重试。")

    return chosen_font, chosen_stroke, chosen_height


def add_watermark(
    image: Image.Image,
    text: str,
    font_path: str | None,
    side_padding: int,
    bottom_margin: int,
) -> Image.Image:
    canvas = image.convert("RGBA")
    overlay = Image.new("RGBA", canvas.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    font, stroke_width, _ = pick_font_size(
        canvas,
        text,
        font_path,
        side_padding,
        bottom_margin,
    )
    _, bold_offset = get_text_style(font.size)
    left, top, right, bottom = measure_text(draw, text, font, stroke_width, bold_offset)
    text_width = right - left
    text_height = bottom - top

    x = max(side_padding - left, (canvas.width - text_width) / 2 - left)
    y = max(-top, canvas.height - bottom_margin - text_height - top)

    draw_bold_text(
        draw,
        (x, y),
        text,
        font,
        DEFAULT_FILL,
        stroke_width,
        DEFAULT_STROKE_FILL,
        bold_offset,
    )
    return Image.alpha_composite(canvas, overlay)


def encode_png_candidates(image: Image.Image) -> list[bytes]:
    candidates: list[bytes] = []
    rgba_image = image.convert("RGBA")

    raw = io.BytesIO()
    rgba_image.save(raw, format="PNG")
    candidates.append(raw.getvalue())

    optimized = io.BytesIO()
    rgba_image.save(optimized, format="PNG", optimize=True, compress_level=9)
    candidates.append(optimized.getvalue())

    for colors in (256, 192, 128, 96, 64, 48, 32, 24, 16, 8):
        quantized = rgba_image.quantize(colors=colors, method=Image.FASTOCTREE, dither=Image.Dither.FLOYDSTEINBERG)
        if "transparency" in rgba_image.info:
            quantized.info["transparency"] = rgba_image.info["transparency"]
        buf = io.BytesIO()
        quantized.save(buf, format="PNG", optimize=True, compress_level=9)
        candidates.append(buf.getvalue())

    return candidates


def encode_jpeg_candidates(image: Image.Image) -> list[bytes]:
    candidates: list[bytes] = []
    rgb_image = image.convert("RGB")
    for quality in range(MAX_JPEG_QUALITY, MIN_JPEG_QUALITY - 1, -5):
        buf = io.BytesIO()
        rgb_image.save(
            buf,
            format="JPEG",
            quality=quality,
            optimize=True,
            progressive=True,
        )
        candidates.append(buf.getvalue())
    return candidates


def resize_image(image: Image.Image, scale: float) -> Image.Image:
    width = max(1, round(image.width * scale))
    height = max(1, round(image.height * scale))
    return image.resize((width, height), Image.Resampling.LANCZOS)


def encode_single_candidate(image: Image.Image, image_format: str) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format=image_format)
    return buf.getvalue()


def encode_candidates_by_format(image: Image.Image, image_format: str) -> list[bytes]:
    fmt = image_format.upper()
    if fmt == "PNG":
        return encode_png_candidates(image)
    if fmt in {"JPG", "JPEG"}:
        return encode_jpeg_candidates(image)
    return [encode_single_candidate(image, image_format)]


def choose_encoded_output(image: Image.Image, image_format: str, original_size: int) -> bytes:
    upper_limit = int(original_size * MAX_OUTPUT_SCALE)
    candidates = encode_candidates_by_format(image, image_format)
    for data in candidates:
        if len(data) <= upper_limit:
            return data

    all_candidates = list(candidates)

    for scale in FALLBACK_SCALE_STEPS:
        resized_image = resize_image(image, scale)
        resized_candidates = encode_candidates_by_format(resized_image, image_format)
        all_candidates.extend(resized_candidates)
        for data in resized_candidates:
            if len(data) <= upper_limit:
                return data

    scale = FALLBACK_SCALE_STEPS[-1]
    while scale > 0.3:
        scale = round(scale * 0.9, 4)
        resized_image = resize_image(image, scale)
        resized_candidates = encode_candidates_by_format(resized_image, image_format)
        all_candidates.extend(resized_candidates)
        for data in resized_candidates:
            if len(data) <= upper_limit:
                return data

    raise RuntimeError(
        f"输出文件仍无法压缩到原图的 {MAX_OUTPUT_SCALE:.0%} 以内，当前最小结果为 {len(min(all_candidates, key=len))} bytes。"
    )


def process_image(
    image_path: Path,
    text: str,
    output: str | None = None,
    font_path: str | None = None,
    side_padding: int = DEFAULT_SIDE_PADDING,
    bottom_margin: int = DEFAULT_BOTTOM_MARGIN,
) -> Path:
    ensure_pillow_available()
    output_path = resolve_output_path(image_path, output)
    if not image_path.exists():
        raise FileNotFoundError(f"输入图片不存在: {image_path}")

    with Image.open(image_path) as image:
        image_format = image.format or image_path.suffix.lstrip(".").upper()
        watermarked = add_watermark(
            image=image,
            text=text,
            font_path=font_path,
            side_padding=side_padding,
            bottom_margin=bottom_margin,
        )
        encoded = choose_encoded_output(
            image=watermarked,
            image_format=image_format,
            original_size=image_path.stat().st_size,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(encoded)
    return output_path


def run_cli(args: argparse.Namespace) -> None:
    if not args.image:
        raise SystemExit("请传入图片路径，或使用 --gui 打开图形界面。")

    image_path = Path(args.image)
    output_path = process_image(
        image_path=image_path,
        text=args.text,
        output=args.output,
        font_path=args.font,
        side_padding=args.side_padding,
        bottom_margin=args.bottom_margin,
    )

    print(f"输入图片: {image_path}")
    print(f"输出图片: {output_path}")
    print(f"水印内容: {args.text}")
    print(f"原图大小: {image_path.stat().st_size} bytes")
    print(f"输出大小: {output_path.stat().st_size} bytes")


def launch_gui(default_text: str = DEFAULT_WATERMARK_TEXT) -> None:
    ensure_pillow_available(use_gui=True)

    import tkinter as tk
    from tkinter import filedialog, messagebox

    root = tk.Tk()
    root.title("图片水印工具")
    root.geometry("640x220")
    root.resizable(False, False)

    image_var = tk.StringVar()
    text_var = tk.StringVar()
    status_var = tk.StringVar(
        value=f"请选择一张图片；水印内容可自定义，留空则使用默认：{default_text}"
    )

    def choose_image() -> None:
        file_path = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[
                ("图片文件", "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff"),
                ("所有文件", "*.*"),
            ],
        )
        if file_path:
            image_var.set(file_path)
            status_var.set("已选择图片，点击“开始加水印”即可生成。")

    def submit() -> None:
        image_path_str = image_var.get().strip()
        watermark_text = text_var.get().strip() or default_text

        if not image_path_str:
            messagebox.showwarning("缺少图片", "请先选择一张图片。")
            return

        try:
            output_path = process_image(
                image_path=Path(image_path_str),
                text=watermark_text,
            )
        except Exception as exc:
            messagebox.showerror("生成失败", str(exc))
            status_var.set("生成失败，请检查图片路径、字体配置或图片格式。")
            return

        status_var.set(f"生成成功：{output_path}；当前水印：{watermark_text}")
        messagebox.showinfo("生成成功", f"已生成加水印图片：\n{output_path}")

    root.columnconfigure(1, weight=1)

    tk.Label(root, text="图片路径").grid(row=0, column=0, padx=12, pady=(18, 8), sticky="w")
    tk.Entry(root, textvariable=image_var, width=58).grid(row=0, column=1, padx=0, pady=(18, 8), sticky="ew")
    tk.Button(root, text="选择图片", command=choose_image, width=12).grid(row=0, column=2, padx=12, pady=(18, 8))

    tk.Label(root, text="水印内容").grid(row=1, column=0, padx=12, pady=8, sticky="w")
    tk.Entry(root, textvariable=text_var, width=58).grid(row=1, column=1, padx=0, pady=8, sticky="ew")
    tk.Label(root, text=f"留空默认：{default_text}", fg="#666666").grid(
        row=2, column=1, padx=0, pady=(0, 6), sticky="w"
    )

    tk.Button(root, text="开始加水印", command=submit, width=16, height=2).grid(
        row=3, column=1, padx=0, pady=(14, 10), sticky="w"
    )

    tk.Label(
        root,
        textvariable=status_var,
        fg="#555555",
        anchor="w",
        justify="left",
        wraplength=600,
    ).grid(row=4, column=0, columnspan=3, padx=12, pady=(4, 0), sticky="w")

    root.bind("<Return>", lambda _event: submit())
    root.mainloop()


def main() -> None:
    args = parse_args()
    if args.gui or not args.image:
        launch_gui(default_text=args.text)
        return
    run_cli(args)


if __name__ == "__main__":
    main()
