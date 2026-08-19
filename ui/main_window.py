"""主窗口 - 完整实现设计稿"""
import json
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QFrame, QSizePolicy, QScrollArea, QMessageBox, QFileDialog, QCheckBox,
    QApplication, QStackedWidget, QGridLayout, QSpacerItem, QMenu
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint, QSize, QEvent
from PyQt6.QtGui import QFont, QColor, QPalette, QAction, QClipboard

from models import Asset, Stats
from database import Database
from utils import (
    format_now, mask_serial, check_password_strength, calculate_status,
    STATUS_CONFIG, TYPE_CONFIG
)
from ui.style import MAIN_STYLE
from ui.dialogs import AssetDialog, DeleteConfirmDialog, RecycleBinDialog, MasterPasswordDialog


class StatCard(QFrame):
    def __init__(self, label, value, color, top_color=None, sublabel="", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setMinimumHeight(90)
        self.setMaximumHeight(100)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        if top_color:
            self.setStyleSheet(f"""
                #statCard {{
                    background: #ffffff;
                    border: 1px solid #e2e8f0;
                    border-radius: 10px;
                    border-top: 3px solid {top_color};
                }}
            """)
        else:
            self.setStyleSheet("""
                #statCard {
                    background: #ffffff;
                    border: 1px solid #e2e8f0;
                    border-radius: 10px;
                }
            """)

        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {color if top_color else '#64748b'}; letter-spacing: 0.5px;")
        label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label_widget)

        value_widget = QLabel(str(value))
        value_widget.setStyleSheet(f"font-size: 28px; font-weight: 700; color: {color}; line-height: 1;")
        value_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value_widget)

        if sublabel:
            sub_widget = QLabel(sublabel)
            sub_widget.setStyleSheet("font-size: 11px; color: #94a3b8; margin-top: 4px;")
            sub_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(sub_widget)

        self.value_label = value_widget

    def set_value(self, value):
        self.value_label.setText(str(value))


class ModuleStatItem(QWidget):
    def __init__(self, icon, icon_bg, label, value, value_color="#0f172a", unit="", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"""
            background: {icon_bg};
            border-radius: 10px;
            min-width: 40px; max-width: 40px;
            min-height: 40px; max-height: 40px;
            font-size: 18px;
            qproperty-alignment: AlignCenter;
        """)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setContentsMargins(0, 0, 0, 0)

        label_widget = QLabel(label)
        label_widget.setStyleSheet("font-size: 12px; color: #64748b; font-weight: 500;")
        text_layout.addWidget(label_widget)

        value_layout = QHBoxLayout()
        value_layout.setSpacing(4)
        value_layout.setContentsMargins(0, 0, 0, 0)

        value_widget = QLabel(str(value))
        value_widget.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {value_color}; line-height: 1;")
        value_layout.addWidget(value_widget)

        if unit:
            unit_widget = QLabel(unit)
            unit_widget.setStyleSheet("font-size: 12px; color: #94a3b8; font-weight: 500;")
            value_layout.addWidget(unit_widget)
        value_layout.addStretch()
        text_layout.addLayout(value_layout)

        layout.addLayout(text_layout)
        self.value_label = value_widget

    def set_value(self, value):
        self.value_label.setText(str(value))


