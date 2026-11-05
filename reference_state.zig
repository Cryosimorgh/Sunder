//! Deterministic CPU reference values for storage verification and bench CLIs.
//! This module has no GPU calls or resource ownership.
const l = @import("layout.zig");

pub fn seed(id: u32, field: u32, stride: u32) u32 {
    const value: f32 = switch (field) {
        0 => @as(f32, @floatFromInt(id & 1023)) / 1024,
        1 => @as(f32, @floatFromInt((id >> 10) & 1023)) / 1024,
        2 => @as(f32, @floatFromInt(@as(i32, @intCast(id % 7)) - 3)) / 1024,
        3 => @as(f32, @floatFromInt(@as(i32, @intCast(id % 5)) - 2)) / 1024,
        6 => 1,
        7 => 2,
        8 => 1.0 / 256.0,
        else => 0,
    };
    return switch (field) {
        12 => id % 3,
        14 => @intFromBool(activeId(id, stride)),
        15 => id,
        else => @bitCast(value),
    };
}
pub fn activeId(id: u32, stride: u32) bool {
    return stride != 0 and id % stride == 0;
}
pub fn expected(id: u32, steps: u32, stride: u32) [l.field_count]u32 {
    var words: [l.field_count]u32 = undefined;
    for (0..l.field_count) |f| words[f] = seed(id, @intCast(f), stride);
    const k: f64 = @floatFromInt(steps);
    const active_: f64 = if (activeId(id, stride)) 1 else 0;
    const coeff = ((2 + active_) * k * (k - 1) / 2 + (1 + active_) * k) / 65536;
    const vx: f32 = @bitCast(words[2]);
    const vy: f32 = @bitCast(words[3]);
    const x: f32 = @bitCast(words[0]);
    const y: f32 = @bitCast(words[1]);
    words[0] = @bitCast(@as(f32, @floatCast(@as(f64, x) + (2 + active_) * k * @as(f64, vx) / 64 + coeff)));
    words[1] = @bitCast(@as(f32, @floatCast(@as(f64, y) + (2 + active_) * k * @as(f64, vy) / 64 - coeff)));
    words[2] = @bitCast(@as(f32, @floatCast(@as(f64, vx) + k / 1024)));
    words[3] = @bitCast(@as(f32, @floatCast(@as(f64, vy) - k / 1024)));
    return words;
}
