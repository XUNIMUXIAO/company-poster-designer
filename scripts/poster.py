#!/usr/bin/env python3
"""Offline architectural festival poster renderer."""

from __future__ import annotations

import argparse
import colorsys
import json
import math
import random
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


TRANSLATIONS = {
    "中秋": "MID AUTUMN FESTIVAL",
    "中秋节": "MID AUTUMN FESTIVAL",
    "国庆": "NATIONAL DAY",
    "国庆节": "NATIONAL DAY",
    "春节": "SPRING FESTIVAL",
    "元旦": "NEW YEAR'S DAY",
    "清明": "QINGMING FESTIVAL",
    "清明节": "QINGMING FESTIVAL",
    "端午": "DRAGON BOAT FESTIVAL",
    "端午节": "DRAGON BOAT FESTIVAL",
    "春分": "SPRING EQUINOX",
    "秋分": "AUTUMN EQUINOX",
    "冬至": "WINTER SOLSTICE",
    "夏至": "SUMMER SOLSTICE",
}
CHINESE_FONTS = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
]
ENGLISH_FONTS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Helvetica.ttc",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/Arial.ttf",
]


def rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def hexrgb(color: tuple[int, int, int]) -> str:
    return "#%02X%02X%02X" % color


def luminance(color: tuple[int, int, int]) -> float:
    channels = [v / 255 for v in color]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def font_path(user_path: str | None, candidates: list[str], language: str) -> str:
    if user_path:
        path = Path(user_path).expanduser()
        if not path.is_file():
            raise ValueError(f"{language} font not found: {path}")
        return str(path)
    for candidate in candidates:
        if Path(candidate).is_file():
            return candidate
    raise ValueError(f"No {language} font found. Use --font-{language} with a font file that contains the required glyphs.")


COLORWAYS = {
    1: ("#CE292D", "#FFF8E8", "#D7A84A", "#252525"),
    2: ("#F5A1C1", "#488FCE", "#F6D84B", "#252126"),
    3: ("#F8E327", "#92D54D", "#F34395", "#191919"),
    4: ("#F464A2", "#FF931E", "#FFD82D", "#48AC43", "#151515"),
    5: ("#F56FAF", "#F9DA28", "#29231F"),
    6: ("#7CCF60", "#F399BD", "#229FA7", "#24232D"),
}
COLORWAY_NAMES = {
    1: "classic-commercial-red-white",
    2: "pink-blue-yellow",
    3: "neon-yellow-acid-green-rose",
    4: "fluorescent-floral",
    5: "fluorescent-pink-yellow",
    6: "green-pink-lake-blue",
}


def shift_hue(color: tuple[int, int, int], offset: float) -> tuple[int, int, int]:
    h, s, v = colorsys.rgb_to_hsv(*(value / 255 for value in color))
    return tuple(round(value * 255) for value in colorsys.hsv_to_rgb((h + offset) % 1, s, v))


def recolor_illustration(art: Image.Image, palette: list[tuple[int, int, int]]) -> Image.Image:
    """Map a single supplied draft to its assigned palette without inventing new hues."""
    indexed = art.quantize(colors=len(palette), method=Image.Quantize.MEDIANCUT)
    source_colors = indexed.getpalette()
    used = [index for _, index in indexed.getcolors(art.width * art.height) or []]
    used.sort(key=lambda index: luminance(tuple(source_colors[index * 3:index * 3 + 3])))
    targets = sorted(palette, key=luminance)
    for source_index, color in zip(used, targets):
        source_colors[source_index * 3:source_index * 3 + 3] = color
    indexed.putpalette(source_colors)
    return indexed.convert("RGB")


def palette_from_reference(path: Path | None, festival: str, proposal: int = 1, palette_id: int | None = None) -> list[tuple[int, int, int]]:
    if path is None:
        return [rgb(value) for value in COLORWAYS[palette_id or random.choice(tuple(COLORWAYS))]]
    with Image.open(path) as source:
        sample = ImageOps.exif_transpose(source).convert("RGB")
    sample.thumbnail((320, 320))
    colors = sample.quantize(colors=12).convert("RGB").getcolors(sample.width * sample.height) or []
    colors.sort(key=lambda item: item[0], reverse=True)
    selected: list[tuple[int, int, int]] = []
    for _count, color in colors:
        if all(sum(abs(color[i] - prev[i]) for i in range(3)) > 72 for prev in selected):
            selected.append(color)
        if len(selected) == 6:
            break
    while len(selected) < 6:
        selected.append(rgb(("#071C54", "#1366DB", "#D92267", "#FF653A", "#FFD51F", "#FFF3B8")[len(selected)]))
    offset = {1: 0.0, 2: -0.09, 3: 0.11}[proposal]
    return sorted((shift_hue(color, offset) for color in selected), key=luminance)


