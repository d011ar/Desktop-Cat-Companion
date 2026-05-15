# Desktop Cat Companion 中文说明

Desktop Cat Companion 是一个用 Python 和 PySide6 实现的桌面小猫和 LLM
聊天陪伴程序。它会以透明、置顶窗口的形式显示在桌面上，可以拖拽移动、
切换动作和颜色，也可以通过 OpenAI-compatible API 和你聊天。

英文文档：[README.md](README.md)

这个项目刻意保持小而清晰，适合作为桌面宠物或聊天陪伴程序的入门模板，
也方便你在此基础上继续二次开发。

说明：当前实现优先面向 Windows 开发和测试。PySide6 本身是跨平台的，所以这套
代码也有机会在 macOS 或 Linux 上运行；但透明窗口、无边框窗口、置顶窗口这些
桌面行为在不同系统和桌面环境上可能表现不同，可能需要做平台适配。

## 功能特性

- 透明、置顶的桌面宠物窗口
- 可拖拽的小猫和右侧气泡控制面板
- 内嵌聊天面板
- 动作控制：吃东西、侧向走路、睡觉、向下走、向上走、自动循环
- 颜色控制：白色、黄色、棕色、黑色
- 使用 `assets/cat.png` 精灵图进行动画裁剪
- 可选接入 OpenAI-compatible 聊天接口
- 未配置 API key 时使用本地 fallback 回复，不会崩溃
- 缺少图片素材时使用代码绘制的占位小猫

## 快速开始

创建 Conda 环境：

```powershell
conda env create -f environment.yml
```

激活环境：

```powershell
conda activate desktop-cat
```

启动程序：

```powershell
python main.py
```

## 可选：配置 LLM 聊天

不配置 API key 也可以运行程序。此时聊天面板会使用本地 fallback 回复。

如果想启用模型聊天，先复制一份本地配置文件：

```powershell
copy .env.example .env
```

然后编辑 `.env`：

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

请不要把 `.env` 提交到 GitHub。仓库里的 `.gitignore` 已经忽略 `.env` 和
`.env.*`，但保留 `.env.example` 作为安全示例。

## 操作方式

- 使用 `Chat` 标签页和小猫聊天。
- 使用 `Actions` 标签页切换固定动作或 `Auto Cycle`。
- 使用 `Colors` 标签页切换白色、黄色、棕色、黑色小猫。
- 双击小猫可以显示或隐藏气泡面板。
- 右键小猫可以快速执行：
  - `Hide Bubble` / `Show Bubble`
  - `Pause Movement` / `Resume Movement`
  - `Exit`
- 按住鼠标左键拖动小猫或气泡，可以移动整个桌宠。

## 项目结构

```text
Desktop_Cat/
  assets/
    cat.png              # 可选 LPC 小猫精灵图
  .env.example           # 安全示例配置，不包含真实密钥
  .gitignore             # 忽略本地密钥、缓存和环境目录
  environment.yml        # Conda 环境定义
  main.py                # 程序入口
  pet_window.py          # 桌宠窗口、精灵图动画、动作和颜色控制
  chat_window.py         # 内嵌聊天面板和后台聊天线程
  llm_client.py          # OpenAI-compatible 客户端和 fallback 回复
```

## 代码说明

### `main.py`

`main.py` 是程序入口。它会加载 `.env` 环境变量，创建 `QApplication`，
构建 `PetWindow`，并启动 Qt 事件循环。

如果你想增加启动日志、单实例检查或平台相关初始化，可以从这里开始。

### `pet_window.py`

`pet_window.py` 是桌面小猫的核心 UI。

主要对象：

- `PetWindow`：透明、置顶的桌宠窗口。
- `CatPose`：小猫动作状态，例如 `WALK_SIDE`、`SLEEP`、`WALK_DOWN`。
- `CatColor`：小猫颜色。
- `AnimationSpec`：描述某个动作使用哪一行、哪几帧、是否移动。
- `POSE_SPECS`：动作到动画帧的映射，是调整动作的核心位置。
- `AUTO_SEQUENCE`：自动循环动作的顺序。

程序会把精灵图当作 `32x32` 的帧网格处理。颜色按每 4 列一组：

- 白色：第 `0-3` 列
- 黄色：第 `4-7` 列
- 棕色：第 `8-11` 列
- 黑色：第 `12-15` 列

如果你想增加动作，通常需要：

1. 在 `CatPose` 中新增动作枚举。
2. 在 `POSE_SPECS` 中配置对应的行号和帧序列。
3. 在 `_build_action_tab()` 中增加一个按钮。

如果你想修改移动逻辑，可以重点查看：

- `_choose_next_target()`
- `_move_tick()`
- `AnimationSpec.moves`

### `chat_window.py`

`chat_window.py` 提供气泡中的聊天面板。

主要对象：

- `ChatPanel`：显示在 `Chat` 标签页里的聊天组件。
- `ChatWorker`：在 `QThread` 中执行 API 请求，避免 UI 卡住。
- `message_started`：用户发送消息时发出。
- `message_finished`：小猫回复完成时发出。

`PetWindow` 会监听这些信号，在聊天时让小猫切换到 `WALK_DOWN` 动作。

### `llm_client.py`

`llm_client.py` 封装 OpenAI-compatible 聊天接口。

它读取：

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_MODEL`

如果没有配置 API key，或者请求失败，它会返回本地 fallback 回复，而不是让程序崩溃。

你可以在这里修改小猫人格、系统提示词、温度、最大 token 数或模型服务商。

## 小猫素材来源

项目可以在没有图片素材时运行，但推荐使用 OpenGameArt 上的 LPC 小猫精灵图：

- 页面：https://opengameart.org/node/69399
- 文件：`cat.png`
- 放置路径：`assets/cat.png`

OpenGameArt 页面说明该素材包含 LPC 风格的猫和狗，提供四方向行走、睡觉、
吃东西，以及四种颜色。

版权/署名声明：

```text
"[LPC] Cats and Dogs" Artist: bluecarrot16 License: CC-BY 3.0 / GPL 3.0 / GPL 2.0 / OGA-BY 3.0 Please link to opengameart: http://opengameart.org/content/lpc-cats-and-dogs
```

如果你要重新分发素材或在其他项目中使用，请先阅读 OpenGameArt 页面和所选许可。

## 二次开发想法

- 增加更多精灵图动作，例如吃东西或更多方向行走。
- 增加心情系统，例如饥饿、困倦、好奇、亲密度。
- 保存用户偏好，例如小猫颜色、上次窗口位置。
- 增加桌面提醒或日程提醒。
- 增加语音输入或语音输出。
- 支持多只桌宠。
- 支持其他动物的自定义精灵图配置。
- 如果你希望把它继续发展成更完整的桌面 Agent，可以增加记忆、工具调用、
  任务规划、提醒等能力。
- 使用 PyInstaller 打包成可执行文件。

## 发布到 GitHub 前的安全提醒

发布前请检查：

- 不要提交 `.env`。
- 不要提交真实 API key、token、cookie 或账号标识。
- 仓库中只保留 `.env.example`。
- 如果有可用工具，可以先做一次本地 secret scan。
- 提交前运行 `git status --short` 检查文件列表。

当前 `.gitignore` 已经忽略 `.env`、`.env.*`、虚拟环境、Python 缓存、构建产物、
日志文件和常见编辑器文件。
