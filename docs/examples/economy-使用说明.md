# 商人与集市使用说明

> **示例片段（2026-11-08 整理）**：「玄陆」是旧示例世界名，当前仓库没有这个故事包。合并进自己的包之后才会生效。见 [../现状.md](../现状.md)。

这是**示例**，不会自动启用，也不会改动现有故事包。合并进自己的故事包后，新旅程才会出现「集市与商人」卡片。

## 接入步骤

1. 打开 `docs/examples/economy-demo.story-fragment.json`。
2. 把 `mechanics.rewards` 与 `mechanics.economy` 两块合并进你 `story` 的 `mechanics`（已有 `rewards` 时，只需追加 `pence` 货币和商人账户）。
3. 把 `_需要的地点与物品` 里的地点、物品补进 `story.locations` / `story.items`；商人的 `location` 必须是已有地点，`account` 必须是 rewards 里的账户，`currency` 必须是 rewards 里的货币。
4. 保存新版本，新建旅程。玩家走到商人所在地点即可在「集市与商人」卡片里买、卖、讨价还价、以物易物。

## 说明

- 示例经济形态由世界设定的科技档位推断；要固定形态，在 `economy` 里加 `"regime": "feudal"`（或 `early_capitalism` / `market`）。
- 讨价还价需要 `mechanics.checks`（version 2）已开启。没开时其余交易照常。
- 价格怎么算、讨价还价档位、限制：见 `docs/economy-design.md`。
- 没有声明 `merchants` 时，引擎行为与旧版完全一致。
