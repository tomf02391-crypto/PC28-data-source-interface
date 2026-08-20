# -*- coding: utf-8 -*-
"""
海报生成器：冰雪版 + 夏日海滩版
新增业务约束：球1 + 球2 + 球3 = 球4
调用 render_all(期号8位字符串,球1,球2,球3,球4)
约束：
    b1,b2,b3: 0‑9
    b4: 0‑27
    int(b1)+int(b2)+int(b3) == int(b4)
    title_str:8位数字字符串
其余画面元素全部固定不变，仅替换数字
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import os, math, random, time

W, H = 1808, 608
OUT = "./output"

def _find_font():
    candidates = [
        r"C:/Windows/Fonts/simhei.ttf",
        r"C:/Windows/Fonts/msyh.ttc",
        "/home/marvis/.fonts/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("未找到可用中文字体，请安装 wqy-microhei 或 Noto CJK")

FONT = _find_font()
print(f"[字体] 使用: {FONT}")

def validate_input(title_str, b1, b2, b3, b4):
    """业务数据校验，出错抛出异常，阻止生成错误图片"""
    if not (isinstance(title_str, str) and len(title_str)==8 and title_str.isdigit()):
        raise ValueError(f"期号必须8位数字字符串，输入:{title_str}")
    for name,val in [("球1",b1),("球2",b2),("球3",b3)]:
        if not isinstance(val,str) or len(val)!=1 or (not val.isdigit()):
            raise ValueError(f"{name}必须0‑9的字符串，输入:{val}")
        iv = int(val)
        if not 0<=iv<=9:
            raise ValueError(f"{name}取值0‑9，输入:{val}")
    if not (isinstance(b4,str) and b4.isdigit()):
        raise ValueError(f"球4必须数字字符串，输入:{b4}")
    i4 = int(b4)
    if not 0 <= i4 <= 27:
        raise ValueError(f"球4取值0‑27，输入:{b4}")

    # ======新增：球1+球2+球3 等于球4校验======
    i1 = int(b1)
    i2 = int(b2)
    i3 = int(b3)
    sum_123 = i1 + i2 + i3
    if sum_123 != i4:
        raise ValueError(f"【业务规则校验失败】球1({i1})+球2({i2})+球3({i3}) = {sum_123}，不等于球4({i4})")

    print(f"✅数据校验通过 | 期号:{title_str} | 球:[{b1},{b2},{b3},{b4}] | {i1}+{i2}+{i3}={i4}")

def vgrad(w, h, stops):
    img = np.zeros((h, w, 3), dtype=np.float32)
    ys = np.linspace(0, 1, h)
    for c in range(3):
        xs = [p for p, _ in stops]
        vals = [v[c] for _, v in stops]
        img[:, :, c] = np.interp(ys, xs, vals)[:, None]
    return Image.fromarray(img.astype(np.uint8), "RGB")

def radial_glow(w, h, cx, cy, radius, color, intensity=1.0):
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / radius
    glow = np.clip(1 - d, 0, 1) ** 2 * intensity
    img = np.zeros((h, w, 3), dtype=np.float32)
    for c in range(3):
        img[:, :, c] = color[c] * glow[:, :]
    return img

def draw_flag(base):
    d = ImageDraw.Draw(base)
    fx, fy, fw, fh = 36, 36, 132, 66
    d.rectangle([fx, fy, fx + fw, fy + fh], fill=(255, 255, 255))
    d.rectangle([fx, fy, fx + fw * 0.28, fy + fh], fill=(200, 16, 46))
    d.rectangle([fx + fw * 0.72, fy, fx + fw, fy + fh], fill=(200, 16, 46))
    mcx, mcy = fx + fw / 2, fy + fh / 2
    leaf = [(mcx, mcy - 14), (mcx - 4, mcy - 9), (mcx - 12, mcy - 9), (mcx - 8, mcy - 4),
            (mcx - 15, mcy - 2), (mcx - 6, mcy - 2), (mcx - 6, mcy + 8), (mcx, mcy + 3),
            (mcx + 6, mcy + 8), (mcx + 6, mcy - 2), (mcx + 15, mcy - 2), (mcx + 8, mcy - 4),
            (mcx + 12, mcy - 9), (mcx + 4, mcy - 9)]
    d.polygon(leaf, fill=(200, 16, 46))
    return base

def draw_title_text(base, num_color_tuple, period_str):
    d = ImageDraw.Draw(base)
    SLOT_X = [497, 561, 625, 689, 753, 817, 881, 945]
    SLOT_Y = 132
    f_big = ImageFont.truetype(FONT, 120)
    d.text((350, SLOT_Y - 70), "第", font=f_big, fill=(0, 0, 0))
    d.text((1000, SLOT_Y - 70), "期", font=f_big, fill=(0, 0, 0))
    f_num = ImageFont.truetype(FONT, 112)
    glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dg = ImageDraw.Draw(glow_layer)
    for idx, ch in enumerate(period_str):
        sx = SLOT_X[idx]
        dg.text((sx - 70, SLOT_Y - 72), ch, font=f_num, fill=(*num_color_tuple, 130))
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(7))
    base = Image.alpha_composite(base.convert("RGBA"), glow_layer).convert("RGB")
    for idx, ch in enumerate(period_str):
        sx = SLOT_X[idx]
        tmp = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        dt = ImageDraw.Draw(tmp)
        bbox = dt.textbbox((0, 0), ch, font=f_num, stroke_width=5)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        dt.text((80 - bbox[0], 80 - bbox[1]), ch, font=f_num, fill=(*num_color_tuple, 255),
                stroke_width=5, stroke_fill=(*num_color_tuple, 220))
        char_im = tmp.copy()
        paste_x = sx - 80 + (64 - tw // 2)
        base.paste(char_im, (paste_x, SLOT_Y - 80), char_im)
    return base

def draw_star_overlay(base, seed=77):
    star_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(star_overlay)
    rnd = random.Random(seed)
    for _ in range(60):
        x = rnd.uniform(0, W)
        y = rnd.uniform(0, H * 0.75)
        r = rnd.uniform(0.7, 2.2)
        ds.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 170))
    star_overlay = star_overlay.filter(ImageFilter.GaussianBlur(1))
    return Image.alpha_composite(base.convert("RGBA"), star_overlay).convert("RGB")

def draw_aurora(base):
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    rnd = random.Random(13)
    for _ in range(5):
        x_start = rnd.randint(0, W)
        pts = []
        y_step = 0
        for _p in range(120):
            x_start += rnd.uniform(-12, 12)
            y_step += 3
            pts.append((x_start, y_step))
        c = rnd.choice([(120, 255, 220, 70), (160, 220, 255, 60), (200, 180, 255, 55)])
        d.line(pts, fill=c, width=rnd.randint(12, 22))
    overlay = overlay.filter(ImageFilter.GaussianBlur(22))
    return Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")

def draw_snowflakes(base):
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    rnd = random.Random(31)
    for _ in range(220):
        x = rnd.uniform(0, W)
        y = rnd.uniform(0, H * 0.82)
        r = rnd.uniform(1.2, 4.5)
        alpha = rnd.randint(70, 180)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, alpha))
    for _ in range(110):
        x = rnd.uniform(0, W)
        y = rnd.uniform(H * 0.72, H)
        sz = rnd.uniform(2, 7)
        d.polygon([(x, y - sz), (x + sz * 0.8, y), (x, y + sz), (x - sz * 0.8, y)], fill=(220, 245, 255, 140))
    overlay = overlay.filter(ImageFilter.GaussianBlur(1.2))
    return Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")

def draw_double_ring_ball_winter(base, cx, cy, r, outer_color, ring_color, num_text, num_color, snow_cover=False):
    overlay_glass = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dg = ImageDraw.Draw(overlay_glass)
    yy, xx = np.mgrid[0:H, 0:W]
    dd = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    mask_outer = dd <= r
    t = np.clip(dd / r, 0, 1)
    shade = np.clip(1 - t, 0, 1)
    arr_gl = np.zeros((H, W, 4), dtype=np.float32)
    for c in range(3):
        arr_gl[:, :, c] = outer_color[c] * (0.32 + 0.68 * shade)
    arr_gl[:, :, 3] = mask_outer * 170
    overlay_glass = Image.fromarray(arr_gl.astype(np.uint8), "RGBA")
    dg = ImageDraw.Draw(overlay_glass)
    dg.ellipse([cx - r, cy - r, cx + r, cy + r], outline=tuple(int(v * 0.42) for v in outer_color) + (220,), width=4)
    dg.ellipse([cx - r * 0.50, cy - r * 0.60, cx - r * 0.03, cy - r * 0.18], fill=(255, 255, 255, 150))
    dg.arc([cx - r * 0.84, cy - r * 0.84, cx + r * 0.84, cy + r * 0.84], -55, 22, fill=(255, 255, 255, 110), width=8)
    dg.ellipse([cx - r * 0.34, cy + r * 0.24, cx + r * 0.34, cy + r * 0.70], fill=(255, 255, 255, 35))
    if snow_cover:
        dg.arc([cx - r, cy - r * 0.90, cx + r, cy - r * 0.08], 180, 360, fill=(255, 255, 255, 190), width=12)
    base = Image.alpha_composite(base.convert("RGBA"), overlay_glass).convert("RGB")
    dr = ImageDraw.Draw(base)
    inner_r1 = r * 0.72
    inner_r2 = r * 0.54
    dr.ellipse([cx - inner_r1, cy - inner_r1, cx + inner_r1, cy + inner_r1], fill=(255, 255, 255))
    dr.ellipse([cx - inner_r1, cy - inner_r1, cx + inner_r1, cy + inner_r1], outline=ring_color, width=6)
    dr.ellipse([cx - inner_r2, cy - inner_r2, cx + inner_r2, cy + inner_r2], fill=(255, 255, 255))
    font = ImageFont.truetype(FONT, int(r * 0.95))
    bbox = dr.textbbox((0, 0), num_text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = cx - tw / 2 - bbox[0]
    ty = cy - th / 2 - bbox[1]
    dr.text((tx, ty), num_text, font=font, fill=num_color, stroke_width=2, stroke_fill=num_color)
    return base

def draw_silver_symbol(base, cx, cy, kind):
    d = ImageDraw.Draw(base)
    silver_light = (238, 242, 248)
    silver_mid = (185, 192, 200)
    silver_dark = (140, 148, 156)
    bar = 34
    thickness = 12
    if kind == "+":
        d.rounded_rectangle([cx - bar, cy - thickness // 2, cx + bar, cy + thickness // 2], radius=6, fill=silver_mid)
        d.rounded_rectangle([cx - thickness // 2, cy - bar, cx + thickness // 2, cy + bar], radius=6, fill=silver_mid)
        d.rounded_rectangle([cx - bar, cy - thickness // 2, cx + bar, cy - thickness // 2 + 4], radius=2, fill=silver_light)
    else:
        d.rounded_rectangle([cx - bar, cy - thickness // 2, cx + bar, cy + thickness // 2], radius=6, fill=silver_mid)
        d.rounded_rectangle([cx - bar, cy + 4, cx + bar, cy + thickness // 2 + 8], radius=6, fill=silver_dark)
        d.rounded_rectangle([cx - bar, cy - thickness // 2, cx + bar, cy - thickness // 2 + 4], radius=2, fill=silver_light)
    return base

def generate_winter_poster(period_str, ball_num_list, out_path=None):
    if out_path is None:
        out_path = os.path.join(OUT, "winter_1808x608.jpg")
    base = vgrad(W, H, [(0.0, (30, 55, 90)), (0.32, (90, 145, 200)), (0.60, (160, 205, 240)), (1.0, (210, 235, 250))])
    base = draw_aurora(base)
    snow_ground = vgrad(W, int(H * 0.38), [(0.0, (200, 228, 245)), (1.0, (245, 250, 254))])
    base.paste(snow_ground, (0, int(H * 0.62)))
    ground_glow = radial_glow(W, H, W // 2, H - 80, 600, (220, 240, 255), 0.32)
    arr = np.array(base).astype(np.float32) + ground_glow
    base = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    base = draw_snowflakes(base)
    base = draw_flag(base)
    base = draw_title_text(base, (220, 0, 0), period_str)
    ball_fixed_cfg = [
        (243, 369, 90, (60, 150, 220), (20, 170, 230), (0, 0, 0), False),
        (623, 369, 90, (135, 75, 185), (110, 40, 170), (0, 0, 0), False),
        (1004, 371, 90, (45, 175, 160), (10, 190, 170), (0, 0, 0), False),
        (1537, 367, 90, (210, 40, 50), (190, 10, 30), (0, 0, 0), True),
    ]
    for i, cfg in enumerate(ball_fixed_cfg):
        bx, by, br, oc, rc, nc, sf = cfg
        num_txt = ball_num_list[i]
        base = draw_double_ring_ball_winter(base, bx, by, br, oc, rc, num_txt, nc, snow_cover=sf)
    base = draw_silver_symbol(base, 433, 370, "+")
    base = draw_silver_symbol(base, 813, 370, "+")
    base = draw_silver_symbol(base, 1300, 370, "=")
    base = draw_star_overlay(base)
    base.save(out_path, "JPEG", quality=82, optimize=True)
    print(f"✅冰雪海报输出:{out_path}")

def draw_sun_rays(base):
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    cx, cy = W - 160, 140
    radius = 100
    for i in range(8):
        angle = math.radians(i * 45)
        x2 = cx + math.cos(angle) * radius * 3.5
        y2 = cy + math.sin(angle) * radius * 3.5
        d.line([(cx, cy), (x2, y2)], fill=(255, 210, 110, 70), width=18)
    d.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=(255, 230, 150, 180))
    d.ellipse([cx - radius * 0.65, cy - radius * 0.65, cx + radius * 0.65, cy + radius * 0.65], fill=(255, 255, 210, 220))
    overlay = overlay.filter(ImageFilter.GaussianBlur(20))
    return Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")

def draw_bokeh(base):
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    rnd = random.Random(24)
    for _ in range(80):
        x = rnd.uniform(0, W)
        y = rnd.uniform(0, H * 0.65)
        r = rnd.uniform(2, 6)
        alpha = rnd.randint(90, 160)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 215, 120, alpha))
    overlay = overlay.filter(ImageFilter.GaussianBlur(2))
    return Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")

def draw_palm_tree(d, px, py):
    d.rounded_rectangle([px - 16, py, px + 16, H], radius=8, fill=(75, 50, 28))
    leaf_angles = [-55, -30, -8, 12, 35, 55]
    for ang in leaf_angles:
        rad = math.radians(ang)
        x2 = px + math.sin(rad) * 150
        y2 = py - math.cos(rad) * 120
        d.line([(px, py - 35), (x2, y2)], fill=(25, 85, 45), width=13)

def draw_double_ring_sunball(base, cx, cy, r, outer_color, ring_color, num_text, num_color, sun_deco=False):
    overlay_glass = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dg = ImageDraw.Draw(overlay_glass)
    yy, xx = np.mgrid[0:H, 0:W]
    dd = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    mask_outer = dd <= r
    t = np.clip(dd / r, 0, 1)
    shade = np.clip(1 - t, 0, 1)
    arr_gl = np.zeros((H, W, 4), dtype=np.float32)
    for c in range(3):
        arr_gl[:, :, c] = outer_color[c] * (0.32 + 0.68 * shade)
    arr_gl[:, :, 3] = mask_outer * 175
    overlay_glass = Image.fromarray(arr_gl.astype(np.uint8), "RGBA")
    dg = ImageDraw.Draw(overlay_glass)
    dg.ellipse([cx - r, cy - r, cx + r, cy + r], outline=tuple(int(v * 0.42) for v in outer_color) + (220,), width=4)
    dg.ellipse([cx - r * 0.50, cy - r * 0.60, cx - r * 0.03, cy - r * 0.18], fill=(255, 255, 255, 160))
    dg.arc([cx - r * 0.84, cy - r * 0.84, cx + r * 0.84, cy + r * 0.84], -55, 22, fill=(255, 255, 255, 120), width=8)
    dg.ellipse([cx - r * 0.34, cy + r * 0.24, cx + r * 0.34, cy + r * 0.70], fill=(255, 255, 255, 40))
    if sun_deco:
        for i in range(12):
            angle = math.radians(i * 30)
            x1 = cx + math.cos(angle) * r * 0.62
            y1 = cy + math.sin(angle) * r * 0.62
            x2 = cx + math.cos(angle) * r * 0.88
            y2 = cy + math.sin(angle) * r * 0.88
            dg.line([(x1, y1), (x2, y2)], fill=(255, 210, 0, 180), width=6)
    base = Image.alpha_composite(base.convert("RGBA"), overlay_glass).convert("RGB")
    dr = ImageDraw.Draw(base)
    inner_r1 = r * 0.72
    inner_r2 = r * 0.54
    dr.ellipse([cx - inner_r1, cy - inner_r1, cx + inner_r1, cy + inner_r1], fill=(255, 255, 255))
    dr.ellipse([cx - inner_r1, cy - inner_r1, cx + inner_r1, cy + inner_r1], outline=ring_color, width=6)
    dr.ellipse([cx - inner_r2, cy - inner_r2, cx + inner_r2, cy + inner_r2], fill=(255, 255, 255))
    font = ImageFont.truetype(FONT, int(r * 0.95))
    bbox = dr.textbbox((0, 0), num_text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = cx - tw / 2 - bbox[0]
    ty = cy - th / 2 - bbox[1]
    dr.text((tx, ty), num_text, font=font, fill=num_color, stroke_width=2, stroke_fill=num_color)
    return base

def draw_gold_symbol(base, cx, cy, kind):
    d = ImageDraw.Draw(base)
    gold_light = (255, 222, 80)
    gold_mid = (220, 175, 0)
    gold_dark = (165, 125, 0)
    bar = 34
    thickness = 12
    if kind == "+":
        d.rounded_rectangle([cx - bar, cy - thickness // 2, cx + bar, cy + thickness // 2], radius=6, fill=gold_mid)
        d.rounded_rectangle([cx - thickness // 2, cy - bar, cx + thickness // 2, cy + bar], radius=6, fill=gold_mid)
        d.rounded_rectangle([cx - bar, cy - thickness // 2, cx + bar, cy - thickness // 2 + 4], radius=2, fill=gold_light)
    else:
        d.rounded_rectangle([cx - bar, cy - thickness // 2, cx + bar, cy + thickness // 2], radius=6, fill=gold_mid)
        d.rounded_rectangle([cx - bar, cy + 4, cx + bar, cy + thickness // 2 + 8], radius=6, fill=gold_dark)
        d.rounded_rectangle([cx - bar, cy - thickness // 2, cx + bar, cy - thickness // 2 + 4], radius=2, fill=gold_light)
    return base

def generate_summer_poster(period_str, ball_num_list, out_path=None):
    if out_path is None:
        out_path = os.path.join(OUT, "summer_1808x608.jpg")
    sky = vgrad(W, H // 2, [(0.0, (40, 95, 150)), (0.45, (100, 170, 220)), (1.0, (240, 210, 160))])
    sea = vgrad(W, H // 4, [(0.0, (22, 105, 145)), (1.0, (18, 82, 122))])
    sand = vgrad(W, H // 4, [(0.0, (212, 172, 122)), (1.0, (238, 198, 148))])
    base = Image.new("RGB", (W, H))
    base.paste(sky, (0, 0))
    base.paste(sea, (0, H // 2))
    base.paste(sand, (0, H * 3 // 4))
    sea_glow = radial_glow(W, H, W // 2, H // 2 + 60, 520, (255, 255, 255), 0.36)
    arr = np.array(base).astype(np.float32) + sea_glow
    base = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    d = ImageDraw.Draw(base)
    for i in range(7):
        y = H // 2 + 18 + i * 17
        d.arc([0, y - 10, W, y + 10], -180, 0, fill=(255, 255, 255, 45), width=3)
    draw_palm_tree(d, 70, H * 0.47)
    draw_palm_tree(d, W - 100, H * 0.47)
    base = draw_sun_rays(base)
    base = draw_bokeh(base)
    sand_glow = radial_glow(W, H, W // 2, H - 60, 480, (255, 212, 112), 0.31)
    arr = np.array(base).astype(np.float32) + sand_glow
    base = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    base = draw_flag(base)
    base = draw_title_text(base, (255, 170, 0), period_str)
    ball_fixed_cfg = [
        (243, 369, 90, (30, 140, 245), (20, 160, 235), (0, 0, 0), False),
        (623, 369, 90, (130, 40, 220), (105, 30, 170), (0, 0, 0), False),
        (1004, 371, 90, (0, 190, 180), (0, 200, 175), (255, 210, 0), False),
        (1537, 367, 90, (215, 30, 55), (195, 15, 35), (255, 210, 0), True),
    ]
    for i, cfg in enumerate(ball_fixed_cfg):
        bx, by, br, oc, rc, nc, sun_deco = cfg
        num_txt = ball_num_list[i]
        base = draw_double_ring_sunball(base, bx, by, br, oc, rc, num_txt, nc, sun_deco=sun_deco)
    base = draw_gold_symbol(base, 433, 370, "+")
    base = draw_gold_symbol(base, 813, 370, "+")
    base = draw_gold_symbol(base, 1300, 370, "=")
    base = draw_star_overlay(base)
    base.save(out_path, "JPEG", quality=80, optimize=True)
    print(f"✅夏日海报输出:{out_path}")

def render_all(title_str, b1, b2, b3, b4):
    """
    对外调用入口
    :param title_str: str,8位期号字符串，例:"34715558"
    :param b1: str 球1 0‑9
    :param b2: str 球2 0‑9
    :param b3: str 球3 0‑9
    :param b4: str 球4 0‑27，必须等于b1+b2+b3
    """
    os.makedirs(OUT, exist_ok=True)
    validate_input(title_str, b1, b2, b3, b4)
    ball_list = [b1, b2, b3, b4]
    generate_winter_poster(title_str, ball_list)
    generate_summer_poster(title_str, ball_list)
    print("\n🎉两张海报全部生成完毕!")

def is_summer() -> bool:
    """按月份判断季节：5-9月为夏日版，其余月份为冰雪版"""
    m = int(time.strftime("%m"))
    return 5 <= m <= 9

def render_season(title_str, b1, b2, b3, b4, out_path):
    """
    推送链路统一入口：按当前季节渲染单张海报到指定输出路径
    """
    os.makedirs(OUT, exist_ok=True)
    validate_input(title_str, b1, b2, b3, b4)
    ball_list = [b1, b2, b3, b4]
    if is_summer():
        generate_summer_poster(title_str, ball_list, out_path)
    else:
        generate_winter_poster(title_str, ball_list, out_path)

if __name__ == "__main__":
    # =========【在这里填你的实际业务数据，运行就生成图片】=========
    # 示例：9+7+0 =16，满足 球1+球2+球3=球4
    render_all(
        title_str="34715558",
        b1="9",
        b2="7",
        b3="0",
        b4="16"
    )
    # ==========================================================
    """
    # 测试错误样例（会直接报错，不会出图）
    # render_all("35123456","2","5","8","20") #2+5+8=15≠20，校验失败
    """
