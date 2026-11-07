/*
 * 织梦 · race-fort-2 预览场景配置：每族一圈不规则辐条墙（正交 + 45° 斜段）+ 2–3 座棱垒 / 棱堡（替换墙格）+ 该族要塞地标。
 * segs 从 start 出发、必须回到起点；bastions 的 c / r 是占地左上格，attach 墙格由 meta.attach_cells 决定。
 * 兽人本批没有新棱堡，外挂 race-fort 已有的尖桩土垒（forts，不替换墙格）。zoom = 棱堡与辐条对接处特写窗口（世界坐标）。
 */
window.RF2_CFG = {
  elf: {
    title: '精灵：荆棘藤墙 + 荆棘棱垒（N / W / SE）+ 树冠要塞',
    race: 'elf', start: [2, 1],
    segs: [['e', 8], ['se', 4], ['s', 4], ['sw', 3], ['w', 7], ['nw', 3], ['n', 6], ['ne', 1], ['n', 1]],
    nodeVar: function (c, r) { return (c + r) % 3 === 0 ? 'west-elf-wallnode-02' : 'west-elf-wallnode-01'; },
    bastions: [{ id: 'west-elf-thornbastion-n', c: 5, r: 0 }, { id: 'west-elf-thornbastion-w', c: 0, r: 5 }, { id: 'west-elf-thornbastion-se', c: 12, r: 10 }],
    landmark: { id: 'west-elf-fortress-01', c: 5, r: 4 },
    vb: [-10, -80, 16 * 48 + 10, 13 * 48 + 80], zoom: [11 * 48, 8.6 * 48, 4 * 48, 3.6 * 48]
  },
  dwarf: {
    title: '矮人：巨石城墙 + 石棱堡（N / NE / S）+ 阶梯山城',
    race: 'dwarf', start: [2, 2],
    segs: [['e', 9], ['se', 4], ['s', 5], ['sw', 2], ['w', 9], ['nw', 2], ['n', 9]],
    nodeVar: function (c, r) { return (c + r) % 3 === 0 ? 'west-dwarf-wallnode-02' : 'west-dwarf-wallnode-01'; },
    bastions: [{ id: 'west-dwarf-bastion-n', c: 5, r: 0 }, { id: 'west-dwarf-bastion-ne', c: 12, r: 3 }, { id: 'west-dwarf-bastion-s', c: 7, r: 13 }],
    landmark: { id: 'west-dwarf-fortress-01', c: 5, r: 5 },
    vb: [0, -100, 17 * 48, 16 * 48 + 100], zoom: [10.5 * 48, 0.6 * 48, 5 * 48, 5 * 48]
  },
  orc: {
    title: '兽人：尖木栅墙 + 尖桩土垒（race-fort 已有，N / E / W）+ 尖桩大寨',
    race: 'orc', start: [2, 2],
    segs: [['e', 8], ['se', 2], ['s', 5], ['sw', 2], ['w', 2], ['nw', 1], ['sw', 1], ['w', 3], ['nw', 1], ['n', 8]],
    nodeVar: function (c, r) { return (c + r) % 4 === 0 ? 'west-orc-wallnode-02' : 'west-orc-wallnode-01'; },
    forts: [{ id: 'west-orc-earthwork-n', c: 5, r: 1 }, { id: 'west-orc-earthwork-e', c: 12, r: 5 }, { id: 'west-orc-earthwork-w', c: 1, r: 6 }],
    landmark: { id: 'west-orc-fortress-01', c: 4, r: 4 },
    // 第一轮截图：特写窗口误框成了整座大寨，改框东侧土垒与幕墙对接处
    vb: [0, -60, 14 * 48, 12 * 48 + 60], zoom: [10.6 * 48, 3.6 * 48, 3.4 * 48, 4 * 48]
  }
};
