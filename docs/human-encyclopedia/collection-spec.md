# 人类生产生活百科 · 首批规范

用户授权建立现实生产生活百科与多标签分类。状态：收集中；不代表完整人类百科，不自动加入故事。原274元素目录以机制/制度/题材母题为主，缺少小麦、钢铁等具体生活条目。

## 目录与分工

本目录每组交付JSON与Markdown：staples（谷物/豆/块根油料）、produce（蔬菜/水果/坚果）、flavors（香料/调味/饮料/糖源）、animal-foods（畜禽/水产/乳蛋等）、materials（天然矿物矿石燃料与人工材料）、tools（农业/厨房/纺织/木石金工/运输工具）。每组约25—40重要条目，质量优先，不宣称穷尽全部食物、作物或历史工具。按全球多地区历史重要性选择，不只欧洲/中国，不罗列所有品种凑数。

## JSON格式

顶层schema_version=1, group, status=candidate, sources=[], elements=[]。
source: id(组前缀), title, url, access(read/search_only/unavailable), supports, rights_note。
element: id(组前缀英文snake_case), name, aliases(数组), tags(数组英文snake_case), summary, details(对象), source_ids(数组), related_ids(数组可空), review_status=needs_review。
details七节字符串必填：definition, mechanism, conditions, exceptions, story_uses, historical_scope, evidence_and_uncertainty。无固定长度；去重复和空泛内容，详细到能理解用途/前提/例外，不抄原文凑长。来源可支撑什么与创作推演分开。

分类用多标签：可用living_organism,crop,cereal,legume,root_tuber,vegetable,fruit,nut,oil_crop,spice,condiment,beverage,sweetener,food,animal,animal_product,aquatic_food,natural_resource,mineral,ore,fuel,processed_material,metal,alloy,tool,facility,agriculture,cooking,textile,woodworking,metalworking,transport等。可扩展但避免同义标签混用。标签用于检索，不是权限或兼容性证明。条目类型、来源性质、制作阶段不可混淆：钢铁是加工材料/合金不是天然矿藏；矿物≠矿床；作物≠所有可食野生物；金属矿石≠已提炼金属。

植物尽量说明常见名的范围，能可靠确定时给科学分类/物种名，不能把多个品种的共性硬套每一个。定义与历史传播分开：起源、驯化、传入、普及不是同一时间；有争议不定死年代。反映环境/季节/土水/劳力/工艺/保存运输需求；不把某时代某地区有某作物当全球默认。食品记录可食部位与需处理/过敏腐败等定性限制，不提供危险野采鉴定或未经支持的医疗声称。

工具讲用途、材料、输入输出、维护、技术前提与时代变体，不能因为知道原理就自动获得制造能力。不得提供危险制造教程。人工材料记与原料、燃料、加工工艺的关系，避免eval或可执行公式。

每组实际搜索并read至少6个可靠不同页面，优先FAO/植物园/Kew/博物馆/USGS/教育机构/专业参考；不可用如实，不把摘要当全文。每条source_ids至少一个可支撑定义或背景的read来源；缺证据时明确范围，不杜撰。来源不保证全部推演正确，review_status不自升。只写分配文件、vantaloom_edit UTF8，禁止shell整文件重编码。校验JSON/唯一ID/引用/标签/七节/MD覆盖。不要改data、StoryPackage、其他组或源码。

## 数据库边界

独立本地SQLite素材库（与旅程数据库隔离），存候选条目、版本、来源、多标签及审查状态；支持标签组合、名称别名检索、单项详情、幂等导入与导出。标签不替代规则验证。百科中存在≠当前世界存在，更不等于人物知道。故事开局选定固定版本，运行期不因素材库更新加入新类型；本次不实现经营模拟或擅定经济人口参数。

构库名单为**显式 14 组**（本目录八组 + `docs/element-catalog` 六组），逐组登记、不走通配；总索引与各组数字见 [README.md](README.md)，库与 CLI 用法见 [database-使用说明.md](database-使用说明.md)。两个增补组（food-supplement / craft-supplement）是独立新增 namespace，不改写原六组数据，可在已发布的旧库上直接追加导入。
