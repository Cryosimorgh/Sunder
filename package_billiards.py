"""Package a verified current-source game into a new versioned portable ZIP."""
from pathlib import Path
import argparse,datetime,hashlib,json,zipfile,struct,subprocess
from build_billiards import verify_build
r=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);parser.add_argument('--evidence',nargs='*',type=Path,default=[]);parser.add_argument('--handoff-patch',type=Path);args=parser.parse_args()
provenance=verify_build()
files={'GPUPhysicsBilliards.exe':r/'zig-out/bin/GPUPhysicsBilliards.exe','Launch.bat':r/'LaunchBilliards.bat','README.txt':r/'BILLIARDS_README.txt','LICENSE-ImGui.txt':r/'third_party/imgui/LICENSE.txt'}
for name,target in [('BILLIARDS_PHYSICS_CORRECTION.md','BILLIARDS_PHYSICS_CORRECTION.md'),('BILLIARDS_VERIFICATION.json','TEST_RESULTS.json')]:
 if (r/name).is_file():files[target]=r/name
files.update({p.name:p for p in r.glob('*.dxil')})
files['BILLIARDS_BUILD.json']=r/'zig-out/bin/BILLIARDS_BUILD.json'
for directory in ['docs/billiards','examples/billiards']:
 for p in (r/directory).rglob('*'):
  if p.is_file():files[p.relative_to(r).as_posix()]=p
for directory in args.evidence:
 for p in directory.rglob('*'):
  if p.is_file():files[(Path('current-evidence')/directory.name/p.relative_to(directory)).as_posix()]=p
if args.handoff_patch:files['CURRENT_WORKING_TREE.patch']=args.handoff_patch
for name in ['build_billiards.py','build_support.py','package_billiards.py','pool.hlsl','pool-schema.json','pool-layout.h']:
 files['handoff-source/'+name]=r/name
hashes={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()}
exe=files['GPUPhysicsBilliards.exe'].read_bytes();pe=struct.unpack_from('<I',exe,0x3c)[0];assert struct.unpack_from('<H',exe,pe+4)[0]==0x8664;op=pe+24;sec=op+struct.unpack_from('<H',exe,pe+20)[0]
def offset(rva):
 for i in range(struct.unpack_from('<H',exe,pe+6)[0]):
  size,va,rawsize,raw=struct.unpack_from('<IIII',exe,sec+40*i+8)
  if va<=rva<va+max(size,rawsize):return raw+rva-va
 raise ValueError(rva)
at=offset(struct.unpack_from('<I',exe,op+120)[0]);imports=[]
while any(exe[at:at+20]):
 name=offset(struct.unpack_from('<I',exe,at+12)[0]);imports.append(exe[name:exe.index(b'\0',name)].decode());at+=20
allowed={'d3d12.dll','dxgi.dll','d3dcompiler_47.dll','dwmapi.dll','kernel32.dll','user32.dll','gdi32.dll','ntdll.dll','msvcrt.dll','ucrtbase.dll','imm32.dll','ole32.dll','advapi32.dll','shell32.dll','version.dll'}
assert all(n.lower() in allowed or n.lower().startswith(('api-ms-win-','ext-ms-win-')) for n in imports),imports
sources=[p for p in r.iterdir() if p.is_file() and p.suffix in {'.c','.cpp','.h','.hlsl','.inc','.zig','.json','.py'}]+[p for p in (r/'third_party/imgui').rglob('*') if p.is_file()]
build=dict(cpu_target='x86_64 baseline',optimization='ReleaseSafe',imported_windows_system_dlls=imports,source_sha256={p.relative_to(r).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},gpu02='UNVERIFIED',g5_qualified=False,verified_host=provenance,
 git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=r,text=True).strip(),working_tree_dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=r,text=True).strip()),
 build_source_dirty=bool(subprocess.check_output(['git','diff','HEAD','--',*provenance['source_sha256']],cwd=r)))
target=(args.output or r/'dist'/('GPUPhysicsBilliards-Windows-x64-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.zip')).resolve();target.parent.mkdir(parents=True,exist_ok=True)
if target.exists():raise FileExistsError('Preserving existing portable; choose a new --output: '+str(target))
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for n,p in sorted(files.items()):z.writestr(n,p.read_bytes())
 z.writestr('results/',b'');z.writestr('SHA256.json',json.dumps(hashes,indent=2));z.writestr('BUILD.json',json.dumps(build,indent=2))
with zipfile.ZipFile(target) as z:
 assert z.testzip() is None;assert all(hashlib.sha256(z.read(n)).hexdigest()==h for n,h in hashes.items())
sha=hashlib.sha256(target.read_bytes()).hexdigest();target.with_suffix('.zip.sha256').write_text(sha+'  '+target.name+'\n')
print(json.dumps(dict(zip=str(target),bytes=target.stat().st_size,sha256=sha,files=len(files),status='PASS'),indent=2))
