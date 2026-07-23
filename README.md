# PixelReforge Pipeline（像素重铸流水线）

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-STDIO-6A5ACD.svg)](docs/mcp.md)
[![uv](https://img.shields.io/badge/package%20manager-uv-DE5FE9.svg)](https://docs.astral.sh/uv/)

[简体中文](README.md) | [English](README.en.md)

> 面向 AI 生成像素画规整与重构的 CLI 与 MCP 批处理流水线。

PixelReforge 用于规整、重构和批量归档 AI 生成的像素画。它基于 [perfect-pixel](https://github.com/theamusing/perfectPixel) 检测并重建逻辑像素网格，同时支持命令行和本地 STDIO MCP，可由 Codex 等兼容客户端直接调用。

## 为什么需要 PixelReforge

AI 生成的图片即使视觉上具有像素画风格，也可能存在：

- 逻辑像素块大小不一致，网格或边界发生偏移；
- 抗锯齿、插值和压缩噪点造成边缘模糊或近似色；
- 输出尺寸与实际逻辑像素网格不匹配；
- 批量素材缺少统一的去重、状态追踪和归档流程。

PixelReforge 可以重新检测网格并按单元格取色，输出规整的 `1x` 像素图和最近邻放大预览图，便于继续编辑、检查与交付。

## 功能概览

- 支持 PNG、JPG、JPEG、WEBP 和 BMP；
- 支持单图、目录批处理和递归扫描；
- 提供 `detect` 自动网格检测和 `source` 原生像素两种模式；
- 同时生成 `1x` 像素图与最近邻放大预览图；
- 根据图片内容、算法版本和参数识别重复任务；
- 持久化处理状态，分别归档成功与失败原图；
- 提供本地 STDIO MCP Server 和 `reforge_image` 工具。

## 快速开始

环境要求：Python 3.10+ 和 [uv](https://docs.astral.sh/uv/)。

```bash
# 安装锁定依赖
uv sync --locked

# 将图片放入 input/ 后启动批处理
uv run pixel-reforge
```

处理结果：

- `output/`：`1x` 结果和放大预览；
- `processed/`：成功或已处理的原图；
- `failed/`：处理失败的原图；
- `data/process_state.json`：任务状态。

更多命令、参数和输出约定请参阅 [CLI 使用指南](docs/cli.md)。

## 像素模式

| 模式 | 行为 | 适用场景 |
| --- | --- | --- |
| `detect` | 自动检测逻辑像素网格并按单元格重新取色 | AI 生成、放大、轻微模糊或网格不规整的像素画 |
| `source` | 将每个输入像素直接作为一个 `1×1` 逻辑像素 | 已经是原生像素尺寸的图片 |

```bash
uv run pixel-reforge --pixel-mode detect
uv run pixel-reforge --pixel-mode source
```

## MCP 快速入口

启动本地 STDIO MCP Server：

```bash
PIXEL_REFORGE_ROOT=/path/to/pixelReforge uv run pixel-reforge-mcp
```

MCP Server 暴露 `reforge_image` 写工具，可让 Codex、Claude Code 等客户端处理 `input/` 中的图片，并返回真实处理状态和输出路径。

完整参数、Codex 与 Claude Code 全局配置，以及 AI 生成到像素重铸的提示词示例，请参阅 [MCP、Codex 与 Claude Code 集成指南](docs/mcp.md)。

## 文档

| 文档 | 内容 |
| --- | --- |
| [CLI 使用指南](docs/cli.md) | 安装、常用命令、完整参数、处理流程和输出约定 |
| [MCP、Codex 与 Claude Code 集成](docs/mcp.md) | MCP 工具参数、客户端版本、全局配置和调用示例 |
| [开发指南](docs/development.md) | 项目结构、测试和依赖管理 |
