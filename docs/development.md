# PixelReforge 开发指南

[返回中文 README](../README.md) | [English](development.en.md)

## 项目结构

```text
pixel_reforge/             Python 源码包
pixel_reforge/mcp_adapter/ MCP STDIO 适配层
tests/                     自动化测试
pyproject.toml             项目与直接依赖声明
uv.lock                    完整依赖锁文件
```

## 测试

在项目根目录运行完整测试套件：

```bash
uv run python -m unittest discover -s tests -v
```

## 依赖管理

直接依赖声明在 `pyproject.toml`，完整的确定版本及文件校验信息记录在 `uv.lock`。提交项目变更时应提交 `uv.lock`，但不应提交 `.venv/` 或 `*.egg-info/`。

添加依赖：

```bash
uv add PACKAGE_NAME
```

删除依赖：

```bash
uv remove PACKAGE_NAME
```

严格按照现有锁文件同步环境：

```bash
uv sync --locked
```

主动升级依赖并更新锁文件：

```bash
uv lock --upgrade
uv sync
```

## 核心依赖

- [perfect-pixel](https://github.com/theamusing/perfectPixel)：负责像素网格检测与规整化处理；
- [OpenCV](https://opencv.org/)：负责图片读取、色彩空间转换、缩放和输出。
