const std = @import("std");
const s = @import("storage.zig");
const e = s.entity;
const l = s.l;
const c = s.c;
const a = std.heap.c_allocator;
fn ensure(v: bool) !void {
    if (!v) return error.Verification;
}
fn json(path: []const u8, value: anytype) !void {
    const bytes = try std.json.Stringify.valueAlloc(a, value, .{ .whitespace = .indent_2 });
    defer a.free(bytes);
    try std.fs.cwd().writeFile(.{ .sub_path = path, .data = bytes });
}
const Verification = struct { objects: u64 = 0, words: u64 = 0, mapping_entries: u64 = 0, coverage_entries: u64 = 0, active_indices: u64 = 0, guards: u64 = 0, first: u32 = 0, last: u32 = 0 };
fn verify(b: *s.Bundle, steps: u32, coverage: bool, model: ?*const e.Store) !Verification {
    var v: Verification = .{};
    const state = try b.read(0);
    for (0..b.n) |i| {
        const id = if (model) |m| m.dense_slot[i] else @as(u32, @intCast(i));
        const age = if (model) |m| m.age[id] else steps;
        const expected = s.expected(id, age, b.stride);
        for (expected, 0..) |word, f| {
            const at = try l.address(b.kind, b.cap, i, f);
            if (state[@intCast(at / 4)] != word) {
                std.debug.print("state mismatch i={} field={} id={} got={x} expected={x}\n", .{ i, f, id, state[@intCast(at / 4)], word });
                return error.State;
            }
            v.words += 1;
        }
        if (i == 0) v.first = id;
        if (i + 1 == b.n) v.last = id;
        v.objects += 1;
    }
    for (state[@intCast((b.plan.logical[0] - l.guard_bytes) / 4)..]) |word| {
        try ensure(word == 0xbaadc0de);
        v.guards += 1;
    }
    try b.unmap();
    const maps = try b.read(1);
    for (0..b.cap) |i| {
        const gen = if (model) |m| m.generation[i] else 1;
        const dense = if (model) |m| m.to_dense[i] else if (i < b.n) @as(u32, @intCast(i)) else e.none;
        const slot = if (model) |m| if (i < m.count) m.dense_slot[i] else e.none else if (i < b.n) @as(u32, @intCast(i)) else e.none;
        try ensure(maps[2 * i] == dense and maps[2 * i + 1] == gen and maps[2 * @as(usize, b.cap) + i] == slot);
        v.mapping_entries += 3;
    }
    for (maps[3 * @as(usize, b.cap) ..]) |word| {
        try ensure(word == 0xbaadc0de);
        v.guards += 1;
    }
    try b.unmap();
    const active = try b.read(2);
    var count: u32 = 0;
    for (0..b.n) |i| {
        const id = if (model) |m| m.dense_slot[i] else @as(u32, @intCast(i));
        const flag = s.activeId(id, b.stride);
        try ensure(active[i] == @intFromBool(flag));
        if (flag) {
            try ensure(active[@as(usize, b.cap) + count] == i);
            count += 1;
            v.active_indices += 1;
        }
    }
    try ensure(active[2 * @as(usize, b.cap)] == count);
    for (active[2 * @as(usize, b.cap) + 1 ..]) |word| {
        try ensure(word == 0xbaadc0de);
        v.guards += 1;
    }
    try b.unmap();
    const visits = try b.read(4);
    if (coverage) {
        for (0..8) |pass| for (0..b.n) |i| {
            const id = if (model) |m| m.dense_slot[i] else @as(u32, @intCast(i));
            const wanted: u32 = if (pass == 4 and !s.activeId(id, b.stride)) 0 else 1;
            if (visits[pass * @as(usize, b.cap) + i] != wanted) {
                std.debug.print("coverage mismatch pass={} i={} got={} want={}\n", .{ pass, i, visits[pass * @as(usize, b.cap) + i], wanted });
                return error.Coverage;
            }
            v.coverage_entries += 1;
        };
    }
    for (visits[8 * @as(usize, b.cap) ..]) |word| {
        try ensure(word == 0xbaadc0de);
        v.guards += 1;
    }
    try b.unmap();
    const output = try b.read(5);
    for (0..b.n) |i| {
        const id = if (model) |m| m.dense_slot[i] else @as(u32, @intCast(i));
        const age = if (model) |m| m.age[id] else steps;
        const words = s.expected(id, age, b.stride);
        var h: u32 = 2166136261;
        for (words) |word| h = (h ^ word) *% 16777619;
        try ensure(output[@as(usize, b.cap) + i] == h);
        const view = [_]u32{ words[0], words[1], words[8], id };
        for (view, 0..) |word, j| try ensure(output[2 * @as(usize, b.cap) + 4 * i + j] == word);
        const render = words[0] ^ std.math.rotl(u32, words[1], 7) ^ words[8] ^ id;
        try ensure(output[6 * @as(usize, b.cap) + i] == render);
        // Position-only key was generated before motion update and active gather.
        if (age > 0) {
            const prev = s.expected(id, age - 1, b.stride);
            const x: f32 = @as(f32, @bitCast(prev[0])) + @as(f32, @bitCast(prev[2])) / 64;
            const y: f32 = @as(f32, @bitCast(prev[1])) + @as(f32, @bitCast(prev[3])) / 64;
            const ix: i32 = @intFromFloat(@floor(x * 1024));
            const iy: i32 = @intFromFloat(@floor(y * 1024));
            const key = @as(u32, @bitCast(ix)) *% 0x9e3779b9 ^ @as(u32, @bitCast(iy));
            try ensure(output[i] == key);
        }
    }
    for (output[7 * @as(usize, b.cap) ..]) |word| {
        try ensure(word == 0xbaadc0de);
        v.guards += 1;
    }
    try b.unmap();
    const scratch = try b.read(3);
    const end = try l.add(try l.add(try s.scratchWords(b.cap), 64), b.cap);
    for (scratch[@intCast(end)..]) |word| {
        try ensure(word == 0xbaadc0de);
        v.guards += 1;
    }
    try b.unmap();
    const control = try b.read(6);
    try ensure(control[0] == 0 and control[1] == b.n and control[2] == b.epoch);
    for (control[4 + l.command_capacity ..]) |word| {
        try ensure(word == 0xbaadc0de);
        v.guards += 1;
    }
    try b.unmap();
    return v;
}
fn grow(b: *s.Bundle, model: *e.Store, newcap: u32) !f64 {
    const start = c.s_clock();
    var next = try s.Bundle.init(b.d, b.n, newcap, b.kind, b.stride, 0);
    errdefer next.deinit();
    next.epoch = b.epoch;
    try next.initialize();
    var next_model = try model.expanded(newcap);
    errdefer next_model.deinit();
    try s.ck(c.s_begin(b.d));
    try next.convertSource(b.handles[0], b.kind, b.cap, false);
    var k = next.constants(false);
    k[7] = b.cap;
    try s.ck(c.s_transition(b.d, b.handles[1], 3));
    try next.dispatch(14, newcap, &k, b.handles[1]);
    try s.ck(c.s_transition(b.d, b.handles[1], 0));
    try s.ck(c.s_submit(b.d, 0));
    b.deinit();
    try ensure(c.s_retired_bytes(next.d) > 0 or c.s_completed(next.d) >= c.s_fence(next.d));
    try s.ck(c.s_wait(next.d));
    _ = c.s_collect(next.d);
    model.deinit();
    model.* = next_model;
    b.* = next;
    return c.s_clock() - start;
}
fn lifecycle(d: *c.StorageDevice, kind: u32) !void {
    var b = try s.Bundle.init(d, 32, 64, kind, 10, 0);
    defer b.deinit();
    try b.initialize();
    var model = try e.Store.init(a, 64, 32);
    defer model.deinit();
    const tx = @import("transaction.zig");
    var stale: [2048]e.Handle = undefined;
    var stale_count: usize = 0;
    for (0..20) |_| {
        var actions: [64]tx.Action = undefined;
        var used: usize = 0;
        for (0..16) |j| {
            const h = model.handle(model.dense_slot[j]);
            stale[stale_count] = h;
            stale_count += 1;
            actions[used] = .{ .destroy = h };
            used += 1;
            actions[used] = .{ .create = {} };
            used += 1;
        }
        for (stale[0..@min(stale_count, 16)]) |h| {
            actions[used] = .{ .lookup = h };
            used += 1;
        }
        var prepared = try tx.prepare(&model, actions[0..used]);
        errdefer prepared.rollback();
        try b.commands(prepared.commands[0..prepared.len]);
        try prepared.publish();
        try ensure(model.count == b.n);
        const control = try b.read(6);
        for (0..used) |j| if (prepared.commands[j].op == 3) try ensure(control[4 + j] == e.none);
        try b.unmap();
    }
    const growth_us = try grow(&b, &model, 128);
    // New IDs above the old capacity are real creations after GPU migration.
    var commands: [64]e.Command = undefined;
    for (&commands) |*command| command.* = (try model.create()).command;
    try b.commands(&commands);
    model.epoch += 1;
    try s.ck(c.s_begin(d));
    try b.pipeline(true, true, false);
    try s.ck(c.s_submit(d, 0));
    try s.ck(c.s_wait(d));
    try model.tick();
    const verified = try verify(&b, 1, true, &model);
    // Delete to zero, then recreate with a different activity policy. Cached
    // active sets must invalidate on both the structural epoch and policy.
    var deletions: [128]tx.Action = undefined;
    const old_count = model.count;
    for (0..old_count) |j| deletions[j] = .{ .destroy = model.handle(model.dense_slot[j]) };
    var empty = try tx.prepare(&model, deletions[0..old_count]);
    try b.commands(empty.commands[0..empty.len]);
    try empty.publish();
    try s.ck(c.s_begin(d));
    try b.pipeline(true, false, false);
    try s.ck(c.s_submit(d, 0));
    try s.ck(c.s_wait(d));
    _ = try verify(&b, 0, true, &model);
    var creations: [32]tx.Action = undefined;
    @memset(&creations, .{ .create = {} });
    var fresh = try tx.prepare(&model, &creations);
    try b.commands(fresh.commands[0..fresh.len]);
    try fresh.publish();
    b.stride = 0;
    try s.ck(c.s_begin(d));
    const k = b.constants(true);
    try b.dispatch(17, b.cap, &k, b.handles[8]);
    try b.pipeline(true, false, false);
    try s.ck(c.s_submit(d, 0));
    try s.ck(c.s_wait(d));
    try model.tick();
    _ = try verify(&b, 1, true, &model);
    // Deliberate delayed completion blocks reset/map and defers retirement.
    const h = c.s_new(d, 65536, 0, "delayed lifetime fixture");
    if (h == 0) return error.Allocation;
    try s.ck(c.s_begin(d));
    try s.ck(c.s_transition(d, h, 1));
    try s.ck(c.s_delay(d));
    try s.ck(c.s_submit(d, 0));
    try ensure(c.s_begin(d) == 0);
    try s.ck(c.s_retire(d, h));
    _ = c.s_collect(d);
    try ensure(c.s_retired_bytes(d) >= 65536);
    try s.ck(c.s_unblock(d));
    try s.ck(c.s_wait(d));
    _ = c.s_collect(d);
    try ensure(c.s_retired_bytes(d) == 0);
    try ensure(c.s_retire(d, h) == 0);
    std.debug.print("lifecycle kind={} records={} growth_us={d:.2} stale={} guards={}\n", .{ kind, verified.objects, growth_us, stale_count, verified.guards });
}
fn largeLifecycle(d: *c.StorageDevice, n: u32, kind: u32, out: []const u8) !void {
    const cap: u32 = try l.capacityFor(try l.add(n, 32));
    var b = try s.Bundle.init(d, n, cap, kind, 10, 0);
    defer b.deinit();
    try b.initialize();
    var model = try e.Store.init(a, cap, n);
    defer model.deinit();
    const tx = @import("transaction.zig");
    var actions: [15]tx.Action = undefined;
    const ids = [_]u32{ 0, n / 2, n - 1, 65535, 65536 };
    for (ids, 0..) |id, j| actions[j] = .{ .destroy = model.handle(id) };
    for (5..10) |j| actions[j] = .{ .create = {} };
    for (ids, 0..) |id, j| actions[10 + j] = .{ .lookup = model.handle(id) };
    var pending = try tx.prepare(&model, &actions);
    errdefer pending.rollback();
    try b.commands(pending.commands[0..pending.len]);
    try pending.publish();
    const query = try b.read(6);
    for (10..15) |j| try ensure(query[4 + j] == e.none);
    try b.unmap();
    try s.ck(c.s_begin(d));
    try b.pipeline(true, false, false);
    try s.ck(c.s_submit(d, 0));
    try s.ck(c.s_wait(d));
    try model.tick();
    const before = try verify(&b, 1, true, &model);
    const old_commit = b.plan.total;
    // Insufficient overlap admission leaves existing storage and allocations intact.
    var memory_before: c.Memory = undefined;
    try s.ck(c.s_memory(d, &memory_before));
    if (s.Bundle.init(d, n, cap * 2, kind, 10, 1)) |*unexpected| {
        var owned = unexpected.*;
        owned.deinit();
        return error.Rejection;
    } else |err| {
        if (err != error.MemoryAdmission) return err;
    }
    var memory_rejected: c.Memory = undefined;
    try s.ck(c.s_memory(d, &memory_rejected));
    try ensure(memory_before.allocations == memory_rejected.allocations and memory_before.committed == memory_rejected.committed);
    const growth_us = try grow(&b, &model, cap * 2);
    try s.ck(c.s_begin(d));
    try b.pipeline(true, false, false);
    try s.ck(c.s_submit(d, 0));
    try s.ck(c.s_wait(d));
    try model.tick();
    const after = try verify(&b, 2, true, &model);
    var memory: c.Memory = undefined;
    try s.ck(c.s_memory(d, &memory));
    try ensure(memory.committed == b.plan.total + c.s_context_bytes(d) and memory.peak_committed >= old_commit + b.plan.total);
    try ensure(c.s_errors(d) == 0);
    try json(out, .{ .status = "LARGE_IDENTITY_COMPACTION_GROWTH_VERIFIED", .n = n, .layout = kind, .initial_capacity = cap, .grown_capacity = b.cap, .initial_commit = old_commit, .grown_ledger = b.plan, .before_growth = before, .after_growth = after, .cpu_metadata_capacity_bytes = @as(u64, b.cap) * 20, .growth_overlap_peak_bytes = memory.peak_committed, .growth_wall_us = growth_us, .budget_rejection_preserved_state = true, .memory = memory, .gpu_validation_errors = c.s_errors(d) });
    std.debug.print("LARGE LIFECYCLE VERIFIED n={} kind={} capacity={} peak={} growth_us={d:.2}\n", .{ n, kind, b.cap, memory.peak_committed, growth_us });
}
pub fn main() !void {
    const args = try std.process.argsAlloc(a);
    defer std.process.argsFree(a, args);
    var n: u32 = 100000;
    var kind: u32 = 0;
    var stride: u32 = 10;
    var steps: u32 = 1;
    var debug = false;
    var bench = false;
    var life = false;
    var large_life = false;
    var cached = false;
    var headroom: u64 = 268435456;
    var percent: u32 = 10;
    var reserve: u64 = 67108864;
    var vector = false;
    var budget_cap: u64 = 0;
    var out: []const u8 = "evidence/single.json";
    var i: usize = 1;
    while (i < args.len) : (i += 1) {
        const arg = args[i];
        if (std.mem.eql(u8, arg, "--debug")) {
            debug = true;
            continue;
        }
        if (std.mem.eql(u8, arg, "--bench")) {
            bench = true;
            continue;
        }
        if (std.mem.eql(u8, arg, "--vector-full")) {
            vector = true;
            continue;
        }
        if (std.mem.eql(u8, arg, "--lifecycle")) {
            life = true;
            continue;
        }
        if (std.mem.eql(u8, arg, "--large-lifecycle")) {
            large_life = true;
            continue;
        }
        if (std.mem.eql(u8, arg, "--cached-active")) {
            cached = true;
            continue;
        }
        i += 1;
        if (i >= args.len) return error.Argument;
        const v = args[i];
        if (std.mem.eql(u8, arg, "--out")) out = v else if (std.mem.eql(u8, arg, "--n")) n = try std.fmt.parseInt(u32, v, 10) else if (std.mem.eql(u8, arg, "--layout")) kind = try std.fmt.parseInt(u32, v, 10) else if (std.mem.eql(u8, arg, "--active-stride")) stride = try std.fmt.parseInt(u32, v, 10) else if (std.mem.eql(u8, arg, "--steps")) steps = try std.fmt.parseInt(u32, v, 10) else if (std.mem.eql(u8, arg, "--headroom-bytes")) headroom = try std.fmt.parseInt(u64, v, 10) else if (std.mem.eql(u8, arg, "--headroom-percent")) percent = try std.fmt.parseInt(u32, v, 10) else if (std.mem.eql(u8, arg, "--driver-reserve-bytes")) reserve = try std.fmt.parseInt(u64, v, 10) else if (std.mem.eql(u8, arg, "--budget-cap")) budget_cap = try std.fmt.parseInt(u64, v, 10) else return error.Argument;
    }
    if (n == 0 or steps == 0 or steps > 1000) return error.Argument;
    const d = try s.open(debug);
    defer c.s_close(d);
    try s.ck(c.s_policy(d, headroom, percent, reserve));
    if (large_life) {
        if (n < 100000) return error.Argument;
        try largeLifecycle(d, n, kind, out);
        return;
    }
    if (life) {
        for (0..10) |site| {
            var before_failure: c.Memory = undefined;
            try s.ck(c.s_memory(d, &before_failure));
            c.s_fail_after(d, @intCast(site));
            if (s.Bundle.init(d, 13325, 13344, 0, 10, 0)) |*unexpected| {
                var owned = unexpected.*;
                owned.deinit();
                return error.ExpectedAllocationFailure;
            } else |err| {
                if (err != error.Allocation) return err;
            }
            var after_failure: c.Memory = undefined;
            try s.ck(c.s_memory(d, &after_failure));
            try ensure(before_failure.committed == after_failure.committed);
        }
        c.s_fail_after(d, std.math.maxInt(u32));
    }
    if (life) {
        for (0..3) |layout| try lifecycle(d, @intCast(layout));
        try ensure(c.s_errors(d) == 0);
        try json(out, .{ .passed = true, .layouts_tested = @as(u32, 3), .random_seed = @as(u32, 0x713), .delayed_retirement = true, .actual_gpu_migration = true, .allocation_failure_sites = @as(u32, 10), .empty_storage_and_active_tests = true, .stale_handles_rejected = true, .gpu_validation_errors = c.s_errors(d) });
        return;
    }
    const cap: u32 = l.capacityFor(n) catch |err| {
        try json(out, .{ .status = "EXPECTED_ADDRESS_REJECTION", .n = n, .actual_processed = @as(u64, 0), .reason = @errorName(err) });
        return;
    };
    var before: c.Memory = undefined;
    try s.ck(c.s_memory(d, &before));
    var b = s.Bundle.init(d, n, cap, kind, stride, budget_cap) catch |err| {
        if (err == error.MemoryAdmission) {
            try json(out, .{ .status = "EXPECTED_BUDGET_REJECTION", .n = n, .actual_processed = @as(u64, 0), .memory = before, .budget_cap = budget_cap });
            return;
        }
        return err;
    };
    defer b.deinit();
    b.vector_full = vector;
    try b.initialize();
    // Round-trip conversion measured separately; render-view conversion remains
    // included in every complete processing pipeline.
    const conversion_start = c.s_clock();
    try s.ck(c.s_begin(d));
    try s.ck(c.s_stamp(d, 0));
    const native = b.handles[0];
    const canonical = b.handles[9];
    b.handles[0] = canonical;
    const native_kind = b.kind;
    b.kind = 0;
    try b.convertSource(native, native_kind, b.cap, false);
    b.kind = native_kind;
    b.handles[0] = native;
    try s.ck(c.s_stamp(d, 1));
    try b.convertSource(canonical, 0, b.cap, false);
    try s.ck(c.s_stamp(d, 2));
    try s.ck(c.s_submit(d, 3));
    try s.ck(c.s_wait(d));
    var convert_times: [32]f64 = undefined;
    try s.ck(c.s_times(d, &convert_times));
    const conversion_cpu = c.s_clock() - conversion_start;
    const warmup: u32 = if (bench) 20 else 0;
    var rows = try a.alloc([9]f64, steps);
    defer a.free(rows);
    var cpu = try a.alloc(f64, steps);
    defer a.free(cpu);
    var totalsteps: u32 = 0;
    // Coverage is per tick. Match the existing lifecycle path's explicit reset.
    for (0..warmup + steps) |tick| {
        try s.ck(c.s_begin(d));
        const start = c.s_clock();
        if (!bench) {
            const k = b.constants(true);
            try b.dispatch(17, b.cap, &k, b.handles[8]);
        }
        try b.pipeline(!bench, !cached or tick == 0, true);
        try s.ck(c.s_submit(d, 9));
        const overhead = c.s_clock() - start;
        try s.ck(c.s_wait(d));
        var times: [32]f64 = undefined;
        try s.ck(c.s_times(d, &times));
        totalsteps += 1;
        if (tick >= warmup) {
            const row = tick - warmup;
            rows[row][0] = times[8] - times[0];
            for (1..9) |j| rows[row][j] = times[j] - times[j - 1];
            cpu[row] = overhead;
        }
    }
    const verified = try verify(&b, totalsteps, !bench, null);
    try ensure(c.s_errors(d) == 0);
    var memory: c.Memory = undefined;
    try s.ck(c.s_memory(d, &memory));
    try ensure(memory.committed == b.plan.total + c.s_context_bytes(d));
    try json(out, .{ .status = "PROCESSED_AND_FULLY_VERIFIED", .headroom_bytes = headroom, .headroom_percent = percent, .opaque_driver_reserve = reserve, .adapter = std.mem.span(c.s_name(d)), .driver = c.s_driver(d), .debug = debug, .n = n, .capacity = cap, .layout = kind, .active_stride = stride, .active_count = verified.active_indices, .steps = steps, .warmup = warmup, .cached_active = cached, .vector_full = vector, .verification = verified, .ledger = b.plan, .memory_before = before, .memory = memory, .allocation_us = b.allocation_us, .conversion_native_to_aos_gpu_us = convert_times[1] - convert_times[0], .conversion_aos_to_native_gpu_us = convert_times[2] - convert_times[1], .conversion_cpu_us = conversion_cpu, .gpu_rows_us = rows, .cpu_record_submit_us = cpu, .gpu_validation_errors = c.s_errors(d), .cache_counters = "UNAVAILABLE unless external profiler capture is attached", .physics_executed = false });
    std.debug.print("VERIFIED N={} layout={} active={} steps={} words={} coverage={} committed={}\n", .{ n, kind, verified.active_indices, totalsteps, verified.words, verified.coverage_entries, memory.committed });
}
