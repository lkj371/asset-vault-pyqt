"""资产模板引擎

- 内置 8 种资产模板（序列号/密码 + 6 种扩展类型）
- 支持用户自定义模板（存储于数据库 vault_meta）
- 每种模板定义：字段列表（含字段类型）、表格列映射、独立到期提醒规则

字段类型（自定义模板可选）:
    text     单行文本
    password 密码（输入掩码 + 眼睛切换）
    textarea 多行文本
    date     日期（可留空 = 不设置）
    select   下拉选项（需提供 options）
    number   数字
    file     附件（保存文件路径）
"""

# ===== 字段类型常量 =====
FIELD_TEXT = "text"
FIELD_PASSWORD = "password"
FIELD_TEXTAREA = "textarea"
FIELD_DATE = "date"
FIELD_SELECT = "select"
FIELD_NUMBER = "number"
FIELD_FILE = "file"

FIELD_TYPE_LABELS = {
    FIELD_TEXT: "单行文本",
    FIELD_PASSWORD: "密码",
    FIELD_TEXTAREA: "多行文本",
    FIELD_DATE: "日期",
    FIELD_SELECT: "下拉选项",
    FIELD_NUMBER: "数字",
    FIELD_FILE: "附件",
}

# 旧版专用类型（使用独立数据列与专属表单）
LEGACY_TYPES = ("serial", "password")


def F(key, label, ftype=FIELD_TEXT, required=False, options=None, placeholder=""):
    """字段定义简写"""
    return {
        "key": key,
        "label": label,
        "type": ftype,
        "required": required,
        "options": options or [],
        "placeholder": placeholder,
    }


# ===== 内置模板 =====
# columns 映射说明：
#   account -> 表格「账号/序列号」列显示的字段（自动镜像到 account 列，参与搜索/排序/右键复制）
#   expire  -> 表格「有效期」列显示的日期字段（驱动状态计算与到期提醒）
# expire_days: 到期提醒阈值（到期前 N 天标记为「将到期」；0/None = 不做日期提醒）
BUILTIN_TEMPLATES = {
    "serial": {
        "key": "serial",
        "label": "序列号",
        "icon": "🔑",
        "color": "#6366f1",
        "bg": "#eef2ff",
        "builtin": True,
        "legacy": True,
        "name_placeholder": "如: JetBrains IntelliJ IDEA",
        "fields": [],
        "columns": {},
        "expire_days": 30,
    },
    "password": {
        "key": "password",
        "label": "密码",
        "icon": "🛡️",
        "color": "#f59e0b",
        "bg": "#fffbeb",
        "builtin": True,
        "legacy": True,
        "name_placeholder": "如: GitHub, 阿里云",
        "fields": [],
        "columns": {},
        "expire_days": None,  # 密码类型不做状态提醒（保持原有行为）
    },
    "apikey": {
        "key": "apikey",
        "label": "API 密钥",
        "icon": "🗝️",
        "color": "#0ea5e9",
        "bg": "#f0f9ff",
        "builtin": True,
        "legacy": False,
        "name_placeholder": "如: 阿里云 OSS、OpenAI",
        "fields": [
            F("access_key", "Access Key", required=True, placeholder="AKID..."),
            F("secret_key", "Secret Key", FIELD_PASSWORD, placeholder="输入后加密存储"),
            F("endpoint", "Endpoint", placeholder="https://api.example.com"),
            F("scope", "权限范围", placeholder="如: 只读 / 读写"),
            F("rotate_cycle", "轮换周期", FIELD_SELECT,
              options=["30 天", "60 天", "90 天", "180 天", "365 天", "不轮换"]),
            F("expire_date", "到期时间", FIELD_DATE),
        ],
        "columns": {"account": "access_key", "expire": "expire_date"},
        "expire_days": 30,
    },
    "sslcert": {
        "key": "sslcert",
        "label": "SSL 证书/域名",
        "icon": "🌐",
        "color": "#10b981",
        "bg": "#ecfdf5",
        "builtin": True,
        "legacy": False,
        "name_placeholder": "如: example.com 证书",
        "fields": [
            F("domain", "域名", required=True, placeholder="example.com"),
            F("ca", "颁发机构", placeholder="如: Let's Encrypt / DigiCert"),
            F("expire_date", "到期时间", FIELD_DATE),
            F("auto_renew", "自动续期", FIELD_SELECT, options=["开启", "关闭"]),
            F("cert_file", "证书文件", FIELD_FILE),
        ],
        "columns": {"account": "domain", "expire": "expire_date"},
        "expire_days": 30,
    },
    "subscription": {
        "key": "subscription",
        "label": "订阅服务",
        "icon": "📺",
        "color": "#ec4899",
        "bg": "#fdf2f8",
        "builtin": True,
        "legacy": False,
        "name_placeholder": "如: Netflix 家庭套餐",
        "fields": [
            F("provider", "服务商", required=True, placeholder="如: Netflix / Spotify"),
            F("plan", "套餐类型", placeholder="如: 高级版 / 家庭版"),
            F("auto_renew", "自动续费", FIELD_SELECT, options=["自动续费", "手动续费"]),
            F("payment", "绑定支付方式", placeholder="如: 支付宝 / Visa 尾号 1234"),
            F("members", "家庭共享成员", placeholder="如: 张三、李四"),
            F("renew_date", "下次续费日", FIELD_DATE),
        ],
        "columns": {"account": "provider", "expire": "renew_date"},
        "expire_days": 7,
    },
    "hardware": {
        "key": "hardware",
        "label": "硬件设备",
        "icon": "🖥️",
        "color": "#64748b",
        "bg": "#f8fafc",
        "builtin": True,
        "legacy": False,
        "name_placeholder": "如: 群晖 NAS DS920+",
        "fields": [
            F("model", "设备型号", required=True, placeholder="如: DS920+ / R4S"),
            F("mac", "MAC 地址", placeholder="AA:BB:CC:DD:EE:FF"),
            F("ip", "管理 IP", placeholder="192.168.1.10"),
            F("ssh_key", "SSH 密钥", FIELD_PASSWORD, placeholder="私钥内容或密码，加密存储"),
            F("firmware", "固件版本", placeholder="如: DSM 7.2"),
        ],
        "columns": {"account": "ip,model"},
        "expire_days": None,
    },
    "wallet": {
        "key": "wallet",
        "label": "数字钱包",
        "icon": "🪙",
        "color": "#d97706",
        "bg": "#fffbeb",
        "builtin": True,
        "legacy": False,
        "name_placeholder": "如: ETH 主钱包",
        "fields": [
            F("address", "钱包地址", required=True, placeholder="0x..."),
            F("chain", "链类型", FIELD_SELECT,
              options=["BTC", "ETH", "ERC20-USDT", "TRC20-USDT", "BSC", "SOL", "其他"]),
            F("seed", "助记词", FIELD_TEXTAREA, placeholder="12/24 个助记词，加密存储"),
            F("privkey_note", "私钥备注", FIELD_PASSWORD, placeholder="私钥或其存放说明，加密存储"),
        ],
        "columns": {"account": "address"},
        "expire_days": None,
    },
    "license": {
        "key": "license",
        "label": "软件许可证",
        "icon": "📜",
        "color": "#8b5cf6",
        "bg": "#f5f3ff",
        "builtin": True,
        "legacy": False,
        "name_placeholder": "如: JetBrains 全家桶 License",
        "fields": [
            F("license_file", "许可证文件", FIELD_FILE),
            F("server", "激活服务器", placeholder="如: https://license.example.com"),
            F("concurrent", "并发数", FIELD_NUMBER),
            F("floating", "许可模式", FIELD_SELECT, options=["浮动许可", "固定许可"]),
            F("expire_date", "到期时间", FIELD_DATE),
        ],
        "columns": {"account": "server,license_file", "expire": "expire_date"},
        "expire_days": 30,
    },
}

