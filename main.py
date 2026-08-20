"""AssetVault - 个人数字资产管理器
离线运行，AES-256-GCM 加密，SQLite 本地存储
"""
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon

from database import Database
from ui.main_window import MainWindow
from ui.dialogs import MasterPasswordDialog


def get_icon_path():
    """获取图标路径（兼容开发与 PyInstaller 打包环境）"""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    p = base / "icon.ico"
    return str(p) if p.exists() else ""


def get_data_dir():
    """获取数据存储目录：与程序同目录，便于维护与备份

    - PyInstaller 打包后：vault.db 存放在 .exe 所在目录
    - 源码运行：vault.db 存放在 main.py 所在目录
    """
    if getattr(sys, "frozen", False):
        # PyInstaller 打包环境：exe 所在目录
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def main():
    # 高分屏支持（必须在 QApplication 创建之前调用，否则不生效）
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName("AssetVault")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("AssetVault")

    # 应用图标（窗口标题栏 / 任务栏）
    icon_path = get_icon_path()
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))

    # 设置全局字体（setFamilies 按顺序回退，避免整串 CSS 写法被当作单一字体名导致匹配失败）
    font = QFont()
    font.setFamilies(["Segoe UI", "Microsoft YaHei", "PingFang SC", "Noto Sans SC", "sans-serif"])
    font.setPointSize(10)
    app.setFont(font)

    data_dir = get_data_dir()
    db_path = data_dir / "vault.db"
    db = Database(str(db_path))

    # 检查是否需要初始化
    if not db.is_initialized():
        dialog = MasterPasswordDialog(mode="init")
        if dialog.exec() != 1:
            sys.exit(0)
        db.initialize(dialog.pw_input.text().strip())
    else:
        dialog = MasterPasswordDialog(mode="unlock")
        if dialog.exec() != 1:
            sys.exit(0)
        if not db.unlock(dialog.pw_input.text().strip()):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "错误", "密码错误，无法解锁 Vault")
            sys.exit(1)

    window = MainWindow(db)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
