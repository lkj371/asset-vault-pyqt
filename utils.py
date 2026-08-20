"""工具函数"""
from datetime import datetime, timedelta
import re

from templates import BUILTIN_TEMPLATES


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


def days_until(expire: str):
    """有效期剩余天数；无值或解析失败返回 None"""
    if not expire:
        return None
    try:
        return (datetime.strptime(expire, "%Y-%m-%d") - datetime.now()).days
    except (ValueError, TypeError):
        return None


def calculate_status(asset, expire_days=None) -> str:
    """计算资产生命周期状态（单选，决定资产是否可用）

    - archived：用户手动归档，优先级最高，自动计算不得覆盖
    - empty：次数/额度耗尽（仅序列号等用量型资产）
    - expired：超出有效期（订阅、证书、域名等）
    - normal：资源充足且在有效期内

    「用量紧张 / 即将到期 / 弱密码」属于健康度告警，见 calculate_alerts，
    不再混入生命周期状态。
    """
    if asset.status == "archived":
        return "archived"
    if asset.asset_type == "serial":
        if (asset.remain or 0) <= 0:
            return "empty"
    d = days_until(asset.expire)
    if d is not None and d < 0:
        return "expired"
    return "normal"


# 用量紧张阈值：剩余次数占总量比例 ≤ 20%
TIGHT_RATIO = 0.2


def calculate_alerts(asset, expire_days=None) -> list:
    """计算资产健康度告警（多标签，可叠加，用于提醒）

    返回告警 key 列表，可能包含：
    - tight：用量紧张，剩余次数/额度低于阈值（≤20%）
    - expiring：即将到期，有效期剩余少于 N 天（按模板 expire_days，如 7/30 天）
    - weak_password：弱密码，安全维度告警

    已归档资产不产生告警（已停用，无需提醒）。
    """
    if asset.status == "archived":
        return []
    alerts = []
    # 用量紧张：剩余 > 0（=0 已是「已用完」状态）且占比 ≤ 20%
    if asset.asset_type == "serial":
        remain = asset.remain or 0
        total = asset.total or 0
        if remain > 0 and remain <= max(1, int(total * TIGHT_RATIO)):
            alerts.append("tight")
    # 即将到期：剩余 0~N 天（已过期属于生命周期状态，不再重复告警）
    d = days_until(asset.expire)
    if d is not None and d >= 0 and expire_days and d <= expire_days:
        alerts.append("expiring")
    # 弱密码：安全维度告警
    if asset.asset_type == "password" and asset.password and is_weak_password(asset.password):
        alerts.append("weak_password")
    return alerts


STATUS_CONFIG = {
    "normal":   {"label": "正常",   "color": "#22c55e", "bg": "#f0fdf4", "border": "#bbf7d0"},
    "empty":    {"label": "已用完", "color": "#ef4444", "bg": "#fef2f2", "border": "#fecaca"},
    "expired":  {"label": "已过期", "color": "#f97316", "bg": "#fff7ed", "border": "#fed7aa"},
    "archived": {"label": "已归档", "color": "#64748b", "bg": "#f8fafc", "border": "#e2e8f0"},
}

# 健康度告警展示配置（与生命周期状态彻底分离，可叠加）
ALERT_CONFIG = {
    "tight":         {"label": "用量紧张", "icon": "🟠", "color": "#f59e0b", "bg": "#fffbeb", "border": "#fde68a"},
    "expiring":      {"label": "即将到期", "icon": "🔴", "color": "#ef4444", "bg": "#fef2f2", "border": "#fecaca"},
    "weak_password": {"label": "弱密码",   "icon": "🟣", "color": "#8b5cf6", "bg": "#f5f3ff", "border": "#ddd6fe"},
}

# 类型展示配置由模板引擎内置模板自动生成（图标/颜色/标签保持一致）
TYPE_CONFIG = {
    key: {"label": tpl["label"], "icon": tpl["icon"], "color": tpl["color"], "bg": tpl["bg"]}
    for key, tpl in BUILTIN_TEMPLATES.items()
}


def get_type_config(asset_type: str, custom_templates=None) -> dict:
    """按类型取展示配置；自定义模板实时传入，未知类型回退默认样式"""
    if custom_templates:
        for tpl in custom_templates:
            if tpl.get("key") == asset_type:
                return {
                    "label": tpl.get("label", asset_type),
                    "icon": tpl.get("icon", "🧩"),
                    "color": tpl.get("color", "#0d9488"),
                    "bg": tpl.get("bg", "#f0fdfa"),
                }
    # 未知/已删除的自定义类型：显示友好兜底名而非原始 key
    fallback_label = "自定义模板" if asset_type.startswith("custom_") else asset_type
    return TYPE_CONFIG.get(asset_type, {"label": fallback_label, "icon": "🧩", "color": "#0d9488", "bg": "#f0fdfa"})
