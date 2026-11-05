const std = @import("std");
const s = @import("storage.zig");
const c = @cImport({
    @cInclude("viewer.h");
});
const a = std.heap.c_allocator;
fn ck(x: c_int) !void {
    if (x == 0) return error.G4Lifecycle;
}
pub fn main() !void {
    const args = try std.process.argsAlloc(a);
    defer std.process.argsFree(a, args);
    if (args.len != 2) return error.OutputDirectory;
    const d = c.s_open_view(1, 0) orelse return error.Device;
    defer c.s_close(d);
    for (s.passes, 0..) |name, pass| {
        const path = try std.fmt.allocPrint(a, "{s}.dxil", .{name});
        defer a.free(path);
        const bytes = try std.fs.cwd().readFileAlloc(a, path, 16777216);
        defer a.free(bytes);
        try ck(c.s_load(d, @intCast(pass), bytes.ptr, bytes.len));
    }
    var b = try s.Bundle.init(@ptrCast(d), 32, 32, 1, 1, 0);
    defer b.deinit();
    try b.initialize();
    var model = try s.entity.Store.init(a, 32, 32);
    defer model.deinit();
    const pc = c.PhysicsConfig{ .n = 32, .capacity = 32, .contacts = 368, .pairs = 240, .design = 1, .fixture = 9, .iterations = 4096, .sleep_frames = 20, .max_bodies = 4096, .max_work = 8388608, .flags = 5, .kick_slot = std.math.maxInt(u32), .dt = 1.0 / 128.0, .budget = 0 };
    const p = c.ph_open(d, &b.handles, &pc) orelse return error.Physics;
    defer c.ph_close(p);
    try ck(c.ph_cell_mode(p, 1));
    try ck(c.ph_scene(p));
    var before: [16 * 32]u32 = undefined;
    for (0..2) |phase| {
        if (phase == 1) {
            const old = model.handle(0);
            const destroy = try model.destroy(old);
            const created = try model.create();
            try b.commands(&.{ destroy, created.command });
            if (created.handle.generation != 2 or created.handle.slot != 0) return error.Generation;
            if (model.lookup(old)) |_| {
                return error.Stale;
            } else |_| {}
            try ck(c.ph_scene_one(p, try model.lookup(created.handle)));
            try ck(c.ph_source_epoch_set(p, 2));
            const after = try b.read(0);
            for (1..32) |stable| {
                const dense = model.to_dense[stable];
                for (0..16) |field| {
                    if (after[field * 32 + dense] != before[field * 32 + stable]) return error.SurvivorChanged;
                }
            }
            try b.unmap();
        }
        var cfg: c.ViewerConfig = std.mem.zeroes(c.ViewerConfig);
        cfg.n = 32;
        cfg.capacity = 32;
        cfg.profile = 9;
        cfg.depth = 3;
        cfg.mode = 2;
        cfg.separate_queue = 1;
        cfg.snapshot = 1;
        cfg.width = 768;
        cfg.height = 768;
        cfg.steps = 20;
        cfg.debug = 1;
        cfg.cell_mode = 1;
        cfg.source_epoch = @intCast(phase + 1);
        cfg.tick_base = @intCast(phase * 20);
        const path = try std.fmt.allocPrintSentinel(a, "{s}/phase{d}.json", .{ args[1], phase }, 0);
        defer a.free(path);
        cfg.output_path = path;
        const v = c.viewer_open(d, &b.handles, p, &cfg) orelse return error.Viewer;
        var closed = false;
        defer if (!closed) c.viewer_close(v);
        try ck(c.viewer_run(v));
        c.viewer_close(v);
        closed = true;
        var verified: c.PhysicsVerification = std.mem.zeroes(c.PhysicsVerification);
        try ck(c.ph_verify(p, &pc, @intCast((phase + 1) * 20), model.dense_slot.ptr, model.generation.ptr, model.to_dense.ptr, &verified));
        if (verified.objects != 32) return error.Coverage;
        if (phase == 0) {
            const data = try b.read(0);
            @memcpy(&before, data[0 .. 16 * 32]);
            try b.unmap();
        }
    }
    const value = .{ .status = "PASS", .objects = 32, .evolving_ticks = 40, .survivor_fields_exact = 31 * 16, .recycled_slot = 0, .old_generation = 1, .new_generation = 2, .old_source_epoch = 1, .new_source_epoch = 2, .full_population_reinitialization = false, .validation_errors = c.s_errors(d) };
    const bytes = try std.json.Stringify.valueAlloc(a, value, .{ .whitespace = .indent_2 });
    defer a.free(bytes);
    const path = try std.fmt.allocPrint(a, "{s}/result.json", .{args[1]});
    defer a.free(path);
    try std.fs.cwd().writeFile(.{ .sub_path = path, .data = bytes });
}
