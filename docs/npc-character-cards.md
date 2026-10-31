# NPC 角色卡

入口：左侧「NPC 角色卡」。选择人物后填写，保存为角色包新版本。新旅程使用新版；「查看当前旅程角色与记忆」按该旅程绑定的版本只读展示。没有人物时，先在「里层创作」建立 NPC。

## 卡片内容

每个次要角色可配置 `npc_card`，不配置的旧角色保持兼容。

| 字段 | 用途 |
| --- | --- |
| identity / experiences | 身份职业与经历，决定话题和表达背景 |
| values | 价值立场，不代替玩家选择 |
| goal / pressure | 当前想得到什么、受什么牵制 |
| boundaries / bargaining | 不能接受什么、可以商谈什么 |
| social_context | 阶层、阵营、当地习俗对人物判断的影响 |
| emotion | 初始情绪；旅程中已批准且未过期的情绪优先 |
| failure_response | 失败后的表达与商谈方式，不自行授予线索或奖励 |
| knowledge | 亲身观察、传闻、推测、误解；每条有来源与确信程度 |

文本字段使用 `{ "text": "保住酒馆生意", "visibility": "public" }`。
取消「可用于公开对话」后为 `private`，仅本人视角和作者评估读取。公开叙述模型不会收到这些秘密，因此秘密本身也不会直接驱动公开对白；可另写不泄密的公开压力或底线。例如私密压力为「欠某人的债」，公开底线为「不愿讨论借款人的身份」。

知识示例：

```json
{
  "text": "渡船工拿走了账本",
  "kind": "misunderstanding",
  "source": "根据争执自行猜测",
  "confidence": 0.9,
  "visibility": "private"
}
```

`misunderstanding` 仅作者看到这个标签，人物视角会读成 `interpretation`。卡片中的观察仍是人物的知识记录，不写入世界事实。确信程度不参与原有属性检定。

## 对话与记忆

- 普通对话与短篇裁定都接入公开角色卡；本人视角和角色发展评估接入完整卡片。
- 行动成功和失败继续使用已有检定、分支与后果；卡片只补充角色解释。失败新线索、替代路线、身份限定选项仍需作者在原有事件行动中配置。
- NPC 只自动记住作者声明其目击的、引擎实际执行的行动结果。短篇使用已有 `action.social.success/failure` 观察者；普通行动可声明 `"witnesses": ["bess"]`，人物必须属于事件且实际同地。
- 未被发现的偷窃、玩家的内心文字、模型自行写的故事不会变成目击事实。说话复用已有 `statement` 记录，仅确认听到，不确认内容为真。
- 目击记忆保存在既有 `beliefs`，类型为 `npc_event`，带来源、时间、结果分支。跟随存档持久化、回滚和失败事务；卡片显示最近八条经历。不会自动传播给其他人物。
- 关系与短期情绪沿用 `development`，不新增好感度轴，也不加入内在声音。

## 接口

- `GET /api/inner/npc-cards`：最新角色包的 NPC 卡片。
- `GET /api/inner/npc-cards?session_id=...`：当前旅程版本、关系和记忆。
- `PUT /api/inner/npc-cards/{character_id}`：`{ "revision": "读取时的版本", "card": {...} }`；包已变化时拒绝覆盖，需重新读取。

均使用现有作者访问令牌。组合包导入、导出和角色卡保存共用包校验与版本存储。

验证：`python -m pytest tests/test_npc_cards.py tests/test_short_scenes.py tests/test_context_trim.py`。
浏览器验收：使用临时数据库装入 `tools.playable_scenes.scenes()[0]` 并创建旅程，启动 `tools/serve_for_probe.py`，运行 `node tools/npc_cards_ui_check.cjs`；可用 `NPC_CARD_TEST_URL` 指定测试地址。该脚本会修改测试角色卡，应仅连接验收用服务。
