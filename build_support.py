"""Incremental native build helpers shared by Sunder production build scripts.

Do not import test runners or test-only modules here. GPU qualification and
regressions live on the test branch; this module only manages build provenance.
"""
from pathlib import Path
import ast
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from functools import lru_cache

from windows_sdk import sdk, headers, compiler

sdk = lru_cache(None)(sdk)
compiler = lru_cache(None)(compiler)

ROOT = Path(__file__).resolve().parent

GENERATORS={
 'generate.py':('schema.json',['layout.zig','layout.h','layout.hlsl']),
 'generate_spatial.py':('spatial-schema.json',['spatial-layout.h']),
 'generate_physics.py':('physics-schema.json',['physics-layout.h','physics-constants.hlsl']),
 'generate_execution.py':('execution-schema.json',['execution-layout.h']),
 'generate_billiards.py':('billiards-schema.json',['billiards-layout.h']),
 'generate_playground.py':('playground-schema.json',['playground-layout.h']),
 'generate_pool.py':('pool-schema.json',['pool-layout.h']),
}
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dependencies(names):
    """Transitive repository-local C/HLSL includes and Zig imports/cIncludes."""
    found=set();pending=list(names)
    while pending:
        name=pending.pop();path=ROOT/name
        if name in found or not path.is_file():continue
        found.add(name)
        for match in re.finditer(r'(?:@import|@cInclude)\("([^"\n]+)"\)|#include\s+"([^"\n]+)"',path.read_text(encoding='utf-8',errors='replace')):
            child=match[1] or match[2];candidate=(path.parent/child).resolve()
            base=ROOT.resolve()
            if candidate.is_relative_to(base) and candidate.is_file():pending.append(candidate.relative_to(base).as_posix())
    return sorted(found)
def shader_jobs():
    def values(path,key):
        tree=ast.parse((ROOT/path).read_text())
        return next(ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id==key for t in node.targets))
    return [('storage.hlsl',n,False) for n in values('build_spatial.py','storage_entries')]+[('spatial.hlsl',n,False) for n in values('build_spatial.py','names')]+[('physics.hlsl',n,True) for n in values('build_physics.py','names')]

class Workflow:
    def __init__(self,out):
        self.out=out;self.cache=ROOT/'.dev-test-cache';self.cache.mkdir(exist_ok=True)
        path=self.cache/'build.json';self.state=json.loads(path.read_text()) if path.exists() else {}
        self.actions=[];self.reused=0;self.ready={};self.tool_hashes=None
    def run(self,name,command,timeout=180):
        start=time.perf_counter();log=self.out/(name+'.log')
        with log.open('w',encoding='utf-8') as stream:
            stream.write(json.dumps([str(x) for x in command])+'\n');stream.flush()
            try:p=subprocess.run([str(x) for x in command],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
            except subprocess.TimeoutExpired:raise RuntimeError(f'{name}: timeout; {log}')
        raw=log.read_text(encoding='utf-8',errors='replace')
        result=dict(name=name,command=[str(x) for x in command],returncode=p.returncode,wall_seconds=time.perf_counter()-start,log=str(log))
        if p.returncode:raise RuntimeError(f'{name}: exit {p.returncode}; {log}\n'+raw[-1800:])
        return result,raw
    def key(self,names,command):
        # Rehash tool contents each invocation; timestamps are never provenance.
        # Share the two large executable hashes across targets within this run.
        if self.tool_hashes is None:
            self.tool_hashes={str(Path(tool).resolve()):digest(tool) for tool in [compiler(),sdk()[1]]}
        payload=dict(command=[str(x) for x in command],sources={name:digest(ROOT/name) for name in dependencies(names)},tools=self.tool_hashes)
        return hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    def build(self,name,inputs,outputs,command):
        key=self.key(inputs,command);paths=[ROOT/n for n in outputs];previous=self.state.get(name)
        valid=all(p.is_file() for p in paths)
        if valid and previous and previous.get('verified_build')==1 and previous['key']==key and previous['outputs']=={n:digest(ROOT/n) for n in outputs}:
            self.reused+=1;return
        # Missing/legacy records may have originated in timestamp-only adoption.
        # Only a successful compiler run establishes reusable provenance.
        result,_=self.run('build-'+name,command);self.actions.append(result)
        self.state[name]=dict(verified_build=1,key=key,outputs={n:digest(ROOT/n) for n in outputs})
        self.save()
    def save(self):
        path=self.cache/'build.json';tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(self.state,indent=2));tmp.replace(path)
    def generate(self):
        for script,(schema,outputs) in GENERATORS.items():
            key=self.key([script,schema],[sys.executable,script]);previous=self.state.get(script)
            if previous and previous['key']==key and all((ROOT/n).is_file() and previous['outputs'].get(n)==digest(ROOT/n) for n in outputs):continue
            # Generate in isolation so a schema check cannot overwrite local edits.
            with tempfile.TemporaryDirectory(prefix='gpu-contract-',dir=self.cache) as directory:
                stage=Path(directory)
                for n in [script,schema]:shutil.copy2(ROOT/n,stage/n)
                result,_=self.run('generate-'+Path(script).stem,[sys.executable,stage/script]);self.actions.append(result)
                generated={n:(stage/n).read_bytes() for n in outputs}
                for n,data in generated.items():
                    path=ROOT/n
                    if path.exists() and path.read_bytes()!=data:
                        diff=subprocess.run(['git','diff','--quiet','HEAD','--',n],cwd=ROOT,capture_output=True)
                        if diff.returncode!=0:raise RuntimeError(f'Preserving edited generated file {n}; reconcile its schema before testing')
                for n,data in generated.items():
                    if not (ROOT/n).exists() or (ROOT/n).read_bytes()!=data:(ROOT/n).write_bytes(data)
            self.state[script]=dict(key=key,outputs={n:digest(ROOT/n) for n in outputs});self.save()
    def gpu(self,target='pool_tests'):
        if target in self.ready:return self.ready[target]
        self.generate();dxc=sdk()[1]
        jobs=[job for job in shader_jobs() if target not in ['storage','spatial'] or job[0]=='storage.hlsl' or (target=='spatial' and job[0]=='spatial.hlsl')]
        for source,entry,strict in jobs:
            command=[dxc,'-T','cs_6_0',*(['-Gis'] if strict else []),'-E',entry,'-Fo',entry+'.dxil',source]
            self.build(entry,[source],[entry+'.dxil'],command)
        dest=ROOT/'zig-out/bin';dest.mkdir(parents=True,exist_ok=True)
        for _,entry,_ in jobs:
            src=ROOT/(entry+'.dxil');dst=dest/src.name
            if not dst.exists() or digest(src)!=digest(dst):shutil.copy2(src,dst)
        main={'physics':'physics_main.zig','storage':'main.zig','spatial':'spatial_main.zig'}.get(target,target+'.zig')
        sources=[main,'runtime.c']+([] if target=='storage' else ['spatial.c'])+([] if target in ['storage','spatial'] else ['physics.c','physics_verify.c','physics_tests.c'])
        command=[compiler(),'build-exe',sources[0],'-cflags','-O2','--',*sources[1:],'-I.',*headers(),'-ld3d12','-ldxgi','-ldxguid','-lkernel32','-lc','-O','ReleaseSafe','-target','x86_64-windows-gnu','-mcpu=baseline','-femit-bin=zig-out/bin/'+target+'.exe']
        self.build(target,sources,['zig-out/bin/'+target+'.exe'],command)
        self.ready[target]=dest/(target+'.exe')
        return self.ready[target]

