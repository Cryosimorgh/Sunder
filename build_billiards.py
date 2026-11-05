"""Incremental current-source playable build; never launches the game."""
from pathlib import Path
import datetime,json,os,shutil,sys
from build_support import ROOT,Workflow,dependencies,digest,shader_jobs
from windows_sdk import sdk

RENDER_JOBS=[('ball_vs','vs_6_0'),('ball_ps','ps_6_0'),('felt_vs','vs_6_0'),('felt_ps','ps_6_0'),('render_clear','cs_6_0'),('render_verify','cs_6_0'),('hud_vs','vs_6_0'),('hud_ps','ps_6_0'),('play_pick','cs_6_0'),('play_pick_resolve','cs_6_0')]

def verify_build(root=ROOT):
    """Reject unknown/stale host or shader provenance without rebuilding."""
    path=root/'zig-out/bin/BILLIARDS_BUILD.json'
    if not path.is_file():raise RuntimeError('Missing verified billiards build; run python build_billiards.py')
    manifest=json.loads(path.read_text())
    if manifest.get('verified_build')!=1:raise RuntimeError('Unknown billiards build provenance')
    if {p.name for p in root.glob('*.dxil')}!=set(manifest['shader_sha256']):raise RuntimeError('Unverified billiards shader inventory')
    for name,expected in manifest['source_sha256'].items():
        p=root/name
        if not p.is_file() or digest(p)!=expected:raise RuntimeError('Stale billiards source: '+name)
    exe=root/'zig-out/bin/GPUPhysicsBilliards.exe'
    if not exe.is_file() or digest(exe)!=manifest['executable_sha256']:raise RuntimeError('Stale/corrupted billiards executable')
    for name,expected in manifest['shader_sha256'].items():
        for p in [root/name,root/'zig-out/bin'/name]:
            if not p.is_file() or digest(p)!=expected:raise RuntimeError('Stale/corrupted billiards shader: '+str(p))
    return manifest

def main():
    out=ROOT/'billiards-test-results'/('build-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));out.mkdir(parents=True)
    w=Workflow(out);lock=w.cache/'running.lock'
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:raise RuntimeError('Another developer build/test is active; preserve its lock')
    os.write(fd,str(os.getpid()).encode());os.close(fd)
    try:
        w.gpu('physics')
        if '--tests' in sys.argv:
            w.gpu('pool_tests');w.gpu('playground_gpu_tests')
        shader_sources=[x[0] for x in shader_jobs()]
        for entry,profile in RENDER_JOBS:
            source='hud.hlsl' if entry.startswith('hud_') else 'render.hlsl';shader_sources.append(source)
            w.build('billiards-'+entry,[source],[entry+'.dxil'],[sdk()[1],'-T',profile,'-E',entry,'-Fo',entry+'.dxil',source])
        inputs=['build_billiards.py','build_viewer.py','windows_sdk.py','build_support.py','playground_main.zig','viewer_runtime.c','bench_support.c','spatial.c','physics.c','physics_verify.c','physics_tests.c','play_ui.cpp']
        inputs += [p.relative_to(ROOT).as_posix() for p in (ROOT/'third_party/imgui').rglob('*') if p.is_file()]
        w.build('billiards-host',inputs,['zig-out/bin/GPUPhysicsPlayground.exe'],[sys.executable,'build_viewer.py','--host-only','--playground'])
        dest=ROOT/'zig-out/bin'
        for p in ROOT.glob('*.dxil'):
            target=dest/p.name
            if not target.is_file() or digest(p)!=digest(target):shutil.copy2(p,target)
        source=dest/'GPUPhysicsPlayground.exe';target=dest/'GPUPhysicsBilliards.exe'
        if not target.is_file() or digest(source)!=digest(target):shutil.copy2(source,target)
        manifest=dict(verified_build=1,status='PASS',executable_sha256=digest(target),
                      source_sha256={n:digest(ROOT/n) for n in dependencies(inputs+shader_sources)},
                      shader_sha256={p.name:digest(p) for p in ROOT.glob('*.dxil')},
                      tool_sha256=w.tool_hashes,host_cache=w.state['billiards-host'],build_actions=w.actions,reused=w.reused)
        (dest/'BILLIARDS_BUILD.json').write_text(json.dumps(manifest,indent=2));verify_build()
        (out/'verification.json').write_text(json.dumps(manifest,indent=2))
        print(f'PASS current-source billiards build; built {len(w.actions)}, reused {w.reused}; evidence {out}')
    finally:lock.unlink()

if __name__=='__main__':main()
