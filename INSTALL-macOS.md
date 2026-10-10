# macOS 安装与测试

适用于 macOS 12 或更新版本、Python 3.10 或更新版本。这个仓库的根目录就是 Codex Skill。脚本可离线运行，不需要 API 密钥；Codex 的图像生成功能是可选增强。

## 安装

从 GitHub 仓库页面点 **Code → Download ZIP**，解压后将文件夹改名为 `company-poster-designer`，移至 `~/.agents/skills/`。然后运行：

```bash
cd ~/.agents/skills/company-poster-designer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/poster.py --self-test
```

重新打开 Codex 会话后，可说：“用 company-poster-designer，拿这张项目照片和我提供的 Logo 做冬至海报”。

## 直接运行脚本

```bash
python scripts/poster.py --base ~/Desktop/project.jpg --festival 冬至 --logo ~/Desktop/my-logo.png --output ~/Desktop/winter-solstice.png
```

默认输出 `winter-solstice-01.png`、`-02.png`、`-03.png` 三套不同配色和标题排版。指定风格参考图时加 `--style-reference ~/Desktop/style.jpg`。有三张不同配色的无字建筑插画时，用 `--illustrations art-a.png art-b.png art-c.png`；仅有一张插画时可用 `--illustration ~/Desktop/architecture.png` 生成配色草案。只需单张时加 `--count 1`。`--size 1200x1800` 可改变画幅，`--chinese` 与 `--english` 可覆盖标题。

Logo 固定在右下角。请通过 `--logo` 提供你有权使用的透明 PNG；仓库不包含品牌素材。若背景对比不足，应调整插画右下角的留白。

每套输出 PNG 和同名 `.json`。JSON 记录方案编号、配色、排版、标题、Logo 位置、透明通道、对比度与检查提示。`--self-test` 用临时生成的建筑图和测试标记验证三套渲染。

## 字体

脚本依次寻找 macOS 的 PingFang、Hiragino、STHeiti 等中文字体。若当前系统没有这些字体，使用 `--font-chinese /absolute/path/font.ttf` 指定支持中文的字体；也可以用 `--font-english` 指定英文字体。脚本找不到中文字体会停止，避免输出方框字。

## 使用提醒

- 项目照片建议短边至少 1200 像素。
- 发布成品前，请人工复核节日译名、项目外观及品牌使用权限。
- 请使用原始透明 Logo，不要重新绘制、裁断字形或用生成模型仿制。
