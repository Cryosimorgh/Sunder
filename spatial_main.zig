const std = @import("std");
const s = @import("storage.zig");
const e = s.entity;
const c = @cImport({
    @cInclude("spatial.h");
});
const a = std.heap.c_allocator;
fn ck(v: c_int) !void {
    if (v == 0) return error.Spatial;
}
fn save(path: []const u8, value: anytype) !void {
    const bytes = try std.json.Stringify.valueAlloc(a, value, .{ .whitespace = .indent_2 });
    defer a.free(bytes);
    try std.fs.cwd().writeFile(.{ .sub_path = path, .data = bytes });
}
pub fn main() !void {
    try ck(c.sp_math_tests());
    const args = try std.process.argsAlloc(a);
    defer std.process.argsFree(a, args);
    var n: u32 = 100000;
    var design: u32 = 1;
    var fixture: u32 = 1;
    var stride: u32 = 1;
    var pairs: u32 = 1000000;
    var visits: u32 = 65536;
    var steps: u32 = 1;
    var warm: u32 = 0;
    var budget: u64 = 0;
    var fail_at: u32 = std.math.maxInt(u32);
    var debug = false;
    var lifecycle = false;
    var boundary = false;
    var fast = true;
    var lifetime = false;
    var scan_test = false;
    var mapping = false;
    var sticky = false;
    var corrupt_guard = false;
    var out: []const u8 = "spatial-result.json";
    var i: usize = 1;
    while (i < args.len) : (i += 1) {
        const arg = args[i];
        if (std.mem.eql(u8, arg, "--debug")) {
            debug = true;
            continue;
        }
        if (std.mem.eql(u8, arg, "--mapping")) {
            mapping = true;
            continue;
        }
        if (std.mem.eql(u8, arg, "--sticky")) {
            sticky = true;
            continue;
        }
        if (std.mem.eql(u8, arg, "--corrupt-guard")) {
            corrupt_guard = true;
            continue;
        }
        if (std.mem.eql(u8, arg, "--scan-test")) {
            scan_test = true;
            continue;
        }
        if (std.mem.eql(u8, arg, "--lifetime")) {
            lifetime = true;
            continue;
        }
        if (std.mem.eql(u8, arg, "--lifecycle")) {
            lifecycle = true;
            continue;
        }
        if (std.mem.eql(u8, arg, "--baseline")) {
            fast = false;
            continue;
        }
        if (std.mem.eql(u8, arg, "--dispatch-boundary")) {
            boundary = true;
            continue;
        }
        i += 1;
        if (i >= args.len) return error.Arg;
        if (std.mem.eql(u8, arg, "--out")) {
            out = args[i];
            continue;
        }
        const v = try std.fmt.parseInt(u64, args[i], 10);
        if (std.mem.eql(u8, arg, "--n")) n = std.math.cast(u32, v) orelse return error.Range else if (std.mem.eql(u8, arg, "--design")) design = @intCast(v) else if (std.mem.eql(u8, arg, "--fixture")) fixture = @intCast(v) else if (std.mem.eql(u8, arg, "--stride")) stride = @intCast(v) else if (std.mem.eql(u8, arg, "--pairs")) pairs = @intCast(v) else if (std.mem.eql(u8, arg, "--visits")) visits = @intCast(v) else if (std.mem.eql(u8, arg, "--steps")) steps = @intCast(v) else if (std.mem.eql(u8, arg, "--warmup")) warm = @intCast(v) else if (std.mem.eql(u8, arg, "--budget")) budget = v else if (std.mem.eql(u8, arg, "--fail-at")) fail_at = @intCast(v) else return error.Arg;
    }
    if (steps == 0 or (sticky and steps < 2)) return error.Config;
    const d = try s.open(debug);
    defer s.c.s_close(d);
    const cap = s.l.capacityFor(n) catch {
        try save(out, .{ .status = "EXPECTED_ADDRESS_REJECTION", .actual_processed = 0 });
        return;
    };
    var b = s.Bundle.init(d, n, cap, 1, stride, 0) catch |err| {
        try save(out, .{ .status = @errorName(err), .actual_processed = 0 });
        return;
    };
    defer b.deinit();
    try b.initialize();
    var model = try e.Store.init(a, cap, n);
    defer model.deinit();
    if (lifecycle) {
        var commands: [15]e.Command = undefined;
        var k: usize = 0;
        for ([_]u32{ 0, n / 2, n - 1 }) |slot| {
            commands[k] = try model.destroy(model.handle(slot));
            k += 1;
        }
        for (0..3) |_| {
            const made = try model.create();
            commands[k] = made.command;
            k += 1;
        }
        try b.commands(commands[0..k]);
    }
    const wall0 = s.c.s_clock();
    var memory_before: s.c.Memory = undefined;
    try s.ck(s.c.s_memory(d, &memory_before));
    const initial = try b.read(0);
    var initial_hash: [32]u8 = undefined;
    std.crypto.hash.sha2.Sha256.hash(std.mem.sliceAsBytes(initial), &initial_hash, .{});
    try b.unmap();
    s.c.s_fail_after(d, fail_at);
    const sp = c.sp_open(@ptrCast(d), &b.handles, n, cap, design, fixture, stride, pairs, visits, budget) orelse {
        const code = c.sp_error();
        const unchanged = try b.read(0);
        var unchanged_hash: [32]u8 = undefined;
        std.crypto.hash.sha2.Sha256.hash(std.mem.sliceAsBytes(unchanged), &unchanged_hash, .{});
        try b.unmap();
        var mem: s.c.Memory = undefined;
        try s.ck(s.c.s_memory(d, &mem));
        const preserved = std.mem.eql(u8, &initial_hash, &unchanged_hash) and mem.committed == memory_before.committed;
        if (!preserved) return error.AllocationRollback;
        try save(out, .{ .status = if (code == 2) "EXPECTED_ADMISSION_REJECTION" else if (code == 1) "EXPECTED_ADDRESS_REJECTION" else if (code == 3 and fail_at < 5) "EXPECTED_ALLOCATION_REJECTION" else "ERROR", .error_code = code, .actual_processed = 0, .n = n, .design = design, .fixture = fixture, .fail_at = fail_at, .state_preserved = preserved, .committed_before = memory_before.committed, .committed_after = mem.committed });
        if (code > 2 and !(code == 3 and fail_at < 5)) return error.SpatialOpen;
        return;
    };
    defer c.sp_close(sp);
    const wall1 = s.c.s_clock();
    c.sp_fast_static(sp, @intFromBool(fast));
    if (boundary) c.sp_dispatch_extent(sp, 16777217);
    try ck(c.sp_fixture(sp));
    const before = try b.read(0);
    try ck(c.sp_state(sp, before.ptr, model.dense_slot.ptr));
    var hash_before: [32]u8 = undefined;
    std.crypto.hash.sha2.Sha256.hash(std.mem.sliceAsBytes(before), &hash_before, .{});
    try b.unmap();
    if (lifetime or scan_test or mapping) {
        if (mapping) try ck(c.sp_mapping_test(sp)) else if (scan_test) try ck(c.sp_scan_test(sp)) else try ck(c.sp_fence_test(sp));
        const unchanged = try b.read(0);
        var lifetime_hash: [32]u8 = undefined;
        std.crypto.hash.sha2.Sha256.hash(std.mem.sliceAsBytes(unchanged), &lifetime_hash, .{});
        try b.unmap();
        if (!std.mem.eql(u8, &hash_before, &lifetime_hash)) return error.LifetimeState;
        try save(out, .{ .status = if (mapping) "MAPPING_PASS" else if (scan_test) "COUNTER_PASS" else "LIFETIME_PASS", .actual_processed = 0, .state_preserved = true, .mapping_cases = if (mapping) @as(u32, 6) else 0, .synthetic_count_words = if (scan_test) n else 0, .synthetic_contact_total = if (scan_test) @as(u64, n) * (std.math.maxInt(u32) - 1) + @as(u64, n) * (n - 1) / 2 else 0, .synthetic_total = if (scan_test) @as(u64, n) * std.math.maxInt(u32) + @as(u64, n) * (n - 1) / 2 else 0, .pending_releases = 0, .retired_after_signal = if (lifetime) @as(u32, 5) else 0, .reset_while_pending_rejected = lifetime, .debug = debug });
        return;
    }
    const wall2 = s.c.s_clock();
    var r: c.SpatialResult = std.mem.zeroes(c.SpatialResult);
    const timings = try a.alloc([12]f64, steps);
    defer a.free(timings);
    const cpu = try a.alloc(f64, steps);
    defer a.free(cpu);
    // G1 active-list compaction writes flags and dense indices once, before G2.
    try s.ck(s.c.s_begin(d));
    try b.compact(false);
    try s.ck(s.c.s_submit(d, 0));
    try s.ck(s.c.s_wait(d));
    if (corrupt_guard) try ck(c.sp_inject(sp, 1));
    for (0..warm + steps) |k| {
        try ck(if (fixture == 0) c.sp_run_zero_reference(sp, &r) else c.sp_run(sp, &r));
        if (sticky and k == 0) try ck(c.sp_inject(sp, 0));
        if (k >= warm) {
            timings[k - warm] = r.stages;
            cpu[k - warm] = r.cpu_us;
        }
    }
    const wall3 = s.c.s_clock();
    try ck(c.sp_verify(sp, &r, model.dense_slot.ptr, model.generation.ptr, model.to_dense.ptr));
    const wall4 = s.c.s_clock();
    const after = try b.read(0);
    var hash_after: [32]u8 = undefined;
    std.crypto.hash.sha2.Sha256.hash(std.mem.sliceAsBytes(after), &hash_after, .{});
    try b.unmap();
    if (!std.mem.eql(u8, &hash_before, &hash_after)) return error.StateChanged;
    const ledger_path = try std.fmt.allocPrintSentinel(a, "{s}.ledger.json", .{out}, 0);
    defer a.free(ledger_path);
    try ck(c.sp_ledger(sp, ledger_path));
    var memory: s.c.Memory = undefined;
    try s.ck(s.c.s_memory(d, &memory));
    const count_exact = (r.status & ~@as(u32, 256)) == 0;
    try save(out, .{ .status = if (r.status == 0) "PASS" else "GPU_REJECTED", .n = n, .capacity = cap, .design = design, .fixture = fixture, .active_stride = stride, .pair_capacity = pairs, .max_visits = visits, .actual_processed = if (r.status == 0) r.verified_objects else 0, .key_processed = r.verified_objects, .reference_integration_count = if (fixture == 0) @as(u32, n) else 0, .active = r.active, .pairs = if (count_exact) @as(?u64, r.pairs) else null, .contacts = if (r.status == 0) @as(?u64, r.contacts) else null, .false_positives = if (r.status == 0) @as(?u64, r.pairs - r.contacts) else null, .candidate_count_exact = count_exact, .verified_pairs = r.verified_pairs, .verified_contacts = r.verified_contacts, .islands = if (r.status == 0) @as(?u32, r.islands) else null, .largest_island = if (r.status == 0) @as(?u32, r.largest) else null, .contact_participants = if (r.status == 0) @as(?u32, r.participants) else null, .gpu_status = r.status, .guards = r.guards, .state_preserved = true, .fast_static = fast, .dispatch_boundary = boundary, .injected_sticky = sticky, .injected_guard = corrupt_guard, .lifecycle = lifecycle, .debug = debug, .steps = steps, .warmup = warm, .gpu_us = timings, .cpu_us = cpu, .spatial_committed = r.committed, .storage_committed = b.plan.total, .memory = memory, .allocation_us = r.allocation_us, .verification_wall_us = [_]f64{ wall1 - wall0, wall2 - wall1, wall3 - wall2, wall4 - wall3, s.c.s_clock() - wall4 }, .validation_errors = s.c.s_errors(d), .state_sha256 = std.fmt.bytesToHex(hash_after, .lower) });
}
