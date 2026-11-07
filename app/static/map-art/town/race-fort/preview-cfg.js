/*
 * 织梦 · race-fort 预览场景配置：每族一圈不规则城墙（正交 + 45° 斜段，带凹角）+ 已有城门 + 节点塔 + 外凸工事。
 * segs 是从 start 出发的 [方向, 步数]，必须回到起点。zoom 是斜段对接处 3 倍特写的世界坐标窗口。
 */
window.RF_CFG = {
  elf: {
    title: '精灵：不规则荆棘藤墙拼接验证',
    note: '北墙正交直段放 west-elf-wall-gate-h，西墙放 gate-v；拐点放树冠哨塔；南墙中段一处 V 形凹角；东墙外接藤木哨台。',
    race: 'elf', start: [2, 1],
    segs: [['e', 5], ['se', 2], ['s', 3], ['sw', 2], ['w', 1], ['nw', 2], ['sw', 1], ['w', 1], ['nw', 1], ['n', 3], ['ne', 1], ['n', 1]],
    gateMode: 'overlay', gateIds: { h: 'west-elf-wall-gate-h', v: 'west-elf-wall-gate-v' },
    gates: [{ c: 4, r: 1, kind: 'h' }, { c: 1, r: 4, kind: 'v' }],
    towers: { '7,1': 'west-elf-walltower-01', '9,6': 'west-elf-walltower-01', '4,6': 'west-elf-walltower-01' },
    nodeVar: function (c, r) { return (c + r) % 3 === 0 ? 'west-elf-wallnode-02' : 'west-elf-wallnode-01'; },
    forts: [{ id: 'west-elf-vineoutpost-01', c: 10, r: 3 }],
    vb: [0, -120, 13 * 48, 10 * 48 + 120], zoom: [7.5 * 48, 0.6 * 48, 2.6 * 48, 2.6 * 48]
  },
  dwarf: {
    title: '矮人：不规则巨石城墙拼接验证',
    note: '北墙正交直段放 west-dwarf-wall-gate-h，西墙放 gate-v；拐点放矮堡塔；南墙西段一处凹角；东墙外接嵌山石堡。',
    race: 'dwarf', start: [2, 1],
    segs: [['e', 5], ['se', 2], ['s', 3], ['sw', 2], ['w', 2], ['nw', 1], ['w', 1], ['sw', 1], ['w', 1], ['n', 6], ['ne', 1]],
    gateMode: 'overlay', gateIds: { h: 'west-dwarf-wall-gate-h', v: 'west-dwarf-wall-gate-v' },
    gates: [{ c: 4, r: 1, kind: 'h' }, { c: 1, r: 5, kind: 'v' }],
    towers: { '7,1': 'west-dwarf-walltower-01', '9,6': 'west-dwarf-walltower-01', '4,7': 'west-dwarf-walltower-01' },
    nodeVar: function (c, r) { return (c + r) % 3 === 0 ? 'west-dwarf-wallnode-02' : 'west-dwarf-wallnode-01'; },
    forts: [{ id: 'west-dwarf-mountainfort-01', c: 10, r: 2 }],
    vb: [0, -140, 14 * 48, 10 * 48 + 140], zoom: [7.5 * 48, 0.4 * 48, 2.6 * 48, 2.6 * 48]
  },
  orc: {
    title: '兽人：不规则尖木栅墙拼接验证',
    note: '北墙正交直段放 west-orc-gate-h、西墙放 gate-v（兽人栅门是替换瓦片，门洞跨两个墙格，替掉这两格之间的两根辐条）；拐点放图腾瞭望塔；南墙 V 形凹角；外接三座尖桩土垒（E、SE、N）。',
    race: 'orc', start: [2, 2],
    segs: [['e', 5], ['se', 2], ['s', 3], ['sw', 2], ['w', 1], ['nw', 2], ['sw', 1], ['w', 1], ['nw', 1], ['n', 3], ['ne', 1], ['n', 1]],
    gateMode: 'replace', gateIds: { h: 'west-orc-gate-h', v: 'west-orc-gate-v' },
    gates: [{ c: 4, r: 2, kind: 'h' }, { c: 1, r: 5, kind: 'v' }],
    towers: { '7,2': 'west-orc-walltower-01', '9,7': 'west-orc-walltower-01', '4,7': 'west-orc-walltower-01' },
    nodeVar: function (c, r) { return (c + r) % 4 === 0 ? 'west-orc-wallnode-02' : 'west-orc-wallnode-01'; },
    // 第二轮按截图修：土垒底边（城内侧）压到幕墙中心线上，不再悬空
    forts: [{ id: 'west-orc-earthwork-e', c: 9, r: 4 }, { id: 'west-orc-earthwork-se', c: 8, r: 8 }, { id: 'west-orc-earthwork-n', c: 6, r: 0 }],
    vb: [0, -100, 13 * 48, 11 * 48 + 100], zoom: [7.5 * 48, 1.6 * 48, 2.6 * 48, 2.6 * 48]
  }
};
