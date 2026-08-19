#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PC28 开奖数据自动抓取 → 校验 → 去重 → 推送 Telegram
数据源: pc28.help 为主，yu28.top 可选备用
依赖: pillow requests (GitHub Actions ubuntu-latest 已预装)
"""

import datetime
import json
import os
import re
import sys
import time
import urllib.request

try:
    import requests
except ImportError:
    requests = None

from PIL import Image, ImageDraw, ImageFont

# ================= 配置 =================
TG_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
CHANNEL_ID = os.environ.get("TG_CHANNEL_ID", "@pc28jndkj")
GROUP_ID = os.environ.get("TG_GROUP_ID", "")
YU28_API_KEY = os.environ.get("YU28_API_KEY", "")

DATA_FILE = "data_pc28.json"
LAST_SENT_FILE = "last_sent.txt"
IMG_FILE = "result.png"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}


# ================= 数据源 =================
def fetch_latest():
    """多数据源轮询：按顺序尝试，返回第一个成功的结果 (item, source_name)"""
    t = int(time.time())
    sources = [("pc28.help", f"https://pc28.help/api/kj.json?t={t}")]
    if YU28_API_KEY:
        sources.append(("yu28.top", f"https://yu28.top/api/kj.json?t={t}&key={YU28_API_KEY}"))

    errors = []
    for name, url in sources:
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=12) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
            items = data.get("data") or []
            if items:
                print(f"[源] {name} 返回 {len(items)} 条，使用该源")
                return items[0], name
            errors.append(f"{name}: 无 data")
        except Exception as e:
            errors.append(f"{name}: {e}")
            print(f"[源] {name} 失败: {e}")
    raise RuntimeError("所有数据源都失败: " + " | ".join(errors))


# ================= 校验 =================
def validate(item):
    """严格校验数据，返回 (period, date, time_str, balls, s, combo, shape) 或抛错"""
    period = str(item.get("nbr", "")).strip()
    if not re.fullmatch(r"\d{5,}", period):
        raise ValueError(f"期号非法: {period!r}")

    date = str(item.get("date", "")).strip()
    time_str = str(item.get("time", "")).strip()
    number = str(item.get("number", "")).strip()
    num_val = str(item.get("num", "")).strip()
    combo = str(item.get("combination", "")).strip()

    parts = number.split("+")
    if len(parts) != 3:
        raise ValueError(f"号码格式非法: {number!r}")
    balls = []
    for p in parts:
        p = p.strip()
        if not re.fullmatch(r"\d", p):
            raise ValueError(f"球号非法: {p!r}")
        balls.append(int(p))

    s = sum(balls)
    if num_val and str(s) != num_val:
        raise ValueError(f"和值校验失败: {balls} 和={s} 但 num={num_val}")

    big_small = "小" if s <= 13 else "大"
    odd_even = "双" if s % 2 == 0 else "单"
    expect = big_small + odd_even
    if combo and combo != expect:
        print(f"[警告] 组合与和值不一致: {combo!r} vs {expect!r}，以计算为准")
    combo = expect

    # 开奖时间校验（源时间为北京时间，Actions runner 为 UTC）
    if date and time_str:
        try:
            dt = datetime.datetime.strptime(f"{date} {time_str}", "%Y-%m-%d %H:%M:%S")
            dt = dt.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
            now_bj = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)
            diff = abs((now_bj - dt).total_seconds())
            if diff > 20 * 60:
                raise ValueError(
                    f"开奖时间异常陈旧: {date} {time_str} "
                    f"(当前北京时间 {now_bj:%Y-%m-%d %H:%M:%S}, 相差 {diff/60:.0f} 分钟)"
                )
        except ValueError as e:
            if "开奖时间异常陈旧" in str(e):
                raise
            print(f"[警告] 时间解析失败，跳过时间校验: {date} {time_str}")

    b1, b2, b3 = balls
    if b1 == b2 == b3:
        shape = "豹子"
    elif b1 == b2 or b2 == b3 or b1 == b3:
        shape = "对子"
    elif (b2 - b1 == 1 and b3 - b2 == 1) or (b1 - b2 == 1 and b2 - b3 == 1):
        shape = "顺子"
    else:
        shape = "杂六"

    return period, date, time_str, balls, s, combo, shape


# ================= 去重 =================
def read_last_sent():
    try:
        with open(LAST_SENT_FILE, "r") as f:
            return f.read().strip()
    except Exception:
        return ""


def write_last_sent(period):
    with open(LAST_SENT_FILE, "w") as f:
        f.write(period + "\n")


def save_data(item):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(item, f, ensure_ascii=False, indent=2)


# ================= 图片 =================
def find_font(size):
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def gen_image(period, date, time_str, balls, s, combo, shape):
    b1, b2, b3 = balls
    width, height = 800, 420
    img = Image.new("RGB", (width, height), color=(15, 31, 47))
    draw = ImageDraw.Draw(img)
    draw.rectangle((10, 10, width - 10, height - 10), outline=(60, 80, 100), width=2)

    font_title = find_font(18)
    font_big = find_font(40)
    font_medium = find_font(28)
    font_small = find_font(16)

    draw.text((30, 30), "PC28 开奖结果", fill=(200, 200, 200), font=font_title)
    draw.text((width - 30, 30), f"第 {period} 期", fill=(255, 255, 255), font=font_title, anchor="rt")

    circle_y = 160
    radius = 52
    spacing = 140
    start_x = (width - 2 * spacing) // 2 - 10
    for i, num in enumerate([str(b1), str(b2), str(b3)]):
        x = start_x + i * spacing
        draw.ellipse((x - radius, circle_y - radius, x + radius, circle_y + radius),
                     fill=(20, 80, 140), outline=(100, 200, 255), width=2)
        draw.text((x, circle_y), num, fill=(255, 255, 255), font=font_big, anchor="mm")
        if i < 2:
            draw.text((x + spacing // 2, circle_y), "+", fill=(100, 150, 200), font=font_big, anchor="mm")

    draw.text((width // 2, circle_y + radius + 15), f"= {s}", fill=(255, 213, 79), font=font_medium, anchor="ma")
    draw.text((width // 2, circle_y + radius + 60), combo, fill=(255, 255, 255), font=font_medium, anchor="ma")
    draw.text((width // 2, circle_y + radius + 100), f"形态：{shape}", fill=(180, 180, 180), font=font_small, anchor="ma")
    draw.text((width - 30, height - 20), f"开奖时间 {date} {time_str}", fill=(120, 140, 160), font=font_small, anchor="rb")

    img.save(IMG_FILE)
    print("[图] result.png 生成成功")


# ================= Telegram =================
def tg_post(method, **kwargs):
    if requests is None:
        raise RuntimeError("缺少 requests 库")
    url = f"https://api.telegram.org/bot{TG_TOKEN}/{method}"
    r = requests.post(url, timeout=25, **kwargs)
    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text[:200]}
    return r.status_code, body


def send_photo(period, balls, s, combo):
    b1, b2, b3 = balls
    caption = f"<b>第{period}期</b> {b1}+{b2}+{b3}={s} {combo}"
    with open(IMG_FILE, "rb") as f:
        status, body = tg_post(
            "sendPhoto",
            data={"chat_id": CHANNEL_ID, "caption": caption, "parse_mode": "HTML"},
            files={"photo": (IMG_FILE, f, "image/png")},
        )
    ok = status == 200 and body.get("ok") is True
    print(f"[TG] 频道图片推送 {'成功' if ok else '失败'}: status={status} {json.dumps(body, ensure_ascii=False)[:300]}")
    return ok


def send_message(period, date, time_str, balls, s, combo, shape):
    if not GROUP_ID:
        print("[TG] 未配置群组，跳过文字推送")
        return False
    b1, b2, b3 = balls
    text = (
        f"📢 最新开奖信息\n"
        f"📅 最新期号: {period}\n"
        f"🔢 开奖结果: {b1}+{b2}+{b3}={s} {combo}\n"
        f"🎉 号码形式: {shape}\n"
        f"⏰ 开奖时间: {date} {time_str}"
    )
    status, body = tg_post(
        "sendMessage",
        data={"chat_id": GROUP_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
    )
    ok = status == 200 and body.get("ok") is True
    print(f"[TG] 群组文字推送 {'成功' if ok else '失败'}: status={status} {json.dumps(body, ensure_ascii=False)[:300]}")
    return ok


# ================= 主流程 =================
def main():
    if not TG_TOKEN:
        raise SystemExit("缺少 TG_BOT_TOKEN（secrets 未配置）")

    item, src = fetch_latest()
    period, date, time_str, balls, s, combo, shape = validate(item)
    print(f"[数] 最新期号: {period} 结果: {'+'.join(map(str, balls))}={s} {combo} 形态:{shape}")

    last = read_last_sent()
    print(f"[去重] 上次已推送: {last!r}, 本次: {period}")
    if last and period <= last:
        print("已推送过该期，跳过推送（仅更新数据文件）")
        save_data(item)
        return 0

    gen_image(period, date, time_str, balls, s, combo, shape)
    ok_channel = send_photo(period, balls, s, combo)
    ok_group = send_message(period, date, time_str, balls, s, combo, shape)

    if ok_channel or ok_group:
        write_last_sent(period)
        save_data(item)
        print("✅ 推送完成")
        return 0

    raise SystemExit("❌ 推送失败（频道与群组均未成功）")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(tb, file=sys.stderr)
        with open("error.log", "w", encoding="utf-8") as f:
            f.write(tb)
        sys.exit(1)
