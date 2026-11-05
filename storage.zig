//! Owns resident GPU storage buffers, memory admission, and compute dispatch.
//! Device creation and deterministic reference calculations are separate modules.
const std = @import("std");
pub const l = @import("layout.zig");
pub const entity = @import("entity.zig");
const device = @import("storage_device.zig");
const reference = @import("reference_state.zig");
pub const c = device.c;
pub const passes = device.passes;
pub const ck = device.ck;
pub const open = device.open;
pub const seed = reference.seed;
pub const activeId = reference.activeId;
pub const expected = reference.expected;

pub fn aligned(x:u64) !u64{return (try l.add(x,65535)) & ~@as(u64,65535);}
pub fn scratchWords(cap:u64) !u64 {return l.prefixWords(cap);}
pub const Ledger=struct {capacity:u32,n:u32,logical:[10]u64,device:[10]u64,total:u64,guard_bytes:u64=256,per_frame_copies:u32=1,contacts:u32=0};
pub fn ledger(d:*c.StorageDevice,n:u32,cap:u32) !Ledger {
 if(cap==0 or cap<n or cap%l.tile!=0)return error.Capacity;
 var x:Ledger=.{.capacity=cap,.n=n,.logical=undefined,.device=undefined,.total=0};
 x.logical=try l.bufferBytes(cap);
 for(x.logical,0..) |bytes,i|{if(bytes>std.math.maxInt(u32))return error.AddressOverflow;const size=c.s_allocation(d,bytes,l.buffer_kinds[i]);if(size==std.math.maxInt(u64))return error.DeviceDimension;x.device[i]=size;x.total=try l.add(x.total,size);}

 return x;
}
pub const Bundle=struct {
 d:*c.StorageDevice,n:u32,cap:u32,kind:u32,stride:u32,epoch:u32=0,handles:[10]u64=.{0}**10,plan:Ledger,allocation_us:f64=0,active_epoch:?u32=null,active_stride:u32=0,active_n:u32=0,vector_full:bool=false,poisoned:bool=false,
 pub fn init(d:*c.StorageDevice,n:u32,cap:u32,kind:u32,stride:u32,budget_cap:u64) !Bundle {
  if(kind>2)return error.Config;const p=try ledger(d,n,cap);if(c.s_admit(d,p.total,budget_cap)==0)return error.MemoryAdmission;
  var s:Bundle=.{.d=d,.n=n,.cap=cap,.kind=kind,.stride=stride,.plan=p};errdefer s.deinit();
  const start=c.s_clock();for(0..10) |i|{s.handles[i]=c.s_new(d,p.logical[i],l.buffer_kinds[i],l.buffer_names[i]);if(s.handles[i]==0)return error.Allocation;}
  s.allocation_us=c.s_clock()-start;return s;
 }
 pub fn deinit(s:*Bundle) void {for(&s.handles) |*h|if(h.*!=0){if(c.s_retire(s.d,h.*)==0)std.process.exit(3);h.*=0;};_=c.s_collect(s.d);}
 pub fn constants(s:*const Bundle,verify:bool) [l.constant_count]u32 {return .{s.n,s.cap,s.kind,s.stride,@intFromBool(verify),0,0,s.cap,0,0,0,0,0,s.epoch,0,0};}
 pub fn bind(s:*Bundle,k:*const [l.constant_count]u32,input:u64) !void {if(s.poisoned)return error.Poisoned;const h:[8]u64=.{s.handles[0],s.handles[1],s.handles[2],s.handles[3],s.handles[4],s.handles[5],s.handles[6],input};try ck(c.s_bind(s.d,&h,k));}
 pub fn dispatch(s:*Bundle,pass:u32,count:u32,k:*const [l.constant_count]u32,input:u64) !void {try s.bind(k,input);try ck(c.s_dispatch(s.d,@intCast(pass),count));}
 pub fn initialize(s:*Bundle) !void {try ck(c.s_begin(s.d));const k=s.constants(false);try s.dispatch(0,s.cap,&k,s.handles[8]);try ck(c.s_submit(s.d,0));try ck(c.s_wait(s.d));}
 pub fn compact(s:*Bundle,verify:bool) !void {
  var k=s.constants(verify);try s.dispatch(1,s.n,&k,s.handles[8]);
  var counts:[8]u32=undefined;var offsets:[8]u32=undefined;var levels:usize=0;var size=(s.n+255)/256;var offset:u32=0;
  while(true){counts[levels]=size;offsets[levels]=offset;levels+=1;offset+=2*size;if(size<=256)break;size=(size+255)/256;}
  for(0..levels) |i|{k[8]=counts[i];k[9]=offsets[i];k[10]=offsets[i]+counts[i];k[11]=if(i+1<levels)offsets[i+1] else 0;try s.dispatch(2,counts[i],&k,s.handles[8]);}
  var j=levels-1;while(j>0){j-=1;k[8]=counts[j];k[10]=offsets[j]+counts[j];k[11]=offsets[j+1]+counts[j+1];try s.dispatch(3,counts[j],&k,s.handles[8]);}
  k=s.constants(verify);k[10]=counts[0];try s.dispatch(4,s.n,&k,s.handles[8]);
 }
 pub fn pipeline(s:*Bundle,verify:bool,rebuild:bool,timed:bool) !void {
  if(timed)try ck(c.s_stamp(s.d,0));
  if(rebuild or s.active_epoch==null or s.active_epoch.?!=s.epoch or s.active_stride!=s.stride or s.active_n!=s.n){if(s.n==0){const k=s.constants(verify);try s.dispatch(16,1,&k,s.handles[8]);}else try s.compact(verify);s.active_epoch=s.epoch;s.active_stride=s.stride;s.active_n=s.n;}
  if(timed)try ck(c.s_stamp(s.d,1));
  const k=s.constants(verify);
  for([_]u32{5,6,7,8,9,10,11},0..) |pass,i|{if(s.n>0)try s.dispatch(if(pass==9 and s.vector_full)15 else pass,s.n,&k,s.handles[8]);if(timed)try ck(c.s_stamp(s.d,@intCast(i+2)));}
 }
 pub fn read(s:*Bundle,index:usize) ![]const u32 {
  const bytes=s.plan.logical[index];if(bytes>s.plan.logical[7])return error.ReadbackCapacity;
  try ck(c.s_begin(s.d));try ck(c.s_transition(s.d,s.handles[index],1));try ck(c.s_copy(s.d,s.handles[7],s.handles[index],bytes));try ck(c.s_transition(s.d,s.handles[index],0));try ck(c.s_submit(s.d,0));try ck(c.s_wait(s.d));
  const p=c.s_map(s.d,s.handles[7],bytes) orelse return error.Map;
  return @as([*]const u32,@ptrCast(@alignCast(p)))[0..@intCast(bytes/4)];
 }
 pub fn unmap(s:*Bundle) !void {try ck(c.s_unmap(s.d,s.handles[7],0));}
 pub fn convertSource(s:*Bundle,old:u64,old_kind:u32,old_cap:u32,verify:bool) !void {
  var k=s.constants(verify);k[6]=old_kind;k[7]=old_cap;try ck(c.s_transition(s.d,old,3));try s.dispatch(12,s.n,&k,old);try ck(c.s_transition(s.d,old,0));
 }
 pub fn commands(s:*Bundle,commands_:[]const entity.Command) !void {
  if(s.poisoned)return error.Poisoned;
  if(commands_.len>l.command_capacity)return error.CommandCapacity;
  for(commands_) |command|if(command.op<1 or command.op>3 or command.slot>=s.cap)return error.Command;
  if(s.epoch==std.math.maxInt(u32))return error.EpochOverflow;
  const bytes=std.mem.sliceAsBytes(commands_);const p=c.s_map(s.d,s.handles[8],0) orelse return error.Map;
  @memcpy(@as([*]u8,@ptrCast(p))[0..bytes.len],bytes);try ck(c.s_unmap(s.d,s.handles[8],bytes.len));
  try ck(c.s_begin(s.d));var k=s.constants(false);k[12]=@intCast(commands_.len);try s.dispatch(13,1,&k,s.handles[8]);try ck(c.s_submit(s.d,0));try ck(c.s_wait(s.d));
  const control=try s.read(6);const errors=control[0];const count=control[1];const epoch=control[2];try s.unmap();
  if(errors!=0 or epoch!=s.epoch+1){s.poisoned=true;return error.StructuralCommit;}
  s.n=count;s.plan.n=count;s.epoch=epoch;
 }
};
