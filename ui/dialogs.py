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
    mask_serial, STATUS_CONFIG, TYPE_CONFIG, get_type_config
)
from templates import (
    FIELD_TEXT, FIELD_PASSWORD, FIELD_TEXTAREA, FIELD_DATE,
    FIELD_SELECT, FIELD_NUMBER, FIELD_FILE, FIELD_TYPE_LABELS,
    LEGACY_TYPES, get_template, ordered_templates, resolve_column,
)


class AssetDialog(QDialog):
    saved = pyqtSignal(object)

    def __init__(self, parent=None, mode="add", asset_type="serial", asset=None, custom_templates=None):
        super().__init__(parent)
        self.mode = mode
        self.current_type = asset_type
        self.asset = asset
        self.custom_templates = custom_templates or []
        self.dynamic_widgets = {}   # 模板字段 key -> (字段定义, 控件)
        self.setWindowTitle("新增资产" if mode == "add" else "编辑资产")
        self.setMinimumWidth(500)
        self.setMaximumHeight(800)
        self.setup_ui()
        if asset:
            self.load_data()

    def template(self):
        return get_template(self.current_type, self.custom_templates)

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
        tpl = self.template()
        icon = QLabel(tpl["icon"])
        icon.setStyleSheet("font-size: 20px;")
        title_layout.addWidget(icon)
        self.title_label = QLabel(f"{'新增' if self.mode == 'add' else '编辑'}{tpl['label']}")
        self.title_label.setObjectName("modalTitle")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        hlayout.addLayout(title_layout)

        layout.addWidget(header)

        # 主体
        body = QWidget()
        body.setObjectName("modalBody")
        blayout = QVBoxLayout(body)
        blayout.setContentsMargins(24, 20, 24, 20)
        blayout.setSpacing(16)

        # 类型选择（仅新增模式）：下拉列出全部内置 + 自定义模板
        if self.mode == "add":
            type_layout = QHBoxLayout()
            type_layout.setSpacing(8)
            type_layout.addWidget(self._form_label("资产类型"))
            self.type_combo = QComboBox()
            self.type_combo.setObjectName("inputField")
            self.type_combo.setCursor(Qt.CursorShape.PointingHandCursor)
            for tpl in ordered_templates(self.custom_templates):
                self.type_combo.addItem(f"{tpl['icon']} {tpl['label']}", tpl["key"])
            idx = self.type_combo.findData(self.current_type)
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)
            self.type_combo.currentIndexChanged.connect(self.on_type_combo_changed)
            type_layout.addWidget(self.type_combo, 1)
            blayout.addLayout(type_layout)

        # 名称
        self.name_label = self._form_label("名称", required=True)
        blayout.addWidget(self.name_label)
        self.name_input = QLineEdit()
        self.name_input.setObjectName("inputField")
        # 命名规范提示：与输入框组成独立小块（4px 间距），
        # 不用负边距，避免被输入框遮挡或与下方标签交叠
        name_hint = QLabel("💡 命名建议：产品/服务名 + 用途或环境，如「阿里云 OSS（生产环境）」")
        name_hint.setObjectName("nameHint")
        name_hint.setStyleSheet("font-size: 11px; color: #94a3b8; background: transparent;")
        name_block = QVBoxLayout()
        name_block.setContentsMargins(0, 0, 0, 0)
        name_block.setSpacing(4)
        name_block.addWidget(self.name_input)
        name_block.addWidget(name_hint)
        blayout.addLayout(name_block)

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

        # 动态模板字段容器（非旧版类型：按模板定义生成表单）
        self.dynamic_container = QWidget()
        self.dynamic_layout = QVBoxLayout(self.dynamic_container)
        self.dynamic_layout.setContentsMargins(0, 0, 0, 0)
        self.dynamic_layout.setSpacing(16)
        blayout.addWidget(self.dynamic_container)

        # 通用字段（仅旧版类型：序列号/密码）
        self.legacy_common = QWidget()
        lcl = QVBoxLayout(self.legacy_common)
        lcl.setContentsMargins(0, 0, 0, 0)
        lcl.setSpacing(16)

        lcl.addWidget(self._form_label("绑定邮箱"))
        self.email_input = QLineEdit()
        self.email_input.setObjectName("inputField")
        self.email_input.setPlaceholderText("account@example.com")
        lcl.addWidget(self.email_input)

        self.legacy_expire_label = self._form_label("有效期至")
        lcl.addWidget(self.legacy_expire_label)
        self.expire_input = QDateEdit()
        self.expire_input.setObjectName("inputField")
        self.expire_input.setCalendarPopup(True)
        self.expire_input.setDate(QDate.currentDate())
        self.expire_input.setDisplayFormat("yyyy-MM-dd")
        self.expire_input.setSpecialValueText("  永久")
        self.expire_input.setDate(QDate(2000, 1, 1))
        lcl.addWidget(self.expire_input)
        blayout.addWidget(self.legacy_common)

        # 标签（全类型通用，供高级筛选组合查询）
        blayout.addWidget(self._form_label("标签"))
        self.tags_input = QLineEdit()
        self.tags_input.setObjectName("inputField")
        self.tags_input.setPlaceholderText("多个标签用逗号分隔，如: 工作, 生产环境")
        blayout.addWidget(self.tags_input)

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

    def on_type_combo_changed(self, index):
        key = self.type_combo.itemData(index)
        if key and key != self.current_type:
            self.switch_type(key)

    def switch_type(self, asset_type):
        self.current_type = asset_type
        tpl = self.template()
        self.title_label.setText(f"{'新增' if self.mode == 'add' else '编辑'}{tpl['label']}")
        self.update_fields_visibility()

    def update_fields_visibility(self):
        tpl = self.template()
        is_legacy = self.current_type in LEGACY_TYPES
        self.serial_fields.setVisible(self.current_type == "serial")
        self.password_fields.setVisible(self.current_type == "password")
        self.legacy_common.setVisible(is_legacy)
        self.dynamic_container.setVisible(not is_legacy)
        # 名称标签与占位随模板变化
        name_text = {"serial": "软件名称", "password": "服务名称"}.get(self.current_type, "名称")
        self.name_label.setText(f"{name_text} <span style='color:#ef4444;'>*</span>")
        self.name_input.setPlaceholderText(tpl.get("name_placeholder") or "")
        if is_legacy:
            self.legacy_expire_label.setText("有效期至" if self.current_type == "serial" else "密码到期提醒")
        else:
            self.build_dynamic_form()

    # ===== 模板引擎动态表单 =====

    def build_dynamic_form(self):
        """按模板字段定义生成表单控件"""
        # 清空旧控件
        while self.dynamic_layout.count():
            item = self.dynamic_layout.takeAt(0)
                # 字段行内可能嵌套子布局（文件选择）
            w = item.widget()
            if w is not None:
                w.deleteLater()
            elif item.layout() is not None:
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget() is not None:
                        sub.widget().deleteLater()
        self.dynamic_widgets = {}

        tpl = self.template()
        old_extra = {}
        if self.asset and self.asset.asset_type == self.current_type and self.asset.extra:
            old_extra = self.asset.extra

        for fdef in tpl.get("fields", []):
            label = self._form_label(fdef["label"], required=fdef.get("required"))
            self.dynamic_layout.addWidget(label)
            widget = self._create_field_widget(fdef, old_extra.get(fdef["key"]))
            if isinstance(widget, QWidget):
                self.dynamic_layout.addWidget(widget)
            else:  # 子布局（附件行）
                self.dynamic_layout.addLayout(widget)
            self.dynamic_widgets[fdef["key"]] = (fdef, widget)

    def _create_field_widget(self, fdef, value=None):
        """按字段类型创建控件，并回填旧值"""
        ftype = fdef.get("type", FIELD_TEXT)
        value = "" if value is None else str(value)

        if ftype == FIELD_PASSWORD:
            row = QHBoxLayout()
            row.setSpacing(8)
            inp = QLineEdit()
            inp.setObjectName("inputField")
            inp.setEchoMode(QLineEdit.EchoMode.Password)
            inp.setPlaceholderText(fdef.get("placeholder") or "输入后加密存储")
            inp.setText(value)
            row.addWidget(inp)
            eye = QPushButton("👁")
            eye.setObjectName("btnSecondary")
            eye.setCursor(Qt.CursorShape.PointingHandCursor)
            eye.setCheckable(True)
            eye.toggled.connect(
                lambda checked, i=inp: i.setEchoMode(
                    QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
                )
            )
            row.addWidget(eye)
            row.setProperty("field_input", True)
            # 用一个容器持有取值控件引用
            holder = QWidget()
            holder.setLayout(row)
            holder.setProperty("value_widget", inp)
            return holder

        if ftype == FIELD_TEXTAREA:
            inp = QTextEdit()
            inp.setObjectName("textArea")
            inp.setPlaceholderText(fdef.get("placeholder") or "")
            inp.setMaximumHeight(70)
            inp.setPlainText(value)
            return inp

        if ftype == FIELD_DATE:
            inp = QDateEdit()
            inp.setObjectName("inputField")
            inp.setCalendarPopup(True)
            inp.setDisplayFormat("yyyy-MM-dd")
            inp.setSpecialValueText("  不设置")
            inp.setMinimumDate(QDate(2000, 1, 1))
            if value:
                try:
                    y, m, d = map(int, value.split("-"))
                    inp.setDate(QDate(y, m, d))
                except (ValueError, TypeError):
                    inp.setDate(QDate(2000, 1, 1))
            else:
                inp.setDate(QDate(2000, 1, 1))
            return inp

        if ftype == FIELD_SELECT:
            inp = QComboBox()
            inp.setObjectName("inputField")
            inp.setCursor(Qt.CursorShape.PointingHandCursor)
            inp.addItem("请选择", "")
            for opt in fdef.get("options", []):
                inp.addItem(opt, opt)
            if value:
                idx = inp.findData(value)
                if idx >= 0:
                    inp.setCurrentIndex(idx)
            return inp

        if ftype == FIELD_NUMBER:
            inp = QSpinBox()
            inp.setObjectName("inputField")
            inp.setRange(0, 999999)
            try:
                inp.setValue(int(value) if value else 0)
            except ValueError:
                inp.setValue(0)
            return inp

        if ftype == FIELD_FILE:
            row = QHBoxLayout()
            row.setSpacing(8)
            inp = QLineEdit()
            inp.setObjectName("inputField")
            inp.setReadOnly(True)
            inp.setPlaceholderText("点击浏览选择文件...")
            inp.setText(value)
            row.addWidget(inp)
            browse = QPushButton("📂 浏览")
            browse.setObjectName("btnSecondary")
            browse.setCursor(Qt.CursorShape.PointingHandCursor)
            browse.clicked.connect(lambda: self._browse_file(inp))
            row.addWidget(browse)
            holder = QWidget()
            holder.setLayout(row)
            holder.setProperty("value_widget", inp)
            return holder

        # 默认：单行文本
        inp = QLineEdit()
        inp.setObjectName("inputField")
        inp.setPlaceholderText(fdef.get("placeholder") or "")
        inp.setText(value)
        return inp

    def _browse_file(self, inp):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "选择文件")
        if path:
            inp.setText(path)

    def _field_value(self, fdef, widget) -> str:
        """从控件提取字段值（空值返回空串）"""
        # 文件/密码行是容器，真正的输入控件挂在属性上
        val_widget = widget.property("value_widget")
        if val_widget is not None:
            widget = val_widget
        ftype = fdef.get("type", FIELD_TEXT)
        if isinstance(widget, QTextEdit):
            return widget.toPlainText().strip()
        if isinstance(widget, QDateEdit):
            d = widget.date()
            return "" if d.year() <= 2000 else d.toString("yyyy-MM-dd")
        if isinstance(widget, QComboBox):
            return widget.currentData() or ""
        if isinstance(widget, QSpinBox):
            v = widget.value()
            return str(v) if v else ""
        return widget.text().strip()

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
        self.note_input.setText(self.asset.note or "")
        self.tags_input.setText(self.asset.tags or "")
        if self.asset.asset_type in LEGACY_TYPES:
            self.email_input.setText(self.asset.email or "")
            if self.asset.expire:
                try:
                    y, m, d = map(int, self.asset.expire.split("-"))
                    self.expire_input.setDate(QDate(y, m, d))
                except (ValueError, TypeError):
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
        # 动态模板字段的回填在 build_dynamic_form 中完成（setup_ui 尾部已触发）

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

        tpl = self.template()
        # 已归档为手动生命周期状态：编辑保存后保留，不被自动计算覆盖
        kept_status = "archived" if (self.asset and self.asset.status == "archived") else "normal"

        if self.current_type in LEGACY_TYPES:
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
                status=kept_status,
                note=self.note_input.toPlainText().strip() or None,
                updated=format_now(),
                tags=self.tags_input.text().strip() or None,
            )
        else:
            # 模板引擎类型：收集动态字段 -> extra，核心列自动镜像
            extra = {}
            for key, (fdef, widget) in self.dynamic_widgets.items():
                val = self._field_value(fdef, widget)
                if fdef.get("required") and not val:
                    QMessageBox.warning(self, "提示", f"{fdef['label']} 不能为空")
                    return
                if val:
                    extra[key] = val
            asset = Asset(
                id=self.asset.id if self.asset else 0,
                asset_type=self.current_type,
                name=self.name_input.text().strip(),
                account=resolve_column(tpl, extra, "account") or "-",
                password=None,
                email=None,
                total=None, used=None, remain=None,
                expire=resolve_column(tpl, extra, "expire") or None,
                url=None,
                status=kept_status,
                note=self.note_input.toPlainText().strip() or None,
                updated=format_now(),
                extra=extra or None,
                tags=self.tags_input.text().strip() or None,
            )
        asset.status = calculate_status(asset, expire_days=tpl.get("expire_days"))
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

    def __init__(self, parent=None, recycle_bin=None, custom_templates=None):
        super().__init__(parent)
        self.recycle_bin = recycle_bin or []
        self.custom_templates = custom_templates or []
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
                tc = get_type_config(asset.asset_type, self.custom_templates)
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


