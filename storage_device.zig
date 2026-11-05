//! Owns D3D12 device initialization and loading of storage compute passes.
//! Buffer lifetime and simulation state are managed by storage.zig.
const std = @import("std");
pub const c = @cImport({
    @cInclude("runtime.h");
});
const a = std.heap.c_allocator;

pub const passes = [_][]const u8{ "initialize", "classify", "scan_counts", "add_prefix", "scatter_safe", "integrate", "keys", "update_motion", "gather", "full_state", "pack_render", "consume_render", "convert", "mutate", "grow_maps", "full_state_vector", "empty_active", "clear_coverage" };
pub fn ck(v: c_int) !void {
    if (v == 0) return error.GPU;
}
pub fn open(debug: bool) !*c.StorageDevice {
    const d = c.s_open(@intFromBool(debug)) orelse return error.Device;
    errdefer c.s_close(d);
    for (passes, 0..) |name, i| {
        const path = try std.fmt.allocPrint(a, "{s}.dxil", .{name});
        defer a.free(path);
        const bytes = try std.fs.cwd().readFileAlloc(a, path, 16 * 1024 * 1024);
        defer a.free(bytes);
        try ck(c.s_load(d, @intCast(i), bytes.ptr, bytes.len));
    }
    return d;
}
