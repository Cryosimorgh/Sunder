//! Production storage executable. Standalone tests are maintained on the test branch.
const std = @import("std");

pub fn build(builder: *std.Build) void {
    const target = builder.standardTargetOptions(.{
        .default_target = .{
            .cpu_arch = .x86_64,
            .os_tag = .windows,
            .abi = .gnu,
        },
    });
    const optimize = builder.standardOptimizeOption(.{});
    const runtime_module = builder.createModule(.{
        .root_source_file = builder.path("main.zig"),
        .target = target,
        .optimize = optimize,
        .link_libc = true,
    });
    runtime_module.addIncludePath(builder.path("."));

    const sdk_include = builder.option(
        []const u8,
        "sdk-include",
        "Windows SDK Include/version directory (compile.py detects this)",
    ) orelse ".";

    for ([_][]const u8{ "um", "shared", "ucrt" }) |directory| {
        runtime_module.addSystemIncludePath(.{
            .cwd_relative = builder.fmt("{s}/{s}", .{ sdk_include, directory }),
        });
    }
    for ([_][]const u8{ "d3d12", "dxgi", "dxguid", "kernel32" }) |library| {
        runtime_module.linkSystemLibrary(library, .{});
    }
    runtime_module.addCSourceFile(.{
        .file = builder.path("runtime.c"),
        .flags = &.{ "-O2" },
    });
    builder.installArtifact(builder.addExecutable(.{
        .name = "storage",
        .root_module = runtime_module,
    }));
}
