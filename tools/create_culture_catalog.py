"""Create the explicit culture/name candidate catalog from compact source data.

The generated JSON is deliberately candidate material: it is not auto-adopted by a
story and every entry remains ``needs_review`` in the encyclopedia database.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "docs" / "human-encyclopedia"
SECTIONS = ("definition", "mechanism", "conditions", "exceptions",
            "story_uses", "historical_scope", "evidence_and_uncertainty")


def src(sid, title, url, supports):
    return {"id": sid, "title": title, "url": url, "access": "read",
            "supports": supports,
            "rights_note": "仅做事实范围与术语核对；条目为自行转述的待审候选，不复制原文。"}


def detail(kind, name, note):
    return {
        "definition": f"{name}：{note}",
        "mechanism": "以语言、媒介、讲述场合与受众共同形成意义；创作时先固定说话者、传播者和听者。",
        "conditions": "需要明确的语言/地区、时代层、社会场合和可接触的传播媒介；名字还需固定转写方式。",
        "exceptions": "现代创作可以改写形式，但不能把现实传统的一个变体声称为全部传统；个别角色的选择也可以违背群体惯例。",
        "story_uses": "用于角色卡、城镇文化、传闻、契约、节庆或线索表达；失败时可以改变玩家理解，却不直接改写世界事实。",
        "historical_scope": "候选资料用于跨时期创作参考；现实历史、宗教与语言边界必须在具体世界包中另行限定。",
        "evidence_and_uncertainty": "来源只支持条目的概述范围；名字池是创作示例，不是人口统计，也不能单独决定角色阶层、性格、宗教或国籍。",
    }


def element(eid, name, summary, tags, sources, note, aliases=(), **extra):
    return {"id": eid, "name": name, "aliases": list(aliases), "tags": tags,
            "summary": summary, "details": detail(tags[0], name, note),
            "source_ids": sources, "related_ids": [], "review_status": "needs_review",
            **extra}


def write(group, note, sources, elements):
    payload = {"schema_version": 1, "group": group, "status": "candidate",
               "note": note, "sources": sources, "elements": elements}
    (ROOT / f"{group}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


LIT_SOURCES = [
    src("culture_lit_poetry", "Poetry — Encyclopaedia Britannica", "https://www.britannica.com/art/poetry", "诗歌的节奏、声音、意象和形式具有多种文化传统。"),
    src("culture_lit_novel", "Novel — Encyclopaedia Britannica", "https://www.britannica.com/art/novel", "小说以叙事、人物、时间和社会环境组织虚构经验。"),
    src("culture_lit_epic", "Epic — Encyclopaedia Britannica", "https://www.britannica.com/art/epic", "史诗的长篇叙事、英雄行动、共同体记忆和口述/书写传承。"),
    src("culture_lit_oral", "UNESCO oral traditions", "https://ich.unesco.org/en/oral-traditions-and-expressions-00053", "故事、歌谣、谚语和表演依赖社群与语境传承。"),
    src("culture_lit_haiku", "Haiku — Encyclopaedia Britannica", "https://www.britannica.com/art/haiku", "俳句的季节语、切字与瞬间意象，以及现代变体。"),
    src("culture_lit_nights", "The Thousand and One Nights — Encyclopaedia Britannica", "https://www.britannica.com/topic/The-Thousand-and-One-Nights", "框架叙事、讲述延宕和多源汇编传统；版本与译本并不相同。"),
    src("culture_lit_glossary", "Poetry Foundation glossary", "https://www.poetryfoundation.org/learn/glossary-terms", "意象、隐喻、叙事诗和抒情诗等教育性术语解释。"),
]

LIT = [
    ("culture_poetry_lyric", "抒情诗", "以说话者的感受、判断或感官经验为中心的诗歌。", ["culture", "poetry", "lyric"], ["culture_lit_poetry", "culture_lit_glossary"], "可表现誓言、悼念、赞美或自我辩护；第一人称诗人不等于作者本人。"),
    ("culture_poetry_narrative", "叙事诗", "以韵文或节奏化语言讲述人物、旅途、战争或家族事件。", ["culture", "poetry", "narrative"], ["culture_lit_poetry", "culture_lit_epic"], "重复句、固定意象和歌者评论可以帮助口述，但不要求所有语言押同一种韵。"),
    ("culture_poetry_epic", "史诗传统", "围绕英雄、神祇、战争或共同体起源组织的长篇叙事传统。", ["culture", "poetry", "epic", "oral"], ["culture_lit_epic", "culture_lit_oral"], "史诗也是共同体记忆和价值争论；不同讲述者可以保留互相矛盾的版本。"),
    ("culture_poetry_elegy", "挽歌与悼亡诗", "围绕死亡、离别、失去和记忆组织的诗歌或仪式文本。", ["culture", "poetry", "ritual"], ["culture_lit_poetry", "culture_lit_oral"], "可以表达悲伤、愤怒、债务或抗议，不预设所有文化都有相同悼亡规则。"),
    ("culture_poetry_song", "民谣与劳动歌", "在劳动、旅行、饮酒或聚会中反复传唱的短歌与口头诗。", ["culture", "poetry", "oral", "class"], ["culture_lit_oral", "culture_lit_poetry"], "重复和即兴改词让群体参与，也可传播讽刺、传闻或隐秘指引。"),
    ("culture_poetry_haiku", "俳句式瞬景诗", "借鉴日本俳句的季节感、切分和瞬间意象，用短文本留下余韵。", ["culture", "poetry", "japanese", "minimal"], ["culture_lit_haiku", "culture_lit_glossary"], "不把五七五当作所有俳句或所有日语诗的硬规则；游戏中应标明是借鉴结构。"),
    ("culture_novel_picaresque", "流浪汉小说结构", "以边缘人物或机灵旅行者的生计、骗局和社会观察串联章节。", ["culture", "novel", "class", "journey"], ["culture_lit_novel"], "流浪不等于自由；债务、法律、饥饿和名声让失败产生新的路线。"),
    ("culture_novel_gothic", "哥特小说氛围", "以封闭空间、家族记忆、秘密、恐惧和不可靠解释制造悬疑。", ["culture", "novel", "horror", "mystery"], ["culture_lit_novel"], "恐怖可以来自继承、禁忌和制度压力；不把精神疾病当作恐怖机制。"),
    ("culture_novel_epistolary", "书信体小说", "通过书信、日记、报告、账本或多份文书拼接叙事。", ["culture", "novel", "epistolary", "evidence"], ["culture_lit_novel"], "文书的日期、缺页、转交和伪造可成为线索，但一封信不等于真相。"),
    ("culture_novel_frame", "框架叙事", "由外层讲述者引出一个或多个内层故事，故事之间可以互相评论。", ["culture", "novel", "oral", "rumor"], ["culture_lit_nights", "culture_lit_oral"], "旅店、审讯、法庭、档案或家庭聚会都能成为框架；版本差异要有来源。"),
    ("culture_novel_coming_age", "成长小说结构", "围绕角色从一种身份、依赖或信念进入另一种状态的叙事结构。", ["culture", "novel", "identity", "development"], ["culture_lit_novel"], "成长不等于变善或变强；长期变化需要事件证据和玩家选择。"),
    ("culture_novel_social", "社会现实主义视角", "把日常生计、制度、阶层关系和物质约束放在人物叙事中心。", ["culture", "novel", "class", "politics"], ["culture_lit_novel"], "现实主义要求幻想也有分配后果；不要用阶层标签替 NPC 说出统一立场。"),
    ("culture_lit_courtly", "宫廷诗与赞助", "由宫廷、贵族、宗教机构或富商赞助的诗歌与文艺生产关系。", ["culture", "poetry", "class", "power"], ["culture_lit_poetry", "culture_lit_novel"], "保护、收入、审查和赞助者期待同时影响创作者；赞助不等于认同。"),
    ("culture_lit_translation", "翻译与改写", "把作品从一种语言、媒介或制度语境转入另一种语境的实践。", ["culture", "language", "translation"], ["culture_lit_novel", "culture_lit_oral"], "翻译会改变押韵、称谓、隐喻和阶层语气；模型不能用直译替代已确定事实。"),
    ("culture_lit_folklore", "民间故事母题", "在社群中反复流传、可被改写的故事结构与意象集合。", ["culture", "story", "oral", "motif"], ["culture_lit_oral", "culture_lit_epic"], "母题可跨地域出现，但每次落地都受人物、场景和价值观改写。"),
]
write("culture-literature", "诗歌、小说、口述传统与文化叙事结构；全部为待审创作候选，不自动进入世界。", LIT_SOURCES,
      [element(i, n, s, t, r, note) for i, n, s, t, r, note in LIT])

ASIA_SOURCES = [
    src("names_asia_behind", "Behind the Name: language and regional usage", "https://www.behindthename.com/names/usage", "按语言、地区和历史用途整理名字；具体拼写与时代用法需逐名核对。"),
    src("names_asia_chinese", "Chinese languages — Encyclopaedia Britannica", "https://www.britannica.com/place/China/Languages", "中文语言与文化背景；不把现代姓名规则外推到所有历史时期。"),
    src("names_asia_japanese", "Japan: Language — Encyclopaedia Britannica", "https://www.britannica.com/place/Japan/Language", "日语书写与称谓背景；同一汉字可能有不同读法。"),
    src("names_asia_korean", "Korea: Language — Encyclopaedia Britannica", "https://www.britannica.com/place/Korea/Language", "韩语语言与罗马化背景；具体姓名读法需要固定系统。"),
    src("names_asia_india", "India: Languages — Encyclopaedia Britannica", "https://www.britannica.com/place/India/Languages", "印度语言多样性和命名背景；不能用单一规则覆盖所有地区。"),
    src("names_asia_arabic", "Arabic language — Encyclopaedia Britannica", "https://www.britannica.com/topic/Arabic-language", "阿拉伯语姓名与语言背景；家族、父名、地域和称号因地而异。"),
    src("names_asia_persian", "Persian language — Encyclopaedia Britannica", "https://www.britannica.com/topic/Persian-language", "波斯语语言与文化背景；历史称谓和现代姓氏制度需分开。"),
    src("names_asia_vietnamese", "Vietnam: Languages — Encyclopaedia Britannica", "https://www.britannica.com/place/Vietnam/Languages", "越南语与文字背景；姓名顺序和时代用法需要本地化核对。"),
]
ASIA = [
    ("names_asian_sinitic", "汉语姓名池", "汉字姓氏、单字或双字名、字/号与称谓组合的创作姓名池。", ["names", "asian", "sinitic"], ["names_asia_chinese", "names_asia_behind"], "姓通常在前、名在后；池内示例：李、王、张、陈、林、赵、沈、顾、明、安、兰、宁。"),
    ("names_asian_japanese", "日语姓名池", "结合家名、汉字或假名读法和敬称的日本式创作姓名池。", ["names", "asian", "japanese"], ["names_asia_japanese", "names_asia_behind"], "同一汉字可有多种读法；池内示例：佐藤、铃木、山本、田中、渡边、春、莲、葵、凛、千代。"),
    ("names_asian_korean", "韩语姓名池", "以家族姓、双音节名字和罗马化变体构成的韩语创作姓名池。", ["names", "asian", "korean"], ["names_asia_korean", "names_asia_behind"], "常见现代结构不是全部历史结构；池内示例：金、李、朴、崔、郑、智勋、敏书、秀妍、泰成、贤宇。"),
    ("names_asian_indic", "南亚姓名池", "覆盖南亚多语言背景的示例姓名池，强调地区、宗教和家族差异。", ["names", "asian", "south-asia"], ["names_asia_india", "names_asia_behind"], "池内示例：阿迪蒂、阿努什卡、拉维、维克拉姆、米拉、卡维、阿鲁恩、德维、帕特尔、奈尔；不能代表整个南亚。"),
    ("names_asian_arabic", "阿拉伯语姓名池", "以个人名、父名、家族/部族名、地名或尊称组合的创作姓名池。", ["names", "asian", "arabic"], ["names_asia_arabic", "names_asia_behind"], "池内示例：阿米娜、莱拉、萨米尔、纳迪尔、哈桑、玛丽亚姆、法里德、扎伊德、哈达德、曼苏尔。"),
    ("names_asian_persian", "波斯语姓名池", "以个人名、家族名、地名和诗性称号组成的波斯语创作姓名池。", ["names", "asian", "persian"], ["names_asia_persian", "names_asia_behind"], "池内示例：达里乌什、法鲁克、帕尔文、希琳、纳维德、罗克珊娜、卡维、萨拉。"),
    ("names_asian_turkic", "突厥语族姓名池", "面向中亚、安纳托利亚和草原背景的示例姓名池。", ["names", "asian", "turkic", "steppe"], ["names_asia_behind", "names_asia_persian"], "池内示例：阿尔斯兰、艾达、丹尼兹、埃姆雷、阿依谢、巴图尔、图兰、塞尔坎；不能代表整个突厥语族。"),
    ("names_asian_vietnamese", "越南语姓名池", "以姓在前、个人名在后和多字名结构为灵感的越南语创作姓名池。", ["names", "asian", "vietnamese"], ["names_asia_vietnamese", "names_asia_behind"], "池内示例：阮、陈、黎、范、黄、明、兰、芳、安、玉；需要固定转写与声调显示。"),
    ("names_asian_mongolic", "蒙古语姓名池", "以草原个人名、家族/部族关系和称号为灵感的创作姓名池。", ["names", "asian", "mongolic", "steppe"], ["names_asia_behind", "names_asia_persian"], "池内示例：巴特尔、额尔登、苏赫、奥云、萨兰、图门、纳兰、博尔特；不把草原名当成固定模板。"),
]
write("names-asian", "亚洲姓名与命名传统候选池；示例名只用于创作，不等于人口统计或身份判定。", ASIA_SOURCES,
      [element(i, n, s, t, r, note, aliases=note.replace("；", "，").replace("、", "，").split("：")[-1].replace("。", "").split("，")) for i, n, s, t, r, note in ASIA])

EURO_SOURCES = [
    src("names_europe_behind", "Behind the Name: European usage", "https://www.behindthename.com/names/usage", "按语言、地区和历史用途整理欧洲名字；具体拼写与时代用法需逐名核对。"),
    src("names_europe_english", "English language — Encyclopaedia Britannica", "https://www.britannica.com/topic/English-language", "英语语言与历史背景；不把现代英语名字外推到所有历史时期。"),
    src("names_europe_french", "French language — Encyclopaedia Britannica", "https://www.britannica.com/topic/French-language", "法语语言背景；地区、阶层与历史拼写存在差异。"),
    src("names_europe_german", "German language — Encyclopaedia Britannica", "https://www.britannica.com/topic/German-language", "德语语言背景；复合姓氏、方言和历史拼写需按时代处理。"),
    src("names_europe_italian", "Italian language — Encyclopaedia Britannica", "https://www.britannica.com/topic/Italian-language", "意大利语语言背景；地区和家族命名差异明显。"),
    src("names_europe_slavic", "Slavic languages — Encyclopaedia Britannica", "https://www.britannica.com/topic/Slavic-languages", "斯拉夫语族背景；各语言的姓名后缀和转写不可互换。"),
    src("names_europe_greek", "Greek language — Encyclopaedia Britannica", "https://www.britannica.com/topic/Greek-language", "希腊语语言背景；古典、拜占庭和现代姓名应分开处理。"),
    src("names_europe_celtic", "Celtic languages — Encyclopaedia Britannica", "https://www.britannica.com/topic/Celtic-languages", "凯尔特语族背景；“凯尔特风”不是单一姓名系统。"),
]
EURO = [
    ("names_europe_english", "英语姓名池", "以英语地区个人名、家族名和职业/地名姓为灵感的创作姓名池。", ["names", "european", "english"], ["names_europe_english", "names_europe_behind"], "池内示例：威廉、爱德华、爱丽丝、埃莉诺、托马斯、玛格丽特、贝克、库珀、伍德、哈珀。"),
    ("names_europe_french", "法语姓名池", "以法语个人名、复合名、家族名和地名姓为灵感的创作姓名池。", ["names", "european", "french"], ["names_europe_french", "names_europe_behind"], "池内示例：让、皮埃尔、克莱尔、玛德琳、路易、伊莎贝尔、杜邦、勒鲁、莫罗、拉丰。"),
    ("names_europe_germanic", "德语/日耳曼姓名池", "以德语区个人名、复合名、家族名和职业姓为灵感的创作姓名池。", ["names", "european", "germanic"], ["names_europe_german", "names_europe_behind"], "池内示例：汉斯、弗里德里希、格蕾塔、安娜、奥托、玛蒂尔达、施密特、瓦格纳、克莱因、霍夫曼。"),
    ("names_europe_italian", "意大利语姓名池", "以意大利语区个人名、家族名和地域姓为灵感的创作姓名池。", ["names", "european", "italian"], ["names_europe_italian", "names_europe_behind"], "池内示例：马可、卢卡、乔瓦尼、比安卡、朱莉娅、贝娅特丽切、罗西、孔蒂、费雷蒂、莫雷蒂。"),
    ("names_europe_iberian", "西班牙/葡萄牙姓名池", "以伊比利亚个人名、复合名和双家族姓为灵感的创作姓名池。", ["names", "european", "iberian"], ["names_europe_behind", "names_europe_english"], "池内示例：迭戈、卡洛斯、伊莎贝尔、卡门、若昂、贝阿特丽斯、加西亚、罗德里格斯、席尔瓦、科斯塔。"),
    ("names_europe_slavic", "斯拉夫姓名池", "按东、南、西斯拉夫语言背景提供个人名、父名和家族后缀的创作池。", ["names", "european", "slavic"], ["names_europe_slavic", "names_europe_behind"], "池内示例：亚历山大、米哈伊尔、安娜、娜杰日达、米拉、卡塔琳娜、伊万诺夫、科瓦尔斯基、诺瓦克、彼得罗夫。"),
    ("names_europe_greek", "希腊语姓名池", "结合古典、拜占庭和现代希腊语背景的创作姓名池。", ["names", "european", "greek"], ["names_europe_greek", "names_europe_behind"], "池内示例：尼科斯、安德烈亚斯、埃琳妮、索菲娅、德米特里、伊莲娜、帕帕佐普洛斯、尼古拉迪斯。"),
    ("names_europe_celtic", "凯尔特语族姓名池", "提供爱尔兰、威尔士、苏格兰等背景的创作姓名池。", ["names", "european", "celtic"], ["names_europe_celtic", "names_europe_behind"], "池内示例：布兰、康纳、奥因、梅芙、布里吉德、格温、麦克劳德、奥康纳、琼斯、埃文斯。"),
    ("names_europe_nordic", "北日耳曼姓名池", "以北欧个人名、父名/母名和自然意象为灵感的创作姓名池。", ["names", "european", "nordic"], ["names_europe_german", "names_europe_behind"], "池内示例：埃里克、莱夫、英格丽、弗蕾雅、斯文、阿斯特丽德、安德森、约翰逊、埃里克松。"),
]
write("names-european", "欧洲姓名与命名传统候选池；示例名只用于创作，不等于历史人口统计或身份判定。", EURO_SOURCES,
      [element(i, n, s, t, r, note, aliases=note.replace("；", "，").replace("、", "，").split("：")[-1].replace("。", "").split("，")) for i, n, s, t, r, note in EURO])


if __name__ == "__main__":
    print("created", ", ".join(p.name for p in ROOT.glob("culture-literature.json")))
