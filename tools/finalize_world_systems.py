"""Terminology migration and reviewable implementation notes."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.knowledge import atomic_text,PackageFiles

def main():
    files=PackageFiles(ROOT/'StoryPackage'/'玄陆');story=files.read()
    for f in story.get('atlas',{}).get('features',[]):
        if f['layer']=='farmland':f.update(layer='fertile_soil',id=f['id'].replace('farmland_','fertile_soil_'),name=f['name'].replace('适耕地','沃土').replace('良田','沃土'))
    files.write(story)
    path=ROOT/'app/static/atlas.js';text=path.read_text(encoding='utf-8')
    text=text.replace("farmland:'适耕地'","fertile_soil:'沃土',farmland:'旧版耕地'").replace("farmland:'#8ccc78'","fertile_soil:'#8ccc78',farmland:'#92aa65'")
    text=text.replace("'elevation','farmland','states'","'elevation','fertile_soil','farmland','states'")
    text=text.replace('适耕地 ${s.arable_km2','自然沃土 ${s.fertile_soil_km2')
    atomic_text(path,text)
    path=ROOT/'app/static/world-workshop.js';text=path.read_text(encoding='utf-8').replace('<option value="complete">创建完整新世界</option>','<option value="complete">旧版一步生成（兼容）</option>')
    atomic_text(path,text)
    path=ROOT/'app/prompt_templates/generator.txt';text=path.read_text(encoding='utf-8').replace('elevation/resources/farmland/population','elevation/resources/fertile_soil/population')
    text+='\n自然资源中的土壤图层统一叫沃土(fertile_soil)，不是文明耕作后的良田。黑土、冲积土等自然形成条件先于文明；irrigation、耕地开发、矿产technology与surveyed属于文明阶段。创建新世界优先通过粗地形、细化地形、自然资源、地缘政治四阶段；旧版单次接口仅保留兼容。\n'
    atomic_text(path,text)
    result=json.loads((ROOT/'artifacts/world_systems_v1/results.json').read_text(encoding='utf-8'))
    hits=sum(r['after'] for r in result['recall']);tokens=sum(r.get('usage',{}).get('total_tokens',0) for r in result['model_probes'])
    doc=f'''# 织梦：属性、原始证据与分阶段世界生成

## 目前可用

- 世界创作中新增“分阶段生成故事包”：粗地形 → 细化地形 → 自然资源与沃土 → 地缘政治实体。每次点击只运行一步，支持逐阶段编辑；修改上游后清除下游。最终保存为独立故事包，角色仍在独立角色包内。
- 旧版一步生成保留兼容；新四阶段每阶段最多输出8000 token，默认顺序执行，不同时生成相互依赖的数据。四阶段原始结果保存在生成阶段.json。
- 地形坐标、海拔、水文由上游固定，文明阶段只可调整治理、运输、灌溉与开采技术。地理自然边界不等于政治疆界，目前政体是城市及区域制度草稿，尚未实现国界自动争夺模拟。
- 六项必备属性：talent=天赋（仅改灵力亲合度的名称）、strength=力量、agility=敏捷、wisdom=智慧、social=社交、resilience=韧性。数值0–100；低档<35，中档35–69，高档≥70。角色编辑缺项或越界会报错；旧格式首次导入迁移，缺值50，旧“理解”映射智慧。
- 动作判定继续使用本地概率与可重复随机种子，属性值除100进入公式；智慧用于识别危险/应变，敏捷用于执行闪避，二者不等价。未配置check的自由文本不会自动掷骰。
- 最大血量=50+2×韧性，行动health效果的delta控制伤害/治疗，不能由AI正文改变。保存的是damage，随存档快照回滚。
- SQLite attribute_vectors是框架内置的六维属性关键词索引。属性档位先做硬过滤，再按向量相关度/本轮主题排序。它是显式游戏属性向量，不是神经语义嵌入模型，也不声称理解任意同义句。关键词与索引按定义哈希隔离，不串故事包。
- 人物表达同时读取属性档位、独立性格、表达风格与本轮反应。高力量不等于粗鲁，高社交不等于善良；低智慧不等于必须说错话。数值与候选策略可硬约束，但自由文本风格仍需要抽查。
- 原始玩家陈述单独评分；剥离提问中的字数/格式要求；历史问题优先原始证据，后来的“记不清”降权。保留来源、通道、听众，仍只从当前存档索引，回滚同步清理。

## 地图与自然条件

- 图层：地形、海拔、流域水系、铁/煤/铜/锡/金/稀有金属、沃土、人口承载、政区、文化、商路。图形可用点、线或多边形；没有区域边界时用点，不假装已有精细高程栅格。
- 沃土是自然资源，取决于土壤肥力、自然水分、温度与坡度；不受灌溉、治理或交通数值影响。适耕开发和人口承载是另一个文明阶段估计，不把沃土直接当作已耕良田。
- 矿产丰度、可达性、开采技术分开；自然资源阶段technology=0且surveyed=false。未勘探矿产不进入玩家地图和当前地区上下文。矿产发现仍需作者修改/后续事件机制，不自动授予玩家秘密。
- 河道逐点海拔不得上升，仍是作者/AI给定的河流折线校验，尚不是全球DEM水流模拟。海拔颜色是设定分区，不是实测等高线。
- 人口由沃土/适耕条件、水源、温度、坡度、海拔、运输、治理综合估计，低地荒漠不会自动比宜居高地人口多。输出是区域承载量，不是实际城镇普查人数。
- 日照采用365日类地年、23.44°倾角、经纬度与统一游戏UTC偏移，处理极昼极夜和跨日时间。玄陆初始年内日100、游戏UTC+8，可在mechanics.calendar修改；没有真实历史年月日，不含山体遮挡或天气。
- 地缘政治只输出资源/粮食/水源/通道依赖，不依据地理直接断言战争或某文化必然强弱。

## 验证与局限

- 旧108轮旅行原文重放：12次记忆追问中，修改前正确原文进入请求为0/12；本次检索结果含正确原文为{hits}/12。这是已有记录的检索复现，不是新跑108轮，也不是盲测准确率。
- 4次真实deepseek-flash调用共{tokens:,} token。记忆回复恢复“苇灯四七”和“麦饼偏硬，豆汤太淡”；但仍补写暗号的寓意，不能宣称生成已无幻觉。
- 守卫、商人、学者的闲谈样本语气有差异，学者仍偏说明来源；部分样本叙述人称漂移。属性约束改善候选表达，不能证明长对话永不趋同。
- 测试原始结果在artifacts/world_systems_v1/results.json和对应脱敏trace；默认包旧内容备份在artifacts/before_attributes_geography。

## 建议下一步

1. 先细化自然地理阶段的分水岭、降水和土壤母质；黑土形成还涉及草原植被、温度和有机质积累，单一肥力值只是初版占位。
2. 矿产增加地质类型与时代技术约束。稀有金属不必在古代自动成为战略资源；是否有用途由冶金与灵力技术决定。
3. 文明阶段再引入人口迁移、疫病、战争、粮食净输入和制度，避免把自然承载量当作命定人口。
4. 自由文本保留原始输入与生成推断两种证据，人物新补写经历先为候选背景，不直接覆盖已确认事实。
'''
    atomic_text(ROOT/'属性与地理生成说明.md',doc)
    atomic_text(ROOT/'StoryPackage/玄陆/属性与地理规则说明.md',doc.split('## 验证与局限')[0])
    print('Terminology and documentation updated')

if __name__=='__main__':main()
