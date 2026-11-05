const std = @import("std");
const s = @import("storage.zig");
const c = @cImport({
    @cInclude("viewer.h");
});
pub fn main() !void {
    const a = std.heap.c_allocator;
    const args = try std.process.argsAlloc(a);
    defer std.process.argsFree(a, args);
    var device_case: ?u32 = null;
    var nonblocking: u32 = 0;
    var profile: u32 = 9;
    var samples: u32 = 16;
    var out: [:0]const u8 = "consumer.json";
    var i: usize = 1;
    while (i < args.len) : (i += 1) {
        const flag = args[i];
        i += 1;
        if (i == args.len) return error.Argument;
        if (std.mem.eql(u8, flag, "--device-case")) device_case = try std.fmt.parseInt(u32, args[i], 10) else if (std.mem.eql(u8, flag, "--nonblocking")) nonblocking = try std.fmt.parseInt(u32, args[i], 10) else if (std.mem.eql(u8, flag, "--out")) out = args[i] else if (std.mem.eql(u8, flag, "--profile")) profile = try std.fmt.parseInt(u32, args[i], 10) else if (std.mem.eql(u8, flag, "--samples")) samples = try std.fmt.parseInt(u32, args[i], 10) else return error.Argument;
    }
    if (device_case) |case_id| {
        try deviceTest(case_id, out);
        return;
    }
    if ((profile != 9 and profile != 13) or samples > 32 or nonblocking > 1) return error.Config;
    const d = try s.open(samples == 0);
    defer s.c.s_close(d);
    var b = try s.Bundle.init(d, 16, try s.l.capacityFor(16), 1, 1, 0);
    defer b.deinit();
    try b.initialize();
    if (c.viewer_consumer_mode_test(@ptrCast(d), &b.handles, profile, samples, nonblocking, out.ptr) == 0) return error.Consumer;
}
fn deviceTest(case_id: u32, out: [:0]const u8) !void {
    if (case_id > 7) return error.Config;
    const a = std.heap.c_allocator;
    const d = try s.open(true);
    var old: ?*s.c.StorageDevice = d;
    var b = try s.Bundle.init(d, 16, try s.l.capacityFor(16), 1, 1, 0);
    try b.initialize();
    const old_id = s.c.s_identity(d);
    const old_buffer = b.handles[0];
    const detail = try std.fmt.allocPrintSentinel(a, "{s}.device.json", .{out}, 0);
    defer a.free(detail);
    if (c.viewer_device_test(@ptrCast(d), &b.handles, case_id, detail.ptr) == 0) return error.DeviceLifecycle;
    b.deinit();
    var final: s.c.DeviceStatus = undefined;
    try s.ck(s.c.s_device_info(d, &final));
    if (final.owners != 0 or final.claims != 0 or final.live_buffers != 0) return error.LeakedOwnership;
    try s.ck(s.c.s_try_close(&old, 1000));
    try s.ck(s.c.s_try_close(&old, 0));
    if (old != null) return error.Close;
    // Recreation is explicit and starts a NEW scene; no failed snapshot is reused.
    const fresh = try s.open(true);
    var next: ?*s.c.StorageDevice = fresh;
    var fresh_b = try s.Bundle.init(fresh, 16, try s.l.capacityFor(16), 1, 1, 0);
    try fresh_b.initialize();
    const new_id = s.c.s_identity(fresh);
    if (new_id == old_id) return error.StaleIdentity;
    if (s.c.s_resource_available(fresh, old_buffer, 1) != 0 or s.c.s_resource_available(fresh, fresh_b.handles[0], 1) == 0) return error.StaleBuffer;
    if (c.viewer_device_recreated(@ptrCast(fresh), &fresh_b.handles) == 0) return error.RecreatedGPU;
    if (s.c.s_errors(fresh) != 0) return error.Validation;
    fresh_b.deinit();
    try s.ck(s.c.s_try_close(&next, 1000));
    try s.ck(s.c.s_try_close(&next, 0));
    const raw = try std.fs.cwd().readFileAlloc(a, detail, 1024 * 1024);
    defer a.free(raw);
    const parsed = try std.json.parseFromSlice(std.json.Value, a, raw, .{});
    defer parsed.deinit();
    const evidence = try std.json.Stringify.valueAlloc(a, .{ .status = "PASS", .case = case_id, .device = parsed.value, .old_identity = old_id, .new_identity = new_id, .old_buffer_rejected = true, .explicit_recreation = true, .fresh_gpu_render_modes = 2, .device_close_repeated = true, .physical_hardware_removal_tested = false, .recovery_scope = "new device/context and fresh scene; no checkpoint continuation" }, .{ .whitespace = .indent_2 });
    defer a.free(evidence);
    try std.fs.cwd().writeFile(.{ .sub_path = out, .data = evidence });
}
