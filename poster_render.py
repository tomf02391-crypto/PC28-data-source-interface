# -*- coding: utf-8 -*-
"""
严格规格渲染 v7：输出固定 2855x960（比例113:38），等比缩放底图，只叠加数字。
- v7修复：球心坐标修正为底图Hough实测球心（解决数字不居中）；金色增饱和提亮（解决掉色）
- 字体：思源黑体 Noto Sans SC Bold(700)
- 顶部期号：与"第/期"严格等高（夏172px / 冬173px）；夏橙红渐变金+细金发光，冬大红+微红发光
- 球号：个位数 220px、两位数 170px（固定字号）；白色内环质心居中，四周留40px边距，不碰圆环边框
- 颜色：夏 蓝/紫球黑字 #000000、青绿/红球金属金；冬 全黑字
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import os

def _find_font():
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "NotoSansSC.ttf"),
        "/home/marvis/.fonts/NotoSansSC.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("未找到思源黑体字体")

FONT = _find_font()
print(f"[字体] {FONT}")
OUT_W, OUT_H = 2855, 960
BALL_MARGIN = 40  # 白圈内四周留边距

SUMMER = {
    "base": os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "120891.png"),
    "title_center": (1641, 297),   # 原图坐标，等比缩放
    "title_h": 173,                 # 缩放后第/期高度(实测)
    "balls": [
        (550, 839, 170),
        (1409, 841, 170),
        (2274, 838, 170),
        (3477, 837, 170),
    ],
}
WINTER = {
    "base": os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "120889.png"),
    "title_center": (1645, 295),
    "title_h": 173,
    "balls": [
        (559, 838, 170),
        (1420, 839, 170),
        (2281, 840, 170),
        (3469, 839, 170),
    ],
}


def load_scaled(cfg):
    im = Image.open(cfg["base"]).convert("RGBA")
    w, h = im.size
    sx, sy = OUT_W / w, OUT_H / h
    return im.resize((OUT_W, OUT_H), Image.LANCZOS), (sx, sy)


def make_font(size, weight=700):
    f = ImageFont.truetype(FONT, size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


def make_char_layer(text, font_size, stroke, fill=(255, 255, 255, 255), target_h=None, supersample=2, weight=700, stroke_fill=(255, 255, 255, 255)):
    """生成文字RGBA图层（含描边）；超采样绘制后缩回 font_size 实际尺寸；target_h 指定时等比缩放到该高度"""
    f = make_font(font_size * supersample, weight=weight)
    pad = stroke + 8
    tmp = Image.new("RGBA", (font_size * 6 * supersample, font_size * 4 * supersample), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    d.text((tmp.width // 2, tmp.height // 2), text, font=f, fill=fill, anchor="mm",
           stroke_width=stroke * supersample, stroke_fill=stroke_fill)
    bbox = tmp.getbbox()
    if bbox is None:
        return None
    layer = tmp.crop(bbox)
    # 超采样降回 1x 尺寸
    if supersample != 1:
        layer = layer.resize((max(1, layer.width // supersample), max(1, layer.height // supersample)), Image.LANCZOS)
    if target_h and layer.height > 0:
        scale = target_h / layer.height
        layer = layer.resize((max(1, int(layer.width * scale)), target_h), Image.LANCZOS)
    return layer


def layer_from_mask(mask_img, color, blur=0):
    a = np.array(mask_img.convert("L"))
    rgba = np.zeros((a.shape[0], a.shape[1], 4), dtype=np.uint8)
    rgba[:, :, 0] = color[0]
    rgba[:, :, 1] = color[1]
    rgba[:, :, 2] = color[2]
    rgba[:, :, 3] = a
    layer = Image.fromarray(rgba, "RGBA")
    if blur > 0:
        layer = layer.filter(ImageFilter.GaussianBlur(blur))
    return layer


def vgrad_layer(mask_img, top_color, bottom_color, blur=0):
    a = np.array(mask_img.convert("L"))
    h, w = a.shape
    rgba = np.zeros((h, w, 4), dtype=np.float32)
    t = np.linspace(0, 1, h)[:, None]
    for c in range(3):
        rgba[:, :, c] = top_color[c] * (1 - t) + bottom_color[c] * t
    rgba[:, :, 3] = a
    layer = Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), "RGBA")
    if blur > 0:
        layer = layer.filter(ImageFilter.GaussianBlur(blur))
    return layer


def paste_center(base, layer, center):
    base.alpha_composite(layer, (int(center[0] - layer.width // 2), int(center[1] - layer.height // 2)))


def detect_white_ring_center(base, cx, cy, r):
    """白色区域质心作为球号放置中心"""
    a = np.array(base.convert("RGB")).astype(np.float32)
    x0, x1 = max(0, int(cx - r * 1.05)), min(base.width, int(cx + r * 1.05))
    y0, y1 = max(0, int(cy - r * 1.05)), min(base.height, int(cy + r * 1.05))
    reg = a[y0:y1, x0:x1]
    rr, gg, bb = reg[:, :, 0], reg[:, :, 1], reg[:, :, 2]
    YY, XX = np.mgrid[0:reg.shape[0], 0:reg.shape[1]]
    dist = np.sqrt((XX - (cx - x0)) ** 2 + (YY - (cy - y0)) ** 2)
    inside = dist <= r * 0.95
    white = (rr > 200) & (gg > 200) & (bb > 200) & inside
    ys, xs = np.where(white)
    if len(xs) < 20:
        return (cx, cy)
    return (float(xs.mean()) + x0, float(ys.mean()) + y0)


def draw_title_summer(base, period, h, center):
    cx, cy = center
    fs = int(h * 1.42)
    sw = int(h * 0.015)
    char = make_char_layer(period, fs, sw, target_h=h, weight=550)
    if char is None:
        return base
    stroke = make_char_layer(period, fs, sw + int(h * 0.03), fill=(15, 10, 12, 255), target_h=h + int(h * 0.06), weight=550)
    glow = make_char_layer(period, fs, sw, target_h=h, weight=550)
    glow_layer = layer_from_mask(glow, (255, 205, 60), blur=int(h * 0.05))
    grad = vgrad_layer(char, (255, 70, 0), (255, 205, 40))
    paste_center(base, glow_layer, (cx, cy))
    if stroke is not None:
        paste_center(base, stroke, (cx, cy))
    paste_center(base, grad, (cx, cy))
    return base


def draw_title_winter(base, period, h, center):
    cx, cy = center
    fs = int(h * 1.42)
    sw = int(h * 0.015)
    char = make_char_layer(period, fs, sw, target_h=h, weight=550)
    if char is None:
        return base
    stroke = make_char_layer(period, fs, sw + int(h * 0.03), fill=(30, 5, 5, 255), target_h=h + int(h * 0.06), weight=550)
    glow = make_char_layer(period, fs, sw, target_h=h, weight=550)
    glow_layer = layer_from_mask(glow, (255, 40, 40), blur=int(h * 0.055))
    red = layer_from_mask(char, (225, 15, 15))
    paste_center(base, glow_layer, (cx, cy))
    if stroke is not None:
        paste_center(base, stroke, (cx, cy))
    paste_center(base, red, (cx, cy))
    return base


def draw_ball_fixed(base, cx, cy, r, num, fs, gold=False):
    """固定字号球号：白圈质心居中；仅防数字超球界"""
    sw = 0
    char = make_char_layer(num, fs, sw)
    if char is None:
        return base
    maxd = r * 2 - 4  # 防超界保护（不强制压到40px边距）
    if char.width > maxd or char.height > maxd:
        sc = min(maxd / char.width, maxd / char.height)
        char = char.resize((int(char.width * sc), int(char.height * sc)), Image.LANCZOS)
    if gold:
        # v8 修复掉色：更饱和浓郁的金属金 + 窄半透明高光 + 深金描边
        stroke_layer = make_char_layer(num, fs, max(2, int(fs * 0.055)), fill=(170, 95, 5, 255), stroke_fill=(170, 95, 5, 255))
        grad = vgrad_layer(char, (255, 216, 90), (215, 105, 0))
        a = np.array(char.convert("L"))
        hi_h = max(2, int(a.shape[0] * 0.16))
        hi_mask = np.zeros_like(a)
        hi_mask[:hi_h, :] = a[:hi_h, :]
        hi_img = Image.fromarray(hi_mask, "L")
        hi_layer = layer_from_mask(hi_img, (255, 244, 200))
        hi_arr = np.array(hi_layer)
        hi_arr[:, :, 3] = (hi_arr[:, :, 3] * 0.6).astype(np.uint8)
        hi_layer = Image.fromarray(hi_arr, "RGBA")
        if stroke_layer is not None:
            paste_center(base, stroke_layer, (cx, cy))
        paste_center(base, grad, (cx, cy))
        paste_center(base, hi_layer, (cx, cy))
    else:
        black = layer_from_mask(char, (0, 0, 0))
        paste_center(base, black, (cx, cy))
    return base


def _render_season(cfg, period, balls, out, style):
    base, (sx, sy) = load_scaled(cfg)
    # 期号中心
    cx0, cy0 = cfg["title_center"]
    tcenter = (cx0 * sx, cy0 * sy)
    h = cfg["title_h"]
    if style == "summer":
        base = draw_title_summer(base, period, h, tcenter)
    else:
        base = draw_title_winter(base, period, h, tcenter)
    # 球号
    for i, (bx, by, br) in enumerate(cfg["balls"]):
        cx, cy = bx * sx, by * sy
        r = br * min(sx, sy)
        cxx, cyy = cx, cy
        num = balls[i]
        fs = 170 if len(num) >= 2 else 220
        if style == "summer" and i >= 2:
            base = draw_ball_fixed(base, cxx, cyy, r, num, fs, gold=True)
        else:
            base = draw_ball_fixed(base, cxx, cyy, r, num, fs, gold=False)
    base.convert("RGB").save(out)
    print(out, "title_h=", h, "title_center=", (int(tcenter[0]), int(tcenter[1])))


def validate_input(title_str, b1, b2, b3, b4):
    if not (isinstance(title_str, str) and len(title_str) >= 5 and title_str.isdigit()):
        raise ValueError(f"期号必须至少5位数字字符串，输入:{title_str}")
    for name, val in [("球1", b1), ("球2", b2), ("球3", b3)]:
        if not (isinstance(val, str) and len(val) == 1 and val.isdigit()):
            raise ValueError(f"{name}必须0-9的字符串，输入:{val}")
    if not (isinstance(b4, str) and b4.isdigit()):
        raise ValueError(f"球4必须数字字符串，输入:{b4}")
    i4 = int(b4)
    if not 0 <= i4 <= 27:
        raise ValueError(f"球4取值0-27，输入:{b4}")
    if int(b1) + int(b2) + int(b3) != i4:
        raise ValueError(f"校验失败：{b1}+{b2}+{b3}={int(b1)+int(b2)+int(b3)} != {b4}")


def is_summer() -> bool:
    import datetime
    m = datetime.datetime.now().month
    return 5 <= m <= 9


def render_season(title_str, b1, b2, b3, b4, out_path="result.png"):
    validate_input(title_str, b1, b2, b3, b4)
    balls = [str(int(b1)), str(int(b2)), str(int(b3)), str(int(b4))]
    style = "summer" if is_summer() else "winter"
    cfg = SUMMER if style == "summer" else WINTER
    _render_season(cfg, title_str, balls, out_path, style)
    return out_path


if __name__ == "__main__":
    render_season("3472020", "1", "2", "7", "10", "result.png")
