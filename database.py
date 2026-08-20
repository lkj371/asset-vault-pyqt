"""SQLite 数据库操作"""
import sqlite3
import json
import os
from pathlib import Path
from typing import List, Optional

from models import Asset, Stats
from utils import calculate_status, is_weak_password, format_now
from crypto import VaultCrypto


class Database:
    # 密码校验串：用于解锁与修改主密码时验证密码正确性
    VERIFIER_TEXT = "ASSETVAULT_OK"

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.crypto: Optional[VaultCrypto] = None
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_tables()

    def _init_tables(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vault_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    account TEXT NOT NULL,
                    password TEXT,
                    email TEXT,
                    total INTEGER,
                    used INTEGER,
                    remain INTEGER,
                    expire TEXT,
                    url TEXT,
                    status TEXT NOT NULL DEFAULT 'normal',
                    note TEXT,
                    updated TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recycle_bin (
                    id INTEGER PRIMARY KEY,
                    asset_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    account TEXT NOT NULL,
                    password TEXT,
                    email TEXT,
                    total INTEGER,
                    used INTEGER,
                    remain INTEGER,
                    expire TEXT,
                    url TEXT,
                    status TEXT NOT NULL,
                    note TEXT,
                    updated TEXT NOT NULL,
                    deleted_at TEXT NOT NULL
                )
            """)
            # 迁移：为模板引擎扩展字段补充 extra 列、高级筛选补充 tags 列（旧库自动升级）
            for table in ("assets", "recycle_bin"):
                cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
                if "extra" not in cols:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN extra TEXT")
                if "tags" not in cols:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN tags TEXT")
            conn.commit()

    def is_initialized(self) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT COUNT(*) FROM vault_meta WHERE key = 'initialized'"
            )
            return cur.fetchone()[0] > 0

    def initialize(self, password: str):
        self.crypto = VaultCrypto(password)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO vault_meta (key, value) VALUES (?, ?)",
                ("salt", self.crypto.get_salt_b64()),
            )
            conn.execute(
                "INSERT OR REPLACE INTO vault_meta (key, value) VALUES (?, ?)",
                ("initialized", "true"),
            )
            conn.execute(
                "INSERT OR REPLACE INTO vault_meta (key, value) VALUES (?, ?)",
                ("verifier", self.crypto.encrypt(self.VERIFIER_TEXT)),
            )
            conn.commit()

    def unlock(self, password: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT value FROM vault_meta WHERE key = 'salt'"
            )
            row = cur.fetchone()
            if not row:
                return False
            salt_b64 = row[0]
            cur = conn.execute(
                "SELECT value FROM vault_meta WHERE key = 'verifier'"
            )
            verifier_row = cur.fetchone()
        try:
            crypto = VaultCrypto.from_salt_b64(password, salt_b64)
        except Exception:
            return False
        # 有校验串时验证密码正确性（旧库无校验串则放行，保持兼容）
        if verifier_row:
            if crypto.decrypt(verifier_row[0]) != self.VERIFIER_TEXT:
                return False
        self.crypto = crypto
        return True

    def change_master_password(self, old_password: str, new_password: str) -> bool:
        """修改主密码：校验旧密码 -> 用新密钥重新加密全部数据 -> 更新 salt/verifier"""
        if not self.crypto:
            return False
        # 校验旧密码（确定性派生，密钥相同即密码正确）
        try:
            old_crypto = VaultCrypto.from_salt_b64(old_password, self.crypto.get_salt_b64())
        except Exception:
            return False
        if old_crypto.key != self.crypto.key:
            return False

        new_crypto = VaultCrypto(new_password)
        with sqlite3.connect(self.db_path) as conn:
            for table in ("assets", "recycle_bin"):
                cur = conn.execute(f"SELECT id, account, password, extra FROM {table}")
                rows = cur.fetchall()
                for rid, enc_acc, enc_pw, enc_extra in rows:
                    dec_acc = self._decrypt(enc_acc)
                    dec_pw = self._decrypt(enc_pw) if enc_pw else None
                    dec_extra = self._decrypt(enc_extra) if enc_extra else None
                    conn.execute(
                        f"UPDATE {table} SET account = ?, password = ?, extra = ? WHERE id = ?",
                        (
                            new_crypto.encrypt(dec_acc),
                            new_crypto.encrypt(dec_pw) if dec_pw else None,
                            new_crypto.encrypt(dec_extra) if dec_extra else None,
                            rid,
                        ),
                    )
            conn.execute(
                "INSERT OR REPLACE INTO vault_meta (key, value) VALUES (?, ?)",
                ("salt", new_crypto.get_salt_b64()),
            )
            conn.execute(
                "INSERT OR REPLACE INTO vault_meta (key, value) VALUES (?, ?)",
                ("verifier", new_crypto.encrypt(self.VERIFIER_TEXT)),
            )
            conn.commit()
        self.crypto = new_crypto
        return True

    def _encrypt(self, text: str) -> str:
        if not self.crypto:
            return text
        return self.crypto.encrypt(text)

    def _decrypt(self, text: str) -> str:
        if not self.crypto or not text:
            return text or ""
        return self.crypto.decrypt(text)

    def _encrypt_extra(self, extra) -> Optional[str]:
        """扩展字段整体加密为 JSON 密文"""
        if not extra:
            return None
        return self._encrypt(json.dumps(extra, ensure_ascii=False))

    def _decrypt_extra(self, text) -> Optional[dict]:
        """解密扩展字段；无内容或解密失败返回 None"""
        if not text:
            return None
        try:
            return json.loads(self._decrypt(text))
        except Exception:
            return None

    # SELECT 列清单（含扩展字段 extra 与标签 tags）
    _COLS = "id, asset_type, name, account, password, email, total, used, remain, expire, url, status, note, updated, extra, tags"
    _COLS_DELETED = _COLS + ", deleted_at"

    def _row_to_asset(self, row, include_deleted=False) -> Asset:
        kwargs = {
            "id": row[0],
            "asset_type": row[1],
            "name": row[2],
            "account": self._decrypt(row[3]),
            "password": self._decrypt(row[4]) if row[4] else None,
            "email": row[5],
            "total": row[6],
            "used": row[7],
            "remain": row[8],
            "expire": row[9],
            "url": row[10],
            "status": row[11],
            "note": row[12],
            "updated": row[13],
            "extra": self._decrypt_extra(row[14]) if len(row) > 14 else None,
            "tags": row[15] if len(row) > 15 else None,
        }
        if include_deleted:
            kwargs["deleted_at"] = row[16] if len(row) > 16 else None
        asset = Asset(**kwargs)
        # 生命周期状态实时重算：旧版 tight/expiring 状态自动迁移，
        # 过期判断保持最新；archived 为手动归档，calculate_status 会保留
        asset.status = calculate_status(asset)
        return asset

    def add_asset(self, asset: Asset) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("""
                INSERT INTO assets (asset_type, name, account, password, email, total, used, remain, expire, url, status, note, updated, extra, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                asset.asset_type,
                asset.name,
                self._encrypt(asset.account),
                self._encrypt(asset.password) if asset.password else None,
                asset.email,
                asset.total,
                asset.used,
                asset.remain,
                asset.expire,
                asset.url,
                asset.status,
                asset.note,
                asset.updated,
                self._encrypt_extra(asset.extra),
                asset.tags,
            ))
            conn.commit()
            return cur.lastrowid

    def update_asset(self, asset: Asset):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE assets SET
                    asset_type = ?, name = ?, account = ?, password = ?,
                    email = ?, total = ?, used = ?, remain = ?,
                    expire = ?, url = ?, status = ?, note = ?, updated = ?, extra = ?, tags = ?
                WHERE id = ?
            """, (
                asset.asset_type,
                asset.name,
                self._encrypt(asset.account),
                self._encrypt(asset.password) if asset.password else None,
                asset.email,
                asset.total,
                asset.used,
                asset.remain,
                asset.expire,
                asset.url,
                asset.status,
                asset.note,
                asset.updated,
                self._encrypt_extra(asset.extra),
                asset.tags,
                asset.id,
            ))
            conn.commit()

    def get_assets(self) -> List[Asset]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(f"""
                SELECT {self._COLS}
                FROM assets ORDER BY updated DESC
            """)
            return [self._row_to_asset(row) for row in cur.fetchall()]

    def delete_asset(self, asset_id: int):
        asset = self.get_asset_by_id(asset_id)
        if not asset:
            return
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO recycle_bin (id, asset_type, name, account, password, email, total, used, remain, expire, url, status, note, updated, extra, tags, deleted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                asset.id, asset.asset_type, asset.name,
                self._encrypt(asset.account),
                self._encrypt(asset.password) if asset.password else None,
                asset.email, asset.total, asset.used, asset.remain,
                asset.expire, asset.url, asset.status, asset.note,
                asset.updated, self._encrypt_extra(asset.extra), asset.tags, format_now(),
            ))
            conn.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
            conn.commit()

    def get_asset_by_id(self, asset_id: int) -> Optional[Asset]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(f"""
                SELECT {self._COLS}
                FROM assets WHERE id = ?
            """, (asset_id,))
            row = cur.fetchone()
            return self._row_to_asset(row) if row else None

    def get_recycle_bin(self) -> List[Asset]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(f"""
                SELECT {self._COLS_DELETED}
                FROM recycle_bin ORDER BY deleted_at DESC
            """)
            return [self._row_to_asset(row, include_deleted=True) for row in cur.fetchall()]

    def restore_asset(self, asset_id: int):
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(f"""
                SELECT {self._COLS}
                FROM recycle_bin WHERE id = ?
            """, (asset_id,))
            row = cur.fetchone()
            if not row:
                return
            conn.execute("""
                INSERT INTO assets (id, asset_type, name, account, password, email, total, used, remain, expire, url, status, note, updated, extra, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, row)
            conn.execute("DELETE FROM recycle_bin WHERE id = ?", (asset_id,))
            conn.commit()

    def permanent_delete(self, asset_id: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM recycle_bin WHERE id = ?", (asset_id,))
            conn.commit()

    def clear_recycle_bin(self):
        """清空回收站（彻底删除全部记录）"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM recycle_bin")
            conn.commit()

    def restore_all(self):
        """全部恢复：将回收站所有记录移回 assets 表"""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(f"""
                SELECT {self._COLS}
                FROM recycle_bin
            """)
            rows = cur.fetchall()
            for row in rows:
                conn.execute("""
                    INSERT OR REPLACE INTO assets (id, asset_type, name, account, password, email, total, used, remain, expire, url, status, note, updated, extra, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, row)
            conn.execute("DELETE FROM recycle_bin")
            conn.commit()

    def get_stats(self) -> Stats:
        assets = self.get_assets()
        serials = [a for a in assets if a.asset_type == "serial"]
        passwords = [a for a in assets if a.asset_type == "password"]

        stats = Stats()
        stats.total = len(assets)
        stats.normal = sum(1 for a in assets if a.status == "normal")
        stats.empty = sum(1 for a in assets if a.status == "empty")
        stats.expired = sum(1 for a in assets if a.status == "expired")
        stats.archived = sum(1 for a in assets if a.status == "archived")
        stats.serial_count = len(serials)
        stats.remain = sum(a.remain or 0 for a in serials)
        stats.pw_count = len(passwords)
        stats.weak_pw = sum(1 for a in passwords if a.password and is_weak_password(a.password))
        stats.pw_with_url = sum(1 for a in passwords if a.url)
        return stats

    # ===== 自定义资产模板（存于 vault_meta，结构不加密） =====

    def get_custom_templates(self) -> List[dict]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT value FROM vault_meta WHERE key = 'custom_templates'"
            )
            row = cur.fetchone()
        if not row:
            return []
        try:
            return json.loads(row[0])
        except Exception:
            return []

    def _save_custom_templates(self, templates: List[dict]):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO vault_meta (key, value) VALUES (?, ?)",
                ("custom_templates", json.dumps(templates, ensure_ascii=False)),
            )
            conn.commit()

    def add_custom_template(self, template: dict):
        templates = self.get_custom_templates()
        templates.append(template)
        self._save_custom_templates(templates)

    def delete_custom_template(self, key: str):
        templates = [t for t in self.get_custom_templates() if t.get("key") != key]
        self._save_custom_templates(templates)

    def export_data(self) -> str:
        assets = self.get_assets()
        recycle = self.get_recycle_bin()
        data = {
            "assets": [a.to_dict() for a in assets],
            "recycle_bin": [a.to_dict() for a in recycle],
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    def import_data(self, json_data: str):
        data = json.loads(json_data)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM assets")
            conn.execute("DELETE FROM recycle_bin")
            for a in data.get("assets", []):
                asset = Asset.from_dict(a)
                conn.execute("""
                    INSERT INTO assets (asset_type, name, account, password, email, total, used, remain, expire, url, status, note, updated, extra, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    asset.asset_type, asset.name,
                    self._encrypt(asset.account),
                    self._encrypt(asset.password) if asset.password else None,
                    asset.email, asset.total, asset.used, asset.remain,
                    asset.expire, asset.url, asset.status, asset.note, asset.updated,
                    self._encrypt_extra(asset.extra), asset.tags,
                ))
            for a in data.get("recycle_bin", []):
                asset = Asset.from_dict(a)
                conn.execute("""
                    INSERT INTO recycle_bin (id, asset_type, name, account, password, email, total, used, remain, expire, url, status, note, updated, extra, tags, deleted_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    asset.id, asset.asset_type, asset.name,
                    self._encrypt(asset.account),
                    self._encrypt(asset.password) if asset.password else None,
                    asset.email, asset.total, asset.used, asset.remain,
                    asset.expire, asset.url, asset.status, asset.note,
                    asset.updated, self._encrypt_extra(asset.extra), asset.tags,
                    asset.deleted_at or format_now(),
                ))
            conn.commit()
