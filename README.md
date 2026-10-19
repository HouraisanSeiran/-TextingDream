# TextingDream

项目名：**TextingDream**。原中文名“织梦”和旧英文标识 TextileDream 作为兼容称呼保留。

Python/FastAPI + SQLite 叙事工作台。默认 DeepSeek；可选择离线测试。

当前默认 **DeepSeek V4.1 Flash**（API 请求名 `deepseek-flash`）。API 页面可分别设置对话/创作模型及推理参数；里层支持并发生成背景和道具、按问题检索聊天原文。完整实现范围、测试和限制见 [当前框架状态](框架状态_20260917.md)。

2026-09-18：默认阶段内追加历史，设置可切回最近几轮；模型输入输出面板展示实际缓存命中/未命中和加权汇总。实现范围及24次真实短对话对照见 [短对话缓存优化报告](artifacts/short_cache_20260918_142503/短对话缓存优化报告.md)。

本地资源账本、定时事件、NPC作息、发言知情记录和表达关键词已接入。表层可查看资源时间并零API等待，里层可编辑规则；见 [本地资源日程使用说明](本地资源日程使用说明.md)。

**双击启动织梦.cmd** 自动打开浏览器。使用已验证的 D:\anaconda\python.exe，不依赖 PATH。

详细使用、模块、规则和限制见 [工程说明.md](工程说明.md)。左侧提供表层对话、里层创作、世界创作、地图、API 配置与设置；旅程存档和章节位于表层对话页内。

正式运行数据保存在 data/textiledream.sqlite3。API Key 在网页填写，只保留于当前服务内存。世界包修改会建立新版本，旧旅程保持原版本。

## 启动

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
$env:DEEPSEEK_API_KEY='你的 key'
.venv\Scripts\uvicorn app.main:app --reload
```

浏览器打开 `http://127.0.0.1:8000`。

## 测试

15 个测试文件用标准库 `unittest` 编写，全部离线运行（不需要 API Key；写入临时数据库，不碰 `data/`）。

```powershell
# 方式一：只依赖运行环境，无需额外安装
.venv\Scripts\python -m unittest discover -s tests -t . -v

# 方式二：pytest（配置写在 pyproject.toml 的 [tool.pytest.ini_options]）
.venv\Scripts\pip install -e ".[dev]"
.venv\Scripts\python -m pytest
```

`pyproject.toml` 同时提供 ruff 配置；当前只启用 `F`/`E9`（未使用的导入或变量、未定义名字、语法错误），因为业务代码刻意写得紧凑，排版类规则会全面报错：

```powershell
.venv\Scripts\python -m ruff check app tests tools
```

## 内容资源

世界观与世界生成已合并到左侧“世界创作”。支持补充当前世界、一次创建完整世界、分步创作与旧草稿编辑。地图支持图层、定位、拖动缩放和知识点阅读；补充内容另存为故事包后启用。资源来源及限制见 [资源使用说明](资源使用说明.md)。

- `StoryPackage/<故事包>/`：以 `总概.md`、分类知识点文档和 `story.json` 为当前世界资料来源；`world_packages/` 保留早期导入资料。
- `character_packages/`：主角、NPC、性格、状态、信念和生成约束。

故事包通过 `character_package_id` 声明兼容的角色包。运行时由引擎装配两者；同一角色包可以被多个故事包复用。

默认连续对话，累计至少 40 轮后在下一次切换主要场景时分章；设置可切回每个主要场景新建。完整正文保留，模型默认接收最近 6 轮和相关知识。通用语料可以留空，核心叙事规则仍然生效。官方 DeepSeek V4 表层默认开启推理，生成质量仍需验证，不能把模型叙述当成引擎已执行的事实。

跨游戏复用的设计边界见 [Minecraft核心适配设计.md](Minecraft核心适配设计.md)。这是一份设计草案，目前没有实现 Minecraft 模组。
