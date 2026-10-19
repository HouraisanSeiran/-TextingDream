from pathlib import Path
root=Path(__file__).resolve().parents[1]/'artifacts/village-complete/src'
p=root/'client/java/com/minecraftzombiearmy/WorkMapScreen.java'
s=p.read_text(encoding='utf-8')
s=s.replace('final List<WorkerMarker> markers=new ArrayList<>();','final List<WorkerMarker> markers=new ArrayList<>();\n    final DualGridTerrain terrain=new DualGridTerrain();')
a=s.index('TacticalTerrain.draw(g,c,snapshot.get(')
b=s.index('if(mx>=x',a)
s=s[:a]+s[b:]
s=s.replace('if(snapshot!=null&&TacticalMapScreen.sameDimension(snapshot)){','if(snapshot!=null&&TacticalMapScreen.sameDimension(snapshot)){\n            terrain.draw(g,snapshot,gridX,gridY,size,biomeLayer);')
s=s.replace('        }g.disableScissor();','            VillageMapDecoration.draw(this,g,mx,my);\n        }g.disableScissor();')
s=s.replace('    @Override public boolean isPauseScreen()', '    @Override public void removed(){terrain.close();super.removed();}\n    @Override public boolean isPauseScreen()')
p.write_text(s,encoding='utf-8')
print('WorkMapScreen wired')
