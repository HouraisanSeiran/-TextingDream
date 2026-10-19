package com.minecraftzombiearmy.work;

import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.Container;
import net.minecraft.world.entity.npc.villager.Villager;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.AABB;

/**
 * Performs the physical part of one construction step.  Planning, material
 * reservation and navigation remain in WorkManager; this class only mutates
 * the world after all those gates have passed.
 */
final class ConstructionExecutor {
    record Result(boolean success, String reason) {}

    Result place(ServerLevel level, Villager villager, WorkOrder order,
                 Blueprint.BlockSpec spec, BlockPos target, String item, int cost) {
        if (!level.hasChunkAt(target)) return new Result(false, "worksite_chunk_unloaded");
        if (!level.getWorldBorder().isWithinBounds(target) || !level.mayInteract(villager, target)) {
            return new Result(false, "target_interaction_denied");
        }
        if (!level.getEntities(villager, new AABB(target)).isEmpty()
                || villager.getBoundingBox().intersects(new AABB(target))) {
            return new Result(false, "target_blocked_by_entity");
        }
        if (!WorkInventory.consume(villager.getInventory(), item, cost)) {
            return new Result(false, "worker_material_missing");
        }
        if (!level.setBlock(target, spec.state(), 2)) {
            WorkInventory.insert(villager.getInventory(), new ItemStack(WorkInventory.item(item), cost));
            return new Result(false, "world_rejected_place");
        }
        if (spec.block.equals("minecraft:water")) {
            WorkInventory.insert(villager.getInventory(), new ItemStack(net.minecraft.world.item.Items.BUCKET));
        }
        villager.getInventory().setChanged();
        villager.swingForAttack(net.minecraft.world.InteractionHand.MAIN_HAND);
        return new Result(true, "ok");
    }
}
