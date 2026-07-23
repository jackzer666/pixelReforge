# PixelReforge Pipeline（像素重铸流水线）

[简体中文](README.md) | [English](README.en.md)

> 面向清晰、网格规整像素图重构的批处理流水线。

PixelReforge 是一套面向像素图规整与批量归档的命令行处理流水线。项目基于 [perfect-pixel](https://github.com/theamusing/perfectPixel) 检测并重建像素网格，同时提供内容去重、状态记录、失败隔离和原图归档等批处理能力。

## 功能概览

- 支持 PNG、JPG、JPEG、WEBP 和 BMP 图片；
- 支持目录批处理、单图处理和子目录递归扫描；
- 同时生成原始尺寸像素图与最近邻放大的预览图；
- 根据图片内容和处理参数识别重复任务，避免无效重复处理；
- 成功与失败任务分别归档，单张图片异常不会中断整个批次；
- 以 JSON 持久化处理状态，并以中文输出处理进度和汇总结果；
- 使用项目级虚拟环境和锁文件，确保依赖隔离及环境可复现。

## 环境要求

- Python 3.10 或更高版本；
- [uv](https://docs.astral.sh/uv/)；
- macOS、Linux 或 Windows。

## 快速开始

### 1. 安装项目依赖

进入项目根目录，根据锁文件创建项目级环境：

```bash
uv sync --locked
```

该命令会在项目根目录创建 `.venv/`，并将锁定版本的依赖及当前项目安装到其中。`.venv/` 只服务于当前项目，不会污染全局 Python 环境。

通常无需手动激活虚拟环境，后续命令直接通过 `uv run` 执行即可。如需激活，可根据系统选择相应命令：

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

### 2. 准备输入图片

将待处理图片放入项目根目录下的 `input/`：

```text
input/
├── character.png
└── landscape.webp
```

运行时所需目录会自动创建，因此无需手动建立缺失目录。

### 3. 启动批处理

```bash
uv run pixel-reforge
```

程序将扫描 `input/` 中受支持的图片，并逐张完成网格检测、像素图生成、状态记录和原图归档。

### 4. 查看处理结果

- 生成图片保存在 `output/`；
- 成功处理或确认重复的原图移动到 `processed/`；
- 处理失败的原图移动到 `failed/`；
- 任务状态记录在 `data/process_state.json`。

## 命令使用

### 批量处理指定目录

```bash
uv run pixel-reforge --input-dir ~/Pictures/pixel-input
```

### 处理单张图片

```bash
uv run pixel-reforge --file ~/Pictures/character.png
```

如果单图位于当前工作目录的 `input/` 内，处理后会按结果归档；如果单图来自 `input/` 之外，则只生成输出，不移动原文件。

### 指定输出目录

```bash
uv run pixel-reforge \
  --input-dir ~/Pictures/pixel-input \
  --output-dir ~/Pictures/pixel-output
```

### 递归扫描子目录

```bash
uv run pixel-reforge --recursive
```

递归模式会扫描输入目录的所有子目录；如果输入目录包含项目托管目录，程序会自动排除 `output/`、`processed/`、`failed/` 和 `data/`，避免再次处理生成文件。

### 重新处理失败任务

```bash
uv run pixel-reforge --retry-failed
```

该命令会读取 `failed/` 中的图片。重试成功后，原图将移动到 `processed/`；再次失败的文件会保留在 `failed/`。

### 强制重新处理

```bash
uv run pixel-reforge --force
```

`--force` 会忽略已有成功记录并重新生成结果，适合需要主动刷新输出的场景。

## 命令参数

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `--file PATH` | 只处理一张指定图片 | 无 |
| `--input-dir PATH` | 批量处理指定目录 | `input/` |
| `--output-dir PATH` | 将生成图片写入指定目录 | `output/` |
| `--retry-failed` | 重新处理 `failed/` 中的图片 | 关闭 |
| `--scale INTEGER` | 设置预览图放大倍数，最小值为 2 | `8` |
| `--force` | 忽略已有成功记录并重新处理 | 关闭 |
| `--recursive` | 递归扫描输入目录的子目录 | 关闭 |
| `-h`、`--help` | 显示命令帮助 | — |

`--file`、`--input-dir` 和 `--retry-failed` 是互斥的输入模式，单次运行只能选择其中一种。

## 处理流程

每张图片依次经过以下步骤：

1. 读取图片并计算 SHA-256 内容指纹；
2. 将内容指纹、算法版本及处理参数组合为任务标识；
3. 检查已有成功记录及其输出文件是否仍然完整；
4. 使用 `perfect-pixel` 检测网格并重建规整像素图；
5. 生成原始尺寸结果和最近邻放大的预览图；
6. 原子写入输出文件及 JSON 状态记录；
7. 根据处理结果归档或隔离原图。

只有当任务标识一致、状态为成功且两个输出文件均存在时，已有结果才会被复用。处理参数或核心依赖版本发生变化后，同一输入图片会被视为新任务。

## 输出文件

每张成功处理的图片会生成两个 PNG 文件：

```text
原名_YYYYMMDD_HHMMSS_微秒_1x.png
原名_YYYYMMDD_HHMMSS_微秒_8x.png
```

- `1x` 文件是重建后的原始像素网格；
- `8x` 文件是默认放大 8 倍的预览图，实际倍数由 `--scale` 决定；
- 如果名称发生冲突，程序会自动追加序号，不会覆盖已有文件；
- 两个输出会先写入临时文件，全部成功后再发布为正式结果。

## 项目目录

```text
pixel_reforge/             Python 源码包
pixel_reforge/mcp_adapter/ MCP STDIO 适配层
tests/                     自动化测试
input/                     默认输入目录
output/                    生成结果目录
processed/                 成功或重复原图归档目录
failed/                    失败原图隔离目录
data/process_state.json    处理状态记录
pyproject.toml             项目与直接依赖声明
uv.lock                    完整依赖锁文件
```

状态文件只保存源文件指纹、处理参数、任务状态、错误信息和输出路径，不保存任何图片内容。

## 退出状态

- 全部任务成功或命中已有结果时，命令返回 `0`；
- 任意图片处理失败，或程序发生无法继续的错误时，命令返回 `1`。

因此，PixelReforge 可以直接集成到 Shell 脚本、自动化任务或其他流水线中。

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

## MCP Server

项目提供本地 STDIO MCP 入口：

```bash
PIXEL_REFORGE_ROOT=/path/to/pixelReforge uv run pixel-reforge-mcp
```

MCP Server 只暴露一个写工具 `reforge_image`：

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `source_path` | 相对于项目 `input/` 的图片路径 | 必填 |
| `scale` | 预览图放大倍数，最小值为 2 | `8` |
| `sample_method` | `center` 或 `majority` | `center` |
| `refine_intensity` | 网格修正强度，范围为 0 到 1 | `0.3` |
| `force` | 是否忽略已有成功记录 | `false` |
| `archive_source` | 成功时移入 `processed/`，失败时移入 `failed/` | `true` |

工具只接受 `input/` 内的相对路径，输出继续写入 `output/` 和
`data/process_state.json`。默认按处理结果归档原图；明确设置
`archive_source=false` 时保留原图。

图片处理在单独的工作进程中串行执行，第三方库的普通输出不会污染 STDIO
协议。客户端取消等待不保证终止已经开始的图片处理。

### 全局配置到 Codex

以下配置会注册到当前用户的 Codex 全局配置，而不是仅对一个项目生效。
Codex 的用户级配置文件位于 `~/.codex/config.toml`；可用字段参见
[Codex 配置参考](https://learn.chatgpt.com/docs/config-file/config-reference#configtoml)。

1. 在 PixelReforge 项目根目录同步虚拟环境：

   ```bash
   uv sync --locked
   ```

2. 确认 MCP 命令已经安装：

   ```bash
   test -x .venv/bin/pixel-reforge-mcp \
     && echo "pixel-reforge-mcp is ready"
   ```

3. 将 `<project-root>` 替换为 PixelReforge 项目根目录的绝对路径，然后注册
   STDIO MCP Server：

   ```bash
   codex mcp add pixel_reforge \
     --env PIXEL_REFORGE_ROOT="<project-root>" \
     -- "<project-root>/.venv/bin/pixel-reforge-mcp"
   ```

   例如，项目位于 `/Users/example/pixelReforge` 时，两个
   `<project-root>` 都替换为 `/Users/example/pixelReforge`。如果已经存在同名
   Server，不要重复添加，直接编辑 `~/.codex/config.toml` 中已有的
   `[mcp_servers.pixel_reforge]`。

4. 如需固定工作目录、超时和写操作审批，在
   `~/.codex/config.toml` 中确认该 Server 配置包含以下内容。不要重复创建同名
   TOML 表，应与第 3 步生成的配置合并：

   ```toml
   [mcp_servers.pixel_reforge]
   command = "<project-root>/.venv/bin/pixel-reforge-mcp"
   cwd = "<project-root>"
   enabled = true
   startup_timeout_sec = 20
   tool_timeout_sec = 300
   enabled_tools = ["reforge_image"]
   default_tools_approval_mode = "writes"

   [mcp_servers.pixel_reforge.env]
   PIXEL_REFORGE_ROOT = "<project-root>"
   ```

5. 检查 Codex 读取到的配置：

   ```bash
   codex mcp get pixel_reforge --json
   codex mcp list
   ```

6. 重启 Codex 或新开会话，使 MCP 连接和工具 Schema 重新加载。之后可以要求：

   ```text
   使用 pixel_reforge 处理 input/character.png，放大倍数设为 8，
   完成后告诉我两个输出文件的绝对路径。
   ```

   MCP 实际收到的 `source_path` 应为相对于 `input/` 的
   `character.png`，不能传绝对路径。`archive_source` 默认为 `true`，所以原图
   成功后会移动到 `processed/`；需要保留时应明确传入
   `archive_source=false`。

### 使用流程：生成并重铸像素图

完成全局配置并重启 Codex 后，可以用一段提示词串联图片生成、MCP 处理和
结果路径回传。将 `<project-root>` 替换为 PixelReforge 项目根目录的绝对路径，
并按需修改图片主题：

```text
请直接完成下面的任务，不要只给我操作步骤：

1. 生成一张像素图，主题为“夜晚森林中的发光蘑菇小屋”。
   图片要求：
   - PNG 格式；
   - 512×512 像素；
   - 清晰、严格对齐的像素网格；
   - 使用有限色板和平涂色块；
   - 不使用抗锯齿、模糊、渐变或细碎纹理；
   - 视觉上接近 32×32 的逻辑像素画，每个逻辑像素大小一致。

2. 将生成的图片实际保存到：
   <project-root>/input/codex_generated_pixel_art.png

3. 确认文件存在后，必须调用 pixel_reforge MCP Server 的 reforge_image
   工具处理它。不要调用 pixel-reforge CLI，也不要自行模拟处理结果。

   MCP 工具参数使用：
   {
     "source_path": "codex_generated_pixel_art.png",
     "scale": 8,
     "sample_method": "center",
     "refine_intensity": 0.3,
     "force": true,
     "archive_source": true
   }

   source_path 是相对于 input/ 的路径，所以不要传
   "input/codex_generated_pixel_art.png" 或绝对路径。

4. 等 MCP 工具执行完成后，读取工具实际返回的 status、outputs 和 error。

5. 最终明确告诉我：
   - 处理状态；
   - 生成图片最初保存的绝对路径；
   - 1x 重铸结果的绝对路径；
   - 8x 预览图的绝对路径；
   - 原图是否已经移动到 processed/。

不要根据文件命名规则猜测输出路径，必须使用 reforge_image 工具实际返回的
outputs。若处理失败，请返回真实错误，不要声称已经成功。
```

执行过程中，Codex 应请求调用 `reforge_image` 写工具；确认审批后，默认会将
成功原图移入 `processed/`，两个结果文件保留在 `output/`。

如果当前 Codex 界面的图片生成功能无法在同一轮继续调用 MCP，可以拆成两轮。
第一轮先生成并保存图片：

```text
生成一张严格网格对齐、无抗锯齿、有限色板的像素图，主题为
“夜晚森林中的发光蘑菇小屋”。

将图片实际保存为：
<project-root>/input/codex_generated_pixel_art.png

必须保存为本地 PNG 文件，不要只在对话中展示图片。
```

第二轮再调用 MCP：

```text
请使用 pixel_reforge MCP Server 的 reforge_image 工具处理刚才生成的图片。

调用参数：
{
  "source_path": "codex_generated_pixel_art.png",
  "scale": 8,
  "sample_method": "center",
  "refine_intensity": 0.3,
  "force": true,
  "archive_source": true
}

不要调用 CLI。完成后读取 MCP 实际返回的 outputs，告诉我处理状态、1x 输出和
8x 预览图的绝对路径。不要自行推测路径；如果失败，返回真实错误。
```
