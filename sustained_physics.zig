// Bounded qualification driver over the existing physics/runtime and CPU oracle.
// No solver, scene generation, GPU-stage control, or production defaults here.
const std = @import("std");
const s = @import("storage.zig");
const a = std.heap.c_allocator;
const c = @cImport({
    @cInclude("physics.h");
    @cInclude("pool-layout.h");
    @cInclude("playground-layout.h");
});
fn ck(x: c_int) !void {
    if (x == 0) return error.API;
}
fn emit(file: std.fs.File, value: anytype) !void {
    const data = try std.json.Stringify.valueAlloc(a, value, .{});
    defer a.free(data);
    try file.writeAll(data);
    try file.writeAll("\n");
}
fn state(b: *s.Bundle, p: *c.Physics, pool: bool) !struct { hash: [32]u8, energy: f64, rest: bool, valid: bool } {
    const raw = try b.read(0);
    defer b.unmap() catch {};
    var h = std.crypto.hash.sha2.Sha256.init(.{});
    h.update(std.mem.sliceAsBytes(raw));
    var body: [16][16]f32 = undefined;
    var e: f64 = 0;
    var rest = true;
    var valid = true;
    for (0..b.n) |i| {
        var values: [16]f32 = undefined;
        for (0..16) |j| values[j] = @bitCast(raw[j * b.cap + i]);
        for (values[0..12]) |v| {
            if (!std.math.isFinite(v)) valid = false;
        }
        if (raw[15 * b.cap + i] != i) valid = false;
        if (values[2] != 0 or values[3] != 0 or values[5] != 0) rest = false;
        if (values[6] > 0) e += (@as(f64, values[2]) * values[2] + @as(f64, values[3]) * values[3]) / (2 * @as(f64, values[6]));
        if (values[7] > 0) e += @as(f64, values[5]) * values[5] / (2 * @as(f64, values[7]));
        if (pool) body[i] = values;
    }
    if (pool) {
        var data: ?*const anyopaque = null;
        var bytes: u64 = 0;
        try ck(c.ph_read(p, 2, &data, &bytes));
        defer _ = c.ph_unmap(p);
        const words = @as([*]const u32, @ptrCast(@alignCast(data.?)));
        // Same retained-current rolling-state offset used by pool_tests.zig F.rolls().
        const base: usize = 256 + 164 * @as(usize, b.cap) + 256 + 32;
        h.update(std.mem.asBytes(&words[base / 4 ..][0..32].*));
        for (0..32) |j| {
            const v: f32 = @bitCast(words[base / 4 + j]);
            if (!std.math.isFinite(v)) valid = false;
            if (v != 0) rest = false;
            e += 0.2 * c.POOL_MASS * @as(f64, v) * v;
        }
        for (body, 0..) |v, i| {
            if (v[0] < c.POOL_RADIUS - 1e-6 or v[0] > c.POOL_TABLE_WIDTH - c.POOL_RADIUS + 1e-6 or v[1] < c.POOL_RADIUS - 1e-6 or v[1] > c.POOL_TABLE_HEIGHT - c.POOL_RADIUS + 1e-6) valid = false;
            for (body[0..i]) |w| {
                const dx = @as(f64, v[0]) - w[0];
                const dy = @as(f64, v[1]) - w[1];
                const distance = @sqrt(dx * dx + dy * dy);
                const rounding = 8.0 * 1.1920928955078125e-7 * (@abs(v[0]) + @abs(v[1]) + @abs(w[0]) + @abs(w[1]) + 4.0 * c.POOL_RADIUS);
                if (distance + rounding < 2 * c.POOL_RADIUS) valid = false;
            }
        }
    }
    var hash: [32]u8 = undefined;
    h.final(&hash);
    return .{ .hash = hash, .energy = e, .rest = rest, .valid = valid };
}
pub fn run(d: *s.c.StorageDevice, b: *s.Bundle, opaque_p: *anyopaque, opaque_cfg: *const anyopaque, model: *s.entity.Store, seconds: u32, path: []const u8) !void {
    const p: *c.Physics = @ptrCast(opaque_p);
    const cfg: *const c.PhysicsConfig = @ptrCast(@alignCast(opaque_cfg));
    const pool = cfg.fixture == 13;
    if (seconds < 1 or seconds > 30 or (pool and b.n != 16) or (!pool and (cfg.fixture < 9 or cfg.fixture > 11 or cfg.flags != 4))) return error.QualificationConfig;
    const dc: *c.StorageDevice = @ptrCast(d);
    const stream_path = try std.fmt.allocPrint(a, "{s}.jsonl", .{path});
    defer a.free(stream_path);
    const file = try std.fs.cwd().createFile(stream_path, .{});
    defer file.close();
    const command = if (pool) s.c.s_new(d, 32, 1, "Existing pool cue qualification command") else 0;
    if (pool and command == 0) return error.Allocation;
    defer if (command != 0) {
        _ = s.c.s_retire(d, command);
        _ = s.c.s_collect(d);
    };
    if (pool) try ck(c.ph_user_command(p, command));
    var prior = try state(b, p, pool);
    if (!prior.valid) return error.InitialState;
    var memory: s.c.Memory = undefined;
    try ck(s.c.s_memory(d, &memory));
    try emit(file, .{ .type = "START", .n = b.n, .fixture = cfg.fixture, .flags = cfg.flags, .dt = cfg.dt, .seconds = seconds, .adapter = std.mem.span(s.c.s_name(d)), .driver = s.c.s_driver(d), .initial_hash = std.fmt.bytesToHex(prior.hash, .lower), .initial_energy = prior.energy, .memory = memory, .pool_independent_KKT = false, .distributed_independent_KKT = !pool, .meaning = "30 wall-clock seconds, fixed global dt; throughput includes every-tick CPU verification/readback/logging" });
    const start = s.c.s_clock();
    var tick: u32 = 0;
    var shots: u32 = 0;
    while (s.c.s_clock() - start < @as(f64, @floatFromInt(seconds)) * 1e6 and tick < 100000) {
        const before = s.c.s_clock();
        var shot = false;
        if (pool) {
            var words = [_]u32{0} ** 8;
            if (prior.rest) {
                words = .{ c.PLAY_COMMAND_MAGIC, 0, 1, 1, @bitCast(@as(f32, if (shots % 2 == 0) 1.5 else -1.5)), 0, shots + 1, tick };
                shot = true;
                shots += 1;
            }
            const raw = s.c.s_map(d, command, 0) orelse return error.Map;
            @memcpy(@as([*]u32, @ptrCast(@alignCast(raw)))[0..8], &words);
            try ck(s.c.s_unmap(d, command, 32));
        }
        var q: c.PhysicsResult = std.mem.zeroes(c.PhysicsResult);
        const api = c.ph_tick(p, tick, &q);
        const verify_start = s.c.s_clock();
        const current = try state(b, p, pool);
        var oracle: c.PhysicsVerification = std.mem.zeroes(c.PhysicsVerification);
        const oracle_ok = if (!pool and q.error_flags == 0 and api != 0) c.ph_verify(p, cfg, tick + 1, model.dense_slot.ptr, model.generation.ptr, model.to_dense.ptr, &oracle) != 0 else pool;
        const injected_energy = if (shot) 0.5 * c.POOL_MASS * 1.5 * 1.5 else 0;
        const energy_bound = 256.0 * 1.1920928955078125e-7 * @max(prior.energy + injected_energy, 1e-12);
        const energy_ok = current.energy <= prior.energy + injected_energy + energy_bound;
        try ck(s.c.s_memory(d, &memory));
        const valid = api != 0 and q.error_flags == 0 and q.published == b.n and current.valid and oracle_ok and energy_ok and s.c.s_errors(d) == 0;
        try emit(file, .{ .type = "TICK", .tick = tick, .elapsed_s = (s.c.s_clock() - start) / 1e6, .api_ok = api != 0, .accepted = q.error_flags == 0 and q.published == b.n and api != 0, .valid = valid, .error_flags = q.error_flags, .published = q.published, .active = q.active, .contacts = q.contacts, .islands = q.islands, .largest = q.largest, .solved_bodies = q.solved_bodies, .iterations = q.total_iterations, .max_iterations = q.max_iterations, .gpu_us = q.gpu_us[0..40], .cpu_record_us = q.cpu_record_us, .cpu_submit_us = q.queue_submit_us, .blocking_us = q.blocking_us, .api_us = q.api_us, .verification_us = s.c.s_clock() - verify_start, .wall_tick_us = s.c.s_clock() - before, .energy = current.energy, .prior_energy = prior.energy, .injected_energy = injected_energy, .energy_ok = energy_ok, .oracle_ok = oracle_ok, .independent = oracle, .state_hash = std.fmt.bytesToHex(current.hash, .lower), .rollback_verified = if (q.error_flags != 0) @as(?bool, std.mem.eql(u8, &prior.hash, &current.hash)) else null, .shot = shot, .memory = memory });
        if (!valid) {
            // Final tick is already fence-complete. Preserve inputs/trial/contact/metadata
            // without dispatching another simulation tick or publishing rejected state.
            for ([_]c_int{ 0, 1, 2, 3 }, [_][]const u8{ "state", "trial", "meta", "contacts" }) |which, name| {
                var view: ?*const anyopaque = null;
                var bytes: u64 = 0;
                try ck(c.ph_read(p, which, &view, &bytes));
                const dump_path = try std.fmt.allocPrint(a, "{s}.failure-{s}.bin", .{ path, name });
                defer a.free(dump_path);
                try std.fs.cwd().writeFile(.{ .sub_path = dump_path, .data = @as([*]const u8, @ptrCast(view.?))[0..bytes] });
                try ck(c.ph_unmap(p));
            }
            return error.QualificationFailure;
        }
        prior = current;
        tick += 1;
    }
    if (tick == 100000) return error.TickBound;
    // Existing spatial corruption hook, separate from timed performance samples.
    try ck(c.ph_inject(p, 1));
    var rejected: c.PhysicsResult = std.mem.zeroes(c.PhysicsResult);
    try ck(c.ph_tick(p, tick, &rejected));
    const after = try state(b, p, pool);
    const rollback = rejected.error_flags != 0 and rejected.published == 0 and std.mem.eql(u8, &prior.hash, &after.hash);
    try emit(file, .{ .type = "ROLLBACK_PROBE", .expected_rejection = true, .error_flags = rejected.error_flags, .published = rejected.published, .rollback_verified = rollback });
    if (!rollback) return error.Rollback;
    try emit(file, .{ .type = "END", .wall_s = (s.c.s_clock() - start) / 1e6, .accepted_ticks = tick, .simulation_s = @as(f64, @floatFromInt(tick)) * cfg.dt, .shots = shots, .state_hash = std.fmt.bytesToHex(after.hash, .lower) });
    _ = dc;
}
pub fn finish(d: *s.c.StorageDevice, path: []const u8, ok: bool, reason: []const u8) !bool {
    var memory: s.c.Memory = undefined;
    try ck(s.c.s_memory(d, &memory));
    const good = memory.committed == memory.context_committed and s.c.s_retired_bytes(d) == 0 and s.c.s_errors(d) == 0;
    const data = try std.json.Stringify.valueAlloc(a, .{ .status = if (ok and good) "PASS" else "FAIL", .reason = reason, .cleanup_ok = good, .memory = memory, .retired_bytes = s.c.s_retired_bytes(d), .validation_errors = s.c.s_errors(d) }, .{ .whitespace = .indent_2 });
    defer a.free(data);
    try std.fs.cwd().writeFile(.{ .sub_path = path, .data = data });
    return ok and good;
}
