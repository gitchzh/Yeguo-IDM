#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全局滚动条样式定义

该模块定义了应用程序中所有滚动条的统一样式，
确保滚动条完全贴右边，无右侧空间。

作者: 椰果IDM开发团队
版本: 1.0.0
"""

# 全局滚动条样式 - 完全贴右边，无右侧空间
GLOBAL_SCROLLBAR_STYLE = """
/* 滚动条样式 - 完全贴右边，无右侧空间 */
QScrollBar:vertical {
    background-color: transparent;
    width: 12px;
    border-radius: 0px;
    margin: 0px;
    position: absolute;
    right: 0px;
    top: 0px;
    bottom: 0px;
    border: none;
}

QScrollBar::handle:vertical {
    background-color: #c1c1c1;
    min-height: 20px;
    border-radius: 0px;
    border: none;
    margin: 0px;
    width: 12px;
}

QScrollBar::handle:vertical:hover {
    background-color: #a8a8a8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    background-color: transparent;
    border: none;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background-color: transparent;
    border: none;
}

/* 确保滚动条完全贴右边 */
QScrollBar::right-arrow:vertical, QScrollBar::left-arrow:vertical {
    width: 0px;
    height: 0px;
    background-color: transparent;
    border: none;
}

/* 水平滚动条样式 - 完全贴底部，无底部空间 */
QScrollBar:horizontal {
    background-color: transparent;
    height: 12px;
    border-radius: 0px;
    margin: 0px;
    position: absolute;
    bottom: 0px;
    left: 0px;
    right: 0px;
    border: none;
}

QScrollBar::handle:horizontal {
    background-color: #c1c1c1;
    min-width: 20px;
    border-radius: 0px;
    border: none;
    margin: 0px;
    height: 12px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #a8a8a8;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
    background-color: transparent;
    border: none;
}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background-color: transparent;
    border: none;
}

/* 确保水平滚动条完全贴底部 */
QScrollBar::right-arrow:horizontal, QScrollBar::left-arrow:horizontal {
    width: 0px;
    height: 0px;
    background-color: transparent;
    border: none;
}
"""

# 文本浏览器专用样式（包含滚动条样式）
TEXT_BROWSER_STYLE = f"""
QTextBrowser {{
    background-color: #ffffff;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    padding: 15px 0px 15px 15px;
    font-family: "Microsoft YaHei", sans-serif;
    font-size: 13px;
    line-height: 1.6;
    margin-right: 0px;
    padding-right: 0px;
}}

{GLOBAL_SCROLLBAR_STYLE}
"""

# 文本编辑器专用样式（包含滚动条样式）
TEXT_EDIT_STYLE = f"""
QTextEdit {{
    background-color: #ffffff;
    border: 1px solid #e1e1e1;
    padding: 6px 0px 6px 8px;
    color: #1e1e1e;
    font-family: "Segoe UI", "Microsoft YaHei", "微软雅黑", sans-serif;
    font-size: 13px;
    border-radius: 3px;
    selection-background-color: #0078d4;
    margin-right: 0px;
    padding-right: 0px;
}}

{GLOBAL_SCROLLBAR_STYLE}
"""

# 列表控件专用样式（包含滚动条样式）
LIST_WIDGET_STYLE = f"""
QListWidget {{
    background-color: #ffffff;
    border: 1px solid #e1e1e1;
    border-radius: 3px;
    padding: 4px;
    margin-right: 0px;
    padding-right: 0px;
}}

{GLOBAL_SCROLLBAR_STYLE}
"""

# 树形控件专用样式（包含滚动条样式）
TREE_WIDGET_STYLE = f"""
QTreeWidget {{
    background-color: #ffffff;
    border: 1px solid #e1e1e1;
    border-radius: 3px;
    padding: 0px;
    margin-right: 0px;
    padding-right: 0px;
}}

{GLOBAL_SCROLLBAR_STYLE}
"""

def apply_global_scrollbar_style(widget):
    """
    为指定控件应用全局滚动条样式
    
    Args:
        widget: 要应用样式的控件
    """
    current_style = widget.styleSheet()
    if current_style:
        # 如果已有样式，添加滚动条样式
        widget.setStyleSheet(current_style + "\n" + GLOBAL_SCROLLBAR_STYLE)
    else:
        # 如果没有样式，直接设置滚动条样式
        widget.setStyleSheet(GLOBAL_SCROLLBAR_STYLE)

def get_text_browser_style():
    """获取文本浏览器样式"""
    return TEXT_BROWSER_STYLE

def get_text_edit_style():
    """获取文本编辑器样式"""
    return TEXT_EDIT_STYLE

def get_list_widget_style():
    """获取列表控件样式"""
    return LIST_WIDGET_STYLE

def get_tree_widget_style():
    """获取树形控件样式"""
    return TREE_WIDGET_STYLE
