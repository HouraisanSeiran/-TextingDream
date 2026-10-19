package com.minecraftzombiearmy.work;
import com.google.gson.*;
import com.minecraftzombiearmy.*;
import net.minecraft.core.*;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.*;
import net.minecraft.tags.*;
import net.minecraft.world.Container;
import net.minecraft.world.entity.*;
import net.minecraft.world.entity.npc.villager.Villager;
import net.minecraft.world.item.*;
import net.minecraft.world.level.block.*;
import net.minecraft.world.level.block.entity.*;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.phys.AABB;
import java.nio.file.Path;
import java.util.*;
import static com.minecraftzombiearmy.ArmyConfig.require;

/** Shared server-thread executor for map, commands and automatic construction supply. */
public final class WorkManager {
    public static final String WORKER_TAG="textingdream_worker";
    public static final Map<String,String> TEMPLATES=Map.of(
        "medium_house","minecraft:village/plains/houses/plains_medium_house_1",
        "farm","minecraft:village/plains/houses/plains_large_farm_1",
        "small_house","minecraft:village/plains/houses/plains_small_house_1",
        "mason_house","minecraft:village/plains/houses/plains_masons_house_1");
    final MinecraftServer server;
    public final VillageEconomy economy;
    final WarehouseService warehouseService;
    final GatherExecutor gatherExecutor=new GatherExecutor();
    private final Path file;
    private final Map<String,Blueprint> blueprints=new LinkedHashMap<>();
    private final Map<String,WorkOrder> orders=new LinkedHashMap<>();
    private final Map<String,Settlement> settlements=new LinkedHashMap<>();
    private final Set<String> protectedBlocks=new HashSet<>();
    private final Map<String,Runtime> runtimes=new HashMap<>();
    private final NavigationService navigation=new NavigationService();
    long tick;private long worldRevision;
    private static final class Runtime {BlockPos target;int scan;String raw="";}
    public WorkManager(MinecraftServer server){
        this.server=server;file=server.getWorldPath(net.minecraft.world.level.storage.LevelResource.ROOT).resolve("minecraftzombiearmy/work.json");
        Blueprint demo=new Blueprint("demo_cabin","示范工棚");for(int x=0;x<3;x++)for(int z=0;z<3;z++)demo.add(x,0,z,"minecraft:oak_planks");demo.add(0,1,0,"minecraft:cobblestone");blueprints.put(demo.id,demo);
        Blueprint work=new Blueprint("work_area","公共工作区");work.add(0,0,0,"minecraft:cobblestone").add(1,0,0,"minecraft:cobblestone").add(2,0,0,"minecraft:cobblestone").add(0,1,0,"minecraft:crafting_table").add(1,1,0,"minecraft:furnace").add(2,1,0,"minecraft:chest");blueprints.put(work.id,work);
        economy=new VillageEconomy(this);
        warehouseService=new WarehouseService(this);
        try{load(ArmyConfig.read(file,JsonObject.class,new JsonObject()));}catch(Exception e){throw new IllegalStateException("Cannot read work save; original preserved",e);}
    }
    public Collection<WorkOrder> orders(){return Collections.unmodifiableCollection(orders.values());}
    public Collection<Settlement> settlements(){return Collections.unmodifiableCollection(settlements.values());}
    public Collection<Blueprint> blueprints(){return Collections.unmodifiableCollection(blueprints.values());}
    public WorkProfile profile(Villager v){return WorkProfile.of(v);}
    ServerLevel level(String dimension){for(var l:server.getAllLevels())if(l.dimension().identifier().toString().equals(dimension))return l;return null;}
    BlockPos warehousePos(Settlement s){return new BlockPos(s.warehouseX,s.warehouseY,s.warehouseZ);}
    public Container warehouse(Settlement s){ServerLevel l=level(s.dimension);if(l==null||!l.hasChunkAt(warehousePos(s)))return null;var e=l.getBlockEntity(warehousePos(s));if(e instanceof ChestBlockEntity&&l.getBlockState(warehousePos(s)).getBlock() instanceof ChestBlock block)return ChestBlock.getContainer(block,l.getBlockState(warehousePos(s)),l,warehousePos(s),true);return e instanceof BarrelBlockEntity?(Container)e:null;}
    static String key(String dimension,BlockPos p){return dimension+"|"+p.asLong();}
    public void protect(ServerLevel l,BlockPos pos){protectedBlocks.add(key(l.dimension().identifier().toString(),pos));}
    public Settlement settlement(String id){Settlement s=settlements.get(id);require(s!=null,"未知村庄仓库");return s;}
    public Settlement bindWarehouse(ServerLevel l,BlockPos pos){
        require(l.hasChunkAt(pos),"Warehouse chunk is not loaded");String dimension=l.dimension().identifier().toString();
        for(var s:settlements.values())if(s.dimension.equals(dimension)&&warehousePos(s).equals(pos))return s;
        require(settlements.size()<64,"Too many settlements");
        Settlement s=new Settlement();s.id="village_"+UUID.randomUUID().toString().substring(0,8);s.dimension=dimension;s.warehouseX=pos.getX();s.warehouseY=pos.getY();s.warehouseZ=pos.getZ();require(warehouse(s)!=null,"请指定箱子或木桶作为仓库");settlements.put(s.id,s);save();return s;
    }
    public void zone(Settlement s,String kind,BlockPos pos){
        require(Math.abs(pos.getX()-s.warehouseX)<=96&&Math.abs(pos.getZ()-s.warehouseZ)<=96,"资源区须在仓库 96 格内");
        if(kind.equals("forest")){require(economy.forestCount(s,pos)>=3,"林区 17×17 内至少需要 3 棵有树叶的真实树木（支持人工林）");s.forestX=pos.getX();s.forestZ=pos.getZ();}else if(kind.equals("quarry")){s.quarryX=pos.getX();s.quarryZ=pos.getZ();s.quarryY=level(s.dimension).getHeightmapPos(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES,pos).getY()-1;}else throw new IllegalArgumentException("Unknown resource zone");save();
    }
    public Villager findVillager(String uuid){UUID id=UUID.fromString(uuid);for(var l:server.getAllLevels())if(l.getEntity(id) instanceof Villager v)return v;return null;}
    public boolean controls(Villager v){if(economy.controls(v))return true;return orders.values().stream().anyMatch(o->o.workerUuid.equals(v.getStringUUID())&&o.active());}
    public WorkOrder current(Villager v){return orders.values().stream().filter(o->o.workerUuid.equals(v.getStringUUID())&&!o.terminal()).findFirst().orElse(null);}
    public static boolean employable(Villager v){return v.isAlive()&&!v.isBaby()&&!ArmyManager.managed(v)&&!WorkProfile.of(v).profession.equals("nitwit");}
    public Settlement affiliation(Villager v){return settlements.values().stream().filter(s->s.workers.contains(v.getStringUUID())).findFirst().orElse(null);}
    private WorkOrder create(Villager v,Settlement s,String kind){
        require(affiliation(v)==null||affiliation(v)==s,"村民已属于其他村庄，需原村庄释放");
        require(employable(v),"Adult non-army villager required");require(current(v)==null,"Villager already has a work order");require(v.level().dimension().identifier().toString().equals(s.dimension),"Villager and warehouse must share a dimension");require(v.distanceToSqr(s.warehouseX+.5,s.warehouseY+.5,s.warehouseZ+.5)<128*128,"Villager is too far from warehouse");require(orders.values().stream().filter(o->!o.terminal()).count()<64,"Too many active work orders");
        WorkOrder o=new WorkOrder();o.id="work_"+UUID.randomUUID();o.workerUuid=v.getStringUUID();o.dimension=s.dimension;o.settlementId=s.id;o.kind=kind;o.createdTick=tick;return o;
    }
    public WorkOrder startBuild(Villager v,Settlement s,String blueprint,BlockPos origin){
        Blueprint bp=blueprint(blueprint);
        WorkOrder o=create(v,s,"construct");require(origin.distSqr(warehousePos(s))<=96*96,"工地须在仓库 96 格内");o.blueprintId=blueprint;o.originX=origin.getX();o.originY=origin.getY();o.originZ=origin.getZ();o.plan=ArmyConfig.JSON.fromJson(ArmyConfig.JSON.toJson(bp.blocks),new com.google.gson.reflect.TypeToken<List<Blueprint.BlockSpec>>(){}.getType());
        ServerLevel l=level(s.dimension);
        for(var b:o.plan){BlockPos p=origin.offset(b.x,b.y,b.z);require(l.hasChunkAt(p)&&l.getWorldBorder().isWithinBounds(p)&&p.getY()>=l.getMinY()&&p.getY()<l.getMaxY(),"Blueprint outside loaded world");require(!protectedBlocks.contains(key(o.dimension,p)),"Worksite overlaps protected building");var old=l.getBlockState(p);require(old.isAir()||old.canBeReplaced()||old.equals(b.state())||foundation(l,p,b),"工地有障碍："+p.toShortString());if(foundation(l,p,b))o.roadSurface.put(Long.toString(p.asLong()),old.toString());}
        for(var other:orders.values())if(!other.terminal()&&isConstruction(other)&&other.dimension.equals(o.dimension))for(var b:other.plan)for(var a:o.plan)require(other.originX+b.x!=origin.getX()+a.x||other.originY+b.y!=origin.getY()+a.y||other.originZ+b.z!=origin.getZ()+a.z,"Worksite overlaps another order");
        orders.put(o.id,o);s.workers.add(v.getStringUUID());v.addTag(WORKER_TAG);refreshDemand(o);save();return o;
    }
    public Blueprint blueprint(String id){return blueprints.computeIfAbsent(id,k->{require(TEMPLATES.containsKey(k),"Unsupported vanilla village blueprint");return Blueprint.vanilla(server,TEMPLATES.get(k),k);});}
    boolean foundation(ServerLevel l,BlockPos p,Blueprint.BlockSpec b){return b.y<=0&&l.getBlockEntity(p)==null&&(l.getBlockState(p).is(Blocks.GRASS_BLOCK)||l.getBlockState(p).is(Blocks.DIRT)||l.getBlockState(p).is(Blocks.STONE));}
    public WorkOrder startDemo(Villager v,BlockPos origin){return startBuild(v,nearest(v),"demo_cabin",origin);}
    public Settlement nearest(Villager v){return settlements.values().stream().filter(s->s.dimension.equals(v.level().dimension().identifier().toString())).min(Comparator.comparingDouble(s->warehousePos(s).distSqr(v.blockPosition()))).orElseThrow(()->new IllegalArgumentException("Register a village warehouse first"));}
    public WorkOrder startGather(Villager v,String kind,int amount){return startGather(v,nearest(v),kind,amount);}
    public WorkOrder startGather(Villager v,Settlement s,String kind,int amount){require(Set.of("gather_wood","gather_stone").contains(kind)&&amount>=1&&amount<=4096,"采集任务无效");WorkOrder o=create(v,s,kind);o.resource=kind.equals("gather_wood")?"minecraft:oak_log":"minecraft:cobblestone";o.requested=amount;orders.put(o.id,o);s.workers.add(v.getStringUUID());v.addTag(WORKER_TAG);save();return o;}
    public void control(String id,String action){WorkOrder o=orders.get(id);require(o!=null&&!o.terminal(),"Unknown or completed order");Villager v=findVillager(o.workerUuid);if(v!=null)v.getNavigation().stop();if(action.equals("resume")){o.status="queued";o.failureReason="";}else if(action.equals("pause")){o.status="paused";o.failureReason="Paused by player";}else if(action.equals("cancel")){o.status="cancelled";o.failureReason="Cancelled by player; carried goods stay with villager";if(v!=null)v.removeTag(WORKER_TAG);}else throw new IllegalArgumentException("Unknown control action");runtimes.remove(o.id);navigation.clear(o.id);save();}
    public void cancel(String id,String reason){control(id,"cancel");}
    public void tick(){tick++;if(tick%10!=0)return;economy.tick();for(var o:List.copyOf(orders.values()))if(o.active())try{step(o);}catch(Exception e){o.status="paused";o.failureReason="执行异常，请检查日志后恢复";ArmyMod.LOG.error("Work order {} paused",o.id,e);}if(tick%200==0)save();}
    private void waiting(WorkOrder o,String phase,String reason){o.status="queued";o.phase=phase;o.failureReason=reason;}
    private void step(WorkOrder o){
        Villager v=findVillager(o.workerUuid);if(v==null){waiting(o,"waiting_worker","村民未加载，等待返回");return;}if(!v.isAlive()){o.status="failed";o.failureReason="工人死亡";return;}if(!v.level().dimension().identifier().toString().equals(o.dimension)){waiting(o,"waiting_worker","村民位于其他维度");return;}
        if(!employable(v)){o.status="paused";o.failureReason="村民当前不能工作";return;}
        Settlement s=settlements.get(o.settlementId);if(s==null){o.status="paused";o.failureReason="旧任务没有仓库，请取消后重建";return;}
        Container chest=warehouse(s);if(chest==null){waiting(o,"waiting_warehouse","仓库未加载或已被破坏");return;}
        if(!economy.canWork(s,v,false)){waiting(o,"daily_routine",s.residents.get(v.getStringUUID()).reason);return;}
        o.status="working";o.failureReason="";o.lastTick=tick;
        if(!isConstruction(o)){gather(o,v,s,chest,o.resource,o.requested-o.collected,true);return;}
        Runtime ongoing=runtimes.get(o.id);if(ongoing!=null&&!ongoing.raw.isEmpty()&&Set.of("logging","quarrying","searching","delivering").contains(o.phase)){gather(o,v,s,chest,ongoing.raw,8,false);return;}
        if(o.cursor>=o.plan.size()){o.phase="returning_surplus";if(!approach(o,v,warehousePos(s),3))return;deposit(v,chest);returnTools(v,chest);complete(o,v);return;}
        Blueprint.BlockSpec spec=o.plan.get(o.cursor);BlockPos target=new BlockPos(o.originX+spec.x,o.originY+spec.y,o.originZ+spec.z);ServerLevel l=(ServerLevel)v.level();
        if(!l.hasChunkAt(target)){waiting(o,"waiting_site","Worksite chunk is not loaded");return;}
        if(l.getBlockState(target).equals(spec.state())){o.skipped++;o.cursor++;refreshDemand(o);return;}
        if(protectedBlocks.contains(key(o.dimension,target))|| (o.kind.equals("road")?!roadUnchanged(o,l,target):!l.getBlockState(target).isAir()&&!l.getBlockState(target).canBeReplaced()&&!l.getBlockState(target).toString().equals(o.roadSurface.get(Long.toString(target.asLong()))))){waiting(o,"blocked","工地有障碍："+target.toShortString());return;}
        String needed=spec.item();int cost=spec.cost();
        if(WorkInventory.count(v.getInventory(),needed)<cost){
            o.phase="returning";if(!approach(o,v,warehousePos(s),3))return;
            deposit(v,chest); // inventories are the only reservation ledger
            if(WorkInventory.count(chest,needed)<cost){
                if(!hasCraftingTable(l,warehousePos(s))&&WorkRecipes.recipe(needed)!=null){waiting(o,"waiting_workstation","仓库旁 4 格内需要工作台");return;}
                if(WorkRecipes.craftStep(chest,needed,cost)){o.phase="crafting";return;}
                String raw=WorkRecipes.missingRaw(chest,needed,cost);
                if(raw.equals("minecraft:cobblestone")||raw.endsWith("_log")){if(s.residents.containsKey(v.getStringUUID())){waiting(o,"waiting_supply","采集工供料："+raw);return;}gather(o,v,s,chest,raw,8,false);return;}
                waiting(o,"waiting_material","Warehouse needs material: "+(raw.isEmpty()?needed:raw));return;
            }
            WorkInventory.transfer(chest,v.getInventory(),needed,Math.min(64,Math.max(cost,o.materials.getOrDefault(needed,cost))));return;
        }
        o.phase="building";if(!approach(o,v,target,5.5))return;
        if(spec.block.equals("minecraft:farmland")&&!economy.hasTool(v,chest,ItemTags.HOES,o,s))return;
        if(spec.block.startsWith("minecraft:stripped_")&&!economy.hasTool(v,chest,ItemTags.AXES,o,s))return;
        if(spec.block.equals("minecraft:water")&&WorkInventory.room(v.getInventory(),new ItemStack(Items.BUCKET))<1){waiting(o,"blocked","背包需要空位回收水桶");return;}
        if(!l.getWorldBorder().isWithinBounds(target)||!l.mayInteract(v,target)){waiting(o,"blocked","此处不能施工");return;}
        if(!l.getEntities(v,new AABB(target)).isEmpty()||v.getBoundingBox().intersects(new AABB(target))){v.getNavigation().moveTo(target.getX()+2.5,v.getY(),target.getZ()+2.5,1);waiting(o,"blocked","实体挡住工地，等待让路");return;}
        if(!WorkInventory.consume(v.getInventory(),needed,cost))return;
        // Suppress neighbor updates until paired doors/beds are placed; preserve template orientation.
        if(!l.setBlock(target,spec.state(),2)){WorkInventory.insert(v.getInventory(),new ItemStack(WorkInventory.item(needed),cost));waiting(o,"blocked","世界拒绝放置");return;}
        if(spec.block.equals("minecraft:water"))WorkInventory.insert(v.getInventory(),new ItemStack(Items.BUCKET));
        if(spec.block.equals("minecraft:farmland"))economy.damageTool(v,ItemTags.HOES);
        if(spec.block.startsWith("minecraft:stripped_"))economy.damageTool(v,ItemTags.AXES);
        protect(l,target);v.swingForAttack(net.minecraft.world.InteractionHand.MAIN_HAND);o.placed++;o.cursor++;o.worldRevision=++worldRevision;refreshDemand(o);
    }
    private void complete(WorkOrder o,Villager v){o.status="completed";o.phase="complete";o.failureReason="";v.getNavigation().stop();v.removeTag(WORKER_TAG);runtimes.remove(o.id);navigation.clear(o.id);save();}
    void refreshDemand(WorkOrder o){o.materials.clear();for(int i=o.cursor;i<o.plan.size();i++){var s=o.plan.get(i);if(s.cost()>0)o.materials.merge(s.item(),s.cost(),Integer::sum);}}
    boolean hasCraftingTable(ServerLevel l,BlockPos p){for(var b:BlockPos.betweenClosed(p.offset(-4,-2,-4),p.offset(4,2,4)))if(l.hasChunkAt(b)&&l.getBlockState(b).is(Blocks.CRAFTING_TABLE))return true;return false;}
    private void deposit(Villager v,Container chest){warehouseService.deposit(v,chest);}
    private void returnTools(Villager v,Container chest){warehouseService.returnTools(v,chest);}
    private ItemStack tool(Villager v,boolean wood){if(v.getMainHandItem().is(wood?ItemTags.AXES:ItemTags.PICKAXES))return v.getMainHandItem();for(int i=0;i<v.getInventory().getContainerSize();i++){var stack=v.getInventory().getItem(i);if(stack.is(wood?ItemTags.AXES:ItemTags.PICKAXES))return stack;}return ItemStack.EMPTY;}
    private void gather(WorkOrder o,Villager v,Settlement s,Container chest,String raw,int amount,boolean standalone){
        o.gatherAttempts++;
        boolean wood=raw.endsWith("_log");ServerLevel l=(ServerLevel)v.level();int cargo=WorkInventory.count(v.getInventory(),raw);
        if(cargo>=Math.max(1,amount)||WorkInventory.room(v.getInventory(),new ItemStack(WorkInventory.item(raw)))==0||o.phase.equals("delivering")){
            o.phase="delivering";if(!approach(o,v,warehousePos(s),3))return;o.warehouseTrips++;int n=warehouseService.deliver(v,chest,raw,cargo);if(standalone){o.collected+=n;o.gatherSuccesses+=n;}if(n==0&&cargo>0){waiting(o,"delivering","仓库已满");return;}if(standalone&&o.collected>=o.requested){returnTools(v,chest);complete(o,v);return;}o.phase="planning";Runtime delivered=runtimes.get(o.id);if(delivered!=null)delivered.raw="";return;
        }
        if(standalone&&amount<=0){complete(o,v);return;}
        ItemStack tool=tool(v,wood);if(tool.isEmpty()){
            o.phase="fetching_tool";if(!approach(o,v,warehousePos(s),3))return;
            for(var e:WorkInventory.counts(chest).entrySet()){ItemStack candidate=new ItemStack(WorkInventory.item(e.getKey()));if(candidate.is(wood?ItemTags.AXES:ItemTags.PICKAXES)){WorkInventory.transfer(chest,v.getInventory(),e.getKey(),1);return;}}
            waiting(o,"waiting_tool",wood?"Warehouse needs an axe":"Warehouse needs a pickaxe");return;
        }
        Integer x=wood?s.forestX:s.quarryX,z=wood?s.forestZ:s.quarryZ;if(x==null){waiting(o,"waiting_zone",wood?"Set a forest zone on the map":"Set an open quarry zone on the map");return;}
        Runtime r=runtimes.computeIfAbsent(o.id,id->new Runtime());if(!raw.equals(r.raw)){r.raw=raw;r.target=null;r.scan=0;}
        if(wood){
            TreeHarvest tree=o.treeRoot==null?null:s.trees.get(o.treeRoot);
            if(tree==null){o.treeRoot=null;for(var candidate:s.trees.values())if(candidate.resource.equals(raw)&&!candidate.remaining.isEmpty()&&!treeClaimed(o,s,candidate.root)){tree=candidate;o.treeRoot=tree.root;break;}}
            if(tree!=null){
                if(tree.remaining.stream().anyMatch(pos->!l.hasChunkAt(BlockPos.of(pos)))){waiting(o,"waiting_tree","采伐树木所在区块未加载");return;}
                tree.remaining.removeIf(pos->!BuiltInRegistries.BLOCK.getKey(l.getBlockState(BlockPos.of(pos)).getBlock()).toString().equals(raw));
                if(tree.remaining.isEmpty()){finishTree(s,o,tree);r.target=null;}else r.target=BlockPos.of(tree.remaining.getFirst());
            }
        }
        if(r.target==null){ // bounded surface scan, never requests new chunks
            for(int i=0;i<(wood?32:289);i++){int index=r.scan++%289;BlockPos column=new BlockPos(x+index%17-8,0,z+index/17-8);if(!l.hasChunkAt(column))continue;BlockPos top=l.getHeightmapPos(Heightmap.Types.WORLD_SURFACE,column).below();
                // Preserve an east-side staircase and take the highest exposed layer first.
                if(!wood&&s.quarryY!=null){int dx=column.getX()-x;if(top.getY()<=s.quarryY-Math.min(3,8-dx))continue;}
                for(int dy=wood?23:0;dy>=0;dy--){BlockPos p=top.below(dy);if(resource(l,p,raw,wood)&&!claimed(o,p)&&(!wood||treeSoil(l,p.below()))&&(wood||r.target==null||p.getY()>r.target.getY())){r.target=p;break;}}
                if(wood&&r.target!=null)break;
            }
            if(r.target==null){if(cargo>0){o.phase="delivering";return;}if(wood&&s.residents.containsKey(v.getStringUUID())&&economy.replant(s,v,chest))return;waiting(o,"searching",wood?"指定林区未发现可采伐树木，等待树苗生长":"指定采石区未发现露天石头");return;}
            if(wood){
                BlockPos root=r.target;Set<BlockPos> seen=new LinkedHashSet<>();Deque<BlockPos> scan=new ArrayDeque<>();scan.add(root);seen.add(root);
                while(!scan.isEmpty()&&seen.size()<128){BlockPos node=scan.removeFirst();for(int dx=-1;dx<=1;dx++)for(int dy=-1;dy<=1;dy++)for(int dz=-1;dz<=1;dz++){
                    BlockPos next=node.offset(dx,dy,dz);if(Math.abs(next.getX()-root.getX())>5||Math.abs(next.getZ()-root.getZ())>5||next.getY()<root.getY()||next.getY()>root.getY()+24||seen.contains(next)||seen.size()>=128)continue;
                    if(!next.equals(root)&&treeSoil(l,next.below()))continue;
                    if(resource(l,next,raw,true)&&!claimed(o,next)){seen.add(next);scan.add(next);}
                }}
                TreeHarvest tree=new TreeHarvest();tree.root=root.asLong();tree.resource=raw;
                tree.remaining.addAll(seen.stream().sorted(Comparator.comparingInt((BlockPos node)->node.getY()).reversed()).map(BlockPos::asLong).toList());
                s.trees.put(tree.root,tree);o.treeRoot=tree.root;r.target=BlockPos.of(tree.remaining.getFirst());migrateReplant(s,tree);save();
            }
        }
        BlockPos p=r.target;if(!resource(l,p,raw,wood)||claimed(o,p)){r.target=null;return;}
        o.lastGatherTarget=p.toShortString();
        o.phase=wood?"logging":"quarrying";if(!approach(o,v,wood&&o.treeRoot!=null?BlockPos.of(o.treeRoot):p,4.5))return;
        if(!tool.isCorrectToolForDrops(l.getBlockState(p))&&!wood){waiting(o,"waiting_tool","镐不能开采此石头");return;}
        if(!l.getEntities(v,new AABB(p)).isEmpty()||v.getBoundingBox().intersects(new AABB(p))){r.target=null;return;}
        GatherExecutor.Result result=gatherExecutor.harvest(l,v,o,p,raw,wood,tool);
        if(!result.success()){o.failureReason="采集未完成："+result.reason();r.target=null;return;}
        o.gatherSuccesses+=result.produced();
        if(wood&&o.treeRoot!=null){TreeHarvest tree=s.trees.get(o.treeRoot);if(tree!=null){tree.harvested(p.asLong());if(tree.remaining.isEmpty())finishTree(s,o,tree);}}
        worldRevision++;
        r.target=null;
    }
    private static boolean treeSoil(ServerLevel l,BlockPos p){return l.getBlockState(p).is(BlockTags.DIRT)||l.getBlockState(p).is(Blocks.GRASS_BLOCK);}
    private boolean treeClaimed(WorkOrder current,Settlement s,long root){return orders.values().stream().anyMatch(o->o!=current&&!o.terminal()&&o.settlementId.equals(s.id)&&Objects.equals(o.treeRoot,root));}
    private void migrateReplant(Settlement s,TreeHarvest tree){s.replants.remove(tree.root);}
    private void finishTree(Settlement s,WorkOrder o,TreeHarvest tree){s.trees.remove(tree.root);s.replants.put(tree.root,tree.resource.replace("_log","_sapling"));o.treeRoot=null;}
    private boolean claimed(WorkOrder current,BlockPos p){
        for(var entry:runtimes.entrySet()){WorkOrder other=orders.get(entry.getKey());if(other!=null&&other!=current&&!other.terminal()&&p.equals(entry.getValue().target)&&other.dimension.equals(current.dimension))return true;}
        for(Settlement s:settlements.values())if(s.dimension.equals(current.dimension))for(var tree:s.trees.values())if(tree.remaining.contains(p.asLong())&&!Objects.equals(current.treeRoot,tree.root))return true;
        return false;
    }
    boolean resource(ServerLevel l,BlockPos p,String raw,boolean wood){
        if(!l.hasChunkAt(p)||protectedBlocks.contains(key(l.dimension().identifier().toString(),p)))return false;
        if(l.structureManager().getStructureWithPieceAt(p,StructureTags.VILLAGE).isValid())return false;
        for(var o:orders.values())if(isConstruction(o)&&o.dimension.equals(l.dimension().identifier().toString()))for(var b:o.plan)if(p.getX()==o.originX+b.x&&p.getY()==o.originY+b.y&&p.getZ()==o.originZ+b.z)return false;
        var state=l.getBlockState(p);
        if(wood&&state.is(BlockTags.LOGS)&&BuiltInRegistries.BLOCK.getKey(state.getBlock()).toString().equals(raw))for(Settlement s:settlements.values())if(s.dimension.equals(l.dimension().identifier().toString()))for(var tree:s.trees.values())if(tree.resource.equals(raw)&&tree.remaining.contains(p.asLong()))return true;
        if(!wood)return state.is(Blocks.STONE)&&l.canSeeSky(p.above());
        if(!BuiltInRegistries.BLOCK.getKey(state.getBlock()).toString().equals(raw)||!state.is(BlockTags.LOGS))return false;
        for(var leaf:BlockPos.betweenClosed(p.offset(-3,-1,-3),p.offset(3,4,3)))if(l.hasChunkAt(leaf)&&l.getBlockState(leaf).is(BlockTags.LEAVES))return true;
        return false;
    }
    boolean approach(WorkOrder o,Villager v,BlockPos p,double reach){boolean reached=navigation.approach(o,v,p,reach,tick);if(reached)o.lastReachablePoint=v.blockPosition().toShortString();return reached;}
    public void save(){try{JsonObject root=new JsonObject();root.addProperty("schema",4);root.addProperty("world_revision",worldRevision);root.add("settlements",ArmyConfig.JSON.toJsonTree(settlements.values()));root.add("orders",ArmyConfig.JSON.toJsonTree(orders.values()));root.add("protected",ArmyConfig.JSON.toJsonTree(protectedBlocks));ArmyConfig.write(file,root);}catch(Exception e){ArmyMod.LOG.error("Work save failed",e);}}
    private void load(JsonObject root){
        if(root.has("world_revision"))worldRevision=root.get("world_revision").getAsLong();
        if(root.has("settlements"))for(var e:root.getAsJsonArray("settlements")){Settlement s=ArmyConfig.JSON.fromJson(e,Settlement.class);require(s.id!=null&&s.dimension!=null,"Invalid settlement save");if(s.ownerUuid==null)s.ownerUuid="";if(s.collaborators==null)s.collaborators=new LinkedHashSet<>();if(s.workers==null)s.workers=new LinkedHashSet<>();if(s.trees==null)s.trees=new LinkedHashMap<>();settlements.put(s.id,s);}
        if(root.has("protected"))for(var e:root.getAsJsonArray("protected"))protectedBlocks.add(e.getAsString());
        if(root.has("orders"))for(var e:root.getAsJsonArray("orders")){WorkOrder o=WorkOrder.load(e.getAsJsonObject());require(o.id!=null&&o.workerUuid!=null&&o.dimension!=null&&o.cursor>=0,"Invalid work save");UUID.fromString(o.workerUuid);if(o.cursor>o.plan.size()){o.cursor=o.plan.size();o.status="cancelled";o.failureReason="旧蓝图缺失，请重新创建任务";}if(o.roadSurface==null)o.roadSurface=new LinkedHashMap<>();Settlement village=settlements.get(o.settlementId);if(village!=null&&(!root.has("schema")||root.get("schema").getAsInt()<3))village.workers.add(o.workerUuid);if(!o.terminal()&&(village==null||!village.residents.containsKey(o.workerUuid))){o.status="paused";o.failureReason="服务器重启，请检查工地后恢复";}orders.put(o.id,o);}
    }
    public static boolean isConstruction(WorkOrder o){return o.kind.equals("construct")||o.kind.equals("road");}
    public boolean roadGround(ServerLevel l,BlockPos p){
        if(!l.hasChunkAt(p)||!l.getWorldBorder().isWithinBounds(p)||protectedBlocks.contains(key(l.dimension().identifier().toString(),p)))return false;
        if(l.getBlockEntity(p)!=null||!l.getFluidState(p).isEmpty()||!l.getBlockState(p.above()).isAir()||!l.getBlockState(p.above(2)).isAir())return false;
        if(l.structureManager().getStructureWithPieceAt(p,StructureTags.VILLAGE).isValid())return false;
        var state=l.getBlockState(p);return state.is(Blocks.GRASS_BLOCK)||state.is(Blocks.DIRT)||state.is(Blocks.COARSE_DIRT)||state.is(Blocks.STONE)||state.is(Blocks.GRAVEL)||state.is(Blocks.DIRT_PATH);
    }
    public List<RoadPlanner.Cell> roadPlan(Settlement s,BlockPos start,BlockPos end){
        ServerLevel l=level(s.dimension);require(l!=null,"维度未加载");
        java.util.function.BiFunction<Integer,Integer,RoadPlanner.Cell> surface=(x,z)->{
            if(Math.abs((long)x-s.warehouseX)>96||Math.abs((long)z-s.warehouseZ)>96)return null;
            BlockPos column=new BlockPos(x,0,z);if(!l.hasChunkAt(column))return null;
            BlockPos p=l.getHeightmapPos(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES,column).below();
            if(!roadGround(l,p))return null;
            for(var o:orders.values())if(!o.terminal()&&isConstruction(o)&&o.dimension.equals(s.dimension))for(var b:o.plan)if(p.equals(new BlockPos(o.originX+b.x,o.originY+b.y,o.originZ+b.z)))return null;
            return new RoadPlanner.Cell(x,p.getY(),z);
        };
        return RoadPlanner.plan(surface.apply(start.getX(),start.getZ()),surface.apply(end.getX(),end.getZ()),surface);
    }
    public WorkOrder startRoad(Villager v,Settlement s,BlockPos start,BlockPos end){
        WorkOrder o=create(v,s,"road");var route=roadPlan(s,start,end);ServerLevel l=level(s.dimension);
        o.originX=route.getFirst().x();o.originY=route.getFirst().y();o.originZ=route.getFirst().z();o.blueprintId="cobblestone_road";
        for(var c:route){BlockPos p=new BlockPos(c.x(),c.y(),c.z());o.plan.add(new Blueprint.BlockSpec(c.x()-o.originX,c.y()-o.originY,c.z()-o.originZ,"minecraft:cobblestone"));o.roadSurface.put(Long.toString(p.asLong()),l.getBlockState(p).toString());}
        orders.put(o.id,o);s.workers.add(v.getStringUUID());v.addTag(WORKER_TAG);refreshDemand(o);save();return o;
    }
    private boolean roadUnchanged(WorkOrder o,ServerLevel l,BlockPos p){return roadGround(l,p)&&l.getBlockState(p).toString().equals(o.roadSurface.get(Long.toString(p.asLong())));}
    public WorkOrder startPlannedRoad(Villager v,Settlement s,List<RoadPlanner.Cell> route){
        WorkOrder o=create(v,s,"road");ServerLevel l=level(s.dimension);o.blueprintId="cobblestone_road";
        for(var c:route){BlockPos p=new BlockPos(c.x(),c.y(),c.z());if(l.getBlockState(p).is(Blocks.COBBLESTONE))continue;require(roadGround(l,p)&&l.getBlockState(p).toString().equals(s.plan.roadSurface.get(Long.toString(p.asLong()))),"道路地形改变，请重新预览");o.plan.add(new Blueprint.BlockSpec(c.x(),c.y(),c.z(),"minecraft:cobblestone"));o.roadSurface.put(Long.toString(p.asLong()),l.getBlockState(p).toString());}
        orders.put(o.id,o);s.workers.add(v.getStringUUID());refreshDemand(o);save();return o;
    }
    public void close(){save();}
}

