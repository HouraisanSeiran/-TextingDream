# arab-special：阿拉伯风格（人族）特殊建筑与文化地标

3/4 斜俯视，48 px 网格，细墨线加不透明平涂，色板见 `docs/town-art-spec.md` 第 15 节。素材**尚未接入游戏**。style=`arab`，race=`common`。

## 文件
- `build.js`：运行 `node build.js` 生成 `sprite.svg` 与 `meta.json`，同时检查 id 唯一、内部 id 前缀、上伸与占地上限、facility 合法、facility 为 null 时必须有 note。
- `arab-special.js`：汇总入口。浏览器挂 `window.TownArt_arabSpecial`，Node 用 `module.exports`。接口：`list / symbol / meta / metaAll / sprite / dims`。
- 画笔模块：`core.js`（色板、mulberry32、基础图元、投影）、`parts.js`（尖拱、瓷砖带、八角星、木格窗、雉堞）、`mass.js`（平顶块、内院、鼓座、穹顶）、`towers.js`（宣礼塔、风塔、星形瓷砖）、`ground.js`（净池、水渠、石板缝、椰枣、柏树、花圃）、`facade.js`（拱廊、门楼 pishtaq、木门、窗排、布棚）。
- 建筑定义：`b-religious.js`、`b-trade.js`、`b-civic.js`、`b-craft.js`、`b-infra.js`、`b-landmark.js`。
- `preview.html` 加 `preview.js`：file:// 可直接打开。页面有图册和城镇广场示意（按锚点 y 排序绘制）。sprite 内联在 0×0 绝对定位的容器里。

## 清单（40 个）
特殊建筑 31 个、露天摊位 4 个（prop，tags 含 `open_air`）、文化地标 5 个。完整字段见 `meta.json`。

| id 后缀 | 名称 | 占地 | facility |
|---|---|---|---|
| mosque-01 / 02 | 清真寺（绿松石穹顶 / 双塔钴蓝穹顶） | 4×3 | temple |
| minaret-01 | 宣礼塔单塔 | 1×1 | temple |
| bazaar-01 / 02 | 巴扎（拱顶长廊 / 筒拱有顶街） | 4×2 / 3×2 | market_hall |
| stall-spice/rug/pottery/lamp-01 | 香料、地毯、陶器、铜灯摊 | 1×1 | market_hall |
| caravanserai-01 | 商队客栈 | 4×3 | caravanserai |
| inn-01 | 旅舍茶馆 | 3×2 | inn |
| townhall-01 | 行政厅 | 3×2 | town_hall |
| palace-01 | 宫殿（总督府） | 4×3 | lord_hall |
| madrasa-01 | 学院 | 3×3 | academy |
| bimaristan-01 | 医院 | 3×2 | infirmary |
| hammam-01 | 公共浴室 | 3×2 | cistern |
| abanbar-01 | 蓄水池（穹顶风塔） | 2×2 | cistern |
| well-01 | 水井井亭 | 1×1 | well |
| forge-01 / smelter-01 / kiln-01 | 铁匠铺 / 冶炼炉 / 陶窑 | 2×2 | forge / smelter / kiln |
| tannery-01 | 制革染坊 | 3×2 | tannery |
| granary-01 | 粮仓 | 2×2 | granary |
| stable-01 | 马厩骆驼栏 | 3×2 | stable |
| barracks-01 | 兵营 | 3×2 | barracks |
| watchtower-01 | 瞭望塔 | 1×1 | watchtower |
| warehouse-01 | 货栈 | 3×2 | warehouse |
| noria-01 / windmill-01 | 水车 / 风磨 | 3×2 / 2×2 | mill |
| dock-01 | 码头（dhow） | 3×3 | dock |
| cemetery-01 | 墓园 | 3×2 | cemetery |
| bridge-01 | 石桥 | 4×2 | bridge |
| minehead-01 | 矿井口 | 2×2 | mine_head |
| boilerhouse-01 | 锅炉房 | 2×2 | boiler_house |
| wardtower-01 | 结界塔 | 1×1 | ward_tower |
| landmark-greatmosque-01 | 大清真寺（islamic） | 6×5 | temple |
| landmark-charbagh-01 | 宫殿园林四分园（persian） | 6×5 | lord_hall |
| landmark-kasbah-01 | 卡斯巴卫城（maghrebi） | 5×5 | barracks |
| landmark-rocktemple-01 | 岩凿神殿（nabataean） | 5×4 | temple |
| landmark-observatory-01 | 天文台（persian） | 5×4 | academy |

FacilityKind 覆盖 26/28。`city_wall` 和 `gate` 由城墙子代理（arab-base）承担，本目录不画。

## 说明与已知问题
- 色板外补了三个颜色：门窗洞 `#5c3d27`、深木 `#7a5233`、铁灰 `#6b6560`。岩凿神殿用了玫瑰砂岩色 `#c9876a / #b06e55 / #8f5644`。
- FacilityKind 里没有浴室，哈曼浴室记为 `cistern`（note 里写明）。穹顶、拱顶没有对应的 RoofId，一律记 `flat_mud`。
- 卡斯巴的 culture 填 `maghrebi`。安达卢斯风格没有单独出图，四分园记为 persian。
- 水车、码头、石桥自带一块示意水面（`#a9b8ad`），接入时可能需要和真正的水面瓦片对齐或裁掉。
- 卡斯巴的大屋面仍偏空；石桥只有正立面感，桥面进深表达弱；摊位尺寸偏小，放在 48 px 格内显得零碎。
- 马厩没画骆驼，避免和 arab-base 的骆驼摆件撞名、重复。
