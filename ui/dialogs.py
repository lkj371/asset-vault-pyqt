"""弹窗组件：新增/编辑、删除确认、回收站、主密码"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QWidget, QGridLayout, QDateEdit, QComboBox, QSpinBox,
    QFrame, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QCheckBox, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt, QDate, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPalette

from models import Asset
from utils import (
    format_now, check_password_strength, calculate_status,
    mask_serial, STATUS_CONFIG, TYPE_CONFIG
)


class AssetDialog(QDialog):
    saved = pyqtSignal(object)

    def __init__(self, parent=None, mode="add", asset_type="serial", asset=None):
        super().__init__(parent)
        self.mode = mode
        self.current_type = asset_type
        self.asset = asset
        self.setWindowTitle("新增资产" if mode == "add" else "编辑资产")
        self.setMinimumWidth(500)
        self.setMaximumHeight(800)
        self.setup_ui()
        if asset:
            self.load_data()

    def setup_ui(self):
        from ui.style import MAIN_STYLE
        self.setStyleSheet(MAIN_STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 头部
        header = QWidget()
        header.setObjectName("modalHeader")
        hlayout = QHBoxLayout(header)
        hlayout.setContentsMargins(20, 16, 20, 16)

        title_layout = QHBoxLayout()
        icon = QLabel(TYPE_CONFIG[self.current_type]["icon"])
        icon.setStyleSheet("font-size: 20px;")
        title_layout.addWidget(icon)
        self.title_label = QLabel(f"{'新增' if self.mode == 'add' else '编辑'}{TYPE_CONFIG[self.current_type]['label']}")
        self.title_label.setObjectName("modalTitle")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        hlayout.addLayout(title_layout)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("modalCloseBtn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        hlayout.addWidget(close_btn)
        layout.addWidget(header)

        # 主体
        body = QWidget()
        body.setObjectName("modalBody")
        blayout = QVBoxLayout(body)
        blayout.setContentsMargins(24, 20, 24, 20)
        blayout.setSpacing(16)

        # 类型选择（仅新增模式）
        if self.mode == "add":
            type_layout = QHBoxLayout()
            type_layout.setSpacing(8)
            self.btn_serial = QPushButton("🔑 序列号")
            self.btn_password = QPushButton("🛡️ 密码")
            self.btn_serial.setObjectName("typeSelectorBtnActive" if self.current_type == "serial" else "typeSelectorBtn")
            self.btn_password.setObjectName("typeSelectorBtnActive" if self.current_type == "password" else "typeSelectorBtn")
            self.btn_serial.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_password.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_serial.clicked.connect(lambda: self.switch_type("serial"))
            self.btn_password.clicked.connect(lambda: self.switch_type("password"))
            type_layout.addWidget(self.btn_serial)
            type_layout.addWidget(self.btn_password)
            blayout.addLayout(type_layout)

        # 名称
        blayout.addWidget(self._form_label("软件名称" if self.current_type == "serial" else "服务名称", required=True))
        self.name_input = QLineEdit()
        self.name_input.setObjectName("inputField")
        self.name_input.setPlaceholderText("如: JetBrains IntelliJ IDEA" if self.current_type == "serial" else "如: GitHub, 阿里云")
        blayout.addWidget(self.name_input)

        # 序列号字段
        self.serial_fields = QWidget()
        sfl = QVBoxLayout(self.serial_fields)
        sfl.setContentsMargins(0, 0, 0, 0)
        sfl.setSpacing(16)

        sfl.addWidget(self._form_label("序列号 / 激活码", required=True))
        serial_row = QHBoxLayout()
        serial_row.setSpacing(8)
        self.serial_input = QLineEdit()
        self.serial_input.setObjectName("inputField")
        self.serial_input.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        serial_row.addWidget(self.serial_input)
        gen_serial_btn = QPushButton("🎲 生成")
        gen_serial_btn.setObjectName("btnSecondary")
        gen_serial_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        gen_serial_btn.clicked.connect(self.generate_serial)
        serial_row.addWidget(gen_serial_btn)
        sfl.addLayout(serial_row)

        count_grid = QGridLayout()
        count_grid.setSpacing(12)
        count_grid.addWidget(self._form_label("总数量"), 0, 0)
        count_grid.addWidget(self._form_label("已用次数"), 0, 1)
        count_grid.addWidget(self._form_label("剩余次数"), 0, 2)
        self.total_spin = QSpinBox()
        self.total_spin.setObjectName("inputField")
        self.total_spin.setRange(0, 9999)
        self.total_spin.setValue(1)
        self.total_spin.valueChanged.connect(self.update_remain)
        count_grid.addWidget(self.total_spin, 1, 0)
        self.used_spin = QSpinBox()
        self.used_spin.setObjectName("inputField")
        self.used_spin.setRange(0, 9999)
        self.used_spin.valueChanged.connect(self.update_remain)
        count_grid.addWidget(self.used_spin, 1, 1)
        self.remain_spin = QSpinBox()
        self.remain_spin.setObjectName("inputField")
        self.remain_spin.setRange(0, 9999)
        self.remain_spin.setReadOnly(True)
        self.remain_spin.setValue(1)
        self.remain_spin.setStyleSheet("background: #f8fafc; color: #94a3b8; font-weight: 600;")
        count_grid.addWidget(self.remain_spin, 1, 2)
        sfl.addLayout(count_grid)
        blayout.addWidget(self.serial_fields)

        # 密码字段
        self.password_fields = QWidget()
        pfl = QVBoxLayout(self.password_fields)
        pfl.setContentsMargins(0, 0, 0, 0)
        pfl.setSpacing(16)

        pfl.addWidget(self._form_label("用户名 / 账号", required=True))
        self.username_input = QLineEdit()
        self.username_input.setObjectName("inputField")
        self.username_input.setPlaceholderText("username")
        pfl.addWidget(self.username_input)

        pfl.addWidget(self._form_label("密码", required=True))
        pw_row = QHBoxLayout()
        pw_row.setSpacing(8)
        self.password_input = QLineEdit()
        self.password_input.setObjectName("inputField")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("••••••••")
        self.password_input.textChanged.connect(self.update_strength)
        pw_row.addWidget(self.password_input)
        gen_pw_btn = QPushButton("🎲 生成")
        gen_pw_btn.setObjectName("btnSecondary")
        gen_pw_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        gen_pw_btn.clicked.connect(self.generate_password)
        pw_row.addWidget(gen_pw_btn)
        self.pw_visible_btn = QPushButton("👁")
        self.pw_visible_btn.setObjectName("btnSecondary")
        self.pw_visible_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pw_visible_btn.setCheckable(True)
        self.pw_visible_btn.toggled.connect(self.toggle_password_visible)
        pw_row.addWidget(self.pw_visible_btn)
        pfl.addLayout(pw_row)

        # 密码强度条
        strength_widget = QWidget()
        strength_layout = QHBoxLayout(strength_widget)
        strength_layout.setContentsMargins(0, 0, 0, 0)
        strength_layout.setSpacing(6)
        self.strength_track = QFrame()
        self.strength_track.setObjectName("strengthTrack")
        self.strength_track.setMinimumWidth(200)
        self.strength_fill = QFrame(self.strength_track)
        self.strength_fill.setObjectName("strengthFill")
        self.strength_fill.setGeometry(0, 0, 0, 4)
        self.strength_fill.setStyleSheet("background: #ef4444;")
        strength_layout.addWidget(self.strength_track)
        self.strength_label = QLabel("未输入")
        self.strength_label.setStyleSheet("font-size: 11px; color: #94a3b8; font-weight: 500;")
        strength_layout.addWidget(self.strength_label)
        strength_layout.addStretch()
        pfl.addWidget(strength_widget)

        pfl.addWidget(self._form_label("网址 / 服务地址"))
        self.url_input = QLineEdit()
        self.url_input.setObjectName("inputField")
        self.url_input.setPlaceholderText("https://example.com")
        pfl.addWidget(self.url_input)
        blayout.addWidget(self.password_fields)

        # 通用字段
        blayout.addWidget(self._form_label("绑定邮箱"))
        self.email_input = QLineEdit()
        self.email_input.setObjectName("inputField")
        self.email_input.setPlaceholderText("account@example.com")
        blayout.addWidget(self.email_input)

        blayout.addWidget(self._form_label("有效期至" if self.current_type == "serial" else "密码到期提醒"))
        self.expire_input = QDateEdit()
        self.expire_input.setObjectName("inputField")
        self.expire_input.setCalendarPopup(True)
        self.expire_input.setDate(QDate.currentDate())
        self.expire_input.setDisplayFormat("yyyy-MM-dd")
        self.expire_input.setSpecialValueText("  永久")
        self.expire_input.setDate(QDate(2000, 1, 1))
        blayout.addWidget(self.expire_input)

        blayout.addWidget(self._form_label("备注"))
        self.note_input = QTextEdit()
        self.note_input.setObjectName("textArea")
        self.note_input.setPlaceholderText("购买渠道、使用设备、其他说明...")
        self.note_input.setMaximumHeight(80)
        blayout.addWidget(self.note_input)

        blayout.addStretch()

        # 底部按钮
        footer = QWidget()
        footer.setObjectName("modalFooter")
        flayout = QHBoxLayout(footer)
        flayout.setContentsMargins(24, 0, 24, 24)
        flayout.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("btnSecondary")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        flayout.addWidget(cancel_btn)
        save_btn = QPushButton("保存")
        save_btn.setObjectName("btnPrimary")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self.save)
        flayout.addWidget(save_btn)

        # 表单主体放入滚动区，内容过高时右侧出现上下滚动条
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(body)
        layout.addWidget(scroll)
        layout.addWidget(footer)

        self.update_fields_visibility()

    def _form_label(self, text, required=False):
        label = QLabel(f"{text} <span style='color:#ef4444;'>*</span>" if required else text)
        label.setObjectName("formLabel")
        return label

    def switch_type(self, asset_type):
        self.current_type = asset_type
        self.btn_serial.setObjectName("typeSelectorBtnActive" if asset_type == "serial" else "typeSelectorBtn")
        self.btn_password.setObjectName("typeSelectorBtnActive" if asset_type == "password" else "typeSelectorBtn")
        self.btn_serial.style().unpolish(self.btn_serial)
        self.btn_serial.style().polish(self.btn_serial)
        self.btn_password.style().unpolish(self.btn_password)
        self.btn_password.style().polish(self.btn_password)
        self.title_label.setText(f"{'新增' if self.mode == 'add' else '编辑'}{TYPE_CONFIG[asset_type]['label']}")
        self.update_fields_visibility()

    def update_fields_visibility(self):
        self.serial_fields.setVisible(self.current_type == "serial")
        self.password_fields.setVisible(self.current_type == "password")

    def update_remain(self):
        self.remain_spin.setValue(max(0, self.total_spin.value() - self.used_spin.value()))

    def generate_serial(self):
        import random, string
        chars = string.ascii_uppercase + string.digits
        serial = '-'.join(''.join(random.choice(chars) for _ in range(4)) for _ in range(4))
        self.serial_input.setText(serial)

    def generate_password(self):
        import random, string
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        pw = ''.join(random.choice(chars) for _ in range(16))
        self.password_input.setText(pw)

    def toggle_password_visible(self, checked):
        self.password_input.setEchoMode(QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password)

    def update_strength(self):
        pw = self.password_input.text()
        result = check_password_strength(pw)
        self.strength_fill.setStyleSheet(f"background: {result['color']};")
        # 计算宽度百分比
        track_width = self.strength_track.width()
        fill_width = int(track_width * int(result['width'].rstrip('%')) / 100)
        self.strength_fill.setGeometry(0, 0, fill_width, 4)
        self.strength_label.setText(result['text'])
        self.strength_label.setStyleSheet(f"font-size: 11px; color: {result['color']}; font-weight: 500;")

    def load_data(self):
        if not self.asset:
            return
        self.name_input.setText(self.asset.name)
        self.email_input.setText(self.asset.email or "")
        self.note_input.setText(self.asset.note or "")
        if self.asset.expire:
            try:
                from PyQt6.QtCore import QDate
                y, m, d = map(int, self.asset.expire.split("-"))
                self.expire_input.setDate(QDate(y, m, d))
            except:
                pass
        if self.asset.asset_type == "serial":
            self.serial_input.setText(self.asset.account)
            self.total_spin.setValue(self.asset.total or 1)
            self.used_spin.setValue(self.asset.used or 0)
            self.remain_spin.setValue(self.asset.remain or 0)
        else:
            self.username_input.setText(self.asset.account)
            self.password_input.setText(self.asset.password or "")
            self.url_input.setText(self.asset.url or "")

    def save(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "提示", "名称不能为空")
            return

        if self.current_type == "serial" and not self.serial_input.text().strip():
            QMessageBox.warning(self, "提示", "序列号不能为空")
            return

        if self.current_type == "password" and not self.username_input.text().strip():
            QMessageBox.warning(self, "提示", "用户名不能为空")
            return

        expire_date = self.expire_input.date()
        expire_str = expire_date.toString("yyyy-MM-dd") if expire_date.year() > 2000 else ""

        asset = Asset(
            id=self.asset.id if self.asset else 0,
            asset_type=self.current_type,
            name=self.name_input.text().strip(),
            account=self.serial_input.text().strip() if self.current_type == "serial" else self.username_input.text().strip(),
            password=self.password_input.text() if self.current_type == "password" else None,
            email=self.email_input.text().strip() or None,
            total=self.total_spin.value() if self.current_type == "serial" else None,
            used=self.used_spin.value() if self.current_type == "serial" else None,
            remain=self.remain_spin.value() if self.current_type == "serial" else None,
            expire=expire_str or None,
            url=self.url_input.text().strip() or None if self.current_type == "password" else None,
            status="normal",
            note=self.note_input.toPlainText().strip() or None,
            updated=format_now(),
        )
        asset.status = calculate_status(asset)
        self.saved.emit(asset)
        self.accept()


class DeleteConfirmDialog(QDialog):
    confirmed = pyqtSignal()

    def __init__(self, parent=None, count=1):
        super().__init__(parent)
        self.setWindowTitle("确认删除")
        self.setMinimumWidth(360)
        self.setup_ui(count)

    def setup_ui(self, count):
        from ui.style import MAIN_STYLE
        self.setStyleSheet(MAIN_STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("🗑️")
        icon.setStyleSheet("font-size: 48px; background: #fef2f2; border-radius: 12px; padding: 12px;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setMaximumSize(72, 72)
        layout.addWidget(icon, alignment=Qt.AlignmentFlag.AlignCenter)

        title = QLabel("确认移入回收站?")
        title.setObjectName("modalTitle")
        title.setStyleSheet("font-size: 17px; font-weight: 700; color: #0f172a;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        desc = QLabel(f"{'这' if count == 1 else f'这 {count} 条'}资产可在回收站中恢复，确认继续吗？")
        desc.setStyleSheet("font-size: 13px; color: #64748b; line-height: 1.6;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("btnSecondary")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton("确认删除")
        confirm_btn.setObjectName("btnDanger")
        confirm_btn.setStyleSheet("""
            QPushButton {
                background: #ef4444; color: white; border: none;
                border-radius: 8px; padding: 9px 18px;
                font-size: 13px; font-weight: 600;
            }
            QPushButton:hover { background: #dc2626; }
        """)
        confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_btn.clicked.connect(self.on_confirm)
        btn_layout.addWidget(confirm_btn)
        layout.addLayout(btn_layout)

    def on_confirm(self):
        self.confirmed.emit()
        self.accept()


class RecycleBinDialog(QDialog):
    restored = pyqtSignal(int)
    permanently_deleted = pyqtSignal(int)
    restored_all = pyqtSignal()
    cleared = pyqtSignal()

    def __init__(self, parent=None, recycle_bin=None):
        super().__init__(parent)
        self.recycle_bin = recycle_bin or []
        self.setWindowTitle("回收站")
        self.setMinimumSize(700, 500)
        self.setup_ui()

    def setup_ui(self):
        from ui.style import MAIN_STYLE
        self.setStyleSheet(MAIN_STYLE)
        # 支持重复调用（恢复/删除/清空后重建界面）：先移除旧布局
        old_layout = self.layout()
        if old_layout is not None:
            while old_layout.count():
                item = old_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            QWidget().setLayout(old_layout)  # 旧布局挂到临时控件上随之销毁

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 头部
        header = QWidget()
        header.setObjectName("modalHeader")
        hlayout = QHBoxLayout(header)
        hlayout.setContentsMargins(20, 16, 20, 16)
        title = QLabel("🗑️ 回收站")
        title.setObjectName("modalTitle")
        hlayout.addWidget(title)
        hlayout.addStretch()

        if self.recycle_bin:
            restore_all_btn = QPushButton("↩️ 全部恢复")
            restore_all_btn.setStyleSheet("""
                QPushButton {
                    background: #f0fdf4; color: #22c55e; border: none;
                    border-radius: 8px; padding: 7px 14px;
                    font-size: 12px; font-weight: 600;
                }
                QPushButton:hover { background: #dcfce7; }
            """)
            restore_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            restore_all_btn.clicked.connect(self.on_restore_all)
            hlayout.addWidget(restore_all_btn)

            clear_btn = QPushButton("🧹 清空回收站")
            clear_btn.setStyleSheet("""
                QPushButton {
                    background: #fef2f2; color: #ef4444; border: none;
                    border-radius: 8px; padding: 7px 14px;
                    font-size: 12px; font-weight: 600;
                }
                QPushButton:hover { background: #fee2e2; }
            """)
            clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            clear_btn.clicked.connect(self.on_clear_all)
            hlayout.addWidget(clear_btn)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("modalCloseBtn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        hlayout.addWidget(close_btn)
        layout.addWidget(header)

        # 表格
        body = QWidget()
        body.setObjectName("modalBody")
        blayout = QVBoxLayout(body)
        blayout.setContentsMargins(20, 20, 20, 20)

        if not self.recycle_bin:
            empty = QLabel("🗑️\n\n回收站为空")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("font-size: 14px; color: #64748b; font-weight: 500; padding: 48px;")
            blayout.addWidget(empty)
        else:
            self.table = QTableWidget()
            self.table.setObjectName("dataTable")
            self.table.setColumnCount(5)
            self.table.setHorizontalHeaderLabels(["名称", "类型", "账号/序列号", "删除时间", "操作"])
            self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            self.table.setAlternatingRowColors(False)
            self.table.verticalHeader().setVisible(False)
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(4, 200)
            self.table.setRowCount(len(self.recycle_bin))
            # 全局 #dataTable::item 的 padding(12px) 会把单元格控件的可用高度挤压到 0，
            # 导致操作列按钮不可见；此处减小 padding 并固定行高
            self.table.setStyleSheet("QTableWidget::item { padding: 6px 12px; }")
            self.table.verticalHeader().setDefaultSectionSize(44)

            for i, asset in enumerate(self.recycle_bin):
                self.table.setItem(i, 0, QTableWidgetItem(asset.name))
                tc = TYPE_CONFIG[asset.asset_type]
                type_item = QTableWidgetItem(f"{tc['icon']} {tc['label']}")
                self.table.setItem(i, 1, type_item)
                self.table.setItem(i, 2, QTableWidgetItem(asset.account))  # 默认明文显示
                self.table.setItem(i, 3, QTableWidgetItem(asset.deleted_at or ""))

                # 字段数据居中对齐
                for col in range(4):
                    cell_item = self.table.item(i, col)
                    if cell_item:
                        cell_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(4, 2, 4, 2)
                action_layout.setSpacing(6)

                restore_btn = QPushButton("↩️ 恢复")
                restore_btn.setStyleSheet("""
                    QPushButton {
                        background: #f0fdf4; color: #22c55e; border: none;
                        border-radius: 6px; padding: 5px 12px;
                        font-size: 12px; font-weight: 600;
                    }
                    QPushButton:hover { background: #dcfce7; }
                """)
                restore_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                restore_btn.clicked.connect(lambda checked, idx=i: self.on_restore(idx))
                action_layout.addWidget(restore_btn)

                del_btn = QPushButton("彻底删除")
                del_btn.setStyleSheet("""
                    QPushButton {
                        background: #fef2f2; color: #ef4444; border: none;
                        border-radius: 6px; padding: 5px 12px;
                        font-size: 12px; font-weight: 600;
                    }
                    QPushButton:hover { background: #fee2e2; }
                """)
                del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                del_btn.clicked.connect(lambda checked, idx=i: self.on_permanent_delete(idx))
                action_layout.addWidget(del_btn)
                action_layout.addStretch()

                self.table.setCellWidget(i, 4, action_widget)

            blayout.addWidget(self.table)

        layout.addWidget(body)

    def on_restore(self, idx):
        self.restored.emit(idx)
        self.recycle_bin.pop(idx)
        self.setup_ui()
        self.update()

    def on_restore_all(self):
        reply = QMessageBox.question(
            self, "确认恢复",
            f"将回收站中的 {len(self.recycle_bin)} 条记录全部恢复，确认吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.restored_all.emit()
            self.recycle_bin.clear()
            self.setup_ui()
            self.update()

    def on_clear_all(self):
        reply = QMessageBox.question(
            self, "确认清空",
            f"将彻底删除回收站中的 {len(self.recycle_bin)} 条记录，无法恢复，确认吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.cleared.emit()
            self.recycle_bin.clear()
            self.setup_ui()
            self.update()

    def on_permanent_delete(self, idx):
        reply = QMessageBox.question(
            self, "确认", "彻底删除后无法恢复，确认吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.permanently_deleted.emit(idx)
            self.recycle_bin.pop(idx)
            self.setup_ui()
            self.update()


class MasterPasswordDialog(QDialog):
    unlocked = pyqtSignal(str)

    def __init__(self, parent=None, mode="unlock"):
        super().__init__(parent)
        self.mode = mode
        self.setWindowTitle("设置主密码" if mode == "init" else "解锁 Vault")
        self.setMinimumWidth(360)
        self.setup_ui()

    def setup_ui(self):
        from ui.style import MAIN_STYLE
        self.setStyleSheet(MAIN_STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("🔐")
        icon.setStyleSheet("font-size: 48px;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        title = QLabel("设置主密码" if self.mode == "init" else "Vault 已锁定")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #0f172a;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        desc = QLabel(
            "请设置主密码用于加密本地数据" if self.mode == "init" else "请输入主密码解锁"
        )
        desc.setStyleSheet("font-size: 13px; color: #64748b;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self.pw_input = QLineEdit()
        self.pw_input.setObjectName("inputField")
        self.pw_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw_input.setPlaceholderText("主密码")
        self.pw_input.returnPressed.connect(self.submit)
        layout.addWidget(self.pw_input)

        if self.mode == "init":
            self.pw_confirm = QLineEdit()
            self.pw_confirm.setObjectName("inputField")
            self.pw_confirm.setEchoMode(QLineEdit.EchoMode.Password)
            self.pw_confirm.setPlaceholderText("确认密码")
            self.pw_confirm.returnPressed.connect(self.submit)
            layout.addWidget(self.pw_confirm)

        btn = QPushButton("确认" if self.mode == "init" else "解锁")
        btn.setObjectName("btnPrimary")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self.submit)
        layout.addWidget(btn)

    def submit(self):
        pw = self.pw_input.text().strip()
        if not pw:
            QMessageBox.warning(self, "提示", "密码不能为空")
            return
        if self.mode == "init":
            if pw != self.pw_confirm.text().strip():
                QMessageBox.warning(self, "提示", "两次密码不一致")
                return
        self.unlocked.emit(pw)
        self.accept()


class ChangeMasterPasswordDialog(QDialog):
    """设置 - 修改主密码"""
    submitted = pyqtSignal(str, str)  # (旧密码, 新密码)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("修改主密码")
        self.setMinimumWidth(400)
        self.setup_ui()

    def setup_ui(self):
        from ui.style import MAIN_STYLE
        self.setStyleSheet(MAIN_STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 头部
        header = QWidget()
        header.setObjectName("modalHeader")
        hlayout = QHBoxLayout(header)
        hlayout.setContentsMargins(20, 16, 20, 16)
        title = QLabel("🔑 修改主密码")
        title.setObjectName("modalTitle")
        hlayout.addWidget(title)
        hlayout.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setObjectName("modalCloseBtn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        hlayout.addWidget(close_btn)
        layout.addWidget(header)

        # 主体
        body = QWidget()
        body.setObjectName("modalBody")
        blayout = QVBoxLayout(body)
        blayout.setContentsMargins(24, 20, 24, 20)
        blayout.setSpacing(12)

        desc = QLabel("修改后，全部已加密数据将使用新密码重新加密，请牢记新主密码。")
        desc.setStyleSheet("font-size: 12px; color: #64748b;")
        desc.setWordWrap(True)
        blayout.addWidget(desc)

        def field(placeholder):
            inp = QLineEdit()
            inp.setObjectName("inputField")
            inp.setEchoMode(QLineEdit.EchoMode.Password)
            inp.setPlaceholderText(placeholder)
            return inp

        label1 = QLabel("当前主密码 <span style='color:#ef4444;'>*</span>")
        label1.setObjectName("formLabel")
        blayout.addWidget(label1)
        self.old_input = field("请输入当前主密码")
        blayout.addWidget(self.old_input)

        label2 = QLabel("新主密码 <span style='color:#ef4444;'>*</span>")
        label2.setObjectName("formLabel")
        blayout.addWidget(label2)
        self.new_input = field("至少 6 位")
        blayout.addWidget(self.new_input)

        label3 = QLabel("确认新主密码 <span style='color:#ef4444;'>*</span>")
        label3.setObjectName("formLabel")
        blayout.addWidget(label3)
        self.confirm_input = field("再次输入新主密码")
        self.confirm_input.returnPressed.connect(self.submit)
        blayout.addWidget(self.confirm_input)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("btnSecondary")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        ok_btn = QPushButton("确认修改")
        ok_btn.setObjectName("btnPrimary")
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.clicked.connect(self.submit)
        btn_layout.addWidget(ok_btn)
        blayout.addLayout(btn_layout)

        layout.addWidget(body)

    def submit(self):
        old_pw = self.old_input.text().strip()
        new_pw = self.new_input.text().strip()
        confirm_pw = self.confirm_input.text().strip()
        if not old_pw:
            QMessageBox.warning(self, "提示", "请输入当前主密码")
            return
        if len(new_pw) < 6:
            QMessageBox.warning(self, "提示", "新主密码至少 6 位")
            return
        if new_pw != confirm_pw:
            QMessageBox.warning(self, "提示", "两次输入的新密码不一致")
            return
        if new_pw == old_pw:
            QMessageBox.warning(self, "提示", "新密码不能与当前密码相同")
            return
        self.submitted.emit(old_pw, new_pw)
        self.accept()
