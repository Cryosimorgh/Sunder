const std = @import("std");

/// An unused mapping entry. Generation counters stop at this value rather than wrapping.
pub const none = std.math.maxInt(u32);

/// A stable external reference. The slot may be reused only with a new generation.
pub const Handle = packed struct {
    slot: u32,
    generation: u32,
};

/// GPU-facing structural command. Keep the memory layout in sync with the shader ABI.
pub const Command = extern struct {
    op: u32,
    slot: u32,
    generation: u32,
    dense: u32,
    next_generation: u32 = 0,
    pad: [3]u32 = .{ 0, 0, 0 },
};

/// Owns the CPU slot-to-dense mapping and its reusable slot list.
///
/// Only a drained structural boundary may mutate this store. Dense positions are
/// not stable identifiers; callers must retain generation-checked handles.
pub const Store = struct {
    allocator: std.mem.Allocator,
    generation: []u32,
    to_dense: []u32,
    dense_slot: []u32,
    age: []u32,
    free: std.ArrayList(u32) = .empty,
    count: u32 = 0,
    epoch: u32 = 0,

    pub fn init(allocator: std.mem.Allocator, capacity: u32, initial_count: u32) !Store {
        if (initial_count > capacity) return error.Capacity;

        const generation = try allocator.alloc(u32, capacity);
        errdefer allocator.free(generation);
        const to_dense = try allocator.alloc(u32, capacity);
        errdefer allocator.free(to_dense);
        const dense_slot = try allocator.alloc(u32, capacity);
        errdefer allocator.free(dense_slot);
        const age = try allocator.alloc(u32, capacity);
        errdefer allocator.free(age);

        var store: Store = .{
            .allocator = allocator,
            .generation = generation,
            .to_dense = to_dense,
            .dense_slot = dense_slot,
            .age = age,
            .count = initial_count,
        };
        errdefer store.free.deinit(allocator);

        @memset(generation, 1);
        @memset(to_dense, none);
        @memset(dense_slot, none);
        @memset(age, 0);

        for (0..initial_count) |index| {
            to_dense[index] = @intCast(index);
            dense_slot[index] = @intCast(index);
        }

        try store.free.ensureTotalCapacityPrecise(allocator, capacity);
        var slot = capacity;
        while (slot > initial_count) {
            slot -= 1;
            store.free.appendAssumeCapacity(slot);
        }
        return store;
    }

    pub fn deinit(self: *Store) void {
        self.allocator.free(self.generation);
        self.allocator.free(self.to_dense);
        self.allocator.free(self.dense_slot);
        self.allocator.free(self.age);
        self.free.deinit(self.allocator);
    }

    /// Rejects stale handles even when their original slot was reused.
    pub fn lookup(self: *const Store, target: Handle) !u32 {
        if (target.slot >= self.generation.len or
            self.generation[target.slot] != target.generation)
        {
            return error.Stale;
        }

        const dense = self.to_dense[target.slot];
        if (dense >= self.count or self.dense_slot[dense] != target.slot) {
            return error.Stale;
        }
        return dense;
    }

    pub fn handle(self: *const Store, slot: u32) Handle {
        return .{ .slot = slot, .generation = self.generation[slot] };
    }

    pub fn create(self: *Store) !struct { handle: Handle, command: Command } {
        if (self.free.items.len == 0 or self.count >= self.dense_slot.len) {
            return error.Capacity;
        }

        const slot = self.free.pop().?;
        const dense = self.count;
        self.count += 1;
        self.to_dense[slot] = dense;
        self.dense_slot[dense] = slot;
        self.age[slot] = 0;

        return .{
            .handle = self.handle(slot),
            .command = .{
                .op = 1,
                .slot = slot,
                .generation = self.generation[slot],
                .dense = dense,
            },
        };
    }

    pub fn destroy(self: *Store, handle_to_destroy: Handle) !Command {
        const dense = try self.lookup(handle_to_destroy);
        const last_dense = self.count - 1;
        const moved_slot = self.dense_slot[last_dense];

        // Swap-compaction keeps the dense array contiguous.
        self.dense_slot[dense] = moved_slot;
        self.to_dense[moved_slot] = dense;
        self.dense_slot[last_dense] = none;
        self.count -= 1;
        self.to_dense[handle_to_destroy.slot] = none;

        // Never wrap the generation counter: a retired slot stays retired.
        if (self.generation[handle_to_destroy.slot] != none) {
            self.generation[handle_to_destroy.slot] += 1;
            self.free.appendAssumeCapacity(handle_to_destroy.slot);
        }

        return .{
            .op = 2,
            .slot = handle_to_destroy.slot,
            .generation = handle_to_destroy.generation,
            .dense = dense,
            .next_generation = self.generation[handle_to_destroy.slot],
        };
    }

    pub fn tick(self: *Store) !void {
        for (self.dense_slot[0..self.count]) |slot| {
            self.age[slot] = try std.math.add(u32, self.age[slot], 1);
        }
    }

    /// Builds a larger independent store; the current owner stays valid on failure.
    pub fn expanded(self: *const Store, new_capacity: u32) !Store {
        if (new_capacity <= self.generation.len) return error.Capacity;

        var next = try Store.init(self.allocator, new_capacity, 0);
        errdefer next.deinit();

        const old_capacity = self.generation.len;
        @memcpy(next.generation[0..old_capacity], self.generation);
        @memcpy(next.to_dense[0..old_capacity], self.to_dense);
        @memcpy(next.dense_slot[0..self.count], self.dense_slot[0..self.count]);
        @memcpy(next.age[0..old_capacity], self.age);

        // Preserve reusable ID ordering; append fresh slots before old free slots.
        next.free.clearRetainingCapacity();
        var slot = new_capacity;
        while (slot > old_capacity) {
            slot -= 1;
            next.free.appendAssumeCapacity(@intCast(slot));
        }
        for (self.free.items) |free_slot| {
            next.free.appendAssumeCapacity(free_slot);
        }

        next.count = self.count;
        next.epoch = self.epoch;
        return next;
    }

    pub fn grow(self: *Store, new_capacity: u32) !void {
        const next = try self.expanded(new_capacity);
        self.deinit();
        self.* = next;
    }
};