def abstraction(source: Image.Image, size: tuple[int, int], palette: list[tuple[int, int, int]]) -> Image.Image:
    photo = ImageOps.fit(ImageOps.exif_transpose(source).convert("RGB"), size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    gray = ImageOps.autocontrast(ImageEnhance.Contrast(photo.convert("L")).enhance(1.17))
    # Map all six tonal bands across the selected palette, regardless of its size.
    tonal_palette = sorted(palette, key=luminance)
    bands = gray.point([min(5, int(v / 43)) for v in range(256)])
    masks = [bands.point([255 if v == band else 0 for v in range(256)]) for band in range(6)]
    result = Image.new("RGB", size, tonal_palette[0])
    for band, mask in enumerate(masks):
        color = tonal_palette[min(len(tonal_palette) - 1, band * len(tonal_palette) // 6)]
        result.paste(color, (0, 0, size[0], size[1]), mask)
    edges = gray.filter(ImageFilter.FIND_EDGES).point([255 if v > 85 else 0 for v in range(256)])
    # Restrained linework clarifies windows and rooflines while keeping broad color planes.
    edges = edges.filter(ImageFilter.MinFilter(3))
    result.paste(tonal_palette[0], (0, 0, size[0], size[1]), edges)
    return result


def title_lines(draw: ImageDraw.ImageDraw, english: str, path: str, width: int, max_height: int,
                max_lines: int = 2) -> tuple[list[str], ImageFont.FreeTypeFont, int]:
    words = english.upper().split()
    for size in range(min(164, width // 6), 43, -2):
        font = ImageFont.truetype(path, size)
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = (current + " " + word).strip()
            if current and draw.textbbox((0, 0), candidate, font=font)[2] > width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        line_h = int(size * 0.98)
        if len(lines) <= max_lines and all(draw.textbbox((0, 0), line, font=font)[2] <= width for line in lines) and len(lines) * line_h <= max_height:
            return lines, font, line_h
    raise ValueError("English title is too long for the selected canvas; supply a shorter --english title or larger --size.")


def region_complexity(image: Image.Image, box: tuple[int, int, int, int], background: tuple[int, int, int]) -> float:
    crop_color = image.crop(box).convert("RGB").resize((64, 32))
    crop = crop_color.convert("L")
    edges = crop.filter(ImageFilter.FIND_EDGES)
    hist = edges.histogram()
    edge_score = sum(i * n for i, n in enumerate(hist)) / max(1, sum(hist))
    pixels = crop_color.load()
    difference = sum(sum(abs(pixels[x, y][i] - background[i]) for i in range(3)) for y in range(32) for x in range(64))
    background_score = difference / (64 * 32 * 28)
    return edge_score + background_score


def intersects(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


def logo_region_contrast(image: Image.Image, box: tuple[int, int, int, int], logo_color: tuple[int, int, int]) -> float:
    sample = image.crop(box).convert("RGB").resize((36, 20))
    pixels = sample.load()
    ratios = sorted(contrast(pixels[x, y], logo_color) for y in range(20) for x in range(36))
    return ratios[int(len(ratios) * 0.1)]


def subject_mask(source: Image.Image, size: tuple[int, int], max_y: int, warm_only: bool = False) -> Image.Image | None:
    """Find a building against a mostly even sky for a restrained type overlap."""
    photo = ImageOps.fit(ImageOps.exif_transpose(source).convert("RGB"), size, method=Image.Resampling.LANCZOS)
    w, h = size
    points = [(int(w * x), int(h * y)) for x, y in ((0.03, 0.04), (0.97, 0.04), (0.03, 0.16), (0.97, 0.16))]
    samples = [photo.getpixel(point) for point in points]
    sky = tuple(sorted(pixel[i] for pixel in samples)[2] for i in range(3))
    difference = ImageChops.difference(photo, Image.new("RGB", size, sky))
    r, g, b = difference.split()
    mask = ImageChops.lighter(ImageChops.lighter(r, g), b).point([255 if v > 72 else 0 for v in range(256)])
    start_y = int(h * 0.16)
    if warm_only:
        source_pixels = photo.load()
        mask_pixels = mask.load()
        for y in range(start_y, max_y):
            for x in range(w):
                red, green, blue = source_pixels[x, y]
                if red <= green * 1.18 or red <= blue * 1.25 or red - green < 34:
                    mask_pixels[x, y] = 0
    band = mask.crop((0, start_y, w, max_y))
    coverage = band.resize((100, 100), Image.Resampling.NEAREST).histogram()[255] / 10000
    if not 0.035 <= coverage <= 0.62:
        return None
    mask = mask.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    limited = Image.new("L", size, 0)
    limited.paste(mask.crop((0, start_y, w, max_y)), (0, start_y))
    return limited


def choose_logo_position(image: Image.Image, logo_size: tuple[int, int], title_boxes: list[tuple[int, int, int, int]], requested: str, logo_color: tuple[int, int, int]) -> tuple[str, tuple[int, int, int, int], float]:
    w, h = image.size
    lw, lh = logo_size
    margin = int(w * 0.055)
    coords = {
        "top-left": (margin, int(h * 0.055)),
        "top-right": (w - margin - lw, int(h * 0.055)),
        "mid-left": (margin, int(h * 0.43)),
        "mid-right": (w - margin - lw, int(h * 0.43)),
        "bottom-left": (margin, h - margin - lh),
        "bottom-right": (w - margin - lw, h - margin - lh),
    }
    if requested == "auto":
        for yf in (0.14, 0.17, 0.20, 0.23, 0.43, 0.54, 0.65, 0.76, 0.87, 0.93):
            for xf in (0.055, 0.22, 0.39, 0.48, 0.56, 0.65, 0.73, 0.82):
                x, y = int(w * xf), int(h * yf)
                if x + lw < w - margin and y + lh < h - margin:
                    coords[f"auto-{xf:.2f}-{yf:.2f}"] = (x, y)
    background = image.getpixel((int(w * 0.02), int(h * 0.40)))
    candidates = {}
    for name, (x, y) in coords.items():
        box = (x, y, x + lw, y + lh)
        penalty = 1000 if any(intersects(box, text_box) for text_box in title_boxes) else 0
        # Keep the architecture's central silhouette available for the project image.
        if x < w * 0.68 and x + lw > w * 0.32 and y > h * 0.32:
            penalty += 12
        ratio = logo_region_contrast(image, box, logo_color)
        contrast_penalty = max(0, 4.5 - ratio) * 25
        candidates[name] = (region_complexity(image, box, background) + penalty + contrast_penalty, box, ratio)
    if requested == "auto":
        name = min(candidates, key=lambda key: candidates[key][0])
    else:
        name = requested
        if any(intersects(candidates[name][1], text_box) for text_box in title_boxes):
            raise ValueError(f"Logo position {name} overlaps the title; choose auto or another position.")
    return name, candidates[name][1], round(candidates[name][2], 2)


def render(args: argparse.Namespace) -> tuple[Path, dict]:
    proposal = getattr(args, "proposal", 1)
    if proposal not in (1, 2, 3):
        raise ValueError("Proposal must be 1, 2, or 3.")
    base_path = Path(args.base).expanduser()
    if not base_path.is_file():
        raise ValueError(f"Base image not found: {base_path}")
    logo_path = Path(args.logo).expanduser()
    if not logo_path.is_file():
        raise ValueError(f"Logo image not found: {logo_path}")
    english = args.english or TRANSLATIONS.get(args.festival)
    if not english:
        raise ValueError("No standard English translation for this festival; provide --english explicitly.")
    w, h = (int(v) for v in args.size.lower().split("x"))
    if w < 600 or h < 800 or w > 4000 or h > 6000:
        raise ValueError("--size must be WxH within 600x800 and 4000x6000.")
    chinese = args.chinese or args.festival
    if not chinese.strip() or not english.strip():
        raise ValueError("Festival and titles must not be empty.")
    c_font = font_path(args.font_chinese, CHINESE_FONTS, "chinese")
    e_font = font_path(args.font_english, ENGLISH_FONTS, "english")
    reference = Path(args.style_reference).expanduser() if args.style_reference else None
    if reference and not reference.is_file():
        raise ValueError(f"Style reference not found: {reference}")
    palette_id = None if reference else (getattr(args, "palette_id", None) or random.choice(tuple(COLORWAYS)))
    palette = palette_from_reference(reference, args.festival, proposal, palette_id)
    panel_color = palette[1]
    illustration_path = Path(args.illustration).expanduser() if args.illustration else base_path
    if not illustration_path.is_file():
        raise ValueError(f"Illustration not found: {illustration_path}")
    with Image.open(illustration_path) as source:
        if args.illustration:
            art = ImageOps.fit(ImageOps.exif_transpose(source).convert("RGB"), (w, h), method=Image.Resampling.LANCZOS)
        else:
            art = abstraction(source, (w, h), palette)
    if getattr(args, "recolor_proposal", 0):
        art = recolor_illustration(art, palette)
    if args.illustration:
        panel_color = art.getpixel((int(w * 0.04), int(h * 0.04)))
    title_color = (255, 255, 255) if contrast(panel_color, (255, 255, 255)) >= 4.5 else (5, 16, 35)
    canvas = art.copy()
    draw = ImageDraw.Draw(canvas)
    # The large color plane and building share space; the roof can cross in front of the headline.
    panel_bottom = int(h * 0.37)
    if not args.illustration:
        draw.polygon([(0, 0), (w, 0), (w, int(h * 0.18)), (int(w * 0.72), panel_bottom), (0, panel_bottom)], fill=panel_color)
        accent = (255, 211, 81) if "国庆" in args.festival else palette[-2]
        radius = int(w * 0.105)
        cx, cy = int(w * 0.83), int(h * 0.235)
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=accent)
        if "国庆" in args.festival:
            points = []
            for index in range(10):
                angle = -math.pi / 2 + index * math.pi / 5
                distance = radius * (0.58 if index % 2 == 0 else 0.24)
                points.append((cx + math.cos(angle) * distance, cy + math.sin(angle) * distance))
            draw.polygon(points, fill=rgb("#B6002E"))
    inner = int(w * 0.055)
    if proposal == 2:
        try:
            english_lines, ef, line_h = title_lines(draw, english, e_font, int(w * 0.68), int(h * 0.16), max_lines=1)
        except ValueError:
            english_lines, ef, line_h = title_lines(draw, english, e_font, int(w * 0.90), int(h * 0.23))
    else:
        english_lines, ef, line_h = title_lines(draw, english, e_font, int(w * 0.90), int(h * 0.23))
    y = int(h * (0.06 if proposal == 2 else 0.035))
    headline_step = int(ef.size * 1.05)
    title_boxes = []
    for index, line in enumerate(english_lines):
        if proposal == 3:
            line_x = inner if index == 0 else int(w * 0.145)
            line_y = int(h * (0.245 if index == 1 else 0.09))
        elif proposal == 2:
            line_x = inner
            line_y = int(h * (0.20 if index == 1 else 0.06))
        else:
            line_x = inner
            line_y = int(h * (0.245 if index == 1 else 0.035)) if args.illustration and len(english_lines) == 2 else y
        draw.text((line_x, line_y), line, font=ef, fill=title_color, stroke_width=0)
        left, top, right, bottom = draw.textbbox((line_x, line_y), line, font=ef)
        title_boxes.append((left - 12, top - 12, right + 12, bottom + 12))
        y = line_y + headline_step
    # Restore only the detected architectural silhouette, not a rectangular photo crop.
    with Image.open(illustration_path) as original:
        mask = subject_mask(original, (w, h), panel_bottom + int(h * 0.035), warm_only=bool(args.illustration))
    if mask is not None:
        canvas.paste(art, (0, 0), mask)
    draw = ImageDraw.Draw(canvas)
    # English carries the headline; Chinese stays a clearly smaller caption.
    cf_size = min(int(w * 0.055), 72, max(20, ef.size // 2))
    cf = ImageFont.truetype(c_font, cf_size)
    while draw.textbbox((0, 0), chinese, font=cf)[2] > int(w * 0.70) and cf_size > 20:
        cf_size -= 2
        cf = ImageFont.truetype(c_font, cf_size)
    if proposal == 3:
        chinese_y = int(h * 0.015)
    elif proposal == 2:
        chinese_y = int(h * (0.325 if len(english_lines) == 2 else 0.17))
    else:
        chinese_y = int(h * 0.365) if args.illustration and len(english_lines) == 2 else max(y + int(h * 0.014), int(h * 0.285))
    if not args.illustration and chinese_y + cf_size > panel_bottom - int(h * 0.012):
        raise ValueError("Titles do not fit in the composition. Use a shorter title or larger canvas.")
    draw.text((inner, chinese_y), chinese, font=cf, fill=title_color)
    left, top, right, bottom = draw.textbbox((inner, chinese_y), chinese, font=cf)
    title_boxes.append((left - 12, top - 12, right + 12, bottom + 12))
    with Image.open(logo_path) as raw_logo:
        logo = raw_logo.convert("RGBA")
    alpha_range = logo.getchannel("A").getextrema()
    if alpha_range != (0, 255):
        raise ValueError("Logo must have a transparent background and opaque artwork.")
    lbbox = logo.getchannel("A").getbbox()
    logo = logo.crop(lbbox)
    lw = int(w * 0.12)
    lh = round(lw * logo.height / logo.width)
    logo = logo.resize((lw, lh), Image.Resampling.LANCZOS)
    pixels = logo.load()
    opaque = [pixels[x, y][:3] for y in range(logo.height) for x in range(logo.width) if pixels[x, y][3] > 240]
    sampled_logo = tuple(int(sum(p[i] for p in opaque) / len(opaque)) for i in range(3))
    name, box, logo_contrast = choose_logo_position(canvas, (lw, lh), title_boxes, args.logo_position, sampled_logo)
    canvas.paste(logo, (box[0], box[1]), logo)
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", optimize=True)
    metadata = {
        "festival": args.festival,
        "proposal": proposal,
        "layout": {1: "left-stacked", 2: "horizontal-band", 3: "staggered"}[proposal],
        "colorway": COLORWAY_NAMES[palette_id] if palette_id else "reference-derived",
        "palette_id": palette_id,
        "chinese_title": chinese,
        "english_title": english,
        "size": [w, h],
        "style": "reference palette" if reference else "pop architecture default",
        "palette": [hexrgb(c) for c in palette],
        "logo_position": name,
        "logo_box": list(box),
        "logo_alpha_range": list(alpha_range),
        "logo_contrast_ratio": logo_contrast,
        "title_contrast_ratio": round(contrast(panel_color, title_color), 2),
        "english_font_size": ef.size,
        "chinese_font_size": cf.size,
        "chinese_font": c_font,
        "warnings": (["Logo contrast under 4.5 on part of its background; inspect before publication"] if logo_contrast < 4.5 else [])
        + (["Title contrast under 4.5 on its primary background; inspect before publication"] if contrast(panel_color, title_color) < 4.5 else []),
    }
    output.with_suffix(".json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return output, metadata


def render_set(args: argparse.Namespace) -> list[tuple[Path, dict]]:
    count = getattr(args, "count", 3)
    if count not in (1, 2, 3):
        raise ValueError("--count must be 1, 2, or 3.")
    illustrations = getattr(args, "illustrations", None)
    if illustrations and len(illustrations) != count:
        raise ValueError("--illustrations requires one artwork path per proposal.")
    if illustrations and count == 1:
        raise ValueError("Use --illustration with --count 1.")
    if illustrations and len({str(Path(path).resolve()) for path in illustrations}) != count:
        raise ValueError("--illustrations requires distinct artwork paths for the proposals.")
    requested = Path(args.output)
    if requested.suffix.lower() != ".png":
        raise ValueError("--output must end in .png.")
    palette_ids = getattr(args, "palette_ids", None)
    if palette_ids:
        if len(palette_ids) != count or len(set(palette_ids)) != count or any(value not in COLORWAYS for value in palette_ids):
            raise ValueError("--palette-ids requires one distinct ID from 1 to 6 per proposal.")
    else:
        palette_ids = random.sample(tuple(COLORWAYS), count)
    results = []
    for index, proposal in enumerate(range(1, count + 1) if count > 1 else [getattr(args, "proposal", 1)]):
        current = argparse.Namespace(**vars(args))
        current.proposal = proposal
        current.palette_id = palette_ids[index]
        if count > 1:
            current.output = str(requested.with_name(f"{requested.stem}-{proposal:02d}.png"))
            if illustrations:
                current.illustration = illustrations[proposal - 1]
            elif args.illustration:
                # A single supplied artwork remains usable for a draft set.
                # Distinct generated artwork for each proposal gives better results.
                current.recolor_proposal = proposal
        results.append(render(current))
    return results


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="poster-smoke-") as td:
        folder = Path(td)
        base = Image.new("RGB", (900, 1300), (179, 218, 230))
        d = ImageDraw.Draw(base)
        d.polygon([(160, 1250), (220, 280), (430, 130), (690, 380), (770, 1250)], fill=(192, 80, 73))
        for y in range(410, 1190, 125):
            for x in range(270, 650, 105):
                d.rectangle((x, y, x + 56, y + 72), fill=(49, 68, 94))
        # Leave a light architectural color plane in the required logo corner.
        d.polygon([(690, 1000), (900, 930), (900, 1300), (690, 1300)], fill=(250, 243, 220))
        base_path = folder / "architecture.png"
        base.save(base_path)
        logo_path = folder / "demo-logo.png"
        demo_logo = Image.new("RGBA", (360, 120), (0, 0, 0, 0))
        ImageDraw.Draw(demo_logo).rectangle((20, 20, 340, 100), fill=(20, 20, 20, 255))
        demo_logo.save(logo_path)
        arguments = argparse.Namespace(base=str(base_path), illustration=None, festival="中秋节", chinese=None, english=None,
                                       style_reference=None, size="900x1350", logo=str(logo_path), logo_position="bottom-right", font_chinese=None,
                                       font_english=None, output=str(folder / "poster.png"))
        output, info = render(arguments)
        with Image.open(output) as result:
            assert result.size == (900, 1350)
        assert info["logo_alpha_range"] == [0, 255]
        assert info["logo_position"] == "bottom-right", info
        assert info["logo_contrast_ratio"] >= 4.5 or any("Logo contrast under" in warning for warning in info["warnings"]), info
        assert info["title_contrast_ratio"] >= 4.5, info
        assert output.with_suffix(".json").is_file()
        arguments.count = 3
        arguments.output = str(folder / "set.png")
        variants = render_set(arguments)
        assert len(variants) == 3
        assert len({info["layout"] for _, info in variants}) == 3
        assert len({tuple(info["palette"]) for _, info in variants}) == 3
        assert len({info["palette_id"] for _, info in variants}) == 3
        assert all(info["palette"] == list(COLORWAYS[info["palette_id"]]) for _, info in variants)
        assert all(path.is_file() and path.with_suffix(".json").is_file() for path, _ in variants)
        print(f"PASS: rendered 3 distinct proposals; logo={info['logo_position']}; contrast={info['logo_contrast_ratio']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a festival poster from a project photo.")
    parser.add_argument("--base", help="Project building photo")
    parser.add_argument("--festival", help="Chinese festival or solar term")
    parser.add_argument("--output", help="Output PNG path")
    parser.add_argument("--logo", help="Path to a logo PNG with transparency; provide your own authorized artwork")
    parser.add_argument("--chinese", help="Override Chinese title")
    parser.add_argument("--english", help="Override English title; required for unfamiliar festivals")
    parser.add_argument("--style-reference", help="Reference image used to derive palette")
    art_group = parser.add_mutually_exclusive_group()
    art_group.add_argument("--illustration", help="One prepared artwork; a three-proposal draft set receives distinct color treatments")
    art_group.add_argument("--illustrations", nargs="+", metavar="ART", help="Different prepared artworks, one per proposal")
    parser.add_argument("--count", type=int, choices=(1, 2, 3), default=3, help="Number of proposals (default: 3)")
    parser.add_argument("--palette-ids", nargs="+", type=int, metavar="ID", help="Optional palette IDs, one distinct value from 1 to 6 per proposal; default: random sample")
    parser.add_argument("--proposal", type=int, choices=(1, 2, 3), default=1, help="Layout and colorway when --count 1 (default: 1)")
    parser.add_argument("--size", default="1200x1800", help="Canvas width x height (default: 1200x1800)")
    parser.add_argument("--logo-position", default="bottom-right", choices=["bottom-right"], help="Logo placement, fixed at bottom-right")
    parser.add_argument("--font-chinese", help="Path to Chinese font file")
    parser.add_argument("--font-english", help="Path to English font file")
    parser.add_argument("--self-test", action="store_true", help="Render synthetic sample and validate output")
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
        else:
            if not (args.base and args.festival and args.output and args.logo):
                parser.error("--base, --festival, --output, and --logo are required unless --self-test is used")
            results = render_set(args)
            for output, info in results:
                print(f"Saved {output} and {output.with_suffix('.json')} (proposal {info['proposal']}: {info['layout']})")
    except (ValueError, OSError, AssertionError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