class TemplateManagerDialog(QDialog):
    """设置 - 资产模板管理：查看内置模板，创建/删除自定义模板"""

    changed = pyqtSignal()

    def __init__(self, parent=None, db=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("资产模板管理")
        self.setMinimumSize(640, 560)
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
        title = QLabel("🧩 资产模板管理")
        title.setObjectName("modalTitle")
        hlayout.addWidget(title)
        hlayout.addStretch()
        layout.addWidget(header)

        body = QWidget()
        body.setObjectName("modalBody")
        blayout = QVBoxLayout(body)
        blayout.setContentsMargins(24, 20, 24, 20)
        blayout.setSpacing(14)

        # ---- 内置模板 ----
        blayout.addWidget(self._form_label("内置模板（预置专属字段，不可删除）"))
        from templates import BUILTIN_ORDER, BUILTIN_TEMPLATES
        builtin_text = "    ".join(
            f"{BUILTIN_TEMPLATES[k]['icon']} {BUILTIN_TEMPLATES[k]['label']}"
            for k in BUILTIN_ORDER
        )
        builtin_label = QLabel(builtin_text)
        builtin_label.setStyleSheet("font-size: 13px; color: #475569; padding: 4px 0;")
        builtin_label.setWordWrap(True)
        blayout.addWidget(builtin_label)

        # ---- 自定义模板列表 ----
        blayout.addWidget(self._form_label("自定义模板"))
        self.custom_list = QTableWidget()
        self.custom_list.setColumnCount(4)
        self.custom_list.setHorizontalHeaderLabels(["名称", "字段数", "到期提醒", "操作"])
        self.custom_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.custom_list.verticalHeader().setVisible(False)
        self.custom_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.custom_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.custom_list.setMaximumHeight(130)
        blayout.addWidget(self.custom_list)
        self.refresh_custom_list()

        # ---- 新建自定义模板 ----
        blayout.addWidget(self._form_label("新建自定义模板"))
        name_row = QHBoxLayout()
        name_row.setSpacing(10)
        self.tpl_name = QLineEdit()
        self.tpl_name.setObjectName("inputField")
        self.tpl_name.setPlaceholderText("模板名称，如: 游戏账号")
        name_row.addWidget(self.tpl_name, 2)
        name_row.addWidget(QLabel("到期提醒:"))
        self.tpl_expire_days = QSpinBox()
        self.tpl_expire_days.setObjectName("inputField")
        self.tpl_expire_days.setRange(0, 365)
        self.tpl_expire_days.setValue(30)
        self.tpl_expire_days.setSpecialValueText("不提醒")
        self.tpl_expire_days.setSuffix(" 天")
        name_row.addWidget(self.tpl_expire_days)
        blayout.addLayout(name_row)

        # 字段表
        self.fields_table = QTableWidget()
        self.fields_table.setColumnCount(4)
        self.fields_table.setHorizontalHeaderLabels(["字段名称", "字段类型", "选项(下拉用,逗号分隔)", "必填"])
        self.fields_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.fields_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.fields_table.verticalHeader().setVisible(False)
        blayout.addWidget(self.fields_table)

        field_btns = QHBoxLayout()
        add_field_btn = QPushButton("➕ 添加字段")
        add_field_btn.setObjectName("btnSecondary")
        add_field_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_field_btn.clicked.connect(self.add_field_row)
        field_btns.addWidget(add_field_btn)
        del_field_btn = QPushButton("➖ 删除选中字段")
        del_field_btn.setObjectName("btnSecondary")
        del_field_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_field_btn.clicked.connect(self.remove_field_row)
        field_btns.addWidget(del_field_btn)
        field_btns.addStretch()
        blayout.addLayout(field_btns)
        self.add_field_row()  # 默认一行

        # 底部
        footer = QWidget()
        footer.setObjectName("modalFooter")
        flayout = QHBoxLayout(footer)
        flayout.setContentsMargins(24, 0, 24, 20)
        flayout.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.setObjectName("btnSecondary")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        flayout.addWidget(close_btn)
        save_btn = QPushButton("💾 保存模板")
        save_btn.setObjectName("btnPrimary")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self.save_template)
        flayout.addWidget(save_btn)
        layout.addWidget(body)
        layout.addWidget(footer)

    def _form_label(self, text):
        label = QLabel(text)
        label.setObjectName("formLabel")
        return label

    def refresh_custom_list(self):
        templates = self.db.get_custom_templates() if self.db else []
        self.custom_list.setRowCount(len(templates))
        for i, tpl in enumerate(templates):
            self.custom_list.setItem(i, 0, QTableWidgetItem(f"{tpl.get('icon', '🧩')} {tpl.get('label', '')}"))
            self.custom_list.setItem(i, 1, QTableWidgetItem(str(len(tpl.get("fields", [])))))
            days = tpl.get("expire_days")
            self.custom_list.setItem(i, 2, QTableWidgetItem(f"前 {days} 天" if days else "不提醒"))
            del_btn = QPushButton("🗑️ 删除")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setStyleSheet("color: #ef4444; border: none; background: transparent; font-size: 12px;")
            del_btn.clicked.connect(lambda checked, k=tpl["key"]: self.delete_template(k))
            self.custom_list.setCellWidget(i, 3, del_btn)
        if not templates:
            self.custom_list.setRowCount(1)
            empty = QTableWidgetItem("暂无自定义模板")
            empty.setForeground(QColor("#94a3b8"))
            self.custom_list.setItem(0, 0, empty)

    def add_field_row(self):
        row = self.fields_table.rowCount()
        self.fields_table.insertRow(row)
        self.fields_table.setItem(row, 0, QTableWidgetItem(""))
        combo = QComboBox()
        for ftype, flabel in FIELD_TYPE_LABELS.items():
            combo.addItem(flabel, ftype)
        self.fields_table.setCellWidget(row, 1, combo)
        self.fields_table.setItem(row, 2, QTableWidgetItem(""))
        chk = QCheckBox()
        chk_widget = QWidget()
        chk_layout = QHBoxLayout(chk_widget)
        chk_layout.setContentsMargins(0, 0, 0, 0)
        chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chk_layout.addWidget(chk)
        self.fields_table.setCellWidget(row, 3, chk_widget)

    def remove_field_row(self):
        row = self.fields_table.currentRow()
        if row >= 0:
            self.fields_table.removeRow(row)

    def save_template(self):
        name = self.tpl_name.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入模板名称")
            return
        fields = []
        for row in range(self.fields_table.rowCount()):
            fname_item = self.fields_table.item(row, 0)
            fname = fname_item.text().strip() if fname_item else ""
            if not fname:
                continue
            combo = self.fields_table.cellWidget(row, 1)
            ftype = combo.currentData()
            opts_item = self.fields_table.item(row, 2)
            opts = [o.strip() for o in (opts_item.text() if opts_item else "").split(",") if o.strip()]
            chk_widget = self.fields_table.cellWidget(row, 3)
            chk = chk_widget.findChild(QCheckBox)
            required = chk.isChecked() if chk else False
            if ftype == FIELD_SELECT and not opts:
                QMessageBox.warning(self, "提示", f"字段「{fname}」是下拉选项类型，请填写选项")
                return
            fields.append({
                "key": f"f{len(fields) + 1}",
                "label": fname,
                "type": ftype,
                "required": required,
                "options": opts,
                "placeholder": "",
            })
        if not fields:
            QMessageBox.warning(self, "提示", "请至少添加一个字段")
            return
        days = self.tpl_expire_days.value()
        from templates import make_custom_template
        tpl = make_custom_template(name, fields, expire_days=days if days > 0 else None)
        self.db.add_custom_template(tpl)
        QMessageBox.information(self, "成功", f"模板「{name}」已创建")
        self.tpl_name.clear()
        self.fields_table.setRowCount(0)
        self.add_field_row()
        self.refresh_custom_list()
        self.changed.emit()

    def delete_template(self, key):
        ret = QMessageBox.question(self, "确认", "删除该自定义模板？已有资产数据不受影响")
        if ret == QMessageBox.StandardButton.Yes:
            self.db.delete_custom_template(key)
            self.refresh_custom_list()
            self.changed.emit()
