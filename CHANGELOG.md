# 3.9.8

- 用 Canvas 绘制跨平台深色按钮，解决 macOS 原生 Tk 按钮发白、文字低对比度的问题。
- 统一 Lucide 矢量按钮图标和深蓝/青色声波应用图标；Windows 与 macOS 同步更新。
- 增加悬停、按下、键盘焦点和禁用状态，支持鼠标、Return、空格键操作。
- 修整输入框、表格边框、滚动条与分组按钮布局。
- 增加打包后的按钮状态、撤销/重做、复制和设置弹窗检查，并在 Intel / Apple Silicon 导出界面截图。

此版本仍采用 ad-hoc 签名。消除 macOS Gatekeeper 的未验证开发者提示，需要另外配置 Developer ID 签名与 Apple 公证。
