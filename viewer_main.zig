const std = @import("std");
const s = @import("storage.zig");
const c = @cImport({
    @cInclude("viewer.h");
});
const a = std.heap.c_allocator;
fn ck(v: c_int) !void {
    if (v == 0) return error.Viewer;
}
pub fn main() !void {
    const args = try std.process.argsAlloc(a);
    defer std.process.argsFree(a, args);
    var cfg: c.ViewerConfig = std.mem.zeroes(c.ViewerConfig);
    cfg.n = 10000;
    cfg.source_epoch = 1;
    cfg.cell_mode = 1;
    cfg.profile = 10;
    cfg.depth = 2;
    cfg.mode = 2;
    cfg.width = 1280;
    cfg.height = 800;
    cfg.steps = 200;
    cfg.budget = 0;
    cfg.interactive = 1;
    var out: [:0]const u8 = "viewer-result.json";
    var capture: ?[:0]const u8 = null;
    var design: u32 = 1;
    var fail_allocation: ?u32 = null;
    var i: usize = 1;
    while (i < args.len) : (i += 1) {
        const arg = args[i];
        if (std.mem.eql(u8, arg, "--debug")) {
            cfg.debug = 1;
            continue;
        }
        if (std.mem.eql(u8, arg, "--interactive")) {
            cfg.steps = 10000;
            cfg.interactive = 2;
            continue;
        }
        if (std.mem.eql(u8, arg, "--quiet")) {
            cfg.interactive = 0;
            continue;
        }
        i += 1;
        if (i >= args.len) return error.Arg;
        if (std.mem.eql(u8, arg, "--out")) {
            out = try a.dupeZ(u8, args[i]);
            continue;
        }
        if (std.mem.eql(u8, arg, "--capture")) {
            capture = try a.dupeZ(u8, args[i]);
            continue;
        }
        if (std.mem.eql(u8, arg, "--budget")) {
            cfg.budget = try std.fmt.parseInt(u64, args[i], 10);
            continue;
        }
        const v = try std.fmt.parseInt(u32, args[i], 10);
        if (std.mem.eql(u8, arg, "--nonblocking")) cfg.nonblocking = v else if (std.mem.eql(u8, arg, "--cell-mode")) cfg.cell_mode = v else if (std.mem.eql(u8, arg, "--fail-frame-allocation")) fail_allocation = v else if (std.mem.eql(u8, arg, "--n")) cfg.n = v else if (std.mem.eql(u8, arg, "--profile")) cfg.profile = v else if (std.mem.eql(u8, arg, "--depth")) cfg.depth = v else if (std.mem.eql(u8, arg, "--mode")) cfg.mode = v else if (std.mem.eql(u8, arg, "--vsync")) cfg.vsync = v else if (std.mem.eql(u8, arg, "--separate")) cfg.separate_queue = v else if (std.mem.eql(u8, arg, "--snapshot")) cfg.snapshot = v else if (std.mem.eql(u8, arg, "--width")) cfg.width = v else if (std.mem.eql(u8, arg, "--height")) cfg.height = v else if (std.mem.eql(u8, arg, "--steps")) cfg.steps = v else if (std.mem.eql(u8, arg, "--warmup")) cfg.warmup = v else if (std.mem.eql(u8, arg, "--stride")) cfg.visual_stride = v else if (std.mem.eql(u8, arg, "--capture-every")) cfg.capture_every = v else if (std.mem.eql(u8, arg, "--self-test")) cfg.self_test = v else if (std.mem.eql(u8, arg, "--execution")) cfg.execution = v else if (std.mem.eql(u8, arg, "--design")) design = v else return error.Arg;
    }
    if (cfg.n == 0 or cfg.n % 16 != 0 or cfg.n > 1000000 or cfg.visual_stride > cfg.n or cfg.profile < 9 or cfg.profile > 11 or cfg.depth < 1 or cfg.depth > 3 or cfg.mode > 2 or cfg.execution > 1 or cfg.width < 64 or cfg.height < 64 or cfg.width > 16384 or cfg.height > 16384 or design > 1) return error.Config;
    if (cfg.separate_queue != 0) cfg.snapshot = 1;
    cfg.output_path = out;
    cfg.capture_prefix = if (capture) |p| p.ptr else null;
    cfg.capacity = try s.l.capacityFor(cfg.n);
    const d = c.s_open_view(@intCast(cfg.debug), @intFromBool(cfg.separate_queue == 0)) orelse return error.Device;
    defer c.s_close(d);
    for (s.passes, 0..) |name, pass| {
        const path = try std.fmt.allocPrint(a, "{s}.dxil", .{name});
        defer a.free(path);
        const bytes = try std.fs.cwd().readFileAlloc(a, path, 16777216);
        defer a.free(bytes);
        try ck(c.s_load(d, @intCast(pass), bytes.ptr, bytes.len));
    }
    var b = s.Bundle.init(@ptrCast(d), cfg.n, cfg.capacity, 1, 1, cfg.budget) catch |err| {
        std.debug.print("GPU storage admission rejected: {s}\n", .{@errorName(err)});
        return err;
    };
    defer b.deinit();
    try b.initialize();
    var model = try s.entity.Store.init(a, cfg.capacity, cfg.n);
    defer model.deinit();
    // Structural mutation is permitted only at a drained owner boundary. The new
    // Physics/viewer owners are created after this G1 transaction has completed.
    if (cfg.self_test == 2) {
        const old = model.handle(0);
        const destroy = try model.destroy(old);
        const created = try model.create();
        try b.commands(&.{ destroy, created.command });
        if (created.handle.generation != old.generation + 1 or created.handle.slot != old.slot) return error.Generation;
        if (model.lookup(old)) |_| {
            return error.Stale;
        } else |_| {}
    }
    cfg.source_epoch = try std.math.add(u32, b.epoch, 1);
    const pc = c.PhysicsConfig{ .n = cfg.n, .capacity = cfg.capacity, .contacts = (cfg.n / 16) * 184, .pairs = (cfg.n / 16) * 120, .design = design, .fixture = cfg.profile, .iterations = 4096, .sleep_frames = 20, .max_bodies = 4096, .max_work = 8388608, .flags = 5, .kick_slot = std.math.maxInt(u32), .dt = 1.0 / 128.0, .budget = cfg.budget };
    const p = c.ph_open(d, &b.handles, &pc) orelse {
        std.debug.print("Physics admission rejected code {d}\n", .{c.ph_error()});
        return error.PhysicsAdmission;
    };
    defer c.ph_close(p);
    try ck(c.ph_execution(p, cfg.execution, 16777216));
    try ck(c.ph_source_epoch_set(p, cfg.source_epoch));
    try ck(c.ph_cell_mode(p, cfg.cell_mode));
    try ck(c.ph_scene(p));
    const initial = try b.read(0);
    var initial_hash: [32]u8 = undefined;
    std.crypto.hash.sha2.Sha256.hash(std.mem.sliceAsBytes(initial), &initial_hash, .{});
    try b.unmap();
    const initial_hex = std.fmt.bytesToHex(initial_hash, .lower);
    var memory_before: c.Memory = undefined;
    try ck(c.s_memory(d, &memory_before));
    if (fail_allocation) |index| c.s_fail_after(d, index);
    const opened = c.viewer_open(d, &b.handles, p, &cfg);
    c.s_fail_after(d, std.math.maxInt(u32));
    if (fail_allocation) |index| {
        if (opened) |unexpected| {
            c.viewer_close(unexpected);
            return error.InjectionNotReached;
        }
        var after: c.Memory = undefined;
        try ck(c.s_memory(d, &after));
        if (after.committed != memory_before.committed or c.s_retired_bytes(d) != 0) return error.FailureCleanup;
        const unchanged = try b.read(0);
        var after_hash: [32]u8 = undefined;
        std.crypto.hash.sha2.Sha256.hash(std.mem.sliceAsBytes(unchanged), &after_hash, .{});
        try b.unmap();
        if (!std.mem.eql(u8, &initial_hash, &after_hash)) return error.FailureState;
        const bytes = try std.json.Stringify.valueAlloc(a, .{ .status = "EXPECTED_REJECTION", .phase = "G4 frame allocation", .injected_index = index, .actual_processed = 0, .actual_published = 0, .managed_before = memory_before.committed, .managed_after = after.committed, .state_unchanged = true, .validation_errors = c.s_errors(d) }, .{ .whitespace = .indent_2 });
        defer a.free(bytes);
        try std.fs.cwd().writeFile(.{ .sub_path = out, .data = bytes });
        return;
    }
    const v = opened orelse return error.ViewerInitialization;
    var viewer_closed = false;
    defer if (!viewer_closed) c.viewer_close(v);
    try ck(c.viewer_run(v));
    const actual_ticks = c.ph_next_tick(p);
    if (cfg.mode != 1 and actual_ticks > 0) {
        var verification: c.PhysicsVerification = std.mem.zeroes(c.PhysicsVerification);
        try ck(c.ph_verify(p, &pc, actual_ticks, model.dense_slot.ptr, model.generation.ptr, model.to_dense.ptr, &verification));
        const bytes = try std.json.Stringify.valueAlloc(a, verification, .{ .whitespace = .indent_2 });
        defer a.free(bytes);
        const path = try std.fmt.allocPrint(a, "{s}.verification.json", .{out});
        defer a.free(path);
        try std.fs.cwd().writeFile(.{ .sub_path = path, .data = bytes });
    }
    var initial_checked: u64 = 0;
    if (cfg.mode == 1 or actual_ticks == 0) try ck(c.ph_verify_initial(p, &pc, model.dense_slot.ptr, &initial_checked));
    const maps = try b.read(1);
    for (0..cfg.capacity) |slot| {
        if (maps[2 * slot] != model.to_dense[slot] or maps[2 * slot + 1] != model.generation[slot] or maps[2 * cfg.capacity + slot] != model.dense_slot[slot]) return error.MapIdentity;
    }
    try b.unmap();
    const state = try b.read(0);
    var hash: [32]u8 = undefined;
    std.crypto.hash.sha2.Sha256.hash(std.mem.sliceAsBytes(state), &hash, .{});
    try b.unmap();
    const hex = std.fmt.bytesToHex(hash, .lower);
    c.viewer_close(v);
    viewer_closed = true;
    var memory_after: c.Memory = undefined;
    try ck(c.s_memory(d, &memory_after));
    if (memory_after.committed != memory_before.committed) return error.ViewerMemoryLeak;
    const ledger = try std.fmt.allocPrintSentinel(a, "{s}.ledger.json", .{out}, 0);
    defer a.free(ledger);
    try ck(c.ph_ledger(p, ledger));
    // A native frame completion is not a physical-oracle PASS. Publish final PASS
    // only after independent physics/initial-state, all mappings and cleanup pass.
    const raw = try std.fs.cwd().readFileAlloc(a, out, 128 * 1024 * 1024);
    defer a.free(raw);
    var parsed = try std.json.parseFromSlice(std.json.Value, a, raw, .{ .allocate = .alloc_always });
    defer parsed.deinit();
    var object = &parsed.value.object;
    try object.put("status", .{ .string = "PASS" });
    try object.put("adapter", .{ .string = std.mem.span(c.s_name(d)) });
    try object.put("driver_version", .{ .integer = @intCast(c.s_driver(d)) });
    try object.put("debug_layer_and_gbv", .{ .bool = cfg.debug != 0 });
    try object.put("actual_physical_entities", .{ .integer = if (cfg.mode != 1 and actual_ticks > 0) cfg.n else 0 });
    try object.put("actual_simulation_ticks", .{ .integer = if (cfg.mode == 1) 0 else actual_ticks });
    try object.put("cell_mode", .{ .integer = cfg.cell_mode });
    try object.put("independent_full_coverage", .{ .bool = true });
    try object.put("initial_objects_verified", .{ .integer = @intCast(initial_checked) });
    try object.put("state_sha256", .{ .string = &hex });
    try object.put("initial_state_sha256", .{ .string = &initial_hex });
    try object.put("identity_slots_verified", .{ .integer = cfg.capacity });
    try object.put("structural_reuse_test", .{ .bool = cfg.self_test == 2 });
    try object.put("cleanup_complete", .{ .bool = true });
    try object.put("cleanup_memory_reconciled", .{ .bool = true });
    try object.put("managed_before_viewer", .{ .integer = @intCast(memory_before.committed) });
    try object.put("managed_after_viewer", .{ .integer = @intCast(memory_after.committed) });
    const result = try std.json.Stringify.valueAlloc(a, parsed.value, .{ .whitespace = .indent_2 });
    defer a.free(result);
    try std.fs.cwd().writeFile(.{ .sub_path = out, .data = result });
    std.debug.print("G4 viewer PASS N={d} mode={d} depth={d}\n", .{ cfg.n, cfg.mode, cfg.depth });
}
