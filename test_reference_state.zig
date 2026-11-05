//! Regression contracts for the production reference-state oracle.
//! Stored exclusively on the test branch; CI stages it into the production tree.
const std = @import("std");
const reference = @import("reference_state.zig");

test "seeded zero-step state is unchanged" {
    for ([_]u32{ 0, 1, 17, 1023, 65535 }) |id| {
        for ([_]u32{ 1, 7, 128 }) |stride| {
            const state = reference.expected(id, 0, stride);
            for (state, 0..) |value, field| {
                try std.testing.expectEqual(reference.seed(id, @intCast(field), stride), value);
            }
        }
    }
}

test "active IDs use the exact stride and never divide by zero" {
    try std.testing.expect(!reference.activeId(0, 0));
    try std.testing.expect(reference.activeId(0, 7));
    try std.testing.expect(reference.activeId(14, 7));
    try std.testing.expect(!reference.activeId(15, 7));
}

test "single active step follows the deterministic reference recurrence" {
    const state = reference.expected(0, 1, 1);
    try std.testing.expectEqual(@as(u32, @bitCast(@as(f32, -7.0 / 65536.0))), state[0]);
    try std.testing.expectEqual(@as(u32, @bitCast(@as(f32, -8.0 / 65536.0))), state[1]);
    try std.testing.expectEqual(@as(u32, @bitCast(@as(f32, -2.0 / 1024.0))), state[2]);
    try std.testing.expectEqual(@as(u32, @bitCast(@as(f32, -3.0 / 1024.0))), state[3]);
}
