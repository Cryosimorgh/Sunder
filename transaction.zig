const std = @import("std");
const entity = @import("entity.zig");
const layout = @import("layout.zig");

/// Structural changes are prepared at an exclusive CPU boundary.
/// The bounded undo journal scales with command count, not world capacity.
pub const Action = union(enum) {
    create: void,
    destroy: entity.Handle,
    lookup: entity.Handle,
};

const SavedSlot = struct {
    id: u32,
    generation: u32,
    dense: u32,
    age: u32,
};

const SavedDense = struct {
    index: u32,
    value: u32,
};

const Undo = struct {
    count: u32,
    slots: [2]SavedSlot,
    slot_count: usize,
    dense: [2]SavedDense,
    dense_count: usize,
};

pub const Prepared = struct {
    model: *entity.Store,
    commands: [layout.command_capacity]entity.Command = undefined,
    undos: [layout.command_capacity]Undo = undefined,
    len: usize = 0,
    undo_count: usize = 0,
    free_length: usize,
    free_saved: [layout.command_capacity]u32 = undefined,
    free_saved_count: usize = 0,
    finished: bool = false,

    fn saveSlot(model: *entity.Store, id: u32) SavedSlot {
        return .{
            .id = id,
            .generation = model.generation[id],
            .dense = model.to_dense[id],
            .age = model.age[id],
        };
    }

    /// Restores the exact pre-prepare mappings and reusable slot order.
    /// May be called more than once; a published transaction cannot be undone.
    pub fn rollback(self: *Prepared) void {
        if (self.finished) return;

        var index = self.undo_count;
        while (index > 0) {
            index -= 1;
            const undo = self.undos[index];

            for (undo.slots[0..undo.slot_count]) |slot| {
                self.model.generation[slot.id] = slot.generation;
                self.model.to_dense[slot.id] = slot.dense;
                self.model.age[slot.id] = slot.age;
            }
            for (undo.dense[0..undo.dense_count]) |dense| {
                self.model.dense_slot[dense.index] = dense.value;
            }
            self.model.count = undo.count;
        }

        self.model.free.items.len = self.free_length;
        @memcpy(
            self.model.free.items[self.free_length - self.free_saved_count ..],
            self.free_saved[0..self.free_saved_count],
        );
        self.finished = true;
    }

    pub fn publish(self: *Prepared) !void {
        if (self.finished) return error.Transaction;
        self.model.epoch = try std.math.add(u32, self.model.epoch, 1);
        self.finished = true;
    }
};

/// Prepares commands or rolls back all CPU mutations if preparation fails.
pub fn prepare(model: *entity.Store, actions: []const Action) !Prepared {
    if (actions.len > layout.command_capacity) return error.CommandCapacity;
    if (model.epoch == std.math.maxInt(u32)) return error.EpochOverflow;

    var prepared: Prepared = .{
        .model = model,
        .free_length = model.free.items.len,
    };
    prepared.free_saved_count = @min(actions.len, model.free.items.len);
    @memcpy(
        prepared.free_saved[0..prepared.free_saved_count],
        model.free.items[model.free.items.len - prepared.free_saved_count ..],
    );
    errdefer prepared.rollback();

    for (actions) |action| {
        switch (action) {
            .create => {
                if (model.free.items.len == 0) return error.Capacity;
                const slot = model.free.items[model.free.items.len - 1];

                prepared.undos[prepared.undo_count] = .{
                    .count = model.count,
                    .slots = .{ Prepared.saveSlot(model, slot), undefined },
                    .slot_count = 1,
                    .dense = .{
                        .{ .index = model.count, .value = model.dense_slot[model.count] },
                        undefined,
                    },
                    .dense_count = 1,
                };
                prepared.undo_count += 1;
                prepared.commands[prepared.len] = (try model.create()).command;
            },
            .destroy => |handle| {
                const dense = try model.lookup(handle);
                const last_dense = model.count - 1;
                const moved_slot = model.dense_slot[last_dense];

                prepared.undos[prepared.undo_count] = .{
                    .count = model.count,
                    .slots = .{
                        Prepared.saveSlot(model, handle.slot),
                        Prepared.saveSlot(model, moved_slot),
                    },
                    .slot_count = 2,
                    .dense = .{
                        .{ .index = dense, .value = model.dense_slot[dense] },
                        .{ .index = last_dense, .value = model.dense_slot[last_dense] },
                    },
                    .dense_count = 2,
                };
                prepared.undo_count += 1;
                prepared.commands[prepared.len] = try model.destroy(handle);
            },
            .lookup => |handle| {
                if (handle.slot >= model.generation.len) return error.Stale;
                prepared.commands[prepared.len] = .{
                    .op = 3,
                    .slot = handle.slot,
                    .generation = handle.generation,
                    .dense = 0,
                };
            },
        }
        prepared.len += 1;
    }
    return prepared;
}
