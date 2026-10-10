# 建筑节日海报设计 Skill

一个用于制作节日与节气建筑海报的 Codex Skill。给它项目建筑照片、节日名称和你有权使用的透明 Logo，它会参考节日文化元素，默认规划三套不同配色与英文主标题排版的波普艺术方案。附带的离线脚本可生成 PNG 草案和同名 JSON 质检记录；完成设计仍需人工检查和调整。

## 仓库内容

- `SKILL.md`：设计流程、配色与交付要求。
- `scripts/poster.py`：用 Pillow 渲染海报草案并写出检查信息。
- `requirements.txt`：脚本依赖。
- `INSTALL-macOS.md`：macOS 安装与测试。
- `examples/`：六张已移除品牌 Logo 的冬至、劳动节海报示例。

仓库**不包含品牌 Logo 或源建筑照片**。使用者通过 `--logo` 提供自己有权使用的透明 PNG，通过 `--base` 提供建筑照片。MIT 许可适用于仓库中的代码和文字；示例海报仅用于展示设计效果，不包含在 MIT 许可范围内。请自行确认建筑图像等素材的使用权。

## 示例海报

以下六张来自实际设计方案，均已移除右下角的品牌 Logo。点击图片可查看原尺寸。

| 冬至 A · 霓虹 | 冬至 B · 花彩 | 冬至 C · 经典 |
| --- | --- | --- |
| [![冬至海报 A](examples/winter-solstice-01.png)](examples/winter-solstice-01.png) | [![冬至海报 B](examples/winter-solstice-02.png)](examples/winter-solstice-02.png) | [![冬至海报 C](examples/winter-solstice-03.png)](examples/winter-solstice-03.png) |

| 劳动节 A | 劳动节 B | 劳动节 C |
| --- | --- | --- |
| [![劳动节海报 A](examples/labor-day-a.png)](examples/labor-day-a.png) | [![劳动节海报 B](examples/labor-day-b.png)](examples/labor-day-b.png) | [![劳动节海报 C](examples/labor-day-c.png)](examples/labor-day-c.png) |

## 安装为 Codex Skill

从本仓库的 **Code → Download ZIP** 下载，解压后将文件夹命名为 `company-poster-designer`，放入个人技能目录：

- macOS / Linux：`~/.agents/skills/company-poster-designer/`
- Windows：`%USERPROFILE%\.agents\skills\company-poster-designer\`

确认该目录下直接有 `SKILL.md`。重新打开 Codex 会话后，提及 `company-poster-designer` 即可使用。Codex 也可从 GitHub 仓库安装 Skill：告诉 Skill Installer 这个仓库的地址。

## 运行脚本

需要 Python 3.10 或更新版本。先安装依赖：

```bash
python -m pip install -r requirements.txt
python scripts/poster.py --self-test
```

然后生成三套草案：

```bash
python scripts/poster.py --base path/to/building.jpg --festival 冬至 --logo path/to/your-logo.png --output path/to/poster.png
```

默认输出 `poster-01.png`、`poster-02.png`、`poster-03.png`，以及同名 JSON。已有三张不同配色的无字建筑插画时，可加 `--illustrations art-a.png art-b.png art-c.png --palette-ids 2 5 6`；只生成一张时加 `--count 1`。完整选项见 `python scripts/poster.py --help`。

这个脚本提供可迭代的草案。最终成品需要逐张检查建筑辨识度、节日符号、标题可读性、Logo 对比度和使用权限。

## 许可

代码与文档按 [MIT License](LICENSE) 发布；`examples/` 中的展示图不在该许可范围内。请自行确认输入照片和 Logo 的使用权。
