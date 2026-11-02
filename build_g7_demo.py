"""Incremental Windows x64 native showcase build; no external GUI framework."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
from windows_sdk import compiler, headers, sdk
from dev_test import dependencies
ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'zig-out/bin'

def main():
    subprocess.run([sys.executable, 'build_physics3.py'], cwd=ROOT, check=True)
    OUT.mkdir(parents=True, exist_ok=True)
    logs = ROOT / 'evidence/g7/native-showcase'
    logs.mkdir(parents=True, exist_ok=True)
    revision = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT, text=True).strip()
    commands = [[str(sdk()[1]), '-T', profile, '-E', entry, '-Fo', str(OUT / ('g7_' + entry + '.dxil')), 'g7_render.hlsl']
                for entry, profile in [('sphere_vs', 'vs_6_0'), ('sphere_ps', 'ps_6_0'), ('container_vs', 'vs_6_0'), ('container_ps', 'ps_6_0')]]
    imgui = ['third_party/imgui/' + x for x in ('imgui.cpp', 'imgui_draw.cpp', 'imgui_tables.cpp', 'imgui_widgets.cpp')]
    commands.append([compiler(), 'build-exe', '-cflags', '-O2', '--', 'physics3.c', 'runtime.c',
                     '-cflags', '-O2', '-std=c++17', '-Wno-nontrivial-memaccess', '-DG7_REVISION="' + revision + '"', '--', 'g7_demo.cpp', *imgui,
                     'third_party/imgui/backends/imgui_impl_win32.cpp', 'third_party/imgui/backends/imgui_impl_dx12.cpp',
                     '-I.', '-Ithird_party/imgui', *headers(), '-ld3d12', '-ldxgi', '-ldxguid', '-lkernel32', '-luser32', '-lgdi32',
                     '-L' + str(sdk()[0].parents[1] / 'Lib' / sdk()[0].name / 'um/x64'), '-ld3dcompiler', '-ldwmapi',
                     '-lc++', '-lc', '-O', 'ReleaseSafe', '-target', 'x86_64-windows-gnu', '-mcpu=baseline',
                     '-femit-bin=' + str(OUT / 'SunderG7.exe')])
    files = dependencies(['g7_demo.cpp', 'g7_scene.h', 'g7_ui_numbers.h', 'g7_native.h', 'g7_render.hlsl', 'physics3.c', 'runtime.c', 'build_g7_demo.py'])
    files = sorted(set(files + imgui + ['third_party/imgui/backends/imgui_impl_win32.cpp', 'third_party/imgui/backends/imgui_impl_dx12.cpp']))
    identity = dict(commands=commands, sources={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in files},
                    tools={str(p): hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [compiler(), sdk()[1]]})
    manifest = logs / 'build.json'
    outputs = [OUT / p for p in ('SunderG7.exe', 'g7_sphere_vs.dxil', 'g7_sphere_ps.dxil', 'g7_container_vs.dxil', 'g7_container_ps.dxil')]
    if manifest.exists():
        prior = json.loads(manifest.read_text())
        if all(prior.get(k) == v for k, v in identity.items()) and all(p.exists() and prior['outputs'].get(p.name) == hashlib.sha256(p.read_bytes()).hexdigest() for p in outputs):
            print('PASS G7 verified unchanged native build reused')
            return
    for i, command in enumerate(commands):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        (logs / f'build-{i}.log').write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(f'Native G7 build {i} failed: {result.stderr[-5000:]}')
    manifest.write_text(json.dumps(dict(identity, outputs={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in outputs}), indent=2))
    print('PASS native G7 executable and perspective sphere shaders')

if __name__ == '__main__':
    main()
