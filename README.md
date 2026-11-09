# PT Clip Viewer

Pro Tools 导出文本中的片段时间码查看、合并与复制工具。概念：JaminFX。

## Windows

运行 `build_windows.ps1` 生成应用及 Inno Setup 安装包。

## macOS Universal 2

在仓库 Actions 中选择 **Build and test macOS Universal 2**，点击 **Run workflow**。
构建使用官方 universal2 Python，主程序与 Python/Tk 同时包含 Intel x86_64 和 Apple Silicon arm64。
TkDnD 以两个独立原生库按进程架构加载。

工作流会对同一 DMG 在 Intel 与 Apple Silicon 运行器上分别检查架构、签名及启动、中文文件导入和剪贴板。
所有检查通过后，下载 **PT-Clip-Viewer-macOS-Universal2-VERIFIED** 制品中的 DMG。
打开 DMG，将应用拖入 Applications。

也可在 Mac 上执行 `bash build_macos.command`；需要 python.org 提供的 Python 3.12 universal2。

目前采用 ad-hoc 签名，没有 Developer ID 签名和 Apple 公证。
具体最低 macOS 版本、拖拽交互和排版仍需在目标机器上验收。

详细步骤见 [Mac通用版云端打包说明](Mac通用版云端打包说明.txt)。

## 已完成的构建验证

[Universal 2 构建与双架构原生测试](https://github.com/JaminFX/pt_clip_viewer/actions/runs/42579664876) 已全部通过。
同一 DMG 在 macOS 15 的 Intel x86_64 与 Apple Silicon arm64 环境中完成验证。

