#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PC28 推送脚本 v3（原图版）
基于用户原图模板，期号/球数字全部来自原图字符，按数据动态渲染
"""
import datetime, json, os, re, sys, time, urllib.request
try:
    import requests
except ImportError:
    requests = None
from PIL import Image, ImageDraw, ImageFont, ImageFilter
try:
    import numpy as np
except ImportError:
    np = None

# ================= 配置 =================
TG_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
CHANNEL_ID = os.environ.get("TG_CHANNEL_ID", "@pc28jndkj")
GROUP_ID = os.environ.get("TG_GROUP_ID", "")
YU28_API_KEY = os.environ.get("YU28_API_KEY", "")
DATA_FILE = "data_pc28.json"
LAST_SENT_FILE = "last_sent.txt"
IMG_FILE = "result.png"

# 资源目录（模板 + 字符）
ASSETS = os.environ.get("ASSETS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets"))
TPL_SUMMER = os.path.join(ASSETS, "tpl_夏_v26.jpg")
TPL_WINTER = os.path.join(ASSETS, "tpl_冬_v26.jpg")
CHAR_DIR = os.path.join(ASSETS, "chars")

# 球心（模板坐标 1808x608）
BALL_CENTERS = [(243, 369), (623, 369), (1004, 371), (1537, 367)]
# 期号槽位中心（7位数字）
SLOT_X = [502, 576, 650, 708, 775, 845, 922]
SLOT_Y = 133
# 数字 -> 期号字符文件名
DIGIT_SLOT = {"3": "3", "4": "4", "7": "7", "1": "1", "5": "5a", "8": "8"}
# 目标颜色 (暗部, 亮部)
COLOR = {
    "红": ((180, 15, 15), (255, 120, 120)),
    "橙金": ((190, 110, 0), (255, 218, 90)),
    "黑": ((12, 12, 12), (80, 80, 80)),
    "金": ((185, 105, 0), (255, 218, 90)),
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}


# ================= 数据源 =================
def fetch_latest():
    t = int(time.time())
    sources = [("pc28.help", f"https://pc28.help/api/kj.json?t={t}", {})]
    if YU28_API_KEY:
        sources.append(("yu28.top", f"https://yu28.top/api/kj.json?t={t}", {"X-Api-Key": YU28_API_KEY}))
    errors = []
    for name, url, extra_headers in sources:
        try:
            headers = dict(HEADERS)
            headers.update(extra_headers)
            req = urllib.request.Request(url, headers=headers)
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
    raise RuntimeError("所有数据源都失败: " + " | ".join(errors))


# ================= 校验 =================
def validate(item):
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
    if date and time_str:
        try:
            dt = datetime.datetime.strptime(f"{date} {time_str}", "%Y-%m-%d %H:%M:%S")
            dt = dt.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
            now_bj = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
            diff = abs((now_bj - dt).total_seconds())
            if diff > 20 * 60:
                raise ValueError(f"开奖时间异常陈旧: {date} {time_str} (相差 {diff/60:.0f} 分钟)")
        except ValueError as e:
            if "开奖时间异常陈旧" in str(e):
                raise
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
    payload = {"countdown": "", "data": [item], "message": "success"}
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


# ================= 图片渲染（v3 原图版） =================
def is_summer():
    try:
        from zoneinfo import ZoneInfo
        now_ny = datetime.datetime.now(ZoneInfo("America/New_York"))
        return now_ny.utcoffset().total_seconds() == -4 * 3600
    except Exception:
        m = datetime.datetime.now().month
        return 4 <= m <= 10

def _recolor(rgba, dark, light):
    rgba = rgba.astype(np.float32)
    gray = rgba[:, :, :3].mean(axis=2)
    alpha = rgba[:, :, 3]
    vals = gray[alpha > 0]
    if len(vals) > 0:
        lo, hi = np.percentile(vals, 5), np.percentile(vals, 95)
        if hi - lo < 1:
            hi = lo + 1
        t = np.clip((gray - lo) / (hi - lo), 0, 1)
    else:
        t = np.full_like(gray, 0.5)
    new = np.zeros_like(rgba)
    for c in range(3):
        new[:, :, c] = (dark[c] * (1 - t) + light[c] * t)
    new[:, :, 3] = alpha
    return new.astype(np.uint8)

def _ensure_fallback(ch):
    """原图没有的数字字符（0,2,6,9）用粗体字体生成"""
    fnt = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 104)
    for s in ["冬", "夏"]:
        p = os.path.join(CHAR_DIR, f"{s}_期_{ch}.png")
        if os.path.exists(p):
            continue
        tmp = Image.new("RGBA", (120, 150), (0, 0, 0, 0))
        dr = ImageDraw.Draw(tmp)
        bb = dr.textbbox((0, 0), ch, font=fnt)
        w, h = bb[2] - bb[0], bb[3] - bb[1]
        dr.text((60 - w / 2 - bb[0], 75 - h / 2 - bb[1]), ch, font=fnt, fill=(128, 128, 128, 255))
        tmp.save(p)

def gen_image(period, date, time_str, balls, s, combo, shape):
    b1, b2, b3 = balls
    summer = is_summer()
    season = "夏" if summer else "冬"
    tpl = TPL_SUMMER if summer else TPL_WINTER
    canvas = Image.open(tpl).convert("RGB").copy()
    color_key = "橙金" if summer else "红"

    # 期号数字
    for i, ch in enumerate(period):
        _ensure_fallback(ch)
        slot = DIGIT_SLOT.get(ch, ch)
        path = os.path.join(CHAR_DIR, f"{season}_期_{slot}.png")
        if not os.path.exists(path):
            continue
        rgba = _recolor(np.array(Image.open(path).convert("RGBA")), *COLOR[color_key])
        h, w = rgba.shape[:2]
        x0, y0 = int(SLOT_X[i] - w / 2), int(SLOT_Y - h / 2)
        canvas.paste(Image.fromarray(rgba), (x0, y0), Image.fromarray(rgba))

    # 球内数字: 0,7,9,16
    ball_nums = [str(b1), str(b2), str(b3), str(s)]
    for i, (cx, cy) in enumerate(BALL_CENTERS):
        d = ball_nums[i]
        src = os.path.join(CHAR_DIR, f"冬_球_{d}.png")
        if not os.path.exists(src):
            src = os.path.join(CHAR_DIR, f"夏_球_{d}.png")
        ck = "黑" if not summer or i in (0, 1) else "金"
        if not os.path.exists(src):
            continue
        rgba = _recolor(np.array(Image.open(src).convert("RGBA")), *COLOR[ck])
        h, w = rgba.shape[:2]
        x0, y0 = int(cx - w / 2), int(cy - h / 2)
        canvas.paste(Image.fromarray(rgba), (x0, y0), Image.fromarray(rgba))

    canvas.save(IMG_FILE, quality=95)
    print(f"[图] {IMG_FILE} 生成成功（{'夏时令' if summer else '冬时令'}模板，期号{period}）")


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
    caption = f"🎯 <b>第{period}期</b> {b1}+{b2}+{b3}={s} {combo}"
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
    print(f"[TG] 群组文字推送 {'成功' if ok else '失败'}: {status}")
    return ok


# ================= Git 提交 =================
def git_commit_push():
    try:
        import subprocess
        subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=False, capture_output=True)
        subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], check=False, capture_output=True)
        subprocess.run(["git", "add", DATA_FILE, LAST_SENT_FILE], check=False, capture_output=True)
        r = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
        if r.returncode == 0:
            print("[git] 无数据变更，跳过提交")
            return
        now = datetime.datetime.now(datetime.timezone.utc)
        subprocess.run(["git", "commit", "-m", f"Update data {now:%Y-%m-%dT%H:%M:%SZ}"], check=False, capture_output=True)
        p = subprocess.run(["git", "push", "origin", "main"], check=False, capture_output=True, timeout=60)
        if p.returncode == 0:
            print("[git] 数据已实时提交并推送")
        else:
            err = (p.stderr or b"").decode("utf-8", errors="replace")[:300]
            print(f"[git] push 失败（不影响推送）: {err}")
    except Exception as e:
        print(f"[git] 提交异常: {e}")


# ================= 单次抓取推送 =================
def run_once(force=False):
    item, src = fetch_latest()
    period, date, time_str, balls, s, combo, shape = validate(item)
    print(f"[数] 最新期号: {period} 结果: {'+'.join(map(str, balls))}={s} {combo} 形态:{shape}")
    last = read_last_sent()
    if last and period <= last and not force:
        print("已推送过该期，跳过推送（仅更新数据文件）")
        save_data(item)
        return False
    gen_image(period, date, time_str, balls, s, combo, shape)
    ok_channel = send_photo(period, balls, s, combo)
    ok_group = send_message(period, date, time_str, balls, s, combo, shape)
    if ok_channel or ok_group:
        write_last_sent(period)
        save_data(item)
        git_commit_push()
        print("✅ 推送完成")
        return True
    raise SystemExit("❌ 推送失败（频道与群组均未成功）")

def main():
    if not TG_TOKEN:
        raise SystemExit("缺少 TG_BOT_TOKEN（secrets 未配置）")
    minutes = None
    args = sys.argv[1:]
    if "--minutes" in args:
        idx = args.index("--minutes")
        if idx + 1 < len(args):
            minutes = max(1, int(args[idx + 1]))
    if not minutes:
        run_once()
        return 0
    start = time.time()
    deadline = start + minutes * 60
    attempts = pushed = 0
    while True:
        if time.time() >= deadline:
            break
        attempts += 1
        try:
            if run_once():
                pushed += 1
        except Exception as e:
            import traceback; traceback.print_exc()
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        time.sleep(min(30, remaining))
    print(f"[循环] 结束：共尝试 {attempts} 次，成功推送 {pushed} 期")
    return 0

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