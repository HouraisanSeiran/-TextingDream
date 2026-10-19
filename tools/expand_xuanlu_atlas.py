"""Add editable geography drafts without changing existing canon, actors or events."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.knowledge import PackageFiles
from app.atlas import Atlas, validate_atlas

# Historical analogues are already documented in the original package. New names
# and spatial ranges below are explicit fiction, not researched historical claims.
POINTS=[
('basins','山川与水系骨架','地形水文',['山脉','水源','流域','地图'],
'架空补充草案：玄陆的行旅分为东部季雨河谷、北缘山前走廊、中段干旱盆地、西部双河灌溉地及内海岸带。高地雨雪补给下游，水量随季节变化；不存在横穿所有山脉而不交代峡口的笔直大河。灵脉与地表河流可以相交，但不等于水源，布阵不能免除引水、疏浚和污染处置。地图以区域关系表达方向，现有经纬参照不决定真实世界尺寸。'),
('eastern_basin','澄京腹地与漕运','聚落生计',['澄京','天朝都城','漕运','粮食'],
'架空补充草案：澄京依靠渭澜河谷的农田、外来漕粮与山地薪炭维持人口。都城沿河设转运埠，山口集镇提供木材、药材与牲畜；各地粮价受收成、仓储损失、运力和地方截留共同影响。灵田只占需长期维护的一部分田地。都城断粮的前兆可以是船工停工、仓券折价或车价上涨，不必立即写成天下饥荒。具体人口、产量与田税数值待作者确定。'),
('pass_water','关城走廊与水站','道路与补给',['西行关城','山口','水站','商队'],
'架空补充草案：西行关城控制的是驿路峡口、山前水站和登记权，不是覆盖整片荒漠的连续城墙。商队按可补水地点安排日程；大车、驮畜与步行队可走的路不同。雪封高口、洪水冲桥、草料短缺会分别改变通行条件。修士能够护送一支急队，并不能让数百头牲畜不饮水。支线水站暂不作为自动可旅行地点，需作者配好事件与补给规则再开放。'),
('oasis_hydrology','沃土双河与渠社','地形水文',['新月沃土商驿','双河','灌渠','水权'],
'架空补充草案：新月沃土商驿处于双河灌溉网与旱路会合处，名称中的绿洲指受维护的水绿聚居带，不等于孤立沙丘中的一口泉。渠社按维护义务分配水时，上游先放水与下游淤积常造成证词冲突。盐分累积、排水不畅与河道迁移需要休耕和排盐，不能只用法术增雨。商驿的粮仓、舟桥和秤量所受不同机构管理，因此交过关税并不自动买到渡河资格。'),
('coastal_winds','内海风季与南岸航路','航海与港口',['西方海港','南岸灯港','风季','航海'],
'架空补充草案：西方海港连接海峡、内海沿岸与北方陆路，南岸灯港承接河口粮运、沿岸航行与译信业务。内海冬季风浪与夏季风向、印度洋季风属于不同尺度，不能混成同一张全球航期表。船长按船型、货物、沿岸补给与风险选择路线；灯塔与熟悉礁岸的引水人各有价值。示意海路线只表达港口联系，不代表船只穿越陆地、保证每日开航或直线航时。'),
('political_layers','疆界、驻军与征税范围','政区与治理',['天朝','新月','西方诸国','疆界'],
'架空补充草案：地图政区层表达政治影响区，不能把一条边界线当成现代统一主权的全部。天朝的直辖州、羁縻共同体与边镇军需区，新月王朝的省署、地方家族和渠社权利，西方诸国的王领、城市自治和寺院地产会交错。谁能征税、审案、征兵或保护道路须分别确认。边地同时交纳数种费用不一定意味两个国家同时拥有完整统治。范围面都是作者工作稿，争议地带留作情节条件。'),
('culture_networks','语言文化与迁徙网络','文化与语言',['语言','文化','移民','万言机'],
'架空补充草案：官文、商用语、家庭口语与礼仪语言未必相同。澄京译馆、关城驿站、沃土市集和两海港形成跨政区的翻译网络，同一城市可住多种语言群体，同一语言群体也不必服从同一君主。万言机需要样本和语境，能协助沟通却不能自动理解暗号、身份礼节或替人证明契约有效。人物用词依据教育、职业、场合与个性生成，不把文化标签写成固定口音笑话。'),
('faith_landscape','圣所、学舍与公共服务','信仰与社会',['信仰','寺院','圣所','学校'],
'架空补充草案：宗教地图标示教团、巡礼与学术联系，不表示某地区居民都持同一解释。天朝的观院与书院、新月的经堂与施济基金、西方的修院与城市圣所都可能办学、保存档案、照顾旅人或经营地产，具体组织权利需当地知识点说明。不同传统能在医药和水利上合作，也会争夺捐赠与司法管辖。圣所提供庇护是否得到地方官认可，应由具体事件裁定。'),
('resource_flows','五站资源交换与短缺','资源与贸易',['贸易','粮食','马匹','盐','矿石'],
'架空补充草案：澄京输出织物、纸墨与工匠服务，需外地畜力及矿料；关城供应护送、转运和驮畜交易，依赖粮草；沃土输出灌溉农产与加工品，需木材和金属；西方海港承担仓储、修船及海陆换装，需船材、绳索和粮食；南岸灯港连接河口粮产、玻璃工艺和译信网络，需可靠淡水与港池疏浚。这里只描述候选经济方向，不自动改变玩家余额、库存或市场价格。'),
('settlement_scale','城市、乡村与腹地层次','聚落生计',['城市','乡村','腹地','集市'],
'架空补充草案：每座主要城市对应河谷、道路或海岸腹地，外围依次可有渡口集镇、周期市集、村落与牧地。行政重要不等于人口最多，军堡也未必产粮。进入街区不会自动新建长篇对话，沿用当前主要场景；只有剧情信息量和旅程条件满足时才分章。县镇、渠社和港区标记是可扩充资料节点，尚未配置事件的标记只能阅读，不能点击后瞬移。'),
('map_evidence','地图版本与制图者立场','地图与信息',['地图','测绘','传闻','边界'],
'架空补充草案：官署图重驿站与税区，商队图重水站与通行代价，船图重泊地与岸标，地方图重渠界和田块。地图记载也是有来源、有时效的知识；传闻中的桥梁不因画在纸上就客观存在。作者图册展示完整设定，玩家图册只显示公开及已解锁内容；角色秘密不藏进公共标记描述。底图采用现代自然地理仅为测试，对架空地形、历史政治疆域和纪年均不构成证据。'),
('maintenance_conflict','跨区域冲突的日常入口','事件素材',['桥梁','修渠','维修','争议'],
'作者补充草案：可用待编事件包括关城两处水站争草料、新月渠社争轮灌先后、西方海港修船工欠薪、南岸引水人与商会争泊位、澄京仓券与实粮不符。每个事件先确定涉及人物、客观记录、误解来源、可观察线索和本地裁定后果，再开放给玩家；这里不意味着事件已经发生，也不自动给任何 NPC 添加罪责。')]

def supplement(directory):
    files=PackageFiles(directory);story=files.read()
    points=[]
    for key,title,category,keywords,body in POINTS:
        points.append({'id':'atlas_xuanlu_'+key,'title':title,'category':'地图补充_'+category,'keywords':keywords,
            'visibility':'author' if key=='maintenance_conflict' else 'public','status':'架空补充工作稿，待作者调整','content':body})
    existing={p['id'] for p in story['knowledge']}
    story['knowledge'].extend(p for p in points if p['id'] not in existing)
    features=[]
    def add(key,name,layer,geom,coords,article,description,locations=()):
        features.append({'id':'atlas_xuanlu_'+key,'name':name,'layer':layer,'geometry':geom,'coordinates':coords,
            'description':description,'knowledge_ids':['atlas_xuanlu_'+article], 'location_ids':list(locations),'visibility':'public'})
    add('eastern_range','东陆山系（范围示意）','terrain','line',[[100,25],[102,29],[105,32],[107,35],[111,38]],'basins','候选山系；影响河谷风雨与山口通行，不作真实海拔断言。')
    add('central_range','中段高地与雪口','terrain','line',[[65,30],[70,34],[74,37],[81,41],[87,43]],'pass_water','高口与山前道路的关系仍需地方图细化。')
    add('dry_basin','山前干旱带','terrain','polygon',[[75,36],[91,36],[101,40],[93,45],[78,43]],'pass_water','绿洲节点依赖地下水、河流及维护；面范围为草案。')
    add('weil_river','渭澜河谷','water','line',[[103,35],[105,34.8],[108.9,34.3],[112,34],[115,33.7]],'eastern_basin','原创河流工作名，借用河谷社会结构，不等于现实河道。')
    add('twin_river_a','沃土双河 · 西支','water','line',[[39,38],[40.5,36.8],[42.5,35],[44.4,33.3],[47,31]],'oasis_hydrology','示意河道，不提供航深和实时水位。')
    add('twin_river_b','沃土双河 · 东支','water','line',[[43,38.5],[44,36.5],[45.2,34.3],[47,31]],'oasis_hydrology','渠系把农业聚落与商驿相连。')
    add('south_river','南岸长河下游','water','line',[[32,24],[32.5,27],[31.7,29],[30.8,30.3],[29.9,31.2]],'coastal_winds','长河下游与河口港联系的示意。')
    add('east_state','天朝影响区（非精确疆界）','states','polygon',[[99,24],[117,23],[123,34],[113,42],[100,40]],'political_layers','直辖、边镇和地方权利需要分开记录。')
    add('crescent_state','新月沃土影响区','states','polygon',[[36,28],[49,27],[55,34],[49,39],[39,38]],'political_layers','政治影响与渠社、族群分布不重合。')
    add('western_states','西方诸国沿海带','states','polygon',[[10,39],[22,37],[30,40],[28,46],[16,48]],'political_layers','多个政治实体的合称，不是一国边界。')
    add('translation_network','跨境译语网络','cultures','line',[[108.9,34.3],[94.7,40.1],[72,38],[44.4,33.3],[28.9,41],[29.9,31.2]],'culture_networks','文化交流网络不是统一族群疆界。')
    add('south_culture','南岸港市多语带','cultures','polygon',[[23,30],[31,29],[35,31],[32,33],[25,33]],'faith_landscape','港市语言和信仰共存，人物仍按个体塑造。')
    route_defs=[('east_route','都城—西行关城',[[108.9,34.3],[106,36],[102,38],[98,39.5],[94.7,40.1]],['tianchao_capital','western_pass']),
        ('oasis_route','山前商路',[[94.7,40.1],[87,42],[78,41],[70,38],[60,36],[52,34],[44.4,33.3]],['western_pass','crescent_oasis']),
        ('western_route','沃土—海峡陆路',[[44.4,33.3],[41,35],[36,37],[32,39],[28.9,41]],['crescent_oasis','western_port']),
        ('sea_route','内海南岸航路',[[28.9,41],[28,40],[26,40],[25,38],[25,35],[28,33],[29.9,31.2]],['western_port','south_lantern_port'])]
    for key,name,coords,locs in route_defs:add(key,name,'routes','line',coords,'coastal_winds' if key=='sea_route' else 'pass_water','工作稿路线；折线仅示方向，不能计算实际里程或自动保证畅通。',locs)
    articles=['eastern_basin','pass_water','oasis_hydrology','coastal_winds','coastal_winds']
    for place,article in zip(story['locations'],articles):
        add('place_'+place['id'],place['name'],'markers','point',[place['coordinates']],article,place['description'],[place['id']])
    for key,name,coords,article,loc in [('capital_quay','澄京转运埠',[109.5,34.1],'eastern_basin','tianchao_capital'),('pass_waterstop','关城山前水站',[93.8,39.5],'pass_water','western_pass'),('canal_house','双河渠社议水所',[44.7,33.5],'oasis_hydrology','crescent_oasis'),('shipyard','海峡修船坞',[28.6,40.7],'resource_flows','western_port'),('pilot_house','南岸引水人会所',[30.1,31.3],'coastal_winds','south_lantern_port')]:
        add(key,name,'markers','point',[coords],article,'可阅读的地方节点，尚未配置独立旅行事件；名称和位置可修改。',[loc])
    atlas=Atlas.model_validate(story.get('atlas',{})).model_dump(mode='json')
    old_ids={f['id'] for f in atlas['features']}
    atlas['features'].extend(f for f in features if f['id'] not in old_ids)
    atlas['title']='玄陆 · 山川、文明与商路图册'
    story['atlas']=atlas
    validate_atlas(story);files.write(story)
    return {'knowledge_added':sum(p['id'] not in existing for p in points),'features_added':sum(f['id'] not in old_ids for f in features)}

if __name__=='__main__':print(json.dumps(supplement(ROOT/'StoryPackage/玄陆'),ensure_ascii=False))
