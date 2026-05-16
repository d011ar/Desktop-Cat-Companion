# Desktop Cat Companion 中文说明

Desktop Cat Companion 是一个用 Python 和 PySide6 构建的小型桌面宠物和轻量 Agent。它会以透明、置顶窗口的形式显示在桌面上，可以拖拽、切换动作和颜色，也可以通过 OpenAI-compatible API 聊天，并提供本地记忆、提醒、待办和低频主动关怀能力。

英文文档：[README.md](README.md)

## 功能特性

- 透明、置顶的桌面宠物窗口
- 可拖拽的小猫窗口和右侧气泡控制面板
- 内嵌聊天面板，可选接入 OpenAI-compatible LLM
- 基于 LLM 的结构化意图识别，用于提醒、待办和记忆
- 本地记忆：偏好、昵称、备注和上次窗口位置
- 本地提醒和待办，使用 JSON 保存
- `Tasks` 标签页：查看、完成、删除和清空任务
- 提醒到期时，小猫会在气泡里提示
- 长时间未互动时，小猫会低频主动关怀
- 动作控制：吃东西、侧向走路、睡觉、向下走、向上走、自动循环
- 颜色控制：白色、黄色、棕色、黑色
- 使用 `assets/cat.png` sprite sheet 进行动画
- 未配置 API key 或缺少 OpenAI 包时，使用安全 fallback 回复

## 快速开始

创建 Conda 环境：

```powershell
conda env create -f environment.yml
```

激活环境：

```powershell
conda activate desktop-cat
```

启动应用：

```powershell
python main.py
```

## 可选：LLM 配置

应用不配置 API key 也可以运行，但自然语言意图识别在配置 OpenAI-compatible 模型后效果最好。没有模型时，应用会保留安全的英文 fallback 回复和简单本地行为。

从示例创建本地 `.env`：

```powershell
copy .env.example .env
```

然后编辑 `.env`：

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

请不要提交 `.env`。仓库的 `.gitignore` 会忽略 `.env` 和 `.env.*`，但保留 `.env.example`。

## Agent 示例

- `remind me in 10 seconds to drink water`
- `tomorrow 10am remind me to call mom`
- `add a todo to buy cat food`
- `remember that I prefer the black cat`
- `what tasks do I have?`
- 配置 LLM 后，也支持其他语言的自然请求。

Agent 会让 LLM 私下分析用户消息，并返回使用英文内部字段的严格 JSON。Python 代码只执行经过校验的本地动作，而用户可见回复由 LLM 按用户使用的语言生成。隐藏推理过程不会显示或保存。

## 操作方式

- 使用 `Chat` 标签页和小猫聊天，也可以创建记忆、提醒或待办。
- 使用 `Tasks` 标签页查看提醒和待办。
- 使用 `Actions` 标签页选择固定动作或 `Auto Cycle`。
- 使用 `Colors` 标签页切换白色、黄色、棕色、黑色小猫。
- 双击小猫可以显示或隐藏气泡面板。
- 右键小猫可快速操作：
  - `Hide Bubble` / `Show Bubble`
  - `Pause Movement` / `Resume Movement`
  - `Show Tasks`
  - `Clear Completed`
  - `Exit`
- 按住鼠标左键拖动小猫或气泡，可以移动整个桌宠。

## 本地数据和隐私

Agent 数据保存在项目内 `data/` 目录：

```text
data/memory.json
data/reminders.json
```

该目录已被 Git 忽略。应用不会执行任意系统命令，不会读取用户文件，不会控制电脑，也不会把提醒或待办同步到外部服务。如果配置了 API key，聊天消息、记忆上下文和 Agent 解析请求可能会发送到你配置的 OpenAI-compatible 模型服务商。

## 项目结构

```text
Desktop_Cat_Companion/
  assets/
    cat.png              # 可选 LPC 小猫sprite sheet 
  data/                  # 本地 Agent 数据，已被 Git 忽略
  .env.example           # 安全示例配置，不包含真实密钥
  agent_core.py          # 本地动作执行和 Agent 编排
  memory_store.py        # 本地 JSON 记忆存储
  reminder_store.py      # 本地 JSON 提醒和待办
  tasks_panel.py         # Tasks 标签页 UI
  chat_window.py         # 内嵌聊天面板和后台线程
  pet_window.py          # 桌宠窗口、动画、定时器和控制
  llm_client.py          # OpenAI-compatible 聊天和结构化解析客户端
  main.py                # 应用入口
  environment.yml        # Conda 环境定义
```

## 小猫素材

这个项目可以在没有图片素材时运行，但预期桌宠使用来自 OpenGameArt 的 LPC 小猫sprite sheet：

- 页面：https://opengameart.org/content/lpc-cats-and-dogs
- 文件：`cat.png`
- 放置位置：`assets/cat.png`

版权/署名声明:

```text
"[LPC] Cats and Dogs" Artist: bluecarrot16 License: CC-BY 3.0 / GPL 3.0 / GPL 2.0 / OGA-BY 3.0 Please link to opengameart: http://opengameart.org/content/lpc-cats-and-dogs
```

第三方素材署名和许可证信息详见 [ATTRIBUTION.md](ATTRIBUTION.md)。

## 发布到 GitHub 前的安全提醒

- 不要提交 `.env`。
- 不要提交 `data/`。
- 不要提交真实 API key、token、cookie 或账号标识。
- 仓库中只保留 `.env.example` 作为安全示例。
