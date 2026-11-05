"""Verified builds of the existing renderer in a windowless CLI harness."""
from pathlib import Path
import subprocess,zipfile,io,importlib.util,sys,shutil,json
from build_support import ROOT, Workflow, shader_jobs, digest
from windows_sdk import compiler,headers,sdk
BASE='7fdd05e38acfe04c264997f880a665f48affe799'
OVERLAY=['viewer.c','viewer.h','render-consumer.inc','render-consumer-tests.inc','render_consumer_main.zig','viewer-schema.json','viewer-layout.h','viewer-cbuffer.hlsl','render.hlsl','pool-schema.json','pool-layout.h']
def control_root():
 stage=ROOT/'.dev-test-cache/p3-control';stage.mkdir(parents=True,exist_ok=True)
 raw=subprocess.run(['git','archive','--format=zip',BASE],cwd=ROOT,capture_output=True,check=True).stdout
 with zipfile.ZipFile(io.BytesIO(raw)) as archive:
  for item in archive.infolist():
   n=Path(item.filename)
   if not item.is_dir() and (len(n.parts)==1 and n.suffix in {'.c','.cpp','.h','.inc','.zig','.hlsl','.json','.py'} or str(n).replace('\\','/').startswith('third_party/')):
    p=stage/n;p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists() or p.read_bytes()!=archive.read(item):p.write_bytes(archive.read(item))
 for n in OVERLAY:
  p=stage/n
  if not p.exists() or p.read_bytes()!=(ROOT/n).read_bytes():p.write_bytes((ROOT/n).read_bytes())
 return stage
def build(out,control=False,blocking=False):
 stage=control_root() if control else ROOT
 spec=importlib.util.spec_from_file_location('p3_control_dev' if control else 'p3_candidate_dev',stage/('dev_test.py' if control else 'build_support.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 w=module.Workflow(out);w.generate();w.build('viewer-ABI',['generate_viewer.py','viewer-schema.json'],['viewer-layout.h','viewer-cbuffer.hlsl'],[sys.executable,'generate_viewer.py'])
 # Compile only inputs/options lacking verified provenance, never adopt by mtime.
 jobs=module.shader_jobs()
 for source,entry,strict in jobs:
  w.build(entry,[source],[entry+'.dxil'],[sdk()[1],'-T','cs_6_0',*(['-Gis'] if strict else []),'-E',entry,'-Fo',entry+'.dxil',source])
 for entry,profile,source in [('ball_vs','vs_6_0','render.hlsl'),('ball_ps','ps_6_0','render.hlsl'),('felt_vs','vs_6_0','render.hlsl'),('felt_ps','ps_6_0','render.hlsl'),('render_clear','cs_6_0','render.hlsl'),('render_verify','cs_6_0','render.hlsl'),('hud_vs','vs_6_0','hud.hlsl'),('hud_ps','ps_6_0','hud.hlsl'),('play_pick','cs_6_0','render.hlsl'),('play_pick_resolve','cs_6_0','render.hlsl')]:
  w.build(entry,[source],[entry+'.dxil'],[sdk()[1],'-T',profile,'-E',entry,'-Fo',entry+'.dxil',source])
 dest=stage/'zig-out/bin';dest.mkdir(parents=True,exist_ok=True)
 for p in stage.glob('*.dxil'):
  q=dest/p.name
  if not q.exists() or digest(q)!=digest(p):shutil.copy2(p,q)
 sources=['render_consumer_main.zig','viewer_runtime.c','bench_support.c','spatial.c','physics.c','physics_verify.c','physics_tests.c']
 cpp=['play_ui.cpp',*[p.relative_to(stage).as_posix() for p in (stage/'third_party/imgui').glob('imgui*.cpp') if p.name!='imgui_demo.cpp'],'third_party/imgui/backends/imgui_impl_win32.cpp']
 command=[compiler(),'build-exe',sources[0],'--cache-dir','.dev-test-cache/obj3','-cflags','-O2','-DG6_RENDER_LEGACY_CONTROL='+str(int(control)),'--',*sources[1:],'-cflags','-O2','-std=c++17','-Wno-nontrivial-memaccess','--',*cpp,'-I.','-Ithird_party/imgui',*headers(),'-ld3d12','-ldxgi','-ldxguid','-lkernel32','-luser32','-lgdi32','-L'+str(sdk()[0].parents[1]/'Lib'/sdk()[0].name/'um/x64'),'-ld3dcompiler','-ldwmapi','-lc++','-lc','-O','ReleaseSafe','-target','x86_64-windows-gnu','-mcpu=baseline','-femit-bin=zig-out/bin/render_consumer.exe']
 # P4's matched control uses the P3 blocking policy with common telemetry.
 # Physics, shaders and renderer bindings are identical in both arms.
 command.insert(command.index('--'),'-DG6_P3_BLOCKING_CONTROL='+str(int(blocking)))
 name='p3_render_consumer' if blocking else 'render_consumer'
 command[-1]='-femit-bin=zig-out/bin/'+name+'.exe'
 w.build(name,sources+cpp,['zig-out/bin/'+name+'.exe'],command)
 return dest/(name+'.exe'),w
