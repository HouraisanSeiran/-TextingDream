# Wiki 待收集清单

本机目前打不开 Wikipedia 和 Britannica。下面这些来源在资料条目文件里仍标为 `access: search_only`，等能访问时统一收集。
收集后按 `docs/human-encyclopedia/collection-spec.md` 的写法：把来源改成 `access: read`，在 `supports` 里写明支撑了条目哪几句话，并更新条目的 `evidence_and_uncertainty`。

收集时每条要回答「要核对的点」一栏里的问题；核对不到的写进 `evidence_and_uncertainty`，不要删掉问题。

## 1. 国家与政体 `docs/element-catalog/polities.json`

| 资料条目 | 待读来源 | 要核对的点 |
|---|---|---|
| polity_feudal_kingdom 封建王国 | [Monarchy](https://en.wikipedia.org/wiki/Monarchy)；[Feudalism (Britannica)](https://www.britannica.com/topic/feudalism) | 封授与效忠的典型结构；百度百科「西欧封建制度」只读到摘要，需补正文 |
| polity_parliamentary_monarchy 议会君主国 | [Constitutional monarchy](https://en.wikipedia.org/wiki/Constitutional_monarchy) | 议会制与二元制的区别；19 世纪的典型例子 |
| polity_bureaucratic_empire 官僚制帝国 | [Empire](https://en.wikipedia.org/wiki/Empire) | 罗马、波斯、中国的官僚制具体做法（百度百科未核对到） |
| polity_industrial_republic 工业共和国 | [Republic](https://en.wikipedia.org/wiki/Republic) | 19 世纪工业化共和国的例子；「工会、财阀」部分目前是设计取舍 |
| polity_city_state_league 城邦与城市同盟 | [City-state (Britannica)](https://www.britannica.com/topic/city-state) | 僭主、同盟霸权（如提洛同盟）未核对 |
| polity_theocratic_state 神权国 | [Theocracy](https://en.wikipedia.org/wiki/Theocracy) | 历史例子与权力结构 |
| polity_tribal_confederation 部族联盟 | [Tribe](https://en.wikipedia.org/wiki/Tribe) | 古典及以后时代仍存在的部族联盟例子（支撑「classical 及以后档位可出现」的设计） |
| polity_merchant_republic 商业共和国 | [Merchant republic](https://en.wikipedia.org/wiki/Merchant_republic)；[Hanseatic League (Britannica)](https://www.britannica.com/topic/Hanseatic-League) | 威尼斯共和国正文（百度百科只读到摘要）；汉萨同盟的范围与年代 |
| polity_mage_council_state 法师议会魔导国 | 无 | 原创，不需收集 |

## 2. 种族补充 `docs/element-catalog/races-supplement.json`

| 资料条目 | 待读来源 | 要核对的点 |
|---|---|---|
| race_deepseam_delvers 深井矿居族 | [Coal mining (Britannica)](https://www.britannica.com/technology/coal-mining)；[dwarf (Britannica)](https://www.britannica.com/topic/dwarf-mythology)；[Coalworkers' pneumoconiosis](https://en.wikipedia.org/wiki/Coalworkers%27_pneumoconiosis) | 公司镇、实物工资、童工；矮人在北欧与日耳曼民间传说里的形象（百度百科落到《魔戒》义项） |
| race_cogwork_grafted 机体嫁接者 | [Prosthesis](https://en.wikipedia.org/wiki/Prosthesis) | 19 世纪义肢的材料与水平 |
| race_canal_boat_clans 运河船民氏族 | [Narrowboat](https://en.wikipedia.org/wiki/Narrowboat) | 英国窄船船民的家庭生活、居住与社会地位（百度百科无词条） |
| race_forge_kindred 炉火裔 | [Salamander (legendary creature)](https://en.wikipedia.org/wiki/Salamander_(legendary_creature))；[Foundry](https://en.wikipedia.org/wiki/Foundry) | 火蜥蜴是火中生物的传说来源（帕拉塞尔苏斯等）；铸造厂工序 |
| race_animated_servitors 魔偶劳役种 | [Golem](https://en.wikipedia.org/wiki/Golem) | 拉比勒夫传说的成文年代；百度百科说「可能源于 19 世纪上半叶德语文学」需复核 |
| race_gaslight_fae 煤灯下的妖精 | [Fairy](https://en.wikipedia.org/wiki/Fairy) | 欧洲 fairy 传说；怕铁的说法出处（百度百科无对应词条） |

以下 URL 是按常见页面名推测的，收集时先确认页面存在：Narrowboat、Salamander (legendary creature)、Fairy、Golem。

## 3. 蒸汽与近现代技术 `docs/element-catalog/steam-tech.json`

| 资料条目 | 待读来源 | 要核对的点 |
|---|---|---|
| tech_steam_locomotive 蒸汽机车 | [Locomotive](https://en.wikipedia.org/wiki/Locomotive) | 1804 特里维西克、1814/1825 斯蒂芬森的先后（百度百科前后矛盾） |
| tech_electric_telegraph 电报 | [Electrical telegraph](https://en.wikipedia.org/wiki/Electrical_telegraph) | 1837 专利、1839 线路、海底电缆年份复核 |
| tech_coal_gas_lighting 煤气照明 | [Gas lighting](https://en.wikipedia.org/wiki/Gas_lighting) | 默多克 1792 / 1808；城市煤气管网普及年代 |
| tech_ironclad_warship 铁甲舰 | [Ironclad warship](https://en.wikipedia.org/wiki/Ironclad_warship) | 1859 光荣号、1862 汉普顿锚地、1873 纯蒸汽 |
| tech_breech_loading_rifle 后膛步枪 | [Breech-loading weapon](https://en.wikipedia.org/wiki/Breech-loading_weapon) | 德莱赛针发枪 1841 列装 |
| tech_bessemer_steel 转炉炼钢 | [Bessemer process](https://en.wikipedia.org/wiki/Bessemer_process) | 1856、1879 托马斯法、平炉 |
| tech_internal_combustion_engine 内燃机 | [Internal combustion engine](https://en.wikipedia.org/wiki/Internal_combustion_engine) | 1860 勒努瓦、1876 奥托、1885 前后汽油机（档位已定：按 1880 年代后的汽油机 / 车用内燃机算近现代 `tech:early_modern`，与机枪同档；只需复核年份） |
| tech_electric_power_grid 电力电网 | [Electrical grid](https://en.wikipedia.org/wiki/Electrical_grid) | 1882 珍珠街电站、早期直流小网、交直流之争（百度百科只讲现代电网） |
| tech_wireless_radio 无线电 | [Radio](https://en.wikipedia.org/wiki/Radio) | 马可尼、特斯拉专利之争；1906、1922 广播 |
| tech_early_airplane 早期飞机 | [Airplane](https://en.wikipedia.org/wiki/Airplane) | 1903 首飞；一战军用 |
| tech_machine_gun 机枪 | [Machine gun](https://en.wikipedia.org/wiki/Machine_gun) | 1884 马克沁；MG34（1934）作为二战前通用机枪 |
| tech_armoured_vehicle 早期装甲车与坦克 | [Tank](https://en.wikipedia.org/wiki/Tank) | 1915 试制、1916 Ⅰ型 |

## 4. 大类 `docs/element-catalog/categories.json`

大类本身是对已有资料条目的分组，不需要来源。新增资料条目进大类时，若该资料条目有 search_only 来源，请追加到本清单。

## 5. 已知抓取问题（换源时注意）

- Wikipedia（中英）连接超时；Britannica、知乎返回 403。
- 百度百科需要无头浏览器（执行人机验证脚本）；直接请求只拿到验证页。
- 百度百科易落到错误义项：「魔像」→《英雄无敌》单位，「矮人」→《魔戒》，「Fairy」→韩国歌曲，「萨拉曼达」→游戏角色，「煤气灯」→本生灯。