class SidebarButton(QPushButton):
    def __init__(self, icon, text, count, active=False, active_style="type", color=None, parent=None):
        super().__init__(parent)
        self.icon = icon
        self.text_text = text
        self.count = count
        self.active = active
        self.active_style = active_style
        self.color = color  # 状态按钮的文字颜色，切换选中态后保持
        self.update_style()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(36)
        self.setMaximumHeight(36)
        self.setText(f"{icon} {text}")

    def update_style(self):
        if self.active:
            if self.active_style == "type":
                text_color = self.color or "#0f172a"
                self.setStyleSheet(f"""
                    QPushButton {{
                        background: #f1f5f9; color: {text_color}; font-weight: 600;
                        border: none; border-radius: 8px;
                        padding: 8px 12px; margin: 0 12px;
                        text-align: left; font-size: 13px;
                    }}
                    QPushButton:hover {{ background: #e2e8f0; }}
                """)
            else:
                text_color = self.color or "#4338ca"
                self.setStyleSheet(f"""
                    QPushButton {{
                        background: #eef2ff; color: {text_color}; font-weight: 600;
                        border: none; border-radius: 8px;
                        padding: 8px 12px; margin: 0 12px;
                        text-align: left; font-size: 13px;
                    }}
                    QPushButton:hover {{ background: #dbeafe; }}
                """)
        else:
            text_color = self.color or "#475569"
            self.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {text_color}; font-weight: 500;
                    border: none; border-radius: 8px;
                    padding: 8px 12px; margin: 0 12px;
                    text-align: left; font-size: 13px;
                }}
                QPushButton:hover {{ background: #f8fafc; }}
            """)

    def set_active(self, active):
        self.active = active
        self.update_style()


class MainWindow(QMainWindow):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.assets = []
        self.recycle_bin = []
        self.selected_ids = set()
        self.current_type = "all"
        self.current_status = "all"
        self.search_text = ""
        self.sort_field = "updated"
        self.sort_asc = False
        self.show_plaintext = True  # 账号/序列号默认明文显示，可在工具栏切换掩码

        self.setWindowTitle("AssetVault - 个人数字资产管理器 v2.0")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        self.setStyleSheet(MAIN_STYLE)
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ===== 顶部标题栏 =====
        header = QWidget()
        header.setObjectName("headerWidget")
        header.setMinimumHeight(60)
        header.setMaximumHeight(60)
        hlayout = QHBoxLayout(header)
        hlayout.setContentsMargins(20, 0, 20, 0)
        hlayout.setSpacing(12)

        logo = QLabel("🔐")
        logo.setObjectName("headerLogo")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hlayout.addWidget(logo)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("AssetVault")
        title.setObjectName("headerTitle")
        title_layout.addWidget(title)
        subtitle = QLabel("个人数字资产管理器 v2.0")
        subtitle.setObjectName("headerSubtitle")
        title_layout.addWidget(subtitle)
        hlayout.addLayout(title_layout)
        hlayout.addStretch()

        badge1 = QLabel("● 数据文件: vault.db")
        badge1.setObjectName("headerBadge")
        badge1.setStyleSheet("background: #f1f5f9; border-radius: 6px; padding: 6px 12px; font-size: 12px; color: #64748b;")
        hlayout.addWidget(badge1)

        badge2 = QLabel("🔒 AES-256 加密")
        badge2.setObjectName("headerBadge")
        badge2.setStyleSheet("background: #f1f5f9; border-radius: 6px; padding: 6px 12px; font-size: 12px; color: #64748b;")
        hlayout.addWidget(badge2)
        main_layout.addWidget(header)

        # ===== 主体 =====
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # ===== 左侧边栏 =====
        sidebar = QWidget()
        sidebar.setObjectName("sidebarWidget")
        sidebar.setMinimumWidth(240)
        sidebar.setMaximumWidth(240)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 16, 0, 16)
        sidebar_layout.setSpacing(0)

        # 资产类型
        type_title = QLabel("资产类型")
        type_title.setObjectName("sidebarSectionTitle")
        sidebar_layout.addWidget(type_title)

        self.type_buttons = {}
        for key, icon, label in [
            ("all", "📁", "全部资产"),
            ("serial", "🔑", "序列号"),
            ("password", "🛡️", "密码"),
        ]:
            btn = SidebarButton(icon, label, 0, active=key == "all", active_style="type")
            btn.clicked.connect(lambda checked, k=key: self.on_type_filter(k))
            self.type_buttons[key] = btn
            sidebar_layout.addWidget(btn)

        sidebar_layout.addSpacing(16)

        # 状态筛选
        status_title = QLabel("状态筛选")
        status_title.setObjectName("sidebarSectionTitle")
        sidebar_layout.addWidget(status_title)

        self.status_buttons = {}
        for key, color, label in [
            ("all", None, "全部状态"),
            ("normal", "#22c55e", "正常"),
            ("tight", "#f59e0b", "紧张"),
            ("empty", "#ef4444", "已用完"),
            ("expiring", "#a855f7", "将到期"),
        ]:
            icon = "●" if color else "📁"
            btn = SidebarButton(icon, label, 0, active=key == "all", active_style="status", color=color)
            btn.clicked.connect(lambda checked, k=key: self.on_status_filter(k))
            self.status_buttons[key] = btn
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        # 设置 + 回收站（并排排列，设置在左、回收站在右）
        btn_row_style = """
            QPushButton {
                background: #ffffff; color: #475569; font-weight: 500;
                border: 1px solid #e2e8f0; border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QPushButton:hover { background: #f8fafc; }
        """

        self.settings_btn = QPushButton("⚙️ 设置")
        self.settings_btn.setStyleSheet(btn_row_style)
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.clicked.connect(self.open_settings)

        recycle_btn = QPushButton("🗑️ 回收站")
        recycle_btn.setStyleSheet(btn_row_style)
        recycle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        recycle_btn.clicked.connect(self.open_recycle_bin)

        self.recycle_count_label = QLabel("0")
        self.recycle_count_label.setStyleSheet("font-size: 11px; color: #ef4444; background: #fef2f2; border-radius: 10px; padding: 1px 7px; font-weight: 600;")

        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(16, 0, 16, 0)
        bottom_layout.setSpacing(8)
        bottom_layout.addWidget(self.settings_btn, 1)
        bottom_layout.addWidget(recycle_btn, 1)
        bottom_layout.addWidget(self.recycle_count_label)
        sidebar_layout.addLayout(bottom_layout)

        body_layout.addWidget(sidebar)

        # ===== 右侧内容区 =====
        content = QScrollArea()
        content.setWidgetResizable(True)
        content.setFrameShape(QFrame.Shape.NoFrame)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(24, 24, 28, 24)
        content_layout.setSpacing(0)

        # 页面标题
        page_header = QWidget()
        ph_layout = QHBoxLayout(page_header)
        ph_layout.setContentsMargins(0, 0, 0, 0)
        ph_layout.setSpacing(0)
        page_title_layout = QVBoxLayout()
        page_title_layout.setSpacing(4)
        self.page_title = QLabel("全部资产")
        self.page_title.setStyleSheet("font-size: 22px; font-weight: 700; color: #0f172a; letter-spacing: -0.3px;")
        page_title_layout.addWidget(self.page_title)
        self.page_subtitle = QLabel("管理您的序列号、密码与数字资产")
        self.page_subtitle.setStyleSheet("font-size: 13px; color: #64748b;")
        page_title_layout.addWidget(self.page_subtitle)
        ph_layout.addLayout(page_title_layout)
        ph_layout.addStretch()

        import_btn = QPushButton("📥 导入")
        import_btn.setObjectName("btnSecondary")
        import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        import_btn.clicked.connect(self.import_data)
        ph_layout.addWidget(import_btn)

        export_btn = QPushButton("📤 导出")
        export_btn.setObjectName("btnSecondary")
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.setMenu(self.create_export_menu())
        ph_layout.addWidget(export_btn)

        add_btn = QPushButton("+ 新增资产")
        add_btn.setObjectName("btnPrimary")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setMenu(self.create_add_menu())
        ph_layout.addWidget(add_btn)
        content_layout.addWidget(page_header)
        content_layout.addSpacing(24)

        # ===== 统计面板：第一行 =====
        stats_row1 = QWidget()
        stats_row1_layout = QHBoxLayout(stats_row1)
        stats_row1_layout.setContentsMargins(0, 0, 0, 0)
        stats_row1_layout.setSpacing(14)

        self.stat_cards = {}
        configs = [
            ("total", "📋 资产总数", "0", "#0f172a", None, ""),
            ("normal", "正常", "0", "#22c55e", "#22c55e", ""),
            ("tight", "紧张", "0", "#f59e0b", "#f59e0b", ""),
            ("empty", "已用完", "0", "#ef4444", "#ef4444", ""),
            ("expiring", "将到期", "0", "#a855f7", "#a855f7", ""),
            ("weak_pw", "弱密码", "0", "#f97316", "#f97316", ""),
        ]
        for key, label, value, color, top, sub in configs:
            card = StatCard(label, value, color, top, sub)
            self.stat_cards[key] = card
            stats_row1_layout.addWidget(card)
        content_layout.addWidget(stats_row1)
        content_layout.addSpacing(16)

        # ===== 统计面板：第二行 =====
        stats_row2 = QWidget()
        stats_row2_layout = QHBoxLayout(stats_row2)
        stats_row2_layout.setContentsMargins(0, 0, 0, 0)
        stats_row2_layout.setSpacing(14)

        # 序列号模块
        serial_module = QFrame()
        serial_module.setObjectName("moduleStatCard")
        serial_module.setStyleSheet("""
            #moduleStatCard {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                padding: 16px 20px;
            }
        """)
        sm_layout = QHBoxLayout(serial_module)
        sm_layout.setContentsMargins(16, 16, 16, 16)
        sm_layout.setSpacing(0)

        self.serial_stat_items = {}
        for icon, bg, label, key, color, unit in [
            ("🔑", "#eff6ff", "序列号资产", "serial_count", "#0f172a", "条"),
            ("🔋", "#f0fdf4", "剩余可用次数", "remain", "#22c55e", "次"),
            ("⚠️", "#fef2f2", "即将到期", "serial_expiring", "#ef4444", "条"),
        ]:
            item = ModuleStatItem(icon, bg, label, "0", color, unit)
            self.serial_stat_items[key] = item
            sm_layout.addWidget(item)
            if key != "serial_expiring":
                div = QFrame()
                div.setStyleSheet("background: #f1f5f9; min-width: 1px; max-width: 1px; min-height: 40px;")
                div.setMaximumWidth(1)
                sm_layout.addWidget(div)
        stats_row2_layout.addWidget(serial_module)

        # 密码模块
        pw_module = QFrame()
        pw_module.setObjectName("moduleStatCard")
        pw_module.setStyleSheet("""
            #moduleStatCard {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                padding: 16px 20px;
            }
        """)
        pm_layout = QHBoxLayout(pw_module)
        pm_layout.setContentsMargins(16, 16, 16, 16)
        pm_layout.setSpacing(0)

        self.pw_stat_items = {}
        for icon, bg, label, key, color, unit in [
            ("🛡️", "#fffbeb", "密码资产", "pw_count", "#0f172a", "条"),
            ("⚡", "#fff7ed", "弱密码", "weak_pw", "#f97316", "条"),
            ("🌐", "#f0f9ff", "关联服务", "pw_with_url", "#0ea5e9", "个"),
        ]:
            item = ModuleStatItem(icon, bg, label, "0", color, unit)
            self.pw_stat_items[key] = item
            pm_layout.addWidget(item)
            if key != "pw_with_url":
                div = QFrame()
                div.setStyleSheet("background: #f1f5f9; min-width: 1px; max-width: 1px; min-height: 40px;")
                div.setMaximumWidth(1)
                pm_layout.addWidget(div)
        stats_row2_layout.addWidget(pw_module)
        content_layout.addWidget(stats_row2)
        content_layout.addSpacing(24)

        # ===== 表格工具栏 =====
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(8)

        self.batch_actions_widget = QWidget()
        batch_layout = QHBoxLayout(self.batch_actions_widget)
        batch_layout.setContentsMargins(0, 0, 0, 0)
        batch_layout.setSpacing(8)

        self.selected_count_label = QLabel("已选 0 项")
        self.selected_count_label.setStyleSheet("font-size: 13px; color: #4338ca; font-weight: 600; padding: 4px 10px; background: #eef2ff; border-radius: 6px;")
        self.selected_count_label.setVisible(False)
        batch_layout.addWidget(self.selected_count_label)

        self.edit_btn = QPushButton("✏️ 编辑")
        self.edit_btn.setObjectName("btnSmall")
        self.edit_btn.setVisible(False)
        self.edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_btn.clicked.connect(self.on_edit)
        batch_layout.addWidget(self.edit_btn)

        self.use_once_btn = QPushButton("📌 使用一次")
        self.use_once_btn.setObjectName("btnWarning")
        self.use_once_btn.setVisible(False)
        self.use_once_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.use_once_btn.clicked.connect(self.on_use_once)
        batch_layout.addWidget(self.use_once_btn)

        self.delete_btn = QPushButton("🗑️ 删除")
        self.delete_btn.setObjectName("btnDanger")
        self.delete_btn.setVisible(False)
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.clicked.connect(self.on_delete)
        batch_layout.addWidget(self.delete_btn)
        toolbar_layout.addWidget(self.batch_actions_widget)
        toolbar_layout.addStretch()

        # 明文/掩码切换（默认明文）
        self.plaintext_btn = QPushButton("👁 明文显示")
        self.plaintext_btn.setObjectName("btnSecondary")
        self.plaintext_btn.setCheckable(True)
        self.plaintext_btn.setChecked(True)
        self.plaintext_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.plaintext_btn.setToolTip("切换账号/序列号的明文与掩码显示")
        self.plaintext_btn.toggled.connect(self.on_toggle_plaintext)
        toolbar_layout.addWidget(self.plaintext_btn)

        search_widget = QWidget()
        search_layout = QHBoxLayout(search_widget)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(0)
        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("font-size: 13px; color: #94a3b8; padding-left: 10px;")
        search_layout.addWidget(search_icon)
        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput")
        self.search_input.setPlaceholderText("搜索名称、账号、邮箱...")
        self.search_input.textChanged.connect(self.on_search)
        search_layout.addWidget(self.search_input)
        toolbar_layout.addWidget(search_widget)

        save_btn = QPushButton("💾 保存")
        save_btn.setObjectName("btnSecondary")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self.on_save)
        toolbar_layout.addWidget(save_btn)
        content_layout.addWidget(toolbar)
        content_layout.addSpacing(12)

        # ===== 数据表格 =====
        self.table = QTableWidget()
        self.table.setObjectName("dataTable")
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "", "名称", "类型", "账号/序列号", "绑定邮箱", "使用/数量", "有效期", "状态", "备注", "更新时间"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 40)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                gridline-color: transparent;
            }
            QTableWidget::item {
                padding: 12px 16px;
                border-bottom: 1px solid #f1f5f9;
                color: #475569;
                font-size: 13px;
            }
            QTableWidget::item:selected {
                background: #eef2ff;
                color: #1e293b;
            }
            QHeaderView::section {
                background: #f8fafc;
                color: #475569;
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 0.3px;
                padding: 12px 16px;
                border: none;
                border-bottom: 1px solid #e2e8f0;
            }
            QHeaderView::section:hover {
                background: #f1f5f9;
            }
        """)
        self.table.horizontalHeader().sectionClicked.connect(self.on_header_clicked)
        # 右键菜单：通过事件过滤器捕获鼠标右键抬起（跨平台稳定，
        # 不依赖各平台对 ContextMenu 事件的合成差异）
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self.table.viewport().installEventFilter(self)
        content_layout.addWidget(self.table)

        # 底部
        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 12, 0, 0)
        footer_layout.setSpacing(0)
        footer_left = QLabel("数据文件: vault.db | 本地 AES-256 加密存储")
        footer_left.setStyleSheet("font-size: 12px; color: #94a3b8;")
        footer_right = QLabel("AssetVault v2.0")
        footer_right.setStyleSheet("font-size: 12px; color: #94a3b8;")
        footer_layout.addWidget(footer_left)
        footer_layout.addStretch()
        footer_layout.addWidget(footer_right)
        content_layout.addWidget(footer)

        content.setWidget(content_widget)
        body_layout.addWidget(content)
        main_layout.addWidget(body)

        # Toast
        self.toast = QLabel("")
        self.toast.setStyleSheet("""
            background: #0f172a; color: white;
            border-radius: 10px; padding: 12px 20px;
            font-size: 13px; font-weight: 500;
        """)
        self.toast.setVisible(False)
        self.toast.setParent(self)
        self.toast.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.toast.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def create_add_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                padding: 4px;
            }
            QMenu::item {
                padding: 10px 14px;
                font-size: 13px;
                color: #475569;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background: #f8fafc;
            }
            QMenu::separator {
                height: 1px;
                background: #f1f5f9;
                margin: 4px 10px;
            }
        """)
        serial_action = QAction("🔑 新增序列号", self)
        serial_action.triggered.connect(lambda: self.open_add_dialog("serial"))
        menu.addAction(serial_action)
        menu.addSeparator()
        pw_action = QAction("🛡️ 新增密码", self)
        pw_action.triggered.connect(lambda: self.open_add_dialog("password"))
        menu.addAction(pw_action)
        return menu

    def show_toast(self, msg):
        self.toast.setText(msg)
        self.toast.adjustSize()
        self.toast.move(
            self.width() - self.toast.width() - 24,
            self.height() - self.toast.height() - 24
        )
        self.toast.setVisible(True)
        QTimer.singleShot(2500, lambda: self.toast.setVisible(False))

    def load_data(self):
        self.assets = self.db.get_assets()
        self.recycle_bin = self.db.get_recycle_bin()
        self.update_stats()
        self.update_table()

    def update_stats(self):
        stats = self.db.get_stats()
        for key, card in self.stat_cards.items():
            card.set_value(getattr(stats, key, 0))

        for key, item in self.serial_stat_items.items():
            item.set_value(getattr(stats, key, 0))

        for key, item in self.pw_stat_items.items():
            item.set_value(getattr(stats, key, 0))

        self.recycle_count_label.setText(str(len(self.recycle_bin)))

        # 更新侧边栏计数
        for key, btn in self.type_buttons.items():
            if key == "all":
                count = stats.total
            elif key == "serial":
                count = stats.serial_count
            else:
                count = stats.pw_count
            btn.setText(f"{btn.icon} {btn.text_text}    {count}")

        for key, btn in self.status_buttons.items():
            if key == "all":
                count = stats.total
            else:
                count = getattr(stats, key, 0)
            btn.setText(f"{btn.icon} {btn.text_text}    {count}")

    def get_filtered_assets(self):
        result = self.assets[:]
        if self.current_type != "all":
            result = [a for a in result if a.asset_type == self.current_type]
        if self.current_status != "all":
            result = [a for a in result if a.status == self.current_status]
        if self.search_text:
            search = self.search_text.lower()
            result = [a for a in result if search in (a.name + a.account + (a.email or "") + (a.note or "") + (a.url or "")).lower()]
        return result

    def update_table(self):
        filtered = self.get_filtered_assets()
        self._table_assets = filtered  # 供右键菜单按行号取记录
        self.table.setRowCount(len(filtered))

        for i, asset in enumerate(filtered):
            st = STATUS_CONFIG.get(asset.status, STATUS_CONFIG["normal"])
            tc = TYPE_CONFIG.get(asset.asset_type, TYPE_CONFIG["serial"])
            is_selected = asset.id in self.selected_ids

            # 复选框
            checkbox = QCheckBox()
            checkbox.setChecked(is_selected)
            checkbox.setStyleSheet("""
                QCheckBox::indicator {
                    width: 16px; height: 16px;
                    border-radius: 4px; border: 1px solid #e2e8f0;
                    background: #ffffff;
                }
                QCheckBox::indicator:checked {
                    background: #6366f1; border-color: #6366f1;
                }
            """)
            checkbox.stateChanged.connect(lambda state, aid=asset.id: self.on_checkbox_changed(aid, state))
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox_layout.addWidget(checkbox)
            self.table.setCellWidget(i, 0, checkbox_widget)

            # 名称（继承应用字体设置粗体，避免空族名回退导致合成加粗发虚）
            name_item = QTableWidgetItem(asset.name)
            bold_font = QFont(QApplication.font())
            bold_font.setBold(True)
            name_item.setFont(bold_font)
            self.table.setItem(i, 1, name_item)

            # 类型
            type_item = QTableWidgetItem(f"{tc['icon']} {tc['label']}")
            type_item.setForeground(QColor(tc["color"]))
            self.table.setItem(i, 2, type_item)

            # 账号/序列号（默认明文，可通过工具栏切换掩码）
            account_display = asset.account if self.show_plaintext else mask_serial(asset.account)
            account_item = QTableWidgetItem(account_display)
            account_item.setFont(QFont("Courier New", 10))
            self.table.setItem(i, 3, account_item)

            # 绑定邮箱
            self.table.setItem(i, 4, QTableWidgetItem(asset.email or "-"))

            # 使用/数量
            if asset.asset_type == "serial":
                usage_item = QTableWidgetItem(f"{asset.used or 0}/{asset.total or 0}")
                remain = asset.remain or 0
                if remain == 0:
                    usage_item.setForeground(QColor("#ef4444"))
                elif remain <= 1:
                    usage_item.setForeground(QColor("#f59e0b"))
                else:
                    usage_item.setForeground(QColor("#22c55e"))
                usage_item.setFont(bold_font)
            else:
                usage_item = QTableWidgetItem("-")
                usage_item.setForeground(QColor("#94a3b8"))
            self.table.setItem(i, 5, usage_item)

            # 有效期（两种类型均显示有效期；密码的网址可通过右键复制）
            expire_item = QTableWidgetItem(asset.expire or "永久")
            if not asset.expire:
                expire_item.setForeground(QColor("#cbd5e1"))
            self.table.setItem(i, 6, expire_item)

            # 状态
            status_item = QTableWidgetItem(st["label"])
            status_item.setForeground(QColor(st["color"]))
            self.table.setItem(i, 7, status_item)

            # 备注
            note_item = QTableWidgetItem(asset.note or "-")
            note_item.setForeground(QColor("#94a3b8"))
            note_item.setFont(QFont("", 10))
            self.table.setItem(i, 8, note_item)

            # 更新时间
            self.table.setItem(i, 9, QTableWidgetItem(asset.updated))

            # 所有字段数据居中对齐
            for col in range(1, 10):
                item = self.table.item(i, col)
                if item:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # 行背景
            if is_selected:
                for col in range(10):
                    item = self.table.item(i, col)
                    if item:
                        item.setBackground(QColor("#eef2ff"))

        self.update_batch_actions()

    def update_batch_actions(self):
        count = len(self.selected_ids)
        self.selected_count_label.setVisible(count > 0)
        self.selected_count_label.setText(f"已选 {count} 项")
        self.edit_btn.setVisible(count == 1)
        self.use_once_btn.setVisible(count == 1 and self.get_selected_asset() and self.get_selected_asset().asset_type == "serial")
        self.delete_btn.setVisible(count > 0)

    def get_selected_asset(self):
        if len(self.selected_ids) != 1:
            return None
        aid = list(self.selected_ids)[0]
        for a in self.assets:
            if a.id == aid:
                return a
        return None

    def on_checkbox_changed(self, asset_id, state):
        if state == Qt.CheckState.Checked.value:
            self.selected_ids.add(asset_id)
        else:
            self.selected_ids.discard(asset_id)
        self.update_table()

    def on_header_clicked(self, index):
        # 列索引 -> Asset 字段（第 0 列为复选框，不参与排序）
        fields = ["", "name", "asset_type", "account", "email", "total", "expire", "status", "note", "updated"]
        if 0 < index < len(fields):
            field = fields[index]
            if self.sort_field == field:
                self.sort_asc = not self.sort_asc
            else:
                self.sort_field = field
                self.sort_asc = True
            self.sort_assets()
            # 表头显示排序方向箭头
            header = self.table.horizontalHeader()
            header.setSortIndicatorShown(True)
            header.setSortIndicator(
                index,
                Qt.SortOrder.AscendingOrder if self.sort_asc else Qt.SortOrder.DescendingOrder,
            )
            self.update_table()

    def sort_assets(self):
        """按当前字段排序；空值恒排末尾，数字与文本分开比较避免类型错误"""

        def key_func(a):
            val = getattr(a, self.sort_field, None)
            if val is None or val == "":
                return (1, 0, 0.0) if self.sort_asc else (-1, 0, 0.0)  # 空值始终沉底
            if isinstance(val, (int, float)):
                return (0, 0, float(val))
            return (0, 1, str(val).lower())

        self.assets.sort(key=key_func, reverse=not self.sort_asc)

    def on_type_filter(self, key):
        self.current_type = key
        for k, btn in self.type_buttons.items():
            btn.set_active(k == key)
        self.selected_ids.clear()
        titles = {"all": "全部资产", "serial": "序列号资产", "password": "密码资产"}
        subtitles = {
            "all": "管理您的序列号、密码与数字资产",
            "serial": "管理软件许可证与激活码",
            "password": "管理账号密码与访问凭证",
        }
        self.page_title.setText(titles.get(key, "全部资产"))
        self.page_subtitle.setText(subtitles.get(key, "管理您的序列号、密码与数字资产"))
        self.update_table()

    def on_status_filter(self, key):
        self.current_status = key
        for k, btn in self.status_buttons.items():
            btn.set_active(k == key)
        self.selected_ids.clear()
        self.update_table()

    def on_search(self, text):
        self.search_text = text
        self.selected_ids.clear()
        self.update_table()

    def eventFilter(self, obj, event):
        """捕获表格视口的鼠标右键抬起，弹出复制菜单"""
        if (
            obj is self.table.viewport()
            and event.type() == QEvent.Type.MouseButtonRelease
            and event.button() == Qt.MouseButton.RightButton
        ):
            self.on_table_context_menu(event.pos())
            return True
        return super().eventFilter(obj, event)

    def on_table_context_menu(self, pos):
        """右键复制：
        - 账号/序列号列：序列号类型复制序列号，密码类型复制密码
        - 有效期列：可复制有效期；密码类型还可复制网址
        """
        row = self.table.rowAt(pos.y())
        col = self.table.columnAt(pos.x())
        if row < 0 or col not in (1, 3, 4, 6):
            return
        assets = getattr(self, "_table_assets", [])
        if row >= len(assets):
            return
        asset = assets[row]

        actions = []  # [(菜单文本, 复制内容)]
        if col == 1:
            if asset.name:
                actions.append(("📋 复制名称", asset.name))
        elif col == 3:
            if asset.asset_type == "password":
                if asset.account:
                    actions.append(("📋 复制账号", asset.account))
                if asset.password:
                    actions.append(("📋 复制密码", asset.password))
            else:
                if asset.account:
                    actions.append(("📋 复制序列号", asset.account))
        elif col == 4:
            if asset.email:
                actions.append(("📋 复制邮箱", asset.email))
        elif col == 6:
            # 有效期始终可复制：未设置时复制页面上显示的"永久"
            actions.append(("📅 复制有效期", asset.expire or "永久"))
            if asset.asset_type == "password" and asset.url:
                actions.append(("🔗 复制网址", asset.url))

        if not actions:
            self.show_toast("❌ 该记录无可复制内容")
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                padding: 4px;
            }
            QMenu::item {
                padding: 10px 14px;
                font-size: 13px;
                color: #475569;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background: #f8fafc;
            }
        """)
        for label, text in actions:
            act = QAction(label, self)
            act.triggered.connect(lambda checked=False, t=text: self.copy_to_clipboard(t))
            menu.addAction(act)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def copy_to_clipboard(self, text):
        QApplication.clipboard().setText(text)
        self.show_toast("📋 已复制到剪贴板")

    def on_toggle_plaintext(self, checked):
        """切换账号/序列号 明文 <-> 掩码（默认明文）"""
        self.show_plaintext = checked
        self.plaintext_btn.setText("👁 明文显示" if checked else "🙈 掩码显示")
        self.update_table()
        self.show_toast("👁 已切换为明文显示" if checked else "🙈 已切换为掩码显示")

    def open_add_dialog(self, asset_type):
        dialog = AssetDialog(self, mode="add", asset_type=asset_type)
        dialog.saved.connect(self.on_asset_saved)
        dialog.exec()

    def on_edit(self):
        asset = self.get_selected_asset()
        if not asset:
            return
        dialog = AssetDialog(self, mode="edit", asset_type=asset.asset_type, asset=asset)
        dialog.saved.connect(self.on_asset_updated)
        dialog.exec()

    def on_asset_saved(self, asset):
        asset.id = self.db.add_asset(asset)
        self.assets.append(asset)
        self.load_data()
        self.show_toast("✅ 新增成功")

    def on_asset_updated(self, asset):
        self.db.update_asset(asset)
        for i, a in enumerate(self.assets):
            if a.id == asset.id:
                self.assets[i] = asset
                break
        self.selected_ids.clear()
        self.load_data()
        self.show_toast("✅ 修改已保存")

    def on_delete(self):
        count = len(self.selected_ids)
        dialog = DeleteConfirmDialog(self, count)
        dialog.confirmed.connect(self.confirm_delete)
        dialog.exec()

    def confirm_delete(self):
        for aid in list(self.selected_ids):
            self.db.delete_asset(aid)
        self.selected_ids.clear()
        self.load_data()
        self.show_toast("🗑️ 已移入回收站")

    def on_use_once(self):
        asset = self.get_selected_asset()
        if not asset or asset.asset_type != "serial":
            return
        if (asset.remain or 0) <= 0:
            self.show_toast("❌ 剩余次数为 0，无法使用")
            return
        asset.used = (asset.used or 0) + 1
        asset.remain = max(0, (asset.total or 0) - asset.used)
        asset.status = calculate_status(asset)
        asset.updated = format_now()
        self.db.update_asset(asset)
        for i, a in enumerate(self.assets):
            if a.id == asset.id:
                self.assets[i] = asset
                break
        self.selected_ids.clear()
        self.load_data()
        self.show_toast(f"📌 已使用一次，剩余 {asset.remain} 次")

    def open_recycle_bin(self):
        dialog = RecycleBinDialog(self, self.recycle_bin)
        dialog.restored.connect(self.on_restore)
        dialog.permanently_deleted.connect(self.on_permanent_delete)
        dialog.cleared.connect(self.on_clear_recycle_bin)
        dialog.restored_all.connect(self.on_restore_all)
        dialog.exec()
        self.load_data()

    def on_clear_recycle_bin(self):
        self.db.clear_recycle_bin()
        self.show_toast("🧹 回收站已清空")

    def on_restore_all(self):
        self.db.restore_all()
        self.show_toast("↩️ 已全部恢复")

    def on_restore(self, idx):
        if 0 <= idx < len(self.recycle_bin):
            asset = self.recycle_bin[idx]
            self.db.restore_asset(asset.id)
            self.show_toast("↩️ 已恢复")

    def on_permanent_delete(self, idx):
        if 0 <= idx < len(self.recycle_bin):
            asset = self.recycle_bin[idx]
            self.db.permanent_delete(asset.id)
            self.show_toast("🗑️ 已彻底删除")

    def on_save(self):
        self.show_toast("💾 数据已保存到本地")

    def create_export_menu(self):
        """导出菜单：JSON 备份 / Excel 表格"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                padding: 4px;
            }
            QMenu::item {
                padding: 10px 14px;
                font-size: 13px;
                color: #475569;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background: #f8fafc;
            }
            QMenu::separator {
                height: 1px;
                background: #f1f5f9;
                margin: 4px 10px;
            }
        """)
        json_action = QAction("📄 导出 JSON 备份", self)
        json_action.triggered.connect(self.export_data)
        menu.addAction(json_action)
        menu.addSeparator()
        csv_action = QAction("📑 导出 CSV (.csv)", self)
        csv_action.triggered.connect(self.export_csv)
        menu.addAction(csv_action)
        excel_action = QAction("📊 导出 Excel (.xlsx)", self)
        excel_action.triggered.connect(self.export_excel)
        menu.addAction(excel_action)
        return menu

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 CSV", "asset_vault_export.csv", "CSV 文件 (*.csv)"
        )
        if not path:
            return
        try:
            self._write_csv(path)
            self.show_toast("📑 已导出 CSV 文件")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出 CSV 失败: {e}")

    def _write_csv(self, path):
        """写出 CSV（utf-8-sig 带 BOM，Excel 打开中文不乱码）"""
        import csv
        headers = [
            "所属", "名称", "类型", "账号/序列号", "密码", "绑定邮箱",
            "总数量", "已用次数", "剩余次数", "有效期/网址",
            "状态", "备注", "更新时间", "删除时间",
        ]
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for a in self.db.get_assets():
                writer.writerow(["资产"] + self._asset_excel_row(a) + [""])
            for a in self.db.get_recycle_bin():
                writer.writerow(["回收站"] + self._asset_excel_row(a) + [a.deleted_at or ""])

    def export_data(self):
        data = self.db.export_data()
        path, _ = QFileDialog.getSaveFileName(self, "导出备份", "asset_vault_backup.json", "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(data)
            self.show_toast("📤 已导出 JSON 备份")

    @staticmethod
    def _excel_width(text) -> int:
        """估算列宽（中文按 2 个字符宽计）"""
        s = "" if text is None else str(text)
        return sum(2 if ord(ch) > 127 else 1 for ch in s)

    def _fill_excel_sheet(self, ws, headers, rows):
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.utils import get_column_letter

        header_fill = PatternFill("solid", fgColor="6366F1")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        thin = Side(style="thin", color="E2E8F0")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        ws.append(headers)
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = border
        for row in rows:
            ws.append(row)
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.border = border
                cell.alignment = Alignment(vertical="center")
        for idx, col in enumerate(ws.columns, 1):
            width = max((self._excel_width(c.value) for c in col), default=8)
            ws.column_dimensions[get_column_letter(idx)].width = min(max(width + 4, 10), 46)
        ws.freeze_panes = "A2"

    @staticmethod
    def _asset_excel_row(a):
        tc = TYPE_CONFIG.get(a.asset_type, TYPE_CONFIG["serial"])
        st = STATUS_CONFIG.get(a.status, STATUS_CONFIG["normal"])
        expire_or_url = (a.expire or "永久") if a.asset_type == "serial" else (a.url or "-")
        return [
            a.name,
            tc["label"],
            a.account,                       # 明文导出
            a.password or "-",
            a.email or "-",
            a.total if a.total is not None else "-",
            a.used if a.used is not None else "-",
            a.remain if a.remain is not None else "-",
            expire_or_url,
            st["label"],
            a.note or "",
            a.updated,
        ]

    def export_excel(self):
        try:
            from openpyxl import Workbook
        except ImportError:
            QMessageBox.warning(
                self, "缺少依赖",
                "导出 Excel 需要 openpyxl，请先安装：\npip install openpyxl"
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 Excel", "asset_vault_export.xlsx", "Excel 文件 (*.xlsx)"
        )
        if not path:
            return
        try:
            wb = Workbook()
            headers = [
                "名称", "类型", "账号/序列号", "密码", "绑定邮箱",
                "总数量", "已用次数", "剩余次数", "有效期/网址",
                "状态", "备注", "更新时间",
            ]
            ws1 = wb.active
            ws1.title = "资产"
            self._fill_excel_sheet(
                ws1, headers,
                [self._asset_excel_row(a) for a in self.db.get_assets()],
            )
            ws2 = wb.create_sheet("回收站")
            self._fill_excel_sheet(
                ws2, headers + ["删除时间"],
                [
                    self._asset_excel_row(a) + [a.deleted_at or ""]
                    for a in self.db.get_recycle_bin()
                ],
            )
            wb.save(path)
            self.show_toast("📊 已导出 Excel 文件")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出 Excel 失败: {e}")

    # ===== 设置 =====
    def create_settings_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                padding: 4px;
            }
            QMenu::item {
                padding: 10px 14px;
                font-size: 13px;
                color: #475569;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background: #f8fafc;
            }
            QMenu::separator {
                height: 1px;
                background: #f1f5f9;
                margin: 4px 10px;
            }
        """)
        change_pw_action = QAction("🔑 修改主密码", self)
        change_pw_action.triggered.connect(self.change_master_password)
        menu.addAction(change_pw_action)
        menu.addSeparator()
        about_action = QAction("ℹ️ 关于 AssetVault", self)
        about_action.triggered.connect(self.show_about)
        menu.addAction(about_action)
        return menu

    def open_settings(self):
        menu = self.create_settings_menu()
        menu.exec(self.settings_btn.mapToGlobal(QPoint(0, self.settings_btn.height() + 4)))

    def change_master_password(self):
        dialog = ChangeMasterPasswordDialog(self)
        dialog.submitted.connect(self.on_master_password_submitted)
        dialog.exec()

    def on_master_password_submitted(self, old_pw: str, new_pw: str):
        if self.db.change_master_password(old_pw, new_pw):
            QMessageBox.information(self, "成功", "主密码修改成功，下次启动请使用新密码解锁")
        else:
            QMessageBox.warning(self, "失败", "当前主密码不正确，修改失败")

    def show_about(self):
        QMessageBox.information(
            self, "关于 AssetVault",
            "AssetVault v2.0\n个人数字资产管理器\n\n本地 AES-256-GCM 加密存储 · 离线运行"
        )

    def import_data(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入备份", "", "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = f.read()
            self.db.import_data(data)
            self.load_data()
            self.show_toast("📥 导入成功")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入失败: {e}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.toast.isVisible():
            self.toast.move(
                self.width() - self.toast.width() - 24,
                self.height() - self.toast.height() - 24
            )
