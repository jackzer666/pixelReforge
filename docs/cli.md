# PixelReforge CLI 使用指南

[返回中文 README](../README.md) | [English](cli.en.md)

本文档介绍 PixelReforge 的安装、命令行参数、处理流程和输出约定。

## 环境要求

- Python 3.10 或更高版本；
- [uv](https://docs.astral.sh/uv/)；
- macOS、Linux 或 Windows。

## 安装

在项目根目录根据锁文件创建环境：

```bash
uv sync --locked
```

该命令会创建项目专用的 `.venv/` 并安装锁定依赖。通常无需手动激活环境，后续命令直接通过 `uv run` 执行。

如需手动激活：

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

## 快速开始

将待处理图片放入项目根目录下的 `input/`：

```text
input/
├── character.png
└── landscape.webp
```

启动默认批处理：

```bash
uv run pixel-reforge
```

运行时所需目录会自动创建。处理完成后：

- 生成图片保存在 `output/`；
- 成功处理或确认重复的原图移动到 `processed/`；
- 处理失败的原图移动到 `failed/`；
- 任务状态记录在 `data/process_state.json`。

## 常用命令

批量处理指定目录：

```bash
uv run pixel-reforge --input-dir ~/Pictures/pixel-input
```

处理单张图片：

```bash
uv run pixel-reforge --file ~/Pictures/character.png
```

如果单图位于当前工作目录的 `input/` 内，处理后会按结果归档；如果来自 `input/` 之外，则只生成输出，不移动原文件。

指定输出目录：

```bash
uv run pixel-reforge \
  --input-dir ~/Pictures/pixel-input \
  --output-dir ~/Pictures/pixel-output
```

递归扫描子目录：

```bash
uv run pixel-reforge --recursive
```

递归模式会自动排除 `output/`、`processed/`、`failed/` 和 `data/`，避免再次处理生成文件。

重新处理 `failed/` 中的任务：

```bash
uv run pixel-reforge --retry-failed
```

忽略已有成功记录并重新生成：

```bash
uv run pixel-reforge --force
```

## 命令参数

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `--file PATH` | 只处理一张指定图片 | 无 |
| `--input-dir PATH` | 批量处理指定目录 | `input/` |
| `--output-dir PATH` | 将生成图片写入指定目录 | `output/` |
| `--retry-failed` | 重新处理 `failed/` 中的图片 | 关闭 |
| `--scale INTEGER` | 设置预览图放大倍数，最小值为 2 | `8` |
| `--pixel-mode {detect,source}` | 自动检测逻辑像素网格，或将每个输入像素按 `1×1` 使用 | `detect` |
| `--force` | 忽略已有成功记录并重新处理 | 关闭 |
| `--recursive` | 递归扫描输入目录的子目录 | 关闭 |
| `-h`、`--help` | 显示命令帮助 | — |

`--file`、`--input-dir` 和 `--retry-failed` 是互斥的输入模式。

### 像素模式

- `detect`：使用 `perfect-pixel` 自动检测并重建逻辑像素网格，适合视觉上像像素画、但网格或颜色不够规整的图片；
- `source`：跳过网格检测，将每个输入像素作为一个 `1×1` 逻辑像素，适合已经是原生像素尺寸的图片。

`source` 模式下，`1x` 输出与输入尺寸相同，预览图宽高分别等于输入宽高乘以 `--scale`。

## 处理流程

每张图片依次经过以下步骤：

1. 读取图片并计算 SHA-256 内容指纹；
2. 将内容指纹、算法版本及处理参数组合为任务标识；
3. 检查已有成功记录及其输出文件是否完整；
4. 按所选像素模式重建或直接使用像素图；
5. 生成 `1x` 结果和最近邻放大预览图；
6. 原子写入输出文件及 JSON 状态记录；
7. 根据处理结果归档或隔离原图。

只有当任务标识一致、状态为成功且两个输出文件均存在时，已有结果才会被复用。处理参数或核心依赖版本变化后，同一输入图片会被视为新任务。

## 输出文件

每张成功处理的图片会生成两个 PNG 文件：

```text
原名_YYYYMMDD_HHMMSS_微秒_1x.png
原名_YYYYMMDD_HHMMSS_微秒_8x.png
```

- `1x` 文件是重建或直接使用的逻辑像素图；
- `8x` 文件是默认放大 8 倍的预览图，实际倍数由 `--scale` 决定；
- 名称冲突时会自动追加序号，不覆盖已有文件；
- 两个输出先写入临时文件，全部成功后再发布。

## 项目运行目录

```text
input/                     默认输入目录
output/                    生成结果目录
processed/                 成功或重复原图归档目录
failed/                    失败原图隔离目录
data/process_state.json    处理状态记录
```

状态文件只保存源文件指纹、处理参数、任务状态、错误信息和输出路径，不保存图片内容。

## 退出状态

- 全部任务成功或命中已有结果时返回 `0`；
- 任意图片处理失败，或程序发生无法继续的错误时返回 `1`。

因此，PixelReforge 可以集成到 Shell 脚本、自动化任务或其他流水线中。
