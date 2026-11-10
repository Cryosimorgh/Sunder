const std = @import("std");
const s = @import("storage.zig");
const c = @cImport({
    @cInclude("physics.h");
    @cInclude("execution-layout.h");
});
const a = std.heap.c_allocator;
fn ck(v: c_int) !void {
    if (v == 0) return error.Physics;
}
fn save(path: []const u8, value: anytype) !void {
    const data = try std.json.Stringify.valueAlloc(a, value, .{ .whitespace = .indent_2 });
    defer a.free(data);
    try std.fs.cwd().writeFile(.{ .sub_path = path, .data = data });
}
fn dump(p: *c.Physics, which: c_int, path: []const u8, n: u32, cap: u32, canonical: bool) !void {
    var data: ?*const anyopaque = null;
    var bytes: u64 = 0;
    try ck(c.ph_read(p, which, &data, &bytes));
    defer _ = c.ph_unmap(p);
    if (canonical) {
        const words = @as([*]const u32, @ptrCast(@alignCast(data.?)))[0 .. bytes / 4];
        const dst = try a.alloc(u32, @as(usize, n) * 16);
        defer a.free(dst);
        for (0..n) |i| for (0..16) |f| {
            dst[16 * i + f] = words[f * cap + i];
        };
        try std.fs.cwd().writeFile(.{ .sub_path = path, .data = std.mem.sliceAsBytes(dst) });
    } else try std.fs.cwd().writeFile(.{ .sub_path = path, .data = @as([*]const u8, @ptrCast(data.?))[0..bytes] });
}
pub fn main() !void {
    const args = try std.process.argsAlloc(a);
    defer std.process.argsFree(a, args);
    var seconds: u32 = 0;
    var cell_mode: u32 = 0;
    var execution: u32 = 0;
    var work_budget: u32 = 16777216;
    var n: u32 = 100000;
    var fixture: u32 = 1;
    var contactcap: u32 = 100000;
    var paircap: u32 = 100000;
    var design: u32 = 1;
    var steps: u32 = 1;
    var warm: u32 = 0;
    var iterations: u32 = 4096;
    var flags: u32 = 1;
    var maxbodies: u32 = 4096;
    var maxwork: u32 = 8388608;
    var kick: u32 = std.math.maxInt(u32);
    var dt: f32 = 1.0 / 128.0;
    var budget: u64 = 0;
    var delete_one = false;
    var injection_at: u32 = 0;
    var ownership_tests = false;
    var publication_tests = false;
    var device_tests = false;
    var recycle = false;
    var injection: u32 = 0;
    var debug = false;
    var trace = false;
    var trace_last = false;
    var verify_each_tick = false;
    var out: []const u8 = "physics-result.json";
    var input: ?[]const u8 = null;
    var i: usize = 1;
    while (i < args.len) : (i += 1) {
        const arg = args[i];
        if (std.mem.eql(u8, arg, "--delete-one")) {
            delete_one = true;
            continue;
        }
        if (std.mem.eql(u8, arg, "--ownership-tests")) {
            ownership_tests = true;
            continue;
        }
        if (std.mem.eql(u8, arg, "--publication-tests")) {
            publication_tests = true;
            continue;
        }
        if (std.mem.eql(u8, arg, "--device-tests")) {
            device_tests = true;
            continue;
        }
        if (std.mem.eql(u8, arg, "--recycle")) {
            recycle = true;
            continue;
        }
        if (std.mem.eql(u8, arg, "--debug")) {
            debug = true;
            continue;
        }
        if (std.mem.eql(u8, arg, "--verify-every-tick")) {
            verify_each_tick = true;
            continue;
        }
        if (std.mem.eql(u8, arg, "--trace-last")) {
            trace_last = true;
            continue;
        }
        if (std.mem.eql(u8, arg, "--trace")) {
            trace = true;
            continue;
        }
        i += 1;
        if (i >= args.len) return error.Arg;
        if (std.mem.eql(u8, arg, "--out")) {
            out = args[i];
            continue;
        }
        if (std.mem.eql(u8, arg, "--input")) {
            input = args[i];
            continue;
        }
        if (std.mem.eql(u8, arg, "--budget")) {
            budget = try std.fmt.parseInt(u64, args[i], 10);
            continue;
        }
        if (std.mem.eql(u8, arg, "--dt")) {
            dt = try std.fmt.parseFloat(f32, args[i]);
            continue;
        }
        const v = try std.fmt.parseInt(u32, args[i], 10);
        if (std.mem.eql(u8, arg, "--seconds")) seconds = v else if (std.mem.eql(u8, arg, "--cell-mode")) cell_mode = v else if (std.mem.eql(u8, arg, "--execution")) execution = v else if (std.mem.eql(u8, arg, "--execution-budget")) work_budget = v else if (std.mem.eql(u8, arg, "--inject-at")) injection_at = v else if (std.mem.eql(u8, arg, "--inject")) injection = v else if (std.mem.eql(u8, arg, "--n")) n = v else if (std.mem.eql(u8, arg, "--fixture")) fixture = v else if (std.mem.eql(u8, arg, "--contacts")) contactcap = v else if (std.mem.eql(u8, arg, "--pairs")) paircap = v else if (std.mem.eql(u8, arg, "--design")) design = v else if (std.mem.eql(u8, arg, "--steps")) steps = v else if (std.mem.eql(u8, arg, "--warmup")) warm = v else if (std.mem.eql(u8, arg, "--iterations")) iterations = v else if (std.mem.eql(u8, arg, "--flags")) flags = v else if (std.mem.eql(u8, arg, "--max-bodies")) maxbodies = v else if (std.mem.eql(u8, arg, "--max-work")) maxwork = v else if (std.mem.eql(u8, arg, "--kick")) kick = v else return error.Arg;
    }
    if (steps == 0 or steps > 1000000 or warm > 1000000 or warm > std.math.maxInt(u32) - steps or (trace and n > 4096)) return error.Config;
    if (injection > 3 or (injection != 0 and injection_at >= warm + steps)) return error.Config;
    if ((recycle or delete_one) and (n != 32 or steps < 3)) return error.Config;
    if (recycle and delete_one) return error.Config;
    const d = try s.open(debug);
    defer s.c.s_close(d);
    const cap = try s.l.capacityFor(n);
    var b = s.Bundle.init(d, n, cap, 1, 1, budget) catch |err| {
        try save(out, .{ .status = "ADMISSION_REJECTED", .phase = "G1-storage", .reason = @errorName(err), .actual_processed = 0 });
        return;
    };
    var owns_bundle = true;
    defer if (owns_bundle) b.deinit();
    try b.initialize();
    var model = try s.entity.Store.init(a, cap, n);
    defer model.deinit();
    if (ownership_tests) {
        if (n != 32) return error.Config;
        try ck(c.ph_ownership_tests(@ptrCast(d), &b.handles));
        try save(out, .{ .status = "PASS", .ownership_tests = true, .validation_errors = s.c.s_errors(d) });
        return;
    }
    if (publication_tests) {
        if (n != 32) return error.Config;
        try ck(c.ph_publication_tests(@ptrCast(d), &b.handles));
        try save(out, .{ .status = "PASS", .publication_tests = true, .validation_errors = s.c.s_errors(d), .device_loss = "UNVERIFIED: no device removal injected" });
        return;
    }
    if (device_tests) {
        if (n != 32) return error.Config;
        try ck(c.ph_device_tests(@ptrCast(d), &b.handles));
        try save(out, .{ .status = "PASS", .device_tests = true, .allocation_failure_points = 10, .delayed_fence = true, .validation_errors = s.c.s_errors(d) });
        return;
    }
    var cfg = c.PhysicsConfig{ .n = n, .capacity = cap, .contacts = contactcap, .pairs = paircap, .design = design, .fixture = fixture, .iterations = iterations, .sleep_frames = 20, .max_bodies = maxbodies, .max_work = maxwork, .flags = flags, .kick_slot = kick, .dt = dt, .budget = budget };
    var p = c.ph_open(@ptrCast(d), &b.handles, &cfg) orelse {
        try save(out, .{ .status = "ADMISSION_REJECTED", .error_code = c.ph_error(), .actual_processed = 0 });
        return;
    };
    var owns_physics = true;
    defer if (owns_physics) c.ph_close(p);
    try ck(c.ph_execution(p, if (execution == 2) 1 else execution, work_budget));
    try ck(c.ph_cell_mode(p, cell_mode));
    if (input) |path| {
        const data = try std.fs.cwd().readFileAlloc(a, path, 4096 * 64);
        defer a.free(data);
        if (data.len != @as(usize, n) * 64) return error.Input;
        try ck(c.ph_input(p, data.ptr, n));
    } else try ck(c.ph_scene(p));

    if ((recycle or delete_one) and (n != 32 or steps < 3)) return error.Config;
    if (recycle and delete_one) return error.Config;
    if (trace) {
        const path = try std.fmt.allocPrint(a, "{s}-state-0.bin", .{out});
        defer a.free(path);
        try dump(p, 0, path, n, cap, true);
    }
    if (seconds != 0) {
        const sustained = @import("sustained_physics.zig");
        var ok = true;
        var reason: []const u8 = "bounded session completed";
        sustained.run(d, &b, @ptrCast(p), @ptrCast(&cfg), &model, seconds, out) catch |err| {
            ok = false;
            reason = @errorName(err);
        };
        c.ph_close(p);
        owns_physics = false;
        b.deinit();
        owns_bundle = false;
        if (!try sustained.finish(d, out, ok, reason)) return error.SustainedFailed;
        return;
    }
    const initial = try b.read(0);
    var initial_hash: [32]u8 = undefined;
    std.crypto.hash.sha2.Sha256.hash(std.mem.sliceAsBytes(initial), &initial_hash, .{});
    try b.unmap();
    var rollback_baseline = initial_hash;
    const descriptors = try a.alloc([c.G4_DESCRIPTOR_WORDS]u32, steps);
    defer a.free(descriptors);
    const recording = try a.alloc(f64, steps);
    defer a.free(recording);
    const submitting = try a.alloc(f64, steps);
    defer a.free(submitting);
    const packets = try a.alloc(u32, steps);
    defer a.free(packets);
    const calls = try a.alloc(u32, steps);
    defer a.free(calls);
    const retry_gpu = try a.alloc(f64, steps);
    defer a.free(retry_gpu);
    const retry_control = try a.alloc(f64, steps);
    defer a.free(retry_control);
    var retries: u32 = 0;
    const api = try a.alloc(f64, steps);
    defer a.free(api);
    const gpu = try a.alloc([64]f64, steps);
    defer a.free(gpu);
    const cpu = try a.alloc(f64, steps);
    defer a.free(cpu);
    const blocking = try a.alloc(f64, steps);
    defer a.free(blocking);
    var r: c.PhysicsResult = std.mem.zeroes(c.PhysicsResult);
    for (0..warm + steps) |t| {
        if (injection != 0 and t == injection_at) {
            const prior = try b.read(0);
            std.crypto.hash.sha2.Sha256.hash(std.mem.sliceAsBytes(prior), &rollback_baseline, .{});
            try b.unmap();
            try ck(c.ph_inject(p, @intCast(injection)));
        }
        if (delete_one and t == 1) {
            try ck(c.ph_state_editable(p));
            const destroy = try model.destroy(model.handle(1));
            try b.commands(&.{destroy});
            n = b.n;
            cfg.n = n;
            const next = c.ph_open(@ptrCast(d), &b.handles, &cfg) orelse return error.Reopen;
            c.ph_close(p);
            p = next;
        }
        if (recycle and t == 1) {
            try ck(c.ph_state_editable(p));
            const old = model.handle(if (fixture == 7) 1 else 0);
            const destroy = try model.destroy(old);
            const created = try model.create();
            try b.commands(&.{ destroy, created.command });
            if (created.handle.generation != old.generation + 1 or created.handle.slot != old.slot) return error.Generation;
            if (model.lookup(old)) |_| {
                return error.Stale;
            } else |_| {}
        }
        try ck(if (execution == 2) c.ph_tick_auto(p, @intCast(t), &r) else c.ph_tick(p, @intCast(t), &r));
        if (verify_each_tick) {
            var every: c.PhysicsVerification = std.mem.zeroes(c.PhysicsVerification);
            try ck(c.ph_verify(p, &cfg, @intCast(t + 1), model.dense_slot.ptr, model.generation.ptr, model.to_dense.ptr, &every));
        }
        retries += r.retry_count;
        if (t >= warm) {
            try ck(c.ph_descriptor(p, &descriptors[t - warm]));
            recording[t - warm] = r.cpu_record_us;
            submitting[t - warm] = r.queue_submit_us;
            packets[t - warm] = r.command_packets;
            calls[t - warm] = r.queue_submit_calls;
            retry_gpu[t - warm] = r.retry_gpu_us;
            retry_control[t - warm] = r.retry_control_us;
            api[t - warm] = r.api_us;
            gpu[t - warm] = r.gpu_us;
            cpu[t - warm] = r.cpu_us;
            blocking[t - warm] = r.blocking_us;
        }
        if (trace) {
            for ([_]c_int{ 0, 1, 2, 3 }, [_][]const u8{ "state", "trial", "meta", "contacts" }) |which, name| {
                const path = try std.fmt.allocPrint(a, "{s}-{s}-{d}.bin", .{ out, name, t + 1 });
                defer a.free(path);
                try dump(p, which, path, n, cap, which == 0 or which == 1);
            }
        }
    }
    if (trace_last) {
        for ([_]c_int{ 0, 1, 2, 3 }, [_][]const u8{ "state", "trial", "meta", "contacts" }) |which, name| {
            const path = try std.fmt.allocPrint(a, "{s}-{s}-{d}.bin", .{ out, name, warm + steps });
            defer a.free(path);
            try dump(p, which, path, n, cap, which == 0 or which == 1);
        }
    }
    var view: ?*const anyopaque = null;
    var bytes: u64 = 0;
    try ck(c.ph_read(p, 2, &view, &bytes));
    const header = @as([*]const u32, @ptrCast(@alignCast(view.?)))[0..64];
    @memcpy(std.mem.asBytes(&r)[0..64], std.mem.sliceAsBytes(header[0..16]));
    const failtick = header[17];
    const generation = header[c.G4_SOURCE_GENERATION_BYTE / 4];
    const accepted_tick = header[c.G4_SOURCE_TICK_BYTE / 4];
    const moving_count = header[c.G4_MOVING_COUNT_BYTE / 4];
    const wall_contacts = header[c.G4_WALL_CONTACTS_BYTE / 4];
    try ck(c.ph_unmap(p));
    var verification: c.PhysicsVerification = std.mem.zeroes(c.PhysicsVerification);
    const verify_start = s.c.s_clock();
    try ck(c.ph_verify(p, &cfg, warm + steps, model.dense_slot.ptr, model.generation.ptr, model.to_dense.ptr, &verification));
    const verification_us = s.c.s_clock() - verify_start;
    const final_state = try b.read(0);
    var final_hash: [32]u8 = undefined;
    std.crypto.hash.sha2.Sha256.hash(std.mem.sliceAsBytes(final_state), &final_hash, .{});
    try b.unmap();
    const rollback: ?bool = if (r.error_flags != 0 and failtick == (if (injection != 0) injection_at + 1 else 1)) std.mem.eql(u8, &rollback_baseline, &final_hash) else null;
    if (rollback != null and !rollback.?) return error.Rollback;
    var actual_pairs: u64 = 0;
    var current_spatial_contacts: u64 = 0;
    try ck(c.ph_spatial_counts(p, &actual_pairs, &current_spatial_contacts));
    const ledger = try std.fmt.allocPrintSentinel(a, "{s}.ledger.json", .{out}, 0);
    defer a.free(ledger);
    try ck(c.ph_ledger(p, ledger));
    var memory: s.c.Memory = undefined;
    try s.ck(s.c.s_memory(d, &memory));
    try save(out, .{ .status = if (r.error_flags != 0) "GPU_REJECTED" else "PASS", .independent_every_tick = verify_each_tick, .cell_mode = cell_mode, .n = n, .capacity = cap, .fixture = fixture, .design = design, .flags = flags, .dt = dt, .iterations = iterations, .contact_capacity = contactcap, .pair_capacity = paircap, .steps = steps, .warmup = warm, .error_flags = r.error_flags, .failed_tick = failtick, .actual_published = r.published, .actual_processed = if (r.error_flags == 0) verification.objects else 0, .independent = verification, .verification_us = verification_us, .state_sha256 = std.fmt.bytesToHex(final_hash, .lower), .initial_sha256 = std.fmt.bytesToHex(initial_hash, .lower), .rollback_verified = rollback, .rollback_baseline_sha256 = std.fmt.bytesToHex(rollback_baseline, .lower), .contact_count_exact = r.error_flags == 0, .attempted_contact_count = r.contacts, .contacts = if (r.error_flags == 0) @as(?u32, r.contacts) else null, .islands = r.islands, .largest = r.largest, .solved_bodies = r.solved_bodies, .solver_dispatches = r.solver_dispatches, .total_iterations = r.total_iterations, .max_iterations = r.max_iterations, .discovery_rounds = r.rounds, .active = r.active, .woken = r.woken, .gpu_cumulative_us = gpu, .cpu_submission_us = cpu, .cpu_blocking_us = blocking, .cpu_api_us = api, .command_packets = r.command_packets, .execution_mode = r.execution_mode, .workload_descriptors = descriptors, .source_generation = generation, .accepted_tick = accepted_tick, .moving_count = moving_count, .wall_contacts = wall_contacts, .admission_retries = retries, .cpu_recording_us = recording, .cpu_queue_submission_us = submitting, .command_packet_samples = packets, .queue_submission_calls = calls, .retry_gpu_us = retry_gpu, .retry_control_us = retry_control, .queue_submit_us = r.queue_submit_us, .cpu_record_us = r.cpu_record_us, .queue_submit_calls = r.queue_submit_calls, .allocation_us = r.allocation_us, .memory = memory, .storage_ledger = b.plan, .adapter = std.mem.span(s.c.s_name(d)), .driver = s.c.s_driver(d), .candidate_count = actual_pairs, .current_spatial_contact_count = current_spatial_contacts, .validation_errors = s.c.s_errors(d), .debug = debug, .recycled = recycle, .deleted = delete_one, .injection_tick = injection_at, .fault_injection = injection });
}
