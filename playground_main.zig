const std = @import("std");
const s = @import("storage.zig");
const c = @cImport({
    @cInclude("viewer.h");
    @cInclude("bench_support.h");
});
const a = std.heap.c_allocator;
fn ck(v: c_int) !void {
    if (v == 0) return error.GPU;
}
const Session = struct {
    d: *c.StorageDevice,
    b: s.Bundle,
    p: *c.Physics,
    v: *c.Viewer,
    cfg: c.ViewerConfig,
    fn open(input: c.ViewerConfig) !*Session {
        var cfg = input;
        cfg.capacity = try s.l.capacityFor(cfg.n);
        const d = c.s_open_view(@intCast(cfg.debug), 1) orelse return error.Device;
        errdefer c.s_close(d);
        const dp = try std.fs.selfExeDirPathAlloc(a);
        defer a.free(dp);
        var dir = try std.fs.openDirAbsolute(dp, .{});
        defer dir.close();
        for (s.passes, 0..) |name, i| {
            const path = try std.fmt.allocPrint(a, "{s}.dxil", .{name});
            defer a.free(path);
            const bytes = try dir.readFileAlloc(a, path, 16777216);
            defer a.free(bytes);
            try ck(c.s_load(d, @intCast(i), bytes.ptr, bytes.len));
        }
        var b = try s.Bundle.init(@ptrCast(d), cfg.n, cfg.capacity, 1, 1, cfg.budget);
        errdefer b.deinit();
        try b.initialize();
        const pc = c.PhysicsConfig{ .n = cfg.n, .capacity = cfg.capacity, .contacts = if (cfg.profile == 13) 256 else if (cfg.profile == 12) cfg.n * 12 else (cfg.n / 16) * 184, .pairs = if (cfg.profile >= 12) cfg.n * 16 else (cfg.n / 16) * 120, .design = 1, .fixture = cfg.profile, .iterations = 4096, .sleep_frames = 20, .max_bodies = 4096, .max_work = 8388608, .flags = if (cfg.profile == 13) 7 else 5, .kick_slot = std.math.maxInt(u32), .dt = 1.0 / 128.0, .budget = cfg.budget };
        const p = c.ph_open(d, &b.handles, &pc) orelse return error.PhysicsAdmission;
        errdefer c.ph_close(p);
        try ck(c.ph_execution(p, cfg.execution, 16777216));
        try ck(c.ph_source_epoch_set(p, cfg.source_epoch));
        try ck(c.ph_cell_mode(p, cfg.cell_mode));
        try ck(c.ph_scene(p));
        const state = try b.read(0);
        var hash: [32]u8 = undefined;
        std.crypto.hash.sha2.Sha256.hash(std.mem.sliceAsBytes(state), &hash, .{});
        try b.unmap();
        const hex = std.fmt.bytesToHex(hash, .lower);
        const scene = try std.json.Stringify.valueAlloc(a, .{ .n = cfg.n, .profile = cfg.profile, .capacity = cfg.capacity, .epoch = cfg.source_epoch, .seed = 18228, .dt = 1.0 / 128.0, .radius = @as(f64, if (cfg.profile == 13) 0.028575 else 1.0 / 16.0), .initial_state_sha256 = &hex, .hash_scope = "full allocated SoA state including padding; drained initialization only" }, .{ .whitespace = .indent_2 });
        defer a.free(scene);
        const path = try std.fmt.allocPrint(a, "{s}/scene-{d}.json", .{ std.mem.span(c.bench_log_directory()), cfg.source_epoch });
        defer a.free(path);
        try std.fs.cwd().writeFile(.{ .sub_path = path, .data = scene });
        const v = c.viewer_open(d, &b.handles, p, &cfg) orelse return error.ViewerAdmission;
        errdefer c.viewer_close(v);
        const self = try a.create(Session);
        self.* = .{ .d = d, .b = b, .p = p, .v = v, .cfg = cfg };
        return self;
    }
    fn close(self: *Session) void {
        c.viewer_close(self.v);
        c.ph_close(self.p);
        self.b.deinit();
        var m: c.Memory = undefined;
        if (c.s_memory(self.d, &m) == 0 or m.committed != m.context_committed or c.s_retired_bytes(self.d) != 0 or c.s_errors(self.d) != 0) std.process.exit(4);
        c.s_close(self.d);
        a.destroy(self);
    }
};
pub fn main() !void {
    const args = try std.process.argsAlloc(a);
    defer std.process.argsFree(a, args);
    var cfg = std.mem.zeroes(c.ViewerConfig);
    cfg.n = 16;
    cfg.profile = 13;
    cfg.ui_mode = 1;
    cfg.depth = 2;
    cfg.mode = 2;
    cfg.width = 1280;
    cfg.height = 800;
    cfg.interactive = 3;
    cfg.cell_mode = 1;
    cfg.source_epoch = 1;
    var output: ?[:0]u8 = null;
    var quiet = false;
    var automated = false;
    var i: usize = 1;
    while (i < args.len) : (i += 1) {
        const arg = args[i];
        if (std.mem.eql(u8, arg, "--debug")) {
            cfg.debug = 1;
            continue;
        }
        if (std.mem.eql(u8, arg, "--quiet")) {
            quiet = true;
            continue;
        }
        if (std.mem.eql(u8, arg, "--automated")) {
            automated = true;
            continue;
        }
        i += 1;
        if (i >= args.len) return error.Argument;
        if (std.mem.eql(u8, arg, "--output-dir")) {
            output = try a.dupeZ(u8, args[i]);
            continue;
        }
        const value = try std.fmt.parseInt(u32, args[i], 10);
        if (std.mem.eql(u8, arg, "--nonblocking")) cfg.nonblocking = value else if (std.mem.eql(u8, arg, "--n")) cfg.n = value else if (std.mem.eql(u8, arg, "--profile")) cfg.profile = value else if (std.mem.eql(u8, arg, "--depth")) cfg.depth = value else if (std.mem.eql(u8, arg, "--vsync")) cfg.vsync = value else if (std.mem.eql(u8, arg, "--steps")) cfg.steps = value else if (std.mem.eql(u8, arg, "--self-test")) cfg.self_test = value else if (std.mem.eql(u8, arg, "--width")) cfg.width = value else if (std.mem.eql(u8, arg, "--height")) cfg.height = value else return error.Argument;
    }
    defer if (output) |o| a.free(o);
    if ((cfg.n != 16 and cfg.n != 100 and cfg.n != 1000 and cfg.n != 10000 and cfg.n != 100000 and cfg.n != 1000000) or cfg.profile < 9 or cfg.profile > 13 or (cfg.profile == 13 and cfg.n != 16) or (cfg.profile != 12 and cfg.n % 16 != 0) or cfg.depth < 1 or cfg.depth > 3 or cfg.vsync > 1 or cfg.width < 640 or cfg.height < 400 or cfg.width > 16384 or cfg.height > 16384) return error.Config;
    if (c.bench_log_start(if (output) |o| o.ptr else null, @intFromBool(automated)) == 0) return error.OutputDirectory;
    defer c.bench_log_close();
    var current = Session.open(cfg) catch |err| {
        std.debug.print("Startup rejected: {s}\n", .{@errorName(err)});
        if (!quiet) c.bench_message("Cannot admit scene or initialize D3D12. Check GPU support, memory and DXIL files alongside the EXE.");
        return err;
    };
    defer current.close();
    var memory: c.Memory = undefined;
    try ck(c.s_memory(current.d, &memory));
    const hw = try std.json.Stringify.valueAlloc(a, .{ .adapter = std.mem.span(c.s_name(current.d)), .driver_version = c.s_driver(current.d), .n = cfg.n, .profile = cfg.profile, .depth = cfg.depth, .dt = 1.0 / 128.0, .automated = automated, .memory = memory, .cpu_target = "x86_64 baseline", .displayed_fps_status = "UNVERIFIED", .scene = "Playable Billiards (16 stationary balls), or explicitly synthetic scientific stress fixtures", .telemetry_queue_capacity = 2048, .rolling_sample_capacity = 4096 }, .{ .whitespace = .indent_2 });
    defer a.free(hw);
    const hp = try std.fmt.allocPrint(a, "{s}/hardware.json", .{std.mem.span(c.bench_log_directory())});
    defer a.free(hp);
    try std.fs.cwd().writeFile(.{ .sub_path = hp, .data = hw });
    std.debug.print("GPU Physics Playground: results {s}\n", .{std.mem.span(c.bench_log_directory())});
    var sessions: u32 = 1;
    var ticks: u64 = 0;
    while (true) {
        const result = c.viewer_run(current.v);
        if (result == 0) return error.Viewer;
        if (result == 1) break;
        var requested: c.ViewerConfig = undefined;
        try ck(c.viewer_request(current.v, &requested));
        if (requested.source_epoch == 0) return error.EpochOverflow;
        var before_hash: [32]u8 = undefined;
        var before_memory: c.Memory = undefined;
        const verify_rejection = current.cfg.self_test == 20 and requested.budget == 1;
        if (verify_rejection) {
            const words = try current.b.read(0);
            std.crypto.hash.sha2.Sha256.hash(std.mem.sliceAsBytes(words), &before_hash, .{});
            try current.b.unmap();
            try ck(c.s_memory(current.d, &before_memory));
        }
        const next = Session.open(requested) catch |err| {
            std.debug.print("Scene change rejected; active scene retained: {s}\n", .{@errorName(err)});
            if (verify_rejection) {
                const words = try current.b.read(0);
                var after_hash: [32]u8 = undefined;
                std.crypto.hash.sha2.Sha256.hash(std.mem.sliceAsBytes(words), &after_hash, .{});
                try current.b.unmap();
                var after_memory: c.Memory = undefined;
                try ck(c.s_memory(current.d, &after_memory));
                if (!std.mem.eql(u8, &before_hash, &after_hash) or before_memory.committed != after_memory.committed) return error.RejectionCorruptedState;
                c.bench_log_event("REJECTION_STATE_HASH_VERIFIED", current.cfg.n, current.cfg.profile);
            }
            c.viewer_rejected(current.v);
            if (!quiet) c.bench_message("Scene allocation rejected. Current scene preserved. Free GPU memory or choose a smaller population.");
            continue;
        };
        ticks += c.viewer_live_ticks(current.v);
        c.viewer_hide(current.v);
        current.close();
        current = next;
        sessions += 1;
        c.bench_log_event("SCENE_REPLACED", requested.n, requested.profile);
    }
    if (current.cfg.self_test == 30) {
        const state = try current.b.read(0);
        const file = try std.fmt.allocPrint(a, "{s}/final-state.bin", .{std.mem.span(c.bench_log_directory())});
        defer a.free(file);
        try std.fs.cwd().writeFile(.{ .sub_path = file, .data = std.mem.sliceAsBytes(state) });
        try current.b.unmap();
    }
    ticks += c.viewer_live_ticks(current.v);
    c.bench_log_event("CLEAN_EXIT", current.cfg.n, current.cfg.profile);
    std.debug.print("PASS sessions={d} simulation_ticks={d} validation_errors={d} telemetry_dropped={d}\n", .{ sessions, ticks, c.s_errors(current.d), c.bench_log_dropped() });
}
