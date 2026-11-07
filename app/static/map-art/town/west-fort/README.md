# west-fort · 西式（人族）不规则城墙与防御工事

美术样板，**尚未接入游戏**。style = west，race = common。`node build.js` 生成 `sprite.svg` 与 `meta.json`（共 55 个 symbol），`preview.html` 用 file:// 直接打开。

## 文件
- `core.js` 公共画笔与色板（mulberry32 种子）；`geom.js` 通用棱柱墙体（方石立面、墙顶走道、垛口）。
- `spoke.js` 城镇墙辐条与节点；`towers.js` 节点角楼；`bastion.js` 棱堡与三角堡；`castle.js` 城堡幕墙辐条；`moat.js` 护城河辐条；`starfort.js` 小星堡。
- `west-fort.js` 汇总（浏览器 `window.TownArt_westFort`，Node 用 `module.exports`）；`build.js` 生成脚本。
- `preview.html` + `preview.js` / `preview-scenes.js` / `preview-b.js` / `preview-d.js`：图册与场景 a、b、c、d。

## 清单
| id | 占地 | category | facility |
|---|---|---|---|
| west-common-wallspoke-{n,ne,e,se,s,sw,w,nw} | 1×1 | wall | city_wall |
| west-common-wallnode、wallnode-02（小望台） | 1×1 | wall | city_wall |
| west-common-wallnode-pass-{h,v,se,ne}（直通节点，追加） | 1×1 | wall | city_wall |
| west-common-nodetower-round、nodetower-octagon | 1×1 | wall | watchtower |
| west-common-bastion-{8 方向} | 3×3 | fort | watchtower |
| west-common-ravelin-{n,e,s,w} | 2×2 | fort | watchtower |
| west-common-castlespoke-{8 方向} | 1×1 | castle | city_wall |
| west-common-castlenode、castlenode-pass-{h,v,se,ne} | 1×1 | castle | city_wall |
| west-common-starfort-01 | 6×6 | landmark | watchtower |
| west-common-moatspoke-{8 方向} | 1×1 | water | null |
| west-common-moatnode、moatnode-pass-{se,ne,h,v} | 1×1 | water | null |

## 拼接约定
- 同格排序键 = 本格前沿 y + 偏移：n/ne/nw +0.1，节点 +0.2，e/w +0.3，s/se/sw +0.4（第 11 节）；棱堡、三角堡 +0.45；城门叠加件 +0.45。
- 斜辐条只按「本行」裁剪（y 在 -48..0），左右会越出格边最多 17 px，所以 viewBox 左右各留 `pad_x = 24`：`viewBox = [-24, 0, 96, H]`。锚点仍是本格前沿中点；放置时 x = 格左边 + viewBox[0]。
- 墙格只有一对相对辐条时，用 `*-pass-*` 直通节点代替墩子（`spoke.nodeFor(dirs)`、`castle.nodeFor`、`moat.nodeFor`），这样走道不被打断。
- 棱堡以城墙拐点墙格为中心占 3×3，meta `arms` 给出两条幕墙接出方向；占地内的辐条照常画，棱堡盖在上面。
- 护城河是地面层（meta `layer: ground`，anchor 在占地底边），要先于所有墙体画。

## 已知问题
- 棱堡台面盖住了占地内幕墙外侧的一半，喉部只补了一条台阶立面。墙体内侧与棱堡的衔接靠遮挡，近看有一处硬边。
- 护城河在 135° 拐角的节点方块角会略微伸出水带外沿，那里也没有岸线。
- 小星堡内院是平移画法（内院地面 + 北侧内墙面），没有画内院的建筑细节。starfort 的 facility 取最近的 watchtower。
- 城门只引用 west-base 的 gate-h / gate-v，没有为 30 px 厚的城堡幕墙单画城门。
