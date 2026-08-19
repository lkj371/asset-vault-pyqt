"""工具函数"""
from datetime import datetime, timedelta
import re


def format_now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def mask_serial(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'[A-Za-z0-9]', '•', text)


def check_password_strength(pw: str) -> dict:
    if not pw:
        return {"score": 0, "text": "未输入", "color": "#94a3b8", "width": "0%"}
    score = 0
    if len(pw) >= 8:
        score += 1
    if len(pw) >= 12:
        score += 1
    if re.search(r'[A-Z]', pw):
        score += 1
    if re.search(r'[0-9]', pw):
        score += 1
    if re.search(r'[^A-Za-z0-9]', pw):
        score += 1

    levels = [
        {"text": "极弱", "color": "#ef4444", "width": "10%"},
        {"text": "弱", "color": "#f97316", "width": "30%"},
        {"text": "中等", "color": "#f59e0b", "width": "50%"},
        {"text": "强", "color": "#22c55e", "width": "75%"},
        {"text": "极强", "color": "#10b981", "width": "100%"},
    ]
    return levels[min(score, 4)]


def is_weak_password(pw: str) -> bool:
    r = check_password_strength(pw)
    return r["text"] in ("弱", "极弱")


def calculate_status(asset) -> str:
    if asset.asset_type == "password":
        return "normal"
    remain = asset.remain or 0
    if remain <= 0:
        return "empty"
    # 剩余次数仅剩 1 次即视为紧张（无论是否设置有效期）
    if remain <= 1:
        return "tight"
    if asset.expire:
        try:
            expire_date = datetime.strptime(asset.expire, "%Y-%m-%d")
            today = datetime.now()
            diff = (expire_date - today).days
            if diff <= 7:
                return "tight"
            if diff <= 30:
                return "expiring"
        except ValueError:
            pass
    return "normal"


STATUS_CONFIG = {
    "normal":   {"label": "正常",   "color": "#22c55e", "bg": "#f0fdf4", "border": "#bbf7d0"},
    "tight":    {"label": "紧张",   "color": "#f59e0b", "bg": "#fffbeb", "border": "#fde68a"},
    "empty":    {"label": "已用完", "color": "#ef4444", "bg": "#fef2f2", "border": "#fecaca"},
    "expiring": {"label": "将到期", "color": "#a855f7", "bg": "#faf5ff", "border": "#e9d5ff"},
}

TYPE_CONFIG = {
    "serial":   {"label": "序列号", "icon": "🔑", "color": "#6366f1", "bg": "#eef2ff"},
    "password": {"label": "密码",   "icon": "🛡️", "color": "#f59e0b", "bg": "#fffbeb"},
}
