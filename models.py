"""数据模型定义"""
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum
import json


class AssetType(Enum):
    SERIAL = "serial"
    PASSWORD = "password"


class AssetStatus(Enum):
    NORMAL = "normal"
    TIGHT = "tight"
    EMPTY = "empty"
    EXPIRING = "expiring"


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

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Asset":
        return cls(**data)


@dataclass
class Stats:
    total: int = 0
    normal: int = 0
    tight: int = 0
    empty: int = 0
    expiring: int = 0
    serial_count: int = 0
    remain: int = 0
    serial_expiring: int = 0
    pw_count: int = 0
    weak_pw: int = 0
    pw_with_url: int = 0
