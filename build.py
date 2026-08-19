"""PyInstaller 打包脚本 - 生成单个 .exe"""
import subprocess
import sys
import shutil
from pathlib import Path


def build():
    """使用 PyInstaller 打包为单个 .exe"""
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "AssetVault",
        "--windowed",           # GUI 模式，不显示控制台
        "--onefile",            # 打包为单个 .exe
        "--noconfirm",          # 覆盖输出目录
        "--clean",              # 清理缓存
        "--icon", "icon.ico",   # 应用图标（exe 文件图标）
        "--add-data", "icon.ico;.",  # 打包进 exe，供运行时窗口图标使用
        # 隐藏导入
        "--hidden-import", "cryptography",
        "--hidden-import", "argon2",
        "--hidden-import", "openpyxl",
        "--hidden-import", "PyQt6.sip",
        # 数据文件
        "--add-data", "ui;ui",
        "main.py",
    ]

    print("开始打包...")
    print(" ".join(cmd))
    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode == 0:
        print("\n✅ 打包成功！")
        print(f"输出目录: {Path('dist').absolute()}")
        print(f"可执行文件: {Path('dist/AssetVault.exe').absolute()}")
    else:
        print("\n❌ 打包失败")
        sys.exit(1)


if __name__ == "__main__":
    build()
