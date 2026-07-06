from __future__ import annotations

import math
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "public" / "assets"
TMP = ROOT / "tmp" / "assetgen" / "hero_frames"
ASSETS.mkdir(parents=True, exist_ok=True)
TMP.mkdir(parents=True, exist_ok=True)

FONT_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
]
FONT_PATH = next((p for p in FONT_CANDIDATES if Path(p).exists()), None)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if FONT_PATH:
        try:
            # PingFang TTC face indexes differ by macOS version; index 0 is safe.
            return ImageFont.truetype(FONT_PATH, size=size, index=0)
        except Exception:
            pass
    return ImageFont.load_default()


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def mix(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def vertical_gradient(size: tuple[int, int], top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size, top)
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        col = mix(top, bottom, t)
        for x in range(w):
            px[x, y] = col
    return img


def radial_glow(base: Image.Image, center: tuple[int, int], radius: int, color: tuple[int, int, int], alpha: int) -> None:
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    cx, cy = center
    steps = 42
    for i in range(steps, 0, -1):
        r = int(radius * i / steps)
        a = int(alpha * (i / steps) ** 2)
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(*color, a))
    base.alpha_composite(overlay)


def rounded_rect(draw: ImageDraw.ImageDraw, box, radius=24, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def draw_text(draw: ImageDraw.ImageDraw, xy, text: str, size: int, fill, anchor=None, bold=False):
    draw.text(xy, text, font=font(size, bold=bold), fill=fill, anchor=anchor)


def draw_avatar(draw: ImageDraw.ImageDraw, cx: int, cy: int, scale: float = 1.0, mouth_open: float = 0.0, eye_shift: float = 0.0):
    # Body
    body_w, body_h = int(190 * scale), int(220 * scale)
    body_box = (cx - body_w // 2, cy + int(40 * scale), cx + body_w // 2, cy + body_h)
    rounded_rect(draw, body_box, int(54 * scale), fill=(19, 34, 49, 255), outline=(78, 101, 126, 130), width=max(1, int(2 * scale)))
    # Neck
    draw.rounded_rectangle((cx - int(18 * scale), cy + int(16 * scale), cx + int(18 * scale), cy + int(72 * scale)), radius=int(9 * scale), fill=(154, 106, 77, 255))
    # Head
    head_w, head_h = int(116 * scale), int(132 * scale)
    head_box = (cx - head_w // 2, cy - int(88 * scale), cx + head_w // 2, cy + int(44 * scale))
    draw.rounded_rectangle(head_box, radius=int(46 * scale), fill=(184, 126, 84, 255), outline=(245, 190, 126, 90), width=max(1, int(2 * scale)))
    # Hair cap
    hair_box = (head_box[0] + int(8 * scale), head_box[1] - int(3 * scale), head_box[2] - int(8 * scale), head_box[1] + int(48 * scale))
    draw.rounded_rectangle(hair_box, radius=int(32 * scale), fill=(47, 38, 34, 255))
    # Eyes
    ex = int(25 * scale)
    ey = cy - int(28 * scale)
    for side in [-1, 1]:
        px = cx + side * ex + int(eye_shift * scale)
        draw.ellipse((px - int(6 * scale), ey - int(6 * scale), px + int(6 * scale), ey + int(6 * scale)), fill=(250, 246, 238, 255))
        draw.ellipse((px - int(2 * scale), ey - int(2 * scale), px + int(2 * scale), ey + int(2 * scale)), fill=(42, 47, 52, 255))
    # Mouth
    mw = int(30 * scale)
    mh = int((6 + 16 * mouth_open) * scale)
    my = cy + int(10 * scale)
    draw.rounded_rectangle((cx - mw // 2, my, cx + mw // 2, my + mh), radius=max(2, int(mh / 2)), fill=(72, 35, 34, 255))
    # Suit line
    draw.line((cx, cy + int(70 * scale), cx, cy + int(205 * scale)), fill=(95, 118, 142, 150), width=max(1, int(3 * scale)))


def draw_control_room_frame(t: float, size=(1280, 860)) -> Image.Image:
    w, h = size
    base = vertical_gradient(size, (10, 14, 19), (20, 31, 44)).convert("RGBA")
    radial_glow(base, (int(w * 0.68), int(h * 0.24)), 360, (92, 201, 255), 70)
    radial_glow(base, (int(w * 0.18), int(h * 0.12)), 320, (240, 179, 90), 55)
    draw = ImageDraw.Draw(base, "RGBA")

    # Subtle grid
    grid_col = (255, 255, 255, 15)
    shift = int((t * 34) % 34)
    for x in range(-shift, w, 34):
        draw.line((x, 0, x, h), fill=grid_col, width=1)
    for y in range(-shift, h, 34):
        draw.line((0, y, w, y), fill=grid_col, width=1)

    # Main stage
    stage = (56, 74, 790, 675)
    rounded_rect(draw, stage, 34, fill=(9, 16, 23, 212), outline=(255, 255, 255, 32), width=2)
    for i in range(5):
        pulse = (math.sin(t * math.tau + i * 0.55) + 1) / 2
        r = int(160 + i * 44 + pulse * 12)
        draw.ellipse((423 - r, 370 - r, 423 + r, 370 + r), outline=(240, 179, 90, max(20, 75 - i * 9)), width=2)
    draw_avatar(draw, 423, 360, scale=1.45, mouth_open=(math.sin(t * math.tau * 4) + 1) / 2, eye_shift=math.sin(t * math.tau * 2) * 5)

    # Caption
    rounded_rect(draw, (90, 585, 756, 652), 20, fill=(4, 9, 14, 190), outline=(255, 255, 255, 28), width=1)
    draw_text(draw, (118, 609), "正在讲解：新品卖点 03 / 18", 30, (245, 248, 250, 255), bold=True)
    wave_x = 545
    for i in range(20):
        v = (math.sin(t * math.tau * 2.6 + i * 0.7) + 1) / 2
        bh = int(10 + v * 30)
        draw.rounded_rectangle((wave_x + i * 8, 631 - bh, wave_x + i * 8 + 4, 631), radius=2, fill=(57, 229, 140, 210))

    # Top status
    rounded_rect(draw, (56, 26, 1225, 62), 18, fill=(255, 255, 255, 25), outline=(255, 255, 255, 26), width=1)
    draw_text(draw, (86, 36), "SYN LIVE CONTROL / 低延迟数字人直播", 19, (232, 238, 244, 255), bold=True)
    draw_text(draw, (1106, 36), "LIVE 00:28:%02d" % int(16 + t * 30), 18, (57, 229, 140, 255), bold=True)

    # Platform panel
    right_x = 825
    panels = ["抖音", "快手", "淘宝", "视频号"]
    for i, p in enumerate(panels):
        y = 92 + i * 112
        rounded_rect(draw, (right_x, y, 1215, y + 86), 22, fill=(255, 255, 255, 32), outline=(255, 255, 255, 24), width=1)
        draw_text(draw, (right_x + 24, y + 25), p, 26, (209, 219, 228, 255), bold=True)
        live = "待授权" if i == 3 else "LIVE"
        col = (240, 179, 90, 255) if i == 3 else (57, 229, 140, 255)
        draw_text(draw, (1164, y + 29), live, 20, col, anchor="ra", bold=True)
        if i != 3:
            prog = 110 + int(80 * ((math.sin(t * math.tau + i) + 1) / 2))
            draw.rounded_rectangle((right_x + 24, y + 60, right_x + 24 + prog, y + 65), radius=3, fill=(57, 229, 140, 180))

    # Chat cards
    chats = [
        ("观众", "这款适合新手吗？"),
        ("AI", "适合，已调用商品库卖点。"),
        ("风控", "金融风险词已拦截 2 条"),
    ]
    for i, (name, text) in enumerate(chats):
        y = 552 + i * 82
        rounded_rect(draw, (825, y, 1215, y + 66), 18, fill=(255, 255, 255, 30), outline=(255, 255, 255, 20), width=1)
        draw_text(draw, (848, y + 12), name, 18, (240, 179, 90, 255), bold=True)
        draw_text(draw, (848, y + 37), text, 20, (232, 238, 244, 255))

    # Timeline
    nodes = ["开场", "商品 A", "问答", "福利", "收尾"]
    for i, node in enumerate(nodes):
        x = 56 + i * 235
        active = i == 1 or (i == 2 and math.sin(t * math.tau) > 0.65)
        fill = (240, 179, 90, 255) if active else (255, 255, 255, 24)
        text_col = (17, 24, 33, 255) if active else (190, 202, 214, 255)
        rounded_rect(draw, (x, 720, x + 205, 780), 18, fill=fill, outline=(255, 255, 255, 24), width=1)
        draw_text(draw, (x + 102, 739), node, 22, text_col, anchor="ma", bold=True)

    return base


def save_control_room_assets():
    poster = draw_control_room_frame(0.18, (1280, 860))
    poster.save(ASSETS / "hero-live-studio-poster.png", optimize=True)

    # Product preview: richer static control-room screen.
    control = draw_control_room_frame(0.32, (1600, 1000))
    draw = ImageDraw.Draw(control, "RGBA")
    rounded_rect(draw, (68, 828, 1532, 940), 30, fill=(246, 241, 232, 240), outline=(255, 255, 255, 40), width=1)
    for i, label in enumerate(["ASR 84ms", "LLM 420ms", "TTS 310ms", "渲染 30fps", "推流 4 路"]):
        x = 100 + i * 285
        draw_text(draw, (x, 858), label, 30, (24, 32, 42, 255), bold=True)
        draw.rounded_rectangle((x, 902, x + 190, 912), radius=5, fill=(240, 179, 90, 230))
    control.save(ASSETS / "product-live-control.png", optimize=True)


def save_product_images():
    # Script timeline
    img = vertical_gradient((1600, 950), (246, 241, 232), (232, 222, 207)).convert("RGBA")
    draw = ImageDraw.Draw(img, "RGBA")
    radial_glow(img, (1380, 90), 340, (240, 179, 90), 60)
    rounded_rect(draw, (70, 72, 1530, 878), 42, fill=(17, 24, 33, 248), outline=(255, 255, 255, 55), width=2)
    draw_text(draw, (122, 120), "SCRIPT STUDIO / PPT · Word · Excel 自动解析", 30, (240, 179, 90, 255), bold=True)
    draw_text(draw, (122, 176), "直播流程时间线", 58, (246, 241, 232, 255), bold=True)
    lanes = ["开场欢迎", "商品卖点", "弹幕问答", "限时福利", "结束引导"]
    for i, lane in enumerate(lanes):
        y = 295 + i * 105
        draw_text(draw, (122, y + 25), lane, 26, (211, 222, 231, 255), bold=True)
        draw.line((300, y + 42, 1460, y + 42), fill=(255, 255, 255, 34), width=2)
        for j in range(4):
            x = 330 + j * 270 + (i % 2) * 60
            color = (240, 179, 90, 230) if (i + j) % 3 == 0 else (92, 201, 255, 160)
            rounded_rect(draw, (x, y, x + 190, y + 72), 20, fill=color, outline=(255, 255, 255, 35), width=1)
            draw_text(draw, (x + 22, y + 21), f"节点 {j + 1}", 22, (17, 24, 33, 255), bold=True)
    img.save(ASSETS / "product-script-timeline.png", optimize=True)

    # Stream health
    img = vertical_gradient((1600, 950), (9, 14, 20), (23, 34, 47)).convert("RGBA")
    radial_glow(img, (260, 200), 380, (57, 229, 140), 60)
    radial_glow(img, (1380, 80), 360, (240, 179, 90), 55)
    draw = ImageDraw.Draw(img, "RGBA")
    rounded_rect(draw, (70, 70, 1530, 880), 42, fill=(255, 255, 255, 22), outline=(255, 255, 255, 38), width=2)
    draw_text(draw, (118, 120), "MULTI STREAM / 平台推流健康", 30, (240, 179, 90, 255), bold=True)
    platforms = ["抖音", "快手", "淘宝", "视频号"]
    for i, p in enumerate(platforms):
        x = 125 + (i % 2) * 720
        y = 220 + (i // 2) * 260
        rounded_rect(draw, (x, y, x + 620, y + 190), 30, fill=(10, 17, 24, 220), outline=(255, 255, 255, 36), width=1)
        draw_text(draw, (x + 34, y + 30), p, 34, (246, 241, 232, 255), bold=True)
        status = "LIVE" if i != 3 else "待授权"
        status_col = (57, 229, 140, 255) if i != 3 else (240, 179, 90, 255)
        draw_text(draw, (x + 555, y + 34), status, 24, status_col, anchor="ra", bold=True)
        for j, label in enumerate(["码率", "延迟", "丢帧"]):
            yy = y + 86 + j * 28
            draw_text(draw, (x + 36, yy), label, 18, (151, 168, 184, 255))
            fill_len = 260 + ((i + j) * 43 % 160)
            draw.rounded_rectangle((x + 122, yy + 8, x + 122 + fill_len, yy + 16), radius=4, fill=status_col)
    img.save(ASSETS / "product-stream-health.png", optimize=True)


def save_solution_images():
    configs = {
        "commerce": ("电商直播", "商品卡 · 优惠弹幕 · 智能促单", (240, 179, 90), (74, 38, 18)),
        "education": ("教育培训", "课件解析 · 数字讲师 · 实时问答", (92, 201, 255), (18, 60, 76)),
        "finance": ("金融服务", "合规话术 · 风险提示 · 人工审核", (164, 140, 255), (38, 40, 78)),
        "gov": ("政企宣传", "政策宣讲 · 展厅讲解 · 服务报告", (57, 229, 140), (32, 62, 46)),
    }
    for name, (title, subtitle, accent, bottom) in configs.items():
        img = vertical_gradient((900, 620), (10, 14, 20), bottom).convert("RGBA")
        radial_glow(img, (700, 80), 260, accent, 80)
        radial_glow(img, (120, 520), 240, (240, 179, 90), 35)
        draw = ImageDraw.Draw(img, "RGBA")
        # environment panels
        for i in range(8):
            x = 60 + (i % 4) * 200
            y = 90 + (i // 4) * 170
            a = 25 + i * 6
            rounded_rect(draw, (x, y, x + 150, y + 105), 22, fill=(255, 255, 255, a), outline=(255, 255, 255, 18), width=1)
        # digital person / podium
        draw_avatar(draw, 236, 272, scale=1.0, mouth_open=0.35, eye_shift=0)
        rounded_rect(draw, (420, 190, 790, 430), 28, fill=(246, 241, 232, 220), outline=(255, 255, 255, 70), width=1)
        draw_text(draw, (450, 222), title, 48, (24, 32, 42, 255), bold=True)
        draw_text(draw, (450, 286), subtitle, 24, (78, 88, 98, 255))
        for j in range(4):
            yy = 340 + j * 22
            draw.rounded_rectangle((450, yy, 735 - j * 45, yy + 9), radius=5, fill=(*accent, 220))
        # overlay title at bottom
        rounded_rect(draw, (48, 486, 852, 572), 24, fill=(7, 11, 16, 190), outline=(255, 255, 255, 24), width=1)
        draw_text(draw, (80, 512), title, 34, (246, 241, 232, 255), bold=True)
        draw_text(draw, (80, 552), subtitle, 20, (206, 216, 226, 255))
        img.save(ASSETS / f"solution-{name}.png", optimize=True)


def save_video():
    # Generate a modest number of frames to keep repo size reasonable.
    frames = 120
    for i in range(frames):
        t = i / frames
        frame = draw_control_room_frame(t, (960, 640))
        frame.save(TMP / f"frame_{i:04d}.png")
    mp4 = ASSETS / "hero-live-studio.mp4"
    cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        "24",
        "-i",
        str(TMP / "frame_%04d.png"),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-crf",
        "24",
        str(mp4),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Optional webm for browsers that prefer it.
    webm = ASSETS / "hero-live-studio.webm"
    cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        "24",
        "-i",
        str(TMP / "frame_%04d.png"),
        "-c:v",
        "libvpx-vp9",
        "-b:v",
        "0",
        "-crf",
        "36",
        str(webm),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    # Keep GPT Image generated hero/product-live assets intact.
    # This local generator only refreshes supporting preview and scene images.
    save_product_images()
    save_solution_images()
    shutil.rmtree(TMP, ignore_errors=True)
    print("Generated supporting marketing assets:")
    for path in sorted(ASSETS.glob("*.png")) + sorted(ASSETS.glob("*.mp4")) + sorted(ASSETS.glob("*.webm")):
        print(f"- {path.relative_to(ROOT)} ({path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
