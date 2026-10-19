"""Create the original high-fantasy story package used for local demos."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "StoryPackage" / "灰烬海"
CHARACTERS = ROOT / "character_packages" / "ash-sea-characters-001.json"


def write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def point(point_id: str, title: str, category: str, keywords: list[str], content: str, *, status="原创设定", visibility="public") -> str:
    meta = {
        "id": point_id,
        "title": title,
        "category": category,
        "keywords": keywords,
        "visibility": visibility,
        "status": status,
    }
    return "```json\n" + json.dumps(meta, ensure_ascii=False, indent=2) + "\n```\n\n" + content


def main() -> None:
    story = {
        "id": "ash-sea-world-001",
        "title": "灰烬海：星炬远征",
        "premise": "群山西侧的灰烬海正在吞没航道。主角带着一枚会记录星光的旧仪器，沿着失落的烽火线寻找熄灭的天穹灯塔。",
        "character_package_id": "ash-sea-characters-001",
        "locations": [
            {"id": "lumen_gate", "name": "曙门城", "description": "建在盐河三角洲上的城邦，保存着远征者出发前最后的档案。", "neighbors": ["cinder_pass"], "scenes": ["departure"]},
            {"id": "cinder_pass", "name": "灰脊关", "description": "穿过黑色山脊的关隘，旧烽火线从这里进入荒原。", "neighbors": ["lumen_gate", "reed_expanse"], "scenes": ["passage"]},
            {"id": "reed_expanse", "name": "回声苇原", "description": "风吹过银色芦苇时会带来远处的声音，商队在此交换水和消息。", "neighbors": ["cinder_pass", "glass_delta"], "scenes": ["rumor"]},
            {"id": "glass_delta", "name": "璃潮三角洲", "description": "潮水退去后留下会反光的盐晶滩，河口聚落靠渡船和制盐维生。", "neighbors": ["reed_expanse", "starfall_keep"], "scenes": ["delta"]},
            {"id": "starfall_keep", "name": "坠星堡", "description": "悬在海崖上的废弃观测堡垒，最后一盏天穹灯曾在这里点燃。", "neighbors": ["glass_delta"], "scenes": ["observatory"]},
        ],
        "events": [
            {"id": "departure", "title": "出发前的星图", "location_id": "lumen_gate", "scene_id": "departure", "premise": "档案官交给主角一张缺角星图，要求查明烽火线为何沉默。", "participants": ["wayfarer"], "player_goal": "决定携带哪条线索离城", "hidden_goal": "让主角发现远征并非王室命令", "next_events": ["passage"], "actions": [{"id": "accept_chart", "label": "收下星图并询问旧烽火线", "ends_event": True, "effects": [{"op": "take", "id": "star_chart"}, {"op": "flag", "id": "accepted_mission", "value": True}], "success_text": "我把缺角星图收进防水囊，向西穿过城门。"}], "max_turns": 8, "exit_flag": "departure_done", "player_enters": True, "major_scene_id": "road_chapter"},
            {"id": "passage", "title": "灰脊关的熄火台", "location_id": "cinder_pass", "scene_id": "passage", "premise": "关上的守烽人不再相信旧王国的地图，山口的火台却留下新鲜灰烬。", "participants": ["wayfarer", "pass_warden"], "player_goal": "判断守烽人的说法是否可信", "hidden_goal": "发现有人在借沉默掩护夜间通行", "next_events": ["rumor_market"], "actions": [{"id": "inspect_ashes", "label": "检查火台的灰烬", "ends_event": True, "check": {"attribute": "wisdom", "difficulty": 0.45}, "success": [{"op": "fact", "text": "灰烬里有近三日留下的蓝色矿粉。"}, {"op": "flag", "id": "saw_blue_ash", "value": True}], "failure": [{"op": "rumor", "character": "pass_warden", "text": "守烽人说火台只是自然复燃。"}], "success_text": "灰烬没有撒谎：有人在夜里重新点过火。"}], "max_turns": 10, "exit_flag": "passage_done", "major_scene_id": "road_chapter"},
            {"id": "rumor_market", "title": "回声苇原的两种方向", "location_id": "reed_expanse", "scene_id": "rumor", "premise": "商队带来两个互相矛盾的消息：北边有安全水源，南边有会说话的废塔。", "participants": ["wayfarer", "reed_trader"], "player_goal": "从传闻中选出下一段路线", "hidden_goal": "让错误消息也留下真实的社会后果", "next_events": ["delta_crossing"], "actions": [{"id": "trade_for_route", "label": "用一份水换取商队路线", "ends_event": True, "costs": {"water": 1}, "effects": [{"op": "take", "id": "reed_token"}, {"op": "rumor", "character": "reed_trader", "text": "商队认为南方渡口仍然开放。"}], "success_text": "芦苇向南倒伏，商队的船印也指向三角洲。"}], "max_turns": 10, "exit_flag": "rumor_done", "major_scene_id": "road_chapter"},
            {"id": "delta_crossing", "title": "璃潮渡口的空船", "location_id": "glass_delta", "scene_id": "delta", "premise": "渡口有一艘无人看守的平底船，船底刻着与星图相同的缺口。", "participants": ["wayfarer", "delta_ferryman"], "player_goal": "取得过河许可并核对船上的刻痕", "hidden_goal": "证明远征线索来自民间维护者", "next_events": ["starfall_observatory"], "actions": [{"id": "cross_delta", "label": "检查空船后渡河", "ends_event": True, "effects": [{"op": "flag", "id": "crossed_delta", "value": True}, {"op": "fact", "text": "渡船由一支不属于王室的维护网络定期修补。"}], "success_text": "船底的刻痕与星图拼合，潮水把我送向海崖。"}], "max_turns": 10, "exit_flag": "delta_done", "major_scene_id": "road_chapter"},
            {"id": "starfall_observatory", "title": "坠星堡的最后一盏灯", "location_id": "starfall_keep", "scene_id": "observatory", "premise": "堡垒顶端的天穹灯仍有微光，点亮它需要说出一路听来的三种不同版本。", "participants": ["wayfarer", "keep_keeper"], "player_goal": "决定是否重新点燃天穹灯", "hidden_goal": "让主角选择公开真相或保留沉默", "next_events": [], "actions": [{"id": "light_beacon", "label": "用星图和三种传闻点灯", "ends_event": True, "entry_flags": {"crossed_delta": True}, "effects": [{"op": "flag", "id": "beacon_lit", "value": True}, {"op": "fact", "text": "天穹灯重新发出微光，附近聚落可以看见新的航标。"}], "success_text": "灯光越过灰烬海，远处的沉默终于有了回答。"}], "max_turns": 12, "exit_flag": "expedition_done", "major_scene_id": "road_chapter"},
        ],
        "items": [
            {"id": "star_chart", "name": "缺角星图", "description": "记录五座烽火台和一条已经改道的航线。", "location_id": "lumen_gate", "authority": "engine"},
            {"id": "reed_token", "name": "芦印牌", "description": "回声苇原商队用来确认水和渡船交换的木牌。", "location_id": "reed_expanse", "authority": "engine"},
        ],
        "major_scenes": [{"id": "road_chapter", "title": "灰烬海远征", "location_ids": ["lumen_gate", "cinder_pass", "reed_expanse", "glass_delta", "starfall_keep"], "force_new_conversation": False}],
        "mechanics": {"narrative_person": "first", "player_position": "protagonist", "visibility_pipeline": "inner_complete_then_surface_projection", "local": {"resources": [{"id": "water", "name": "饮水", "unit": "份", "initial": 3, "maximum": 8, "per_hour": 0}], "turn_hours": 1, "travel_hours": 4, "memory_limit": 200}},
    }

    atlas = {"version": 1, "title": "灰烬海 · 星炬远征图册", "note": "原创架空地图；坐标只用于图册展示，不表示现实地理。", "features": [
        {"id": "ash_coast", "name": "灰烬海岸", "layer": "terrain", "geometry": "line", "coordinates": [[-5, 36], [4, 38], [13, 35], [21, 31]], "description": "被灰尘和盐雾反复改写的海岸线。", "knowledge_ids": ["ash_sea_geography"], "location_ids": [], "visibility": "public", "terrain_kind": "desert"},
        {"id": "cinder_range", "name": "灰脊山链", "layer": "terrain", "geometry": "line", "coordinates": [[-9, 48], [-4, 44], [2, 42], [8, 40]], "description": "火山岩山链，旧烽火线穿过山口。", "knowledge_ids": ["ash_sea_geography"], "location_ids": [], "visibility": "public", "terrain_kind": "mountain"},
        {"id": "road_route", "name": "星炬旧路", "layer": "routes", "geometry": "line", "coordinates": [[-3, 41], [-2, 43], [3, 42], [10, 39], [17, 35]], "description": "五座烽火设施之间的旧驿路。", "knowledge_ids": ["beacon_network"], "location_ids": ["lumen_gate", "cinder_pass", "reed_expanse", "glass_delta", "starfall_keep"], "visibility": "public"},
        {"id": "lumen_gate_marker", "name": "曙门城", "layer": "markers", "geometry": "point", "coordinates": [[-3, 41]], "description": "远征起点。", "knowledge_ids": ["lumen_gate_lore"], "location_ids": ["lumen_gate"], "visibility": "public"},
        {"id": "cinder_pass_marker", "name": "灰脊关", "layer": "markers", "geometry": "point", "coordinates": [[-2, 43]], "description": "第一座沉默烽火台。", "knowledge_ids": ["cinder_pass_lore"], "location_ids": ["cinder_pass"], "visibility": "public"},
        {"id": "reed_expanse_marker", "name": "回声苇原", "layer": "markers", "geometry": "point", "coordinates": [[3, 42]], "description": "消息和饮水交换地。", "knowledge_ids": ["reed_expanse_lore"], "location_ids": ["reed_expanse"], "visibility": "public"},
        {"id": "glass_delta_marker", "name": "璃潮三角洲", "layer": "markers", "geometry": "point", "coordinates": [[10, 39]], "description": "通向海崖的渡口。", "knowledge_ids": ["glass_delta_lore"], "location_ids": ["glass_delta"], "visibility": "public"},
        {"id": "starfall_keep_marker", "name": "坠星堡", "layer": "markers", "geometry": "point", "coordinates": [[17, 35]], "description": "最后一座天穹灯堡。", "knowledge_ids": ["starfall_keep_lore"], "location_ids": ["starfall_keep"], "visibility": "public"},
    ]}

    characters = {"id": "ash-sea-characters-001", "title": "灰烬海：远征角色", "description": "星炬远征的原创角色包。", "generation_constraints": {"allowed_roles": ["旅人", "守烽人", "商人", "渡船人", "守堡人"], "max_power_level": 3}, "characters": [
        {"id": "wayfarer", "name": "行路人", "role": "主角", "traits": ["好奇", "耐心", "不轻信权威"], "personality": {"求知": 0.8, "谨慎": 0.7, "同理心": 0.6}, "state": {"疲劳": 0.1}, "location_id": "lumen_gate", "attributes": {"talent": 55, "strength": 45, "agility": 55, "wisdom": 65, "social": 55, "resilience": 60}},
        {"id": "pass_warden", "name": "伊岚守烽人", "role": "次要角色", "traits": ["守规矩", "不安", "熟悉山路"], "personality": {"谨慎": 0.8, "责任": 0.8}, "state": {"警惕": 0.6}, "location_id": "cinder_pass", "attributes": {"talent": 35, "strength": 65, "agility": 55, "wisdom": 60, "social": 40, "resilience": 70}},
        {"id": "reed_trader", "name": "芦原商人萨芙", "role": "次要角色", "traits": ["圆滑", "记账准确", "害怕欠债"], "personality": {"社交": 0.8, "谨慎": 0.6}, "state": {"好感": 0.2}, "location_id": "reed_expanse", "attributes": {"talent": 40, "strength": 40, "agility": 60, "wisdom": 65, "social": 80, "resilience": 50}},
        {"id": "delta_ferryman", "name": "璃潮渡船人赫岚", "role": "次要角色", "traits": ["沉默", "守约", "熟悉潮汐"], "personality": {"责任": 0.8, "谨慎": 0.7}, "state": {"警惕": 0.4}, "location_id": "glass_delta", "attributes": {"talent": 45, "strength": 55, "agility": 65, "wisdom": 60, "social": 45, "resilience": 65}},
        {"id": "keep_keeper", "name": "守堡者欧洛", "role": "次要角色", "traits": ["孤独", "重视证据", "不再效忠王室"], "personality": {"求真": 0.9, "谨慎": 0.7}, "state": {"警惕": 0.5}, "location_id": "starfall_keep", "attributes": {"talent": 75, "strength": 35, "agility": 40, "wisdom": 85, "social": 50, "resilience": 45}},
    ]}

    write(PACKAGE / "总概.md", """# 灰烬海：星炬远征\n\n这是一个原创的史诗远征世界。北方群山的火山灰沿风暴落入海湾，古老航道逐渐失效，五座天穹灯只剩最后一座仍有微光。曙门城的档案官委托一名行路人沿旧路西行，查明烽火线沉默的原因。\n\n世界里没有全知的地图。王室档案、商队传闻和守烽人的记忆各自保留一部分真相，玩家需要在不同版本之间作出判断。天穹灯由民间维护者长期修补，远征的真正问题是：谁有权决定哪些道路应当重新被照亮。\n\n本故事包完全为 TextingDream 创作，人物、地名、历史和规则均为原创。\n""")
    write(PACKAGE / "story.json", json.dumps(story, ensure_ascii=False, indent=2))
    write(PACKAGE / "atlas.json", json.dumps(atlas, ensure_ascii=False, indent=2))
    write(CHARACTERS, json.dumps(characters, ensure_ascii=False, indent=2))

    docs = {
        "00_世界根基/ash_sea_history.md": point("ash_sea_history", "灰烬海的历史", "00_世界根基", ["灰烬海", "天穹灯", "历史"], "两百年前，灰脊山链连续喷发，沿岸城邦以五座天穹灯维持航路。旧王国衰落后，灯塔维护转由商队、渡船人和守烽人共同承担。王室档案仍把灯塔写成自己的遗产，民间记录则认为它属于所有依靠航道生活的人。"),
        "00_世界根基/beacon_network.md": point("beacon_network", "星炬网络", "00_世界根基", ["烽火", "星炬", "航路", "维护"], "五座灯堡以星位相互校准，灯光本身不能驱散灰尘，却能为渡船和商队标记可通行的风口。每座灯堡都需要本地维护者提供燃料、镜片和天气记录。重新点灯会改变附近聚落的路线选择。"),
        "01_地理与气候/ash_sea_geography.md": point("ash_sea_geography", "灰烬海地理", "01_地理与气候", ["山脉", "海岸", "三角洲", "芦原"], "灰脊山链从北方斜入海湾，山口以西是回声苇原，南部河流在璃潮三角洲分叉。灰尘会随季风改变能见度；地图上的直线不能直接换算旅行时间，真正的通行取决于水源、潮汐和旧路维护情况。"),
        "02_社会与势力/lumen_gate_lore.md": point("lumen_gate_lore", "曙门城的档案", "02_社会与势力", ["曙门城", "档案", "城邦"], "曙门城的档案院保存王室时期的路线册，也保存民间修补记录。档案官希望道路恢复，却不愿承认王室已经失去对灯塔的直接控制。城市居民把远征者当作带回消息的人，而不是正式使者。"),
        "02_社会与势力/cinder_pass_lore.md": point("cinder_pass_lore", "灰脊关的守烽人", "02_社会与势力", ["灰脊关", "守烽人", "矿粉"], "守烽人以家族轮值维护山口火台。伊岚知道有人夜间借蓝色矿粉制造假火，却担心说出名字会让关口失去补给。她承认自己看见过新鲜灰烬，但不承认知道谁留下它。"),
        "02_社会与势力/reed_expanse_lore.md": point("reed_expanse_lore", "回声苇原的商路", "02_社会与势力", ["回声苇原", "商队", "传闻", "水"], "芦原商队用木牌记录水、船位和欠款。这里的传闻通常带着来源，但转述两次后就会混入路线偏好。萨芙不相信王室地图，却相信能指出水井的旧歌。"),
        "02_社会与势力/glass_delta_lore.md": point("glass_delta_lore", "璃潮三角洲的渡船网络", "02_社会与势力", ["璃潮", "渡船", "维护者", "盐晶"], "三角洲渡船人维护着一套不挂王室印记的航标。每艘船的船底都有缺口形刻痕，用来标记最近一次修补的灯堡。渡船人只承认实际完成的修补，不承认纸面上的归属。"),
        "03_远征与人物/starfall_keep_lore.md": point("starfall_keep_lore", "坠星堡的守堡者", "03_远征与人物", ["坠星堡", "守堡者", "天穹灯", "证据"], "坠星堡的守堡者欧洛独自看守最后的灯。他要求来访者同时说出档案、守烽人和商队的版本，因为任何单一来源都可能隐藏自己的利益。点灯后，新的航标会让附近聚落重新选择贸易方向。"),
        "03_远征与人物/ash_sea_energy.md": point("ash_sea_energy", "星光燃料", "03_远征与人物", ["星光", "燃料", "仪器", "魔法"], "天穹灯使用从陨石玻璃中提取的微弱星光作为校准燃料。星光可以记录方向和时间，不能替人判断谎言，也不能凭空制造物资。行路人的旧仪器只能保存少量光痕，每次使用都需要在灯堡或观测台重新校准。"),
        "04_未知与秘密/maintenance_secret.md": point("maintenance_secret", "被隐去的维护记录", "04_未知与秘密", ["秘密", "维护记录", "民间网络"], "旧王国曾经中断过一次灯塔维护，并把事故归咎于商队。实际记录显示，维护者为了保护下游聚落主动熄灭过一座灯，避免把船引入塌陷河口。此事只有守堡者和少数渡船人知道。", visibility="author"),
    }
    for path, text in docs.items():
        write(PACKAGE / "知识点" / path, text)
    print(f"created {PACKAGE}")


if __name__ == "__main__":
    main()
