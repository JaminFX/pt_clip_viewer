# PT Clip Viewer 3.9.10

Pro Tools 导出文本中的片段时间码查看、合并与复制工具。应用 LOGO 保持原始亮蓝版本。

## 使用软件

- `release/`：当前 Windows 安装包、Mac Universal 2 DMG、Mac 使用说明和校验和。
- Windows 便携版：`dist/pt_clip_viewer/pt_clip_viewer.exe`，请保留同目录 `_internal`，不要只复制单个 EXE。
- Mac 安装、在系统设置中允许打开及固定到 Dock / 启动列表：见 [Mac 使用说明](Mac使用说明.html)。
- 审核结论与残余风险：见 [安全审核报告](安全审核/安全审核报告.html)。

## 构建

需要官方 Python 3.14.10 或更高安全修订版；安装包的最终用户不需要安装 Python。

Windows：安装 Inno Setup 6，然后运行 `powershell -ExecutionPolicy Bypass -File .\build_windows.ps1`。

Mac：运行 `bash build_macos.command`。默认使用 `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3.14`。
主程序与 Python/Tk 以 Universal 2 构建。Intel 的 Tk 9 拖拽库已固定在 `vendor/` 并有哈希清单，原始构建源码提交和许可证一并保留。

依赖安装应使用 `requirements-build.lock` 及 `--require-hashes`，不要只按浮动依赖重新解析。
也可在 GitHub Actions 手动运行 **Build and test macOS Universal 2**，下载 VERIFIED 制品。

## 检查

```text
python verify_release.py
python verify_universal.py
python verify_security.py
python ui_validation.py build/ui-preview
```

软件不连接后台服务。Mac 目前仍采用 ad-hoc 签名，尚无 Developer ID 签名或 Apple 公证。
详细版本记录见 [CHANGELOG](CHANGELOG.md)。
