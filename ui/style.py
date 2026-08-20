"""QSS 样式系统 - 精确还原设计稿"""

MAIN_STYLE = """
/* ===== 全局 ===== */
QWidget {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans SC', sans-serif;
    font-size: 13px;
    color: #1e293b;
}

QMainWindow {
    background: #f8fafc;
}

QScrollArea {
    border: none;
    background: transparent;
}

QScrollBar:vertical {
    background: transparent;
    width: 6px;
    border-radius: 3px;
}

QScrollBar::handle:vertical {
    background: #cbd5e1;
    border-radius: 3px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* ===== 顶部标题栏 ===== */
#headerWidget {
    background: #ffffff;
    border-bottom: 1px solid #e2e8f0;
    padding: 0 32px;
    min-height: 52px;
    max-height: 52px;
}

#headerLogo {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #6366f1, stop:1 #8b5cf6);
    border-radius: 8px;
    color: white;
    font-size: 16px;
    min-width: 30px;
    max-width: 30px;
    min-height: 30px;
    max-height: 30px;
}

#headerTitle {
    font-size: 16px;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: -0.3px;
}

#headerBadge {
    background: #f1f5f9;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
    color: #64748b;
}

/* ===== 左侧边栏 ===== */
#sidebarWidget {
    background: #ffffff;
    border-right: 1px solid #e2e8f0;
    min-width: 240px;
    max-width: 240px;
}

#sidebarFilterWidget {
    background: transparent;
}

#sidebarSectionTitle {
    font-size: 11px;
    font-weight: 700;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    padding: 20px 16px 8px 16px;
}

#sidebarBtn {
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 8px 12px;
    margin: 0 12px;
    text-align: left;
    font-size: 13px;
    color: #475569;
    font-weight: 500;
}

#sidebarBtn:hover {
    background: #f8fafc;
}

#sidebarBtn:checked, #sidebarBtn:active {
    background: #f1f5f9;
    color: #0f172a;
    font-weight: 600;
}

#sidebarBtnActive {
    background: #f1f5f9;
    color: #0f172a;
    font-weight: 600;
    border: none;
    border-radius: 8px;
    padding: 8px 12px;
    margin: 0 12px;
    text-align: left;
    font-size: 13px;
}

#sidebarBtnActiveType {
    background: #f1f5f9;
    color: #0f172a;
    font-weight: 600;
    border: none;
    border-radius: 8px;
    padding: 8px 12px;
    margin: 0 12px;
    text-align: left;
    font-size: 13px;
}

#sidebarBtnActiveStatus {
    background: #eef2ff;
    color: #4338ca;
    font-weight: 600;
    border: none;
    border-radius: 8px;
    padding: 8px 12px;
    margin: 0 12px;
    text-align: left;
    font-size: 13px;
}

#sidebarCount {
    font-size: 11px;
    color: #64748b;
    background: #f1f5f9;
    border-radius: 10px;
    padding: 1px 7px;
    font-weight: 600;
}

#sidebarCountActive {
    font-size: 11px;
    color: #4338ca;
    background: #dbeafe;
    border-radius: 10px;
    padding: 1px 7px;
    font-weight: 600;
}

/* ===== 按钮 ===== */
#btnPrimary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #6366f1, stop:1 #8b5cf6);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
    font-family: inherit;
}

#btnPrimary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #4f46e5, stop:1 #7c3aed);
}

#btnSecondary {
    background: #ffffff;
    color: #475569;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px;
    font-weight: 500;
    font-family: inherit;
}

#btnSecondary:hover {
    background: #f8fafc;
    border-color: #cbd5e1;
}

#btnDanger {
    background: #fef2f2;
    color: #ef4444;
    border: 1px solid #fee2e2;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 500;
    font-family: inherit;
}

#btnDanger:hover {
    background: #fee2e2;
}

#btnWarning {
    background: #fffbeb;
    color: #d97706;
    border: 1px solid #fef3c7;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 500;
    font-family: inherit;
}

#btnWarning:hover {
    background: #fef3c7;
}

#btnSmall {
    background: #ffffff;
    color: #475569;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 500;
    font-family: inherit;
}

#btnSmall:hover {
    background: #f8fafc;
}

/* ===== 输入框 ===== */
#inputField {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 9px 12px;
    font-size: 14px;
    color: #334155;
    font-family: inherit;
    selection-background-color: #6366f1;
}

#inputField:focus {
    border-color: #6366f1;
}

#inputField:read-only {
    background: #f8fafc;
    color: #94a3b8;
    font-weight: 600;
}

#searchInput {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 7px 12px 7px 32px;
    font-size: 13px;
    color: #334155;
    font-family: inherit;
    min-width: 240px;
}

#searchInput:focus {
    border-color: #6366f1;
}

#textArea {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 9px 12px;
    font-size: 14px;
    color: #334155;
    font-family: inherit;
    selection-background-color: #6366f1;
}

#textArea:focus {
    border-color: #6366f1;
}

/* ===== 表格 ===== */
#dataTable {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    gridline-color: #f1f5f9;
    font-size: 13px;
    selection-background-color: #eef2ff;
    selection-color: #1e293b;
}

#dataTable::item {
    padding: 12px 16px;
    border-bottom: 1px solid #f1f5f9;
    color: #475569;
}

#dataTable::item:selected {
    background: #eef2ff;
    color: #1e293b;
}

#dataTable QHeaderView::section {
    background: #f8fafc;
    color: #475569;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.3px;
    padding: 12px 16px;
    border: none;
    border-bottom: 1px solid #e2e8f0;
}

#dataTable QHeaderView::section:hover {
    background: #f1f5f9;
}

/* ===== 统计卡片 ===== */
#statCard {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 16px;
}

#statCardTopline {
    background: transparent;
    border-radius: 10px 10px 0 0;
    min-height: 3px;
    max-height: 3px;
}

#statCardValue {
    font-size: 28px;
    font-weight: 700;
    line-height: 1;
}

#statCardLabel {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

#statCardSublabel {
    font-size: 11px;
    color: #94a3b8;
    margin-top: 4px;
}

/* ===== 模块统计卡片 ===== */
#moduleStatCard {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 16px 20px;
}

#moduleStatIcon {
    border-radius: 10px;
    min-width: 40px;
    max-width: 40px;
    min-height: 40px;
    max-height: 40px;
    font-size: 18px;
}

#moduleStatLabel {
    font-size: 12px;
    color: #64748b;
    font-weight: 500;
    margin-bottom: 2px;
}

#moduleStatValue {
    font-size: 20px;
    font-weight: 700;
    color: #0f172a;
    line-height: 1;
}

#moduleStatUnit {
    font-size: 12px;
    color: #94a3b8;
    font-weight: 500;
}

/* ===== 弹窗 ===== */
#modalOverlay {
    background: rgba(15, 23, 42, 180);
}

#modalBox {
    background: #ffffff;
    border-radius: 12px;
}

#modalHeader {
    border-bottom: 1px solid #f1f5f9;
    padding: 20px 24px;
}

#modalTitle {
    font-size: 16px;
    font-weight: 700;
    color: #0f172a;
}

#modalBody {
    padding: 24px;
}

#modalFooter {
    padding: 0 24px 24px 24px;
}

/* ===== 类型选择按钮 ===== */
#typeSelectorBtn {
    background: #ffffff;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    padding: 10px;
    font-size: 13px;
    color: #475569;
    font-weight: 500;
    font-family: inherit;
}

#typeSelectorBtn:hover {
    background: #f8fafc;
}

#typeSelectorBtnActive {
    background: #eef2ff;
    border: 2px solid #6366f1;
    border-radius: 8px;
    padding: 10px;
    font-size: 13px;
    color: #4338ca;
    font-weight: 600;
    font-family: inherit;
}

/* ===== 密码强度条 ===== */
#strengthTrack {
    background: #e2e8f0;
    border-radius: 2px;
    min-height: 4px;
    max-height: 4px;
}

#strengthFill {
    border-radius: 2px;
    min-height: 4px;
    max-height: 4px;
}

/* ===== 标签 ===== */
#statusTag {
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 600;
}

#typeTag {
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 600;
}

/* ===== 复选框 ===== */
QCheckBox {
    spacing: 4px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #e2e8f0;
    background: #ffffff;
}

QCheckBox::indicator:checked {
    background: #6366f1;
    border-color: #6366f1;
}

QCheckBox::indicator:hover {
    border-color: #6366f1;
}

/* ===== 下拉菜单 ===== */
#dropdownMenu {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 4px;
}

#dropdownItem {
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 13px;
    color: #475569;
    font-weight: 500;
    text-align: left;
    font-family: inherit;
}

#dropdownItem:hover {
    background: #f8fafc;
}

/* ===== Toast ===== */
#toast {
    background: #0f172a;
    color: white;
    border-radius: 10px;
    padding: 12px 20px;
    font-size: 13px;
    font-weight: 500;
}

/* ===== 空状态 ===== */
#emptyIcon {
    background: #f1f5f9;
    border-radius: 16px;
    min-width: 64px;
    max-width: 64px;
    min-height: 64px;
    max-height: 64px;
    font-size: 28px;
}

#emptyTitle {
    font-size: 16px;
    font-weight: 600;
    color: #475569;
}

#emptyDesc {
    font-size: 13px;
    color: #94a3b8;
}

/* ===== 分割线 ===== */
#divider {
    background: #f1f5f9;
    min-width: 1px;
    max-width: 1px;
    min-height: 40px;
    max-height: 40px;
}

/* ===== 表单标签 ===== */
#formLabel {
    font-size: 13px;
    font-weight: 600;
    color: #475569;
    margin-bottom: 6px;
}

#formRequired {
    color: #ef4444;
}
"""
