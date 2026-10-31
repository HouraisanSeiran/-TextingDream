# 河港汛期 · 验收证据

本目录是本机实测的截图与机器可读记录，**不代替**审查方的独立复跑。

## 截图

| 文件 | 视口 | 内容 |
|---|---|---|
| `01-start-profiles-1440x1000.png` | 1440×1000 | 新建旅程弹窗：三个起点（本地居民 / 外来旅人 / 行会学徒），每条带身份、目标、开局已知 |
| `02-journey-1440x1000.png` | 1440×1000 | 起点回执面板 + 行动候选（标签下方是成本 · 时长 · 检定） |
| `03-confirm-cost-1440x1000.png` | 1440×1000 | 「确认这一步」弹窗：成本「可支使的人手 × 1」、时长 1 小时、检定 wisdom · 0.35 |
| `04-after-confirm-1440x1000.png` | 1440×1000 | 确认后事件推进（正文变长，事件结束） |
| `05-intent-1440x1000.png` | 1440×1000 | 自由意图「我想把沙袋压上闸板」→ 引擎明确「不裁定」、不改状态 |
| `06-journey-390x844.png` | 390×844 | 窄屏表层页（无横向溢出，0px） |
| `07-start-profiles-390x844.png` | 390×844 | 窄屏新建旅程弹窗（三个起点同样可读，0px 溢出） |
| `08-ending-and-warnings-1440x1000.png` | 1440×1000 | 已记录的「全失」结局 + 已知预警面板（只有玩家真正确认知道的消息） |
| `09-old-package-dialog-1440x1000.png` | 1440×1000 | 旧包（无 start_profiles / traits / pressure / endings）的新建旅程弹窗：**整个起点区域隐藏**，没有多出任何控件 |
| `10-intent-candidate-1440x1200.png` | 1440×1200 | 自由意图「核账」（作者公开别名）→ 候选只给“能做是什么”：成本/时长/检定，**不包含**成功与失败描述 |
| `11-confirm-no-result-1440x1200.png` | 1440×1200 | 确认弹窗：成本 · 时长 · 完整检定（属性 + 难度），同样的不泄露未发生结果 |
| `12-after-execution-1440x1200.png` | 1440×1200 | 确认执行后：作者侧分支文本正常出现（“账上进的比出的少”），证明隔离没削弱叙事 |

## 机器可读记录

- `browser-evidence.json`：视口、溢出像素、起点列表、行动文本、确认弹窗文本、意图提示、响应条数、`>=400` 响应列表、控制台错误。
- `api-route-ending.json`：API 驾驶到全失结局后，`/api/sessions/{id}` 返回的 `opening` / `warnings` / `ending` 原文。
- `browser-isolation-evidence.json`：候选/确认弹窗的全文、“是否泄露未发生结果”的两项漏检（均应为空），以及执行后出现的是哪一条分支文本。

## 跑法（本机，无网络）

1. 起隔离实例（临时库 + 临时 `StoryPackage` 副本，不碰正式 `data/`）：

   ```
   $env:PYTHONUTF8='1'; $env:REPO_ROOT='D:\codexwork\织梦'
   $env:DEMO_WORKDIR='D:\Vantaloom\data\temp\demo-run'; $env:DEMO_PORT='8899'
   & "D:\anaconda\python.exe" -X utf8 serve_demo.py
   ```

2. 显式启用故事包（`POST /api/inner/packages/河港汛期/activate`，带 bootstrap 拿到的 token）。
3. Playwright 用系统 Edge（`channel='msedge'`）跑 1440×1000 与 390×844 两套视口，启动前把 `provider` 设为 `offline`；
   全部请求都指向 `127.0.0.1`，没有调用任何模型。

## 看到什么、没看到什么

- 两个视口横向溢出均为 0px；没有 `pageerror`。
- 控制台唯一一条错误是浏览器自己请求 `/favicon.ico` 得到 404（仓库没有 favicon，页面也没声明）。
  **这里只记录现象，没有据此改任何东西，也不猜根因。**
- 截图里的事件名、身份、成本、检定都是引擎当前状态的真实回显；没有手工改 DOM 再截图。
- “30–60 分钟可玩”是设计目标，本目录**没有**时长实测数据。