# 模板展示顺序
BUILTIN_ORDER = [
    "serial", "password", "apikey", "sslcert",
    "subscription", "hardware", "wallet", "license",
]

# 侧栏分组（信息架构：凭证类 / 授权类 / 基础设施）
TEMPLATE_GROUPS = [
    ("凭证类", ["password", "apikey", "wallet"]),
    ("授权类", ["serial", "license", "subscription"]),
    ("基础设施", ["sslcert", "hardware"]),
]


def get_all_templates(custom_templates=None) -> dict:
    """全部模板 = 内置 + 自定义（自定义同名 key 不覆盖内置）"""
    result = dict(BUILTIN_TEMPLATES)
    for tpl in (custom_templates or []):
        key = tpl.get("key", "")
        if key and key not in result:
            result[key] = tpl
    return result


def ordered_templates(custom_templates=None) -> list:
    """按固定顺序返回内置模板，自定义模板排在最后"""
    result = [BUILTIN_TEMPLATES[k] for k in BUILTIN_ORDER]
    result.extend(custom_templates or [])
    return result


def get_template(asset_type: str, custom_templates=None) -> dict:
    """获取模板；未知类型回退到序列号模板"""
    tpl = get_all_templates(custom_templates).get(asset_type)
    if tpl:
        return tpl
    return BUILTIN_TEMPLATES["serial"]


def resolve_column(template: dict, extra: dict, mapping_key: str) -> str:
    """解析列映射：支持 'a,b' 回退写法（第一个非空字段胜出）"""
    spec = (template.get("columns") or {}).get(mapping_key)
    if not spec:
        return ""
    extra = extra or {}
    for field_key in spec.split(","):
        val = extra.get(field_key.strip())
        if val:
            return str(val)
    return ""


def make_custom_template(name: str, fields: list, expire_days=None) -> dict:
    """创建自定义模板定义"""
    import time
    # 列映射：账号列 = 第一个字段；有效期列 = 第一个日期字段
    account_field = fields[0]["key"] if fields else ""
    expire_field = next((f["key"] for f in fields if f.get("type") == FIELD_DATE), "")
    return {
        "key": f"custom_{int(time.time() * 1000)}",
        "label": name,
        "icon": "🧩",
        "color": "#0d9488",
        "bg": "#f0fdfa",
        "builtin": False,
        "legacy": False,
        "name_placeholder": "",
        "fields": fields,
        "columns": {"account": account_field, "expire": expire_field},
        "expire_days": expire_days or None,
    }
