package com.minecraftzombiearmy.work;

import com.minecraftzombiearmy.ArmyMod;
import net.minecraft.core.*;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.*;
import net.minecraft.world.Container;
import net.minecraft.world.SimpleContainer;
import net.minecraft.world.entity.*;
import net.minecraft.world.entity.monster.Monster;
import net.minecraft.world.entity.npc.villager.Villager;
import net.minecraft.world.item.*;
import net.minecraft.world.level.block.*;
import net.minecraft.world.level.block.entity.FurnaceBlockEntity;
import net.minecraft.world.level.block.state.properties.BedPart;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.phys.AABB;
import java.util.*;
import static com.minecraftzombiearmy.ArmyConfig.require;

/** All inventory, world, navigation and population mutations execute on the server thread. */
public final class VillageEconomy {
    private final WorkManager m;
    private static final List<String> FOOD=List.of("minecraft:bread","minecraft:baked_potato","minecraft:carrot");
    private static final List<String> SEEDS=List.of("minecraft:wheat_seeds","minecraft:carrot","minecraft:potato");
    private final Map<String,WorkOrder> routines=new HashMap<>();
    public VillageEconomy(WorkManager manager){m=manager;}
    private WorkOrder routine(Villager v){return routines.computeIfAbsent(v.getStringUUID(),id->{WorkOrder o=new WorkOrder();o.id="routine_"+id;o.workerUuid=id;return o;});}
    public boolean controls(Villager v){Settlement s=m.affiliation(v);return s!=null&&s.residents.containsKey(v.getStringUUID());}
    public void assign(Settlement s,Villager v,String job,BlockPos station){
        require(Set.of("idle","gatherer","builder","farmer").contains(job),"未知岗位");
        require(WorkManager.employable(v)&&(m.affiliation(v)==null||m.affiliation(v)==s),"村民不可任职或属于其他聚落");
        require(m.current(v)==null,"先结束当前工单再调整岗位");
        require(station.distSqr(m.warehousePos(s))<96*96,"工作站超出村庄范围");
        Resident r=s.residents.computeIfAbsent(v.getStringUUID(),id->new Resident());r.job=job;r.stationX=station.getX();r.stationY=station.getY();r.stationZ=station.getZ();r.joined=v.level().getGameTime();
        s.workers.add(v.getStringUUID());((WorkerAppearance)v).textingdream$worker(!job.equals("idle"));v.setPersistenceRequired();m.save();
    }
    public void recruitment(Settlement s,String mode){require(Set.of("off","camp","pioneer").contains(mode),"未知招募方式");s.recruiting=!mode.equals("off");if(s.recruiting)s.recruitment=mode;m.save();}
    public void preview(Settlement s,BlockPos anchor){
        require(s.plan==null||s.plan.state.equals("preview")||s.plan.state.equals("complete"),"已有正在施工的村庄计划");
        ServerLevel l=m.level(s.dimension);VillagePlan plan=new VillagePlan();plan.revision=s.revision+1;
        int x=anchor.getX(),z=anchor.getZ(),y=anchor.getY()-1;
        plan.sites.add(new VillagePlan.Site("medium_house",x,y,z));
        plan.sites.add(new VillagePlan.Site("medium_house",x,y,z+16));
        plan.sites.add(new VillagePlan.Site("medium_house",x+20,y,z));
        plan.sites.add(new VillagePlan.Site("medium_house",x+20,y,z+16));
        plan.sites.add(new VillagePlan.Site("farm",x,y,z+32));
        plan.sites.add(new VillagePlan.Site("work_area",x+20,y,z+32));
        Set<Long> occupied=new HashSet<>();
        for(var site:plan.sites){Blueprint bp=m.blueprint(site.blueprint);validateSite(s,site,occupied);for(var e:bp.materials.entrySet())plan.materials.merge(e.getKey(),e.getValue(),Integer::sum);}
        // Reserve every footprint before finding routes, including positions which are still air.
        List<BlockPos> entries=new ArrayList<>();entries.add(m.warehousePos(s).offset(-2,0,0));
        for(var site:plan.sites){var bp=m.blueprint(site.blueprint);var door=bp.blocks.stream().filter(b->b.block.endsWith("_door")&&"lower".equals(b.properties.get("half"))).findFirst();entries.add(door.map(b->new BlockPos(site.x+b.x-2,site.y,site.z+b.z)).orElse(new BlockPos(site.x-2,site.y,site.z+1)));}
        for(int i=1;i<entries.size();i++){
            final BlockPos a=entries.get(i-1),b=entries.get(i);
            java.util.function.BiFunction<Integer,Integer,RoadPlanner.Cell> surface=(cx,cz)->{
                if(Math.abs(cx-s.warehouseX)>96||Math.abs(cz-s.warehouseZ)>96)return null;
                BlockPos col=new BlockPos(cx,0,cz);if(!l.hasChunkAt(col))return null;
                BlockPos p=l.getHeightmapPos(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES,col).below();
                if(occupied.contains(new BlockPos(cx,0,cz).asLong())||!m.roadGround(l,p))return null;
                return new RoadPlanner.Cell(cx,p.getY(),cz);
            };
            var route=RoadPlanner.plan(surface.apply(a.getX(),a.getZ()),surface.apply(b.getX(),b.getZ()),surface);plan.roads.add(route);
            for(var c:route){BlockPos p=new BlockPos(c.x(),c.y(),c.z());if(plan.roadSurface.put(Long.toString(p.asLong()),l.getBlockState(p).toString())==null)plan.materials.merge("minecraft:cobblestone",1,Integer::sum);}
        }
        s.plan=plan;s.status="预览：4 栋双床住宅、农田、工作区及道路；等待确认";m.save();
    }
    private void validateSite(Settlement s,VillagePlan.Site site,Set<Long> occupied){
        var l=m.level(s.dimension);var bp=m.blueprint(site.blueprint);Set<Long> footprint=new HashSet<>();
        for(var b:bp.blocks){BlockPos p=new BlockPos(site.x+b.x,site.y+b.y,site.z+b.z);require(l.hasChunkAt(p)&&l.getWorldBorder().isWithinBounds(p)&&p.distSqr(m.warehousePos(s))<96*96,"计划超出已加载村庄范围");var old=l.getBlockState(p);require(old.isAir()||old.canBeReplaced()||m.foundation(l,p,b),"请先清理工地："+p.toShortString());
            footprint.add(new BlockPos(p.getX(),0,p.getZ()).asLong());
            for(var other:m.orders())if(WorkManager.isConstruction(other)&&other.dimension.equals(s.dimension))for(var c:other.plan)require(other.originX+c.x!=p.getX()||other.originY+c.y!=p.getY()||other.originZ+c.z!=p.getZ(),"计划与已有建筑重叠");
        }
        for(long key:footprint){var p=BlockPos.of(key);require(!occupied.contains(key),"建筑重叠");int surface=l.getHeightmapPos(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES,new BlockPos(p.getX(),0,p.getZ())).getY()-1;require(surface==site.y,"场地须平整，地表高度应为 "+site.y+"："+p.getX()+","+p.getZ());}
        occupied.addAll(footprint);
    }
    public void approve(Settlement s,boolean roads){require(s.plan!=null&&s.plan.state.equals("preview"),"没有待确认计划");Set<Long> occupied=new HashSet<>();for(var site:s.plan.sites)validateSite(s,site,occupied);s.plan.state="approved";s.plan.roadsApproved=roads;s.status="计划已批准，等待建筑工与材料";m.save();}
    public void tick(){
        for(Settlement s:m.settlements()){
            ServerLevel l=m.level(s.dimension);Container chest=m.warehouse(s);if(l==null||chest==null)continue;
            if(m.tick%100==0){census(s,l,chest);recruit(s,l,chest);}
            for(var entry:List.copyOf(s.residents.entrySet())){
                Villager v=m.findVillager(entry.getKey());if(v==null)continue;Resident r=entry.getValue();
                ((WorkerAppearance)v).textingdream$worker(!r.job.equals("idle"));
                // Custom work replaces the vanilla brain, including its door-opening behavior.
                for(var door:BlockPos.betweenClosed(v.blockPosition().offset(-1,0,-1),v.blockPosition().offset(1,1,1))){var state=l.getBlockState(door);if(state.getBlock() instanceof DoorBlock block&&!state.getValue(DoorBlock.OPEN)&&!state.is(Blocks.IRON_DOOR))block.setOpen(v,l,state,door,true);}
                if(!v.isAlive()){s.residents.remove(entry.getKey());s.workers.remove(entry.getKey());continue;}
                if(!v.level().dimension().identifier().toString().equals(s.dimension))continue;
                if(r.arriving){r.state="arriving";r.reason="从村庄外围步行迁入";if(walk(v,m.warehousePos(s),3)){r.arriving=false;r.state="idle";}continue;}
                if(!canWork(s,v,r.job.equals("farmer")))continue;
                if(m.current(v)!=null)continue;
                if(r.job.equals("farmer")){farm(s,v,chest);continue;}
                if(!s.automatic)continue;
                if(r.job.equals("gatherer")){if(replant(s,v,chest))continue;supply(s,v,chest);}
                if(r.job.equals("builder"))build(s,v);
            }
        }
    }
    private void census(Settlement s,ServerLevel l,Container chest){
        List<BlockPos> beds=new ArrayList<>();for(var p:BlockPos.betweenClosed(m.warehousePos(s).offset(-48,-8,-48),m.warehousePos(s).offset(48,12,48))){if(!l.hasChunkAt(p))continue;var state=l.getBlockState(p);if(state.getBlock() instanceof BedBlock&&state.getValue(BedBlock.PART)==BedPart.HEAD&&housingReady(s,l,p))beds.add(p.immutable());}
        s.beds=beds.size();s.food=food(chest);Set<Long> used=new HashSet<>();
        for(var r:s.residents.values())if(r.home!=null&&beds.contains(BlockPos.of(r.home))&&used.add(r.home)){}else r.home=null;
        for(var r:s.residents.values())if(r.home==null)for(var b:beds)if(used.add(b.asLong())){r.home=b.asLong();break;}
    }
    private boolean housingReady(Settlement s,ServerLevel l,BlockPos p){
        var state=l.getBlockState(p);BlockPos foot=p.relative(state.getValue(BedBlock.FACING).getOpposite());var other=l.getBlockState(foot);
        if(other.getBlock()!=state.getBlock()||other.getValue(BedBlock.PART)!=BedPart.FOOT||!l.getBlockState(p.above()).isAir()||!l.getBlockState(foot.above()).isAir())return false;
        for(var o:m.orders())if(o.dimension.equals(s.dimension)&&WorkManager.isConstruction(o))for(var b:o.plan)if(p.equals(new BlockPos(o.originX+b.x,o.originY+b.y,o.originZ+b.z)))return o.status.equals("completed");
        return true; // Player-provided camp beds remain valid without a construction order.
    }
    public static int food(Container chest){return WorkInventory.count(chest,"minecraft:bread")+WorkInventory.count(chest,"minecraft:baked_potato")+Math.max(0,WorkInventory.count(chest,"minecraft:carrot")-8);}
    public boolean canWork(Settlement s,Villager v,boolean emergencyFood){
        Resident r=s.residents.get(v.getStringUUID());if(r==null)return true;ServerLevel l=(ServerLevel)v.level();long now=l.getGameTime();Container chest=m.warehouse(s);
        if(r.arriving)return false;
        if(r.mealAt==0)r.mealAt=now+1200;
        if(now>=r.mealAt){r.hunger=Math.max(0,r.hunger-1);r.mealAt=now+1200;}
        var threats=l.getEntitiesOfClass(Monster.class,v.getBoundingBox().inflate(16),e->e.isAlive());
        if(!threats.isEmpty())r.unsafeUntil=now+200;
        if(now<r.unsafeUntil){r.state="retreat";r.reason="附近有怪物，保留任务并撤退";retreat(s,v,r,true);return false;}
        if(r.hunger<=16&&chest!=null&&food(chest)>0){r.state="eating";r.reason="前往仓库用餐";if(!walk(v,m.warehousePos(s),3))return false;for(String id:FOOD)if(WorkInventory.count(chest,id)>(id.endsWith(":carrot")?8:0)&&WorkInventory.consume(chest,id,1)){r.hunger=Math.min(20,r.hunger+6);break;}}
        boolean emergency=emergencyFood&&r.hunger<=6;
        if(r.hunger<=2&&!emergency){r.state="hungry";r.reason="严重缺粮，普通工作暂停；农民保留应急供粮";v.getNavigation().stop();return false;}
        if(l.getDefaultClockTime()%24000>=12000&&!emergency){r.state="rest";r.reason="夜间休息，白天续作";retreat(s,v,r,false);return false;}
        if(r.pioneerUntil>0&&now>r.pioneerUntil&&r.home==null){r.state="homeless";r.reason="拓荒露宿 3 日到期，请提供床位";return false;}
        if(r.hunger<=6&&m.tick%40!=0){r.state="hungry";r.reason="缺粮，低效工作";return false;}
        if(!r.state.equals("processing"))r.state="working";r.reason="";return true;
    }
    private void retreat(Settlement s,Villager v,Resident r,boolean threat){
        ServerLevel l=(ServerLevel)v.level();BlockPos target=r.home==null?m.warehousePos(s):BlockPos.of(r.home);
        for(int dx=-3;dx<=3;dx++)for(int dz=-3;dz<=3;dz++)for(int dy=-1;dy<=1;dy++){
            BlockPos p=target.offset(dx,dy,dz);if(!safe(l,p))continue;if(threat&&!l.getEntitiesOfClass(Monster.class,new AABB(p).inflate(12),e->e.isAlive()).isEmpty())continue;
            if(walk(v,p,1.5))v.getNavigation().stop();return;
        }
        r.reason="找不到安全退避点，请清除营地附近怪物或障碍";v.getNavigation().stop();
    }
    private boolean safe(ServerLevel l,BlockPos p){return l.hasChunkAt(p)&&l.getWorldBorder().isWithinBounds(p)&&l.getBlockState(p).isAir()&&l.getBlockState(p.above()).isAir()&&l.getBlockState(p.below()).isCollisionShapeFullBlock(l,p.below())&&l.getFluidState(p).isEmpty();}
    private boolean walk(Villager v,BlockPos pos,double reach){return m.approach(routine(v),v,pos,reach);}
    private void recruit(Settlement s,ServerLevel l,Container chest){
        if(!s.recruiting||l.getGameTime()<s.nextRecruit)return;
        int capacity=s.recruitment.equals("pioneer")?Math.max(4,s.beds):s.beds;
        if(s.residents.size()>=Math.min(8,capacity)){s.status="招募等待空余床位（拓荒营地最多 4 人）";return;}
        if(food(chest)<(s.residents.size()+1)*4){s.status="招募暂停：每位居民需要 4 份储备食物";return;}
        if(s.residents.values().stream().anyMatch(r->r.hunger<=6)){s.status="招募暂停：现有居民缺粮";return;}
        if(!l.getEntitiesOfClass(Monster.class,new AABB(m.warehousePos(s)).inflate(24),e->e.isAlive()).isEmpty()){s.status="招募暂停：营地不安全";return;}
        Villager candidate=null;
        for(var v:l.getEntitiesOfClass(Villager.class,new AABB(m.warehousePos(s)).inflate(48),WorkManager::employable))if(m.affiliation(v)==null&&m.current(v)==null&&!l.structureManager().getStructureWithPieceAt(v.blockPosition(),StructureTags.VILLAGE).isValid()){candidate=v;break;}
        if(candidate==null){
            for(int i=0;i<16;i++){double angle=i*Math.PI/8;BlockPos p=l.getHeightmapPos(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES,m.warehousePos(s).offset((int)(Math.cos(angle)*32),0,(int)(Math.sin(angle)*32)));
                if(!safe(l,p))continue;var v=new Villager(EntityTypes.VILLAGER,l);v.snapTo(p.getX()+.5,p.getY(),p.getZ()+.5);var path=v.getNavigation().createPath(m.warehousePos(s).west(),1);if(path==null||!path.canReach())continue;
                v.finalizeSpawn(l,l.getCurrentDifficultyAt(p),EntitySpawnReason.EVENT,null);v.setPersistenceRequired();l.addFreshEntity(v);candidate=v;break;
            }
        }
        if(candidate==null){s.status="招募等待可步行到营地的安全外围入口";return;}
        assign(s,candidate,"idle",m.warehousePos(s));Resident r=s.residents.get(candidate.getStringUUID());r.arriving=true;if(s.recruitment.equals("pioneer"))r.pioneerUntil=l.getGameTime()+72000;s.nextRecruit=l.getGameTime()+1200;s.status="有迁入者正在前往营地，抵达后手动任职";m.save();
    }
    private void build(Settlement s,Villager v){
        if(s.plan==null||!s.plan.state.equals("approved"))return;
        for(var site:s.plan.sites){if(!site.order.isEmpty()){WorkOrder o=order(site.order);if(o!=null&&o.status.equals("completed"))site.state="complete";else if(o!=null&&o.terminal()){site.state="cancelled";s.plan.reason="工单已取消，需人工处理";}continue;}
            try{WorkOrder o=m.startBuild(v,s,site.blueprint,new BlockPos(site.x,site.y,site.z));site.order=o.id;site.state="working";s.plan.reason="";}catch(IllegalArgumentException e){s.plan.reason=e.getMessage();}return;
        }
        if(s.plan.sites.stream().anyMatch(site->!site.state.equals("complete")))return;
        if(s.plan.roadsApproved&&s.plan.roadOrders.size()<s.plan.roads.size()){
            // Shared segments must finish before another road takes ownership of those cells.
            if(s.plan.roadOrders.stream().map(this::order).anyMatch(o->o!=null&&!o.terminal()))return;
            try{s.plan.roadOrders.add(m.startPlannedRoad(v,s,s.plan.roads.get(s.plan.roadOrders.size())).id);}catch(IllegalArgumentException e){s.plan.reason=e.getMessage();}return;
        }
        if(s.plan.roadsApproved&&s.plan.roadOrders.stream().map(this::order).anyMatch(o->o==null||!o.status.equals("completed")))return;
        s.plan.state="complete";s.status="村庄计划建成";m.save();
    }
    private WorkOrder order(String id){return m.orders().stream().filter(o->o.id.equals(id)).findFirst().orElse(null);}
    private void supply(Settlement s,Villager v,Container chest){
        Set<String> demands=new LinkedHashSet<>();
        for(var o:m.orders())if(o.settlementId.equals(s.id)&&o.active()&&WorkManager.isConstruction(o))for(var e:o.materials.entrySet()){
            String raw=WorkRecipes.missingRaw(chest,e.getKey(),Math.min(16,e.getValue()));if(raw.equals("minecraft:cobblestone")||raw.endsWith("_log")&&!raw.contains("stripped_"))demands.add(raw);
        }
        for(String raw:demands){if(m.orders().stream().anyMatch(o->o.settlementId.equals(s.id)&&!o.terminal()&&o.resource.equals(raw)))continue;
            var o=m.startGather(v,s,raw.equals("minecraft:cobblestone")?"gather_stone":"gather_wood",16);o.resource=raw;return;}
        s.residents.get(v.getStringUUID()).reason="等待木石需求";
    }
    public int forestCount(Settlement s,BlockPos center){
        ServerLevel l=m.level(s.dimension);int count=0;
        for(int x=-8;x<=8;x++)for(int z=-8;z<=8;z++){BlockPos col=center.offset(x,0,z);if(!l.hasChunkAt(col))continue;BlockPos top=l.getHeightmapPos(Heightmap.Types.WORLD_SURFACE,col);
            for(int dy=1;dy<=24;dy++){BlockPos p=top.below(dy);if(!l.getBlockState(p).is(BlockTags.LOGS)||!(l.getBlockState(p.below()).is(BlockTags.DIRT)||l.getBlockState(p.below()).is(Blocks.GRASS_BLOCK)))continue;
                boolean leaves=false;for(var leaf:BlockPos.betweenClosed(p.offset(-2,1,-2),p.offset(2,12,2)))if(l.hasChunkAt(leaf)&&l.getBlockState(leaf).is(BlockTags.LEAVES)){leaves=true;break;}if(leaves)count++;break;
            }
        }return count;
    }
    boolean replant(Settlement s,Villager v,Container chest){
        ServerLevel l=(ServerLevel)v.level();for(var entry:List.copyOf(s.replants.entrySet())){BlockPos p=BlockPos.of(entry.getKey());if(!l.hasChunkAt(p))continue;String id=entry.getValue();
            if(s.trees.containsKey(entry.getKey()))continue;
            if(!l.getBlockState(p).isAir()){if(l.getBlockState(p).getBlock() instanceof SaplingBlock)s.replants.remove(entry.getKey());continue;}
            if(!l.getBlockState(p.below()).is(BlockTags.DIRT)&&!l.getBlockState(p.below()).is(Blocks.GRASS_BLOCK)){s.residents.get(v.getStringUUID()).reason="补种点缺少土壤";continue;}
            if(WorkInventory.count(v.getInventory(),id)==0){if(WorkInventory.count(chest,id)==0){s.residents.get(v.getStringUUID()).reason="补种缺少实际树苗："+id;continue;}if(!walk(v,m.warehousePos(s),3))return true;WorkInventory.transfer(chest,v.getInventory(),id,1);return true;}
            if(!walk(v,p,3))return true;Item item=WorkInventory.item(id);if(!(item instanceof BlockItem bi)||!bi.getBlock().defaultBlockState().canSurvive(l,p)){s.residents.get(v.getStringUUID()).reason="树苗不能在此生长";continue;}
            if(l.setBlock(p,bi.getBlock().defaultBlockState(),3)){WorkInventory.consume(v.getInventory(),id,1);s.replants.remove(entry.getKey());}return true;
        }return false;
    }
    public boolean hasTool(Villager v,Container chest,TagKey<Item> tag,WorkOrder o,Settlement s){
        if(!findTool(v,tag).isEmpty())return true;if(!m.approach(o,v,m.warehousePos(s),3))return false;
        for(var e:WorkInventory.counts(chest).entrySet())if(new ItemStack(WorkInventory.item(e.getKey())).is(tag)){WorkInventory.transfer(chest,v.getInventory(),e.getKey(),1);return false;}
        o.failureReason="仓库缺少施工工具："+tag.location();return false;
    }
    private ItemStack findTool(Villager v,TagKey<Item> tag){for(int i=0;i<v.getInventory().getContainerSize();i++){var t=v.getInventory().getItem(i);if(t.is(tag))return t;}return ItemStack.EMPTY;}
    public void damageTool(Villager v,TagKey<Item> tag){var tool=findTool(v,tag);if(!tool.isEmpty())tool.hurtAndBreak(1,(ServerLevel)v.level(),null,item->{});}
    private void farm(Settlement s,Villager v,Container chest){
        Resident r=s.residents.get(v.getStringUUID());ServerLevel l=(ServerLevel)v.level();BlockPos center=new BlockPos(r.stationX,r.stationY,r.stationZ);
        List<BlockPos> plots=new ArrayList<>();for(var p:BlockPos.betweenClosed(center.offset(-8,-3,-8),center.offset(8,3,8)))if(l.hasChunkAt(p)&&l.getBlockState(p).is(Blocks.FARMLAND))plots.add(p.above().immutable());
        if(!r.foodStage.equals("idle")){processFood(s,v,chest);return;}
        if(deliverFood(s,v,chest))return;
        if(plots.isEmpty()){r.reason="工作站 8 格内没有已建成的耕地";processFood(s,v,chest);return;}
        for(BlockPos p:plots){var state=l.getBlockState(p);if(state.getBlock() instanceof CropBlock crop&&crop.isMaxAge(state)){
                if(!walk(v,p,3))return;List<ItemStack> drops=Block.getDrops(state,l,p,null,v,ItemStack.EMPTY);SimpleContainer probe=new SimpleContainer(v.getInventory().getContainerSize());for(int i=0;i<probe.getContainerSize();i++)probe.setItem(i,v.getInventory().getItem(i).copy());
                boolean fits=true;for(var drop:drops)if(WorkInventory.insert(probe,drop.copy())!=drop.getCount())fits=false;
                if(!fits){deliverFood(s,v,chest);return;}if(l.setBlock(p,Blocks.AIR.defaultBlockState(),3))for(var drop:drops)WorkInventory.insert(v.getInventory(),drop.copy());return;
            }}
        for(int i=0;i<plots.size();i++){BlockPos p=plots.get(i);if(!l.getBlockState(p).isAir())continue;String seed=SEEDS.get(i%3);
            if(WorkInventory.count(v.getInventory(),seed)==0){if(WorkInventory.count(chest,seed)==0)continue;if(!walk(v,m.warehousePos(s),3))return;WorkInventory.transfer(chest,v.getInventory(),seed,8);return;}
            if(!walk(v,p,3))return;CropBlock crop=(CropBlock)(seed.endsWith("wheat_seeds")?Blocks.WHEAT:seed.endsWith("carrot")?Blocks.CARROTS:Blocks.POTATOES);
            if(l.setBlock(p,crop.getStateForAge(0),3))WorkInventory.consume(v.getInventory(),seed,1);return;
        }
        if(deliverFood(s,v,chest))return;processFood(s,v,chest);
    }
    private boolean deliverFood(Settlement s,Villager v,Container chest){
        boolean cargo=WorkInventory.counts(v.getInventory()).entrySet().stream().anyMatch(e->FoodSupply.foodCargo(e.getKey(),e.getValue())>0);if(!cargo)return false;
        if(!walk(v,m.warehousePos(s),3))return true;int moved=0;
        for(var e:WorkInventory.counts(v.getInventory()).entrySet())moved+=WorkInventory.transfer(v.getInventory(),chest,e.getKey(),FoodSupply.foodCargo(e.getKey(),e.getValue()));
        if(moved==0)s.residents.get(v.getStringUUID()).reason="仓库已满，农产品暂存村民背包";return true;
    }
    private void processFood(Settlement s,Villager v,Container chest){
        ServerLevel l=(ServerLevel)v.level();Resident r=s.residents.get(v.getStringUUID());
        if(r.foodStage.equals("deliver")){
            if(r.furnaceCargo>0){if(!walk(v,m.warehousePos(s),3))return;r.furnaceCargo=Math.min(r.furnaceCargo,WorkInventory.count(v.getInventory(),"minecraft:potato"));r.furnaceCargo-=WorkInventory.transfer(v.getInventory(),chest,"minecraft:potato",r.furnaceCargo);if(r.furnaceCargo>0){r.reason="仓库已满，等待退回加工材料";return;}}
            if(deliverFood(s,v,chest))return;r.foodStage="idle";r.furnace=null;r.furnaceCargo=0;return;
        }
        if(r.foodStage.equals("idle")){
            if(deliverFood(s,v,chest))return;
            if(WorkInventory.count(chest,"minecraft:wheat")>=3){if(!walk(v,m.warehousePos(s),3))return;if(!m.hasCraftingTable(l,m.warehousePos(s))){r.reason="仓库旁需要工作台制作面包";return;}WorkRecipes.craftStep(chest,"minecraft:bread",WorkInventory.count(chest,"minecraft:bread")+1);return;}
            r.furnace=null;
            for(var p:BlockPos.betweenClosed(m.warehousePos(s).offset(-6,-2,-6),m.warehousePos(s).offset(6,2,6)))if(l.hasChunkAt(p)&&l.getBlockEntity(p) instanceof FurnaceBlockEntity furnace){
                if(furnace.getItem(0).isEmpty()||furnace.getItem(0).is(Items.POTATO)){r.furnace=p.asLong();break;}
            }
            if(r.furnace==null){r.reason="等待作物成熟；仓库旁 6 格内需要熔炉";return;}
            r.foodStage="fetch";
        }
        BlockPos pos=BlockPos.of(r.furnace);
        if(!l.hasChunkAt(pos)){r.reason="等待加工区加载";return;}
        if(!(l.getBlockEntity(pos) instanceof FurnaceBlockEntity furnace)){r.foodStage="deliver";r.reason="熔炉被移除，材料退回仓库";return;}
        if(r.foodStage.equals("fetch")){
            if(!furnace.getItem(2).isEmpty()){r.foodStage="furnace";return;}
            if(!walk(v,m.warehousePos(s),3))return;
            r.furnaceCargo=0;
            if(furnace.getItem(0).isEmpty()){
                int n=FoodSupply.furnaceBatch(WorkInventory.count(chest,"minecraft:potato"),0,WorkInventory.room(v.getInventory(),new ItemStack(Items.POTATO)));
                r.furnaceCargo=WorkInventory.transfer(chest,v.getInventory(),"minecraft:potato",n);
            }
            if(furnace.getItem(1).isEmpty()&&(r.furnaceCargo>0||furnace.getItem(0).is(Items.POTATO)))for(String fuel:List.of("minecraft:coal","minecraft:charcoal")){
                if(WorkInventory.count(v.getInventory(),fuel)>0)break;
                if(WorkInventory.transfer(chest,v.getInventory(),fuel,1)>0)break;
            }
            r.foodStage="furnace";return;
        }
        if(!walk(v,pos,3))return;
        if(furnace.getItem(2).is(Items.BAKED_POTATO)){
            int n=Math.min(furnace.getItem(2).getCount(),WorkInventory.room(v.getInventory(),furnace.getItem(2)));
            if(n>0){WorkInventory.insert(v.getInventory(),furnace.removeItem(2,n));furnace.setChanged();}r.foodStage="deliver";return;
        }
        if(furnace.getItem(0).isEmpty()&&r.furnaceCargo>0){
            int n=Math.min(r.furnaceCargo,WorkInventory.count(v.getInventory(),"minecraft:potato"));
            if(n>0&&WorkInventory.consume(v.getInventory(),"minecraft:potato",n)){furnace.setItem(0,new ItemStack(Items.POTATO,n));furnace.setChanged();}r.furnaceCargo=0;
        }
        if(furnace.getItem(0).is(Items.POTATO)&&furnace.getItem(1).isEmpty())for(String fuel:List.of("minecraft:coal","minecraft:charcoal"))if(WorkInventory.consume(v.getInventory(),fuel,1)){furnace.setItem(1,new ItemStack(WorkInventory.item(fuel)));furnace.setChanged();break;}
        r.reason=furnace.getItem(0).isEmpty()?"保留种薯，等待农产品":"熔炉加工中；需要实际煤或木炭";
        // A concurrent farmer/player may have filled the input slot; return our unused shipment.
        r.foodStage=r.furnaceCargo>0?"deliver":"idle";
    }
}
