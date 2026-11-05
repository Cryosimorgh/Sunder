"""Build the isolated native 3D slice using the existing Windows SDK runtime."""
from pathlib import Path
import hashlib,json,subprocess
from windows_sdk import sdk,headers,compiler
from build_support import dependencies
R=Path(__file__).resolve().parent
OUT=R/'evidence/p10/build'
ENTRIES=['clear','prepare','hash','contacts','solve','gather','integrate','validate','publish','converge_clear','converge_check','converge_finish','cache_clear','cache_publish','color','colored_solve','color_prepare']
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    dxc=sdk()[1]
    commands=[]
    for name in ENTRIES:
        commands.append([str(dxc),'-T','cs_6_0','-Gis','-E','p3_'+name,'-Fo',str(OUT/('p3_'+name+'.dxil')),'physics3.hlsl'])
    commands.append([compiler(),'build-lib','-dynamic','-cflags','-O2','--','physics3.c','runtime.c','-I.',*headers(),'-ld3d12','-ldxgi','-ldxguid','-lkernel32','-lc','-O','ReleaseSafe','-target','x86_64-windows-gnu','-femit-bin='+str(OUT/'physics3.dll')])
    files=dependencies(['physics3.c','runtime.c','physics3.hlsl','physics3-schema.json','build_physics3.py'])
    identity={'commands':commands,'sources':{p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in files},'tools':{str(p):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [compiler(),dxc]}}
    prior=OUT/'manifest.json'
    if prior.exists():
        saved=json.loads(prior.read_text())
        if all(saved.get(k)==v for k,v in identity.items()) and all((OUT/p).is_file() and hashlib.sha256((OUT/p).read_bytes()).hexdigest()==h for p,h in saved['outputs'].items()):
            print('PASS native3D verified unchanged build reused');return
    for i,cmd in enumerate(commands):
        p=subprocess.run(cmd,cwd=R,capture_output=True,text=True)
        (OUT/f'build-{i}.log').write_text(p.stdout+p.stderr)
        if p.returncode:raise RuntimeError(f'{cmd[0]} exit {p.returncode}: {p.stdout[-1500:]}{p.stderr[-1500:]}')
    result=dict(identity,outputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.suffix in ['.dll','.dxil']})
    (OUT/'manifest.json').write_text(json.dumps(result,indent=2))
    print('PASS native3D build: 17 shaders and isolated runtime DLL')
if __name__=='__main__':main()
