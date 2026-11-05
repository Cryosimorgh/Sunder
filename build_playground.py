from pathlib import Path
import sys
from windows_sdk import run,compiler,headers
if '--tests' in sys.argv or '--tests-only' in sys.argv:
    required = ['pool_tests.zig', 'playground_gpu_tests.zig']
    absent = [name for name in required if not (Path(__file__).parent / name).exists()]
    if absent:
        raise RuntimeError('Run native test builds on the test branch; missing ' + ', '.join(absent))
run(sys.executable,'generate_playground.py')
run(sys.executable,'generate_pool.py')
if '--tests-only' not in sys.argv:
 run(sys.executable,'build_physics.py')
 run(sys.executable,'build_viewer.py','--playground')
if '--tests' in sys.argv or '--tests-only' in sys.argv:
 run(compiler(),'build-exe','playground_gpu_tests.zig','-cflags','-O2','--','runtime.c','spatial.c','physics.c','physics_verify.c','physics_tests.c','-I.',*headers(),'-ld3d12','-ldxgi','-ldxguid','-lkernel32','-lc','-O','ReleaseSafe','-target','x86_64-windows-gnu','-mcpu=baseline','-femit-bin=zig-out/bin/playground_gpu_tests.exe')

if "--tests" in sys.argv or "--tests-only" in sys.argv:
 run(compiler(),"build-exe","pool_tests.zig","-cflags","-O2","--","runtime.c","spatial.c","physics.c","physics_verify.c","physics_tests.c","-I.",*headers(),"-ld3d12","-ldxgi","-ldxguid","-lkernel32","-lc","-O","ReleaseSafe","-target","x86_64-windows-gnu","-mcpu=baseline","-femit-bin=zig-out/bin/pool_tests.exe")
