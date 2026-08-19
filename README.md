# AssetVault - 个人数字资产管理器 (Python + PyQt6 版)

离线运行的 Windows 桌面应用，用于管理序列号、软件许可证和密码。

## 功能特性

- 🔐 **AES-256-GCM 加密** - 所有敏感数据本地加密存储
- 🔑 **序列号管理** - 管理软件许可证、激活码，支持使用次数追踪
- 🛡️ **密码管理** - 安全存储账号密码，内置密码强度检测
- 👁️ **明文/掩码切换** - 账号与序列号默认明文显示，可一键切换为掩码
- 🗑️ **回收站** - 软删除机制，支持恢复和彻底删除
- 📊 **状态统计** - 实时统计资产状态（正常/紧张/已用完/将到期/弱密码）
- 📤 **导入导出** - 支持 JSON 备份恢复、CSV 与 Excel（.xlsx）表格导出
- 📋 **快捷复制** - 账号/序列号列右键一键复制明文到剪贴板
- ⚙️ **设置菜单** - 侧边栏回收站下方新增设置入口，支持修改主密码（全量数据自动重加密）
- 🎲 **密码生成器** - 内置强密码生成工具

> 注意：导出文件（JSON / Excel）中账号、序列号、密码均为**明文**，请妥善保管导出文件。

## 技术栈

- **前端**: PyQt6 + 纯 CSS 样式（按设计稿精确实现）
- **后端**: Python 3.10+
- **数据库**: SQLite（本地文件）
- **加密**: Argon2id + AES-256-GCM (cryptography 库)

## 快速开始

### 环境要求

- Python 3.10 或更高版本
- Windows 10/11

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行

```bash
python main.py
```

### 打包为 .exe

```bash
pip install pyinstaller
python build.py
```

打包完成后，可执行文件位于 `dist/AssetVault.exe`。

## 手动打包命令

```bash
pyinstaller --name AssetVault --windowed --onefile --noconfirm --clean main.py
```

## 数据存储

- 数据库文件：`%APPDATA%\com.assetvault.app\vault.db`
- 加密方式：Argon2id 派生密钥 + AES-256-GCM 加密
- 首次运行需设置主密码

## 项目结构

```
asset-vault/
├── main.py              # 入口
├── build.py             # 打包脚本
├── requirements.txt     # 依赖
├── models.py            # 数据模型
├── database.py          # SQLite 数据库
├── crypto.py            # AES-256-GCM 加密
├── utils.py             # 工具函数
├── ui/
│   ├── __init__.py
│   ├── style.py         # QSS 样式系统
│   ├── dialogs.py       # 弹窗组件
│   └── main_window.py   # 主窗口
└── README.md
```

## 安全说明

- 主密码仅用于本地派生加密密钥，**不会上传到任何服务器**
- 所有数据存储在本地 SQLite 数据库中
- 敏感字段（密码、序列号）使用 AES-256-GCM 加密
- 密钥通过 Argon2id（内存困难型哈希）派生，抵抗暴力破解

## 许可证

MIT
