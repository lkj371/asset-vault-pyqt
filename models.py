"""数据模型定义"""
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum
import json


class AssetType(Enum):
    SERIAL = "serial"
    PASSWORD = "password"


class AssetStatus(Enum):
    """资产生命周期状态（单选）；用量紧张/即将到期/弱密码为可叠加告警，见 utils.calculate_alerts"""
    NORMAL = "normal"
    EMPTY = "empty"
    EXPIRED = "expired"
    ARCHIVED = "archived"


@dataclass
class Asset:
    id: int
    asset_type: str  # "serial" | "password"
    name: str
    account: str
    password: Optional[str] = None
    email: Optional[str] = None
    total: Optional[int] = None
    used: Optional[int] = None
    remain: Optional[int] = None
    expire: Optional[str] = None
    url: Optional[str] = None
    status: str = "normal"
    note: Optional[str] = None
    updated: str = ""
    deleted_at: Optional[str] = None
    extra: Optional[dict] = None  # 模板引擎扩展字段（数据库中整体加密存储）
    tags: Optional[str] = None    # 标签（逗号分隔，用于高级筛选组合查询；非敏感，明文存储）

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Asset":
        return cls(**data)


@dataclass
class Stats:
    total: int = 0
    normal: int = 0
    empty: int = 0
    expired: int = 0
    archived: int = 0
    serial_count: int = 0
    remain: int = 0
    pw_count: int = 0
    weak_pw: int = 0
    pw_with_url: int = 0
