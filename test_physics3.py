"""Independent double-precision CPU oracle around the actual D3D12 3D kernels.
No Python contact solver is used to produce the GPU result.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,json,math,struct,time,traceback,os
import numpy as np
R=Path(__file__).resolve().parent
BUILD=R/'evidence/p10/build'
E=Path(os.environ.get('SUNDER_P10_EVIDENCE_DIR',str(R/'evidence/p10')))
U=np.finfo(np.float32).eps

class Result(C.Structure):
    _fields_=[(n,C.c_uint32) for n in ['error','contacts','published','generation','tick','max_degree','candidates','awake']]+[('phases_us',C.c_double*8),('committed',C.c_uint64)]
class Lease(C.Structure):
    _fields_=[('context',C.c_uint64),('serial',C.c_uint64),('buffer',C.c_uint64),('slot',C.c_uint32),('generation',C.c_uint32)]
def library():
    dll=C.CDLL(str(BUILD/'physics3.dll'))
    signatures={'open':([C.c_uint32,C.c_uint32,C.c_uint32,C.c_int,C.c_char_p],C.c_void_p),'close':([C.c_void_p],C.c_int),'seed':([C.c_void_p,C.c_void_p,C.c_void_p,C.c_uint32],C.c_int),'stage':([C.c_void_p,C.c_void_p],C.c_int),'drop_stage':([C.c_void_p],C.c_int),'tick':([C.c_void_p,C.c_float,C.c_void_p,C.c_float,C.c_uint32,C.POINTER(Result)],C.c_int),'read':([C.c_void_p,C.c_void_p],C.c_int),'contacts':([C.c_void_p,C.c_void_p,C.c_uint32],C.c_int),'acquire':([C.c_void_p,C.POINTER(Lease)],C.c_int),'release':([C.c_void_p,C.POINTER(Lease)],C.c_int),'reader_test':([C.c_void_p],C.c_int),'adapter':([C.c_void_p],C.c_char_p)}
    for name,(args,ret) in signatures.items():f=getattr(dll,'ph3_'+name);f.argtypes=args;f.restype=ret
    return dll
DLL=None
def soa(n):
    a=np.zeros((48,n),dtype=np.float32);a[9]=1;a[19]=1;a[20]=.25;a[21]=.8;a[22]=.3
    inertia=.4*.25**2
    a[24:27]=inertia;a[30:33]=1/inertia
    a[36].view(np.uint32)[:]=np.arange(n,dtype=np.uint32);a[37].view(np.uint32)[:]=1
    return a
def set_mass(a,i,m):
    a[19,i]=0 if m==0 else 1/m
    if m:a[24:27,i]=.4*m*a[20,i]**2;a[30:33,i]=1/a[24:27,i]
def rotation(q):
    x,y,z,w=np.asarray(q,dtype=float)
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
def tensor(a,i,base):
    x,y,z,xy,xz,yz=a[base:base+6,i].astype(float)
    return np.array([[x,xy,xz],[xy,y,yz],[xz,yz,z]])
def world(a,i,base):
    q=rotation(a[6:10,i]);return q@tensor(a,i,base)@q.T
def free(a,dt,g):
    v=a[3:6].astype(float).copy();w=a[10:13].astype(float).copy()
    for i in range(a.shape[1]):
        if a[19,i]>0:
            v[:,i]+=dt*(g+a[19,i]*a[13:16,i])
            w[:,i]+=dt*world(a,i,30)@a[16:19,i]
    return v,w
def energy(a):
    answer=0.
    for i in range(a.shape[1]):
        if a[19,i]>0:answer+=.5*np.dot(a[3:6,i].astype(float),a[3:6,i])/a[19,i]+.5*a[10:13,i]@world(a,i,24)@a[10:13,i]
    return float(answer)
def momentum(a):
    p=np.zeros(3);l=np.zeros(3)
    for i in range(a.shape[1]):
        if a[19,i]>0:
            mv=a[3:6,i].astype(float)/a[19,i];p+=mv;l+=np.cross(a[:3,i],mv)+world(a,i,24)@a[10:13,i]
    return p,l
def project(v,cap):
    size=np.linalg.norm(v);return v*min(1.,cap/size) if size else v

class GPU:
    def __init__(self,a,planes=None,iterations=128,capacity=None,debug=False):
        self.n=a.shape[1];self.capacity=capacity or max(64,self.n*2);self.ptr=DLL.ph3_open(self.n,self.capacity,iterations,debug,str(BUILD).encode());assert self.ptr,'D3D12 context/build admission failed'
        self.planes=np.asarray(planes if planes is not None else [],dtype=np.float32).reshape(-1,4)
        self.seed(a)
    def seed(self,a):
        a=np.ascontiguousarray(a,dtype=np.float32)
        assert DLL.ph3_seed(self.ptr,a.ctypes.data,self.planes.ctypes.data,len(self.planes)),'seed failed'
        self.state=a.copy()
    def read(self):
        a=np.empty((48,self.n),dtype=np.float32);assert DLL.ph3_read(self.ptr,a.ctypes.data);return a
    def step(self,dt=1/128,g=(0,0,0),cell=2.,inject=0,accept=True,oracle=True):
        before=self.state.copy();gravity=np.asarray(g,dtype=np.float32);dt=float(np.float32(dt));r=Result()
        assert DLL.ph3_tick(self.ptr,dt,gravity.ctypes.data,cell,inject,C.byref(r)),'host tick/backpressure failure'
        after=self.read()
        if accept:
            assert r.error==0 and r.published==self.n,('GPU rejected',r.error,r.contacts)
            if oracle:self.check(before,after,dt,gravity,r,cell)
            self.state=after
        else:
            assert r.error and r.published==0,('expected rejection',r.error)
            assert after.tobytes()==before.tobytes(),'rejection changed accepted state'
        return r
    def check(self,a,b,dt,g,r,cell):
        assert np.isfinite(b[:36]).all() and np.max(np.abs(np.linalg.norm(b[6:10],axis=0)-1))<2e-5
        assert np.array_equal(a[36:38].view(np.uint32),b[36:38].view(np.uint32))
        vf,wf=free(a,dt,g);vr=vf.copy();wr=wf.copy();seen=set();worst=0.;contact_records=[]
        raw=np.zeros((max(1,r.contacts),128),dtype=np.uint8)
        if r.contacts:assert DLL.ph3_contacts(self.ptr,raw.ctypes.data,r.contacts)
        for record in raw[:r.contacts]:
            data=record.tobytes();i,j=struct.unpack_from('<II',data);ln=struct.unpack_from('<d',data,16)[0];lt=np.array(struct.unpack_from('<3d',data,24));target=struct.unpack_from('<d',data,48)[0]
            assert (i,j) not in seen;seen.add((i,j))
            if j<self.n:
                delta=a[:3,i].astype(float)-a[:3,j];dist=np.linalg.norm(delta);normal=delta/dist;gap=dist-float(a[20,i])-float(a[20,j]);vb=vf[:,j];rest=min(a[21,i],a[21,j]);mu=min(a[22,i],a[22,j]);kn=float(a[19,i])+float(a[19,j])
                assert np.linalg.norm(b[:3,i].astype(float)-b[:3,j])+16*U*max(1.,np.linalg.norm(b[:3,i])+np.linalg.norm(b[:3,j]))>=float(a[20,i])+float(a[20,j])
            else:
                pl=self.planes[j-self.n].astype(float);pl/=np.linalg.norm(pl[:3]);normal=pl[:3];gap=normal@a[:3,i]-pl[3]-a[20,i];vb=np.zeros(3);rest=a[21,i];mu=a[22,i];kn=float(a[19,i]);assert normal@b[:3,i]-pl[3]-a[20,i]>=-16*U*max(1.,np.linalg.norm(b[:3,i]))
            assert np.max(np.abs(normal-np.array(struct.unpack_from('<3d',data,56))))<2e-12
            vn=(vf[:,i]-vb)@normal;expected=-gap/dt if gap>0 and vn>=-gap/dt else max(-gap/dt,-float(rest)*vn if vn<-.5 else 0.)
            assert abs(target-expected)<1e-10*max(1,abs(expected)),('target',target,expected)
            impulse=normal*ln+lt
            for body,sign in [(i,1),(j,-1)]:
                if body>=self.n:continue
                vr[:,body]+=sign*a[19,body]*impulse
                if a[19,body]>0:wr[:,body]+=world(a,body,30)@np.cross(-sign*normal*a[20,body],sign*impulse)
            contact_records.append((i,j,normal,ln,lt,target,mu,kn))
        for i,j,normal,ln,lt,target,mu,kn in contact_records:
            # KKT is evaluated at the solved configuration, before orientation
            # advection changes angular velocity for a non-isotropic inertia.
            u=b[3:6,i].astype(float)+np.cross(wr[:,i],-normal*a[20,i])
            if j<self.n:u-=b[3:6,j]+np.cross(wr[:,j],normal*a[20,j])
            vnormal=u@normal
            bound=lambda z:0 if a[19,z]==0 else np.max(np.sum(np.abs(tensor(a,z,30)),axis=1))
            kt=kn+float(a[20,i])**2*bound(i)+(float(a[20,j])**2*bound(j) if j<self.n else 0)
            rn=abs(ln-max(0.,ln-(vnormal-target)/kn))*kn
            rt=np.linalg.norm(lt-project(lt-(u-vnormal*normal)/kt,float(mu)*ln))*kt
            tol=64*U*max(.001,abs(target),np.linalg.norm(b[3:6,i]),np.linalg.norm(b[3:6,j]) if j<self.n else 0)
            assert ln>=0 and rn<=tol*1.0001 and rt<=tol*1.0001 and abs(lt@normal)<1e-10,('KKT',rn,rt,tol)
            worst=max(worst,rn,rt)
        assert np.allclose(b[3:6],vr,rtol=8*U,atol=2e-7),'independent impulse reconstruction: v'
        for i in range(self.n):
            if a[19,i]>0:
                expected_l=world(a,i,24)@wr[:,i];observed_l=world(b,i,24)@b[10:13,i]
                assert np.allclose(observed_l,expected_l,rtol=16*U,atol=2e-7),'independent angular momentum reconstruction'
        expected=a[:3].astype(float)+dt*b[3:6]
        assert np.allclose(b[:3],expected,rtol=3*U,atol=2e-7),'xyz integration'
        # Independent Rodrigues orientation oracle; no shader quaternion helper.
        for i in range(self.n):
            w=wr[:,i];angle=np.linalg.norm(w)*dt
            if a[19,i]>0 and angle>0:
                axis=w/np.linalg.norm(w);x,y,z=axis;K=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
                step=np.eye(3)+math.sin(angle)*K+(1-math.cos(angle))*(K@K)
                assert np.max(np.abs(rotation(b[6:10,i])-step@rotation(a[6:10,i])))<8*U,'3D quaternion integration'
        # Independent O(N^2) contact completeness oracle only for small cases.
        for i in range(self.n):
            for j in range(i+1,self.n):
                if a[19,i]+a[19,j]==0:continue
                delta=a[:3,i].astype(float)-a[:3,j];d=np.linalg.norm(delta);normal=delta/d;gap=d-a[20,i]-a[20,j];vn=(vf[:,i]-vf[:,j])@normal
                if d<=cell:assert (i,j) in seen,('missing reachable pair',i,j)
            if a[19,i]>0:
                for j,raw_plane in enumerate(self.planes):
                    pl=raw_plane.astype(float);pl/=np.linalg.norm(pl[:3]);gap=pl[:3]@a[:3,i]-pl[3]-a[20,i];vn=vf[:,i]@pl[:3]
                    if gap<=cell*.5-a[20,i]:assert (i,self.n+j) in seen
        self.worst_residual=worst
    def close(self):
        if self.ptr:assert DLL.ph3_close(self.ptr),'unsafe teardown';self.ptr=None
    def __enter__(self):return self
    def __exit__(self,*args):self.close()

def axes():
    for direction in np.vstack([np.eye(3),[1,2,-3]]):
        a=soa(1);a[3:6,0]=direction;a[10:13,0]=direction
        with GPU(a) as p:
            p.step();assert np.allclose(p.state[:3,0],direction/128,atol=1e-8),'independent xyz motion'
        a=soa(1)
        with GPU(a) as p:
            p.step(g=direction);assert np.allclose(p.state[3:6,0],direction/128,atol=1e-8),'independent gravity axes'
        a=soa(2);a[:3,1]=[10,10,10];a[3:6,0]=direction;a[13:16,0]=[.2,-.4,.6];a[16:19,0]=[.01,.02,-.03]
        with GPU(a) as p:
            p.step(g=(.1,-.3,.2));assert np.all(np.abs(p.state[:3,0])>0);assert np.linalg.norm(p.state[6:9,0])>0
    # Non-diagonal tensor in a rotated body frame, independent Euler equation.
    a=soa(1);I=np.array([[.04,.004,.002],[.004,.05,-.003],[.002,-.003,.06]]);inv=np.linalg.inv(I)
    for base,m in [(24,I),(30,inv)]:a[base:base+6,0]=[m[0,0],m[1,1],m[2,2],m[0,1],m[0,2],m[1,2]]
    a[6:10,0]=[0,math.sin(.3),0,math.cos(.3)];a[10:13,0]=[.2,.3,-.1];a[16:19,0]=[.01,-.02,.03]
    with GPU(a) as p:p.step(dt=.001)

def impacts():
    results=[]
    for direction in np.vstack([np.eye(3),np.array([1,2,3])/math.sqrt(14)]):
        direction=direction/np.linalg.norm(direction)
        for friction in [0.,.35]:
            a=soa(2);a[:3,0]=-.25*direction;a[:3,1]=.25*direction
            # Correct roundoff in oblique touching input is handled by bias bounds.
            tangent=np.cross(direction,[0,1,0] if abs(direction[1])<.9 else [1,0,0]);tangent/=np.linalg.norm(tangent)
            a[3:6,0]=direction+.4*tangent;a[3:6,1]=-direction;a[21]=.8;a[22]=friction
            p0,l0=momentum(a);e0=energy(a)
            with GPU(a) as p:
                r=p.step();p1,l1=momentum(p.state)
                assert np.allclose(p0,p1,atol=2e-6) and np.allclose(l0,l1,atol=2e-6),'linear/angular momentum'
                assert energy(p.state)<=e0+3e-6,'passive energy increase'
                if friction:assert np.linalg.norm(p.state[10:13])>.1,'missing friction spin'
                if friction==0:assert abs((p.state[3:6,0]-p.state[3:6,1])@direction+1.6)<2e-5,'restitution impulse'
                results.append(dict(contacts=r.contacts,residual=p.worst_residual,energy_before=e0,energy_after=energy(p.state)))
    # Unequal mass and static sphere impulse transfer.
    for mass in [0,3]:
        a=soa(2);a[0]=[-.25,.25];a[3,0]=2;set_mass(a,1,mass);a[22]=0;a[21]=1
        with GPU(a) as p:
            p.step();expected=-2 if mass==0 else -1
            assert abs(p.state[3,0]-expected)<2e-6
            if mass==0:assert np.array_equal(p.state[:,1],a[:,1])
    a=soa(2);a[0]=[-.125,.375];a[20]=[.125,.375];a[3:6,0]=[1,.4,-.2]
    for i in range(2):set_mass(a,i,i+1)
    p0,l0=momentum(a);e0=energy(a)
    with GPU(a) as p:
        p.step();p1,l1=momentum(p.state);assert np.allclose(p0,p1,atol=3e-6) and np.allclose(l0,l1,atol=3e-6);assert energy(p.state)<=e0+3e-6
    a=soa(2);a[0]=[-.25,.25];a[3:6,0]=[.6,2,3];a[22]=.01
    p0,l0=momentum(a);e0=energy(a)
    with GPU(a) as p:
        p.step();p1,l1=momentum(p.state)
        assert np.allclose(p0,p1,atol=3e-6) and np.allclose(l0,l1,atol=3e-6)
        assert energy(p.state)<=e0+3e-6
        assert abs((p.state[3,0]-p.state[3,1])+.48)<2e-5,'grazing normal restitution'
    return results

def planes_and_rest():
    for normal in np.vstack([np.eye(3),np.array([1,2,-3])/math.sqrt(14)]):
        normal=normal/np.linalg.norm(normal);a=soa(1);a[:3,0]=normal*.25;a[3:6,0]=-normal*2+np.cross(normal,[.3,.2,.1]);a[21]=.7
        with GPU(a,[list(normal)+[0]]) as p:
            p.step();assert p.state[3:6,0]@normal>1.3999;assert energy(p.state)<=energy(a)+2e-6
    normal=np.array([1.,-2.,3.]);normal/=np.linalg.norm(normal);a=soa(1);a[:3,0]=normal*2.25;a[3:6,0]=-normal*2
    with GPU(a,[list(normal)+[2.]]) as p:p.step()
    a=soa(1);a[1]=.25;a[21]=0
    with GPU(a,[[0,1,0,0]]) as p:
        for _ in range(48):p.step(g=(0,-9.81,0))
        assert p.state[23,0]==32 and abs(p.state[1,0]-.25)<1e-6,'rest/sleep'
        edited=p.state.copy();edited[13,0]=2;p.seed(edited);r=p.step(g=(0,-9.81,0));assert r.tick==49,'edit reset the global clock';assert p.state[23,0]==0 and p.state[3,0]>0,'force wake'
    a=soa(1);a[1]=.25;a[10:13,0]=[1,2,3];a[21]=0;e0=energy(a)
    with GPU(a,[[0,1,0,0]]) as p:
        p.step(g=(0,-9.81,0));assert energy(p.state)<=e0+2e-6;assert np.linalg.norm(p.state[3:6,0])>0,'spin-to-translation friction'
    # Resolve small initial overlap and reject insufficient iteration budget.
    a=soa(2);a[0]=[-.249,.249];a[21]=0
    with GPU(a) as p:p.step();assert p.state[0,1]-p.state[0,0]>=.5-2e-6

def grazing_and_multisphere():
    a=soa(2);a[:3,1]=[.51,0,0];a[4,0]=2
    with GPU(a) as p:p.step();assert np.array_equal(p.state[3:6],a[3:6]),'grazing noncontact'
    # Genuine xyz cluster: six isolated oblique impacts, distinct normals and spin.
    a=soa(12)
    for pair in range(6):
        axis=np.array([1+pair,2-pair,.5+pair]);axis/=np.linalg.norm(axis);center=np.array([pair*4.,pair%2*4.,pair%3*4.]);a[:3,2*pair]=center-.25*axis;a[:3,2*pair+1]=center+.25*axis;a[3:6,2*pair]=axis+np.cross(axis,[.1,.2,.3]);a[3:6,2*pair+1]=-axis
    with GPU(a) as p:
        initial=a[:13].T.tolist();frames=[]
        for _ in range(5):
            r=p.step();frames.append({'tick':r.tick,'contacts':r.contacts,'state_px_py_pz_vx_vy_vz_qx_qy_qz_qw_wx_wy_wz':p.state[:13].T.tolist(),'independent_cpu_oracle':'PASS'})
        assert np.linalg.norm(p.state[10:13])>.1
        (E/'demo.json').write_text(json.dumps({'description':'12 spheres, six differently oriented 3D collisions, actual accepted GPU states','initial':initial,'frames':frames},indent=2))
    # One coupled tetrahedral cluster (six contacts, degree three), not just pairs.
    a=soa(4);a[:3]=np.array([[1,1,-1,-1],[1,-1,1,-1],[1,-1,-1,1]])*(.5/math.sqrt(8));a[3:6]=-a[:3]*2;a[21]=.8
    p0,l0=momentum(a);e0=energy(a)
    with GPU(a,iterations=256) as p:
        r=p.step();assert r.contacts==6 and r.max_degree==3
        p1,l1=momentum(p.state);assert np.allclose(p0,p1,atol=3e-6) and np.allclose(l0,l1,atol=3e-6)
        assert energy(p.state)<=e0+3e-6
    a=soa(2);a[0]=[-.25,.25];a[3:6,0]=[1,.2,.3];a[3:6,1]=[-1,-.1,.2]
    for i in range(2):
        I=np.array([[.03,.002,.001],[.002,.04,-.001],[.001,-.001,.05]]);inv=np.linalg.inv(I)
        for base,m in [(24,I),(30,inv)]:a[base:base+6,i]=[m[0,0],m[1,1],m[2,2],m[0,1],m[0,2],m[1,2]]
        a[6:10,i]=[0,math.sin(.2+i*.1),0,math.cos(.2+i*.1)]
    p0,l0=momentum(a);e0=energy(a)
    with GPU(a) as p:
        p.step(dt=1/1024);p1,l1=momentum(p.state)
        assert np.allclose(p0,p1,atol=3e-6) and np.allclose(l0,l1,atol=3e-6),'tensor contact momentum'
        assert energy(p.state)<=e0+3e-6
    # A newly moving middle sphere must not tunnel into an initially stationary,
    # positively separated third sphere after receiving the first impulse.
    a=soa(3);a[0]=[0,.5,1.005];a[3,0]=2;a[21:23]=0
    with GPU(a,iterations=256) as p:
        p.step();assert p.state[3,2]>0,'missed impulse-induced contact'
        assert np.min(np.diff(p.state[0]))>=.5-2e-6

def rejection_and_snapshots():
    a=soa(2);a[0]=[-.25,.25];a[3]=[1,-1]
    with GPU(a) as p:
        for field,value in [(0,float('nan')),(6,2.),(20,-1.),(30,0.)]:
            invalid=p.state.copy();invalid[field,0]=value
            assert not DLL.ph3_seed(p.ptr,invalid.ctypes.data,p.planes.ctypes.data,len(p.planes)),'invalid edit accepted'
            assert np.array_equal(p.read(),p.state),'invalid seed changed accepted state'
        before=p.read().tobytes();p.step(inject=1,accept=False);assert p.read().tobytes()==before
        p.step(cell=.1,accept=False)
        leases=[]
        for _ in range(3):
            lease=Lease();assert DLL.ph3_acquire(p.ptr,C.byref(lease));leases.append(lease)
            if len(leases)<3:p.step()
        result=Result();g=np.zeros(3,np.float32);assert not DLL.ph3_tick(p.ptr,1/128,g.ctypes.data,2.,0,C.byref(result)),'missing bounded backpressure'
        assert not DLL.ph3_close(p.ptr),'closed held snapshot'
        for lease in leases:assert DLL.ph3_release(p.ptr,C.byref(lease))
        p.step()
        assert not DLL.ph3_tick(p.ptr,1/64,g.ctypes.data,2.,0,C.byref(result)),'changed fixed timestep accepted'
    # Deliberate capacity rejection must preserve a valid accepted generation.
    a=soa(8)
    for i in range(8):a[:3,i]=[.12*(i&1),.12*((i>>1)&1),.12*((i>>2)&1)]
    with GPU(a,capacity=2) as p:r=p.step(accept=False);assert r.error&1
    a=soa(4);a[0]=np.arange(4)*.5;a[3,0]=1;a[21]=0
    with GPU(a,iterations=1) as p:r=p.step(accept=False);assert r.error&4
    a=soa(1)
    with GPU(a) as p:assert DLL.ph3_reader_test(p.ptr),'delayed native GPU snapshot consumer'


def transactional_world_edits():
    # P10 world publication contract: staging never edits an accepted snapshot,
    # even after a failed tick. Compare bytes, tick IDs, then CPU physics oracle.
    a=soa(2);a[0]=[-.25,.25];a[3]=[1.,-1.]
    with GPU(a) as p:
        before=p.read().tobytes()
        edited=a.copy();edited[3,0]=1.5
        assert DLL.ph3_stage(p.ptr,edited.ctypes.data),'stage rejected valid candidate'
        assert p.read().tobytes()==before,'stage modified accepted state'
        result=Result();g=np.zeros(3,dtype=np.float32)
        assert DLL.ph3_tick(p.ptr,np.float32(1/128),g.ctypes.data,np.float32(2.),1,C.byref(result))
        assert result.error&16 and result.published==0,'injected failure published'
        assert p.read().tobytes()==before,'rejected tick exposed staged state'
        assert DLL.ph3_drop_stage(p.ptr),'could not discard rejected candidate'
        assert DLL.ph3_stage(p.ptr,edited.ctypes.data)
        assert DLL.ph3_tick(p.ptr,np.float32(1/128),g.ctypes.data,np.float32(2.),0,C.byref(result))
        assert not result.error and result.published==2 and result.tick==1
        after=p.read()
        p.check(edited,after,float(np.float32(1/128)),g,result,2.)
        p.state=after
        assert not np.array_equal(after,a),'accepted candidate did not advance'

def native_replay():
    a=soa(4);a[:3]=np.array([[1,1,-1,-1],[1,-1,1,-1],[1,-1,-1,1]])*(.5/math.sqrt(8));a[3:6]=-a[:3]*2
    states=[]
    for _ in range(2):
        with GPU(a,iterations=256) as p:
            p.step();states.append(p.state)
    # Both runs independently passed the physical oracle. Their bitwise match is
    # an observation only, never an acceptance requirement or global guarantee.
    return {'bitwise_equal_observed':states[0].tobytes()==states[1].tobytes(),'max_numeric_difference':float(np.max(np.abs(states[0][:36].astype(float)-states[1][:36]))),'requirement':'independent numerical validity; no bitwise promise'}

def debug_validation():
    a=soa(2);a[0]=[-.25,.25];a[3:6,0]=[1,.2,.3];a[3,1]=-1
    with GPU(a,debug=True) as p:
        p.step();p.step(inject=1,accept=False)
        assert DLL.ph3_reader_test(p.ptr),'GPU-validation delayed snapshot consumer'

def stress(n):
    a=soa(n);i=np.arange(n);pair=i//2;side=i%2;axis=np.array([1.,2.,3.]);axis/=np.linalg.norm(axis)
    # 3D separated lattice. Every pair is a real two-body oblique impact.
    centers=np.vstack([pair%100,(pair//100)%100,pair//10000]).astype(np.float32)*4
    a[:3]=centers+axis[:,None]*np.where(side==0,-.25,.25);a[3:6]=axis[:,None]*np.where(side==0,1.,-1.);a[3:6,::2]+=np.cross(axis,[.2,.3,.1])[:,None]
    # Large coordinates quantize oblique gaps; use dyadic touching x pairs for
    # stress so the same physical input is representable at all populations.
    a[:3]=centers;a[0]+=np.where(side==0,-.25,.25);a[3:6]=np.array([[1.],[.2],[.3]])*np.where(side==0,1.,-1.);a[21]=.8
    e0=float(np.sum(np.sum(a[3:6].astype(float)**2,axis=0)/2));timings=[]
    start=time.perf_counter()
    with GPU(a,iterations=64,capacity=n) as p:
        adapter=DLL.ph3_adapter(p.ptr).decode();r=p.step(oracle=False)
        b=p.state
        # Independent per-pair checks in vectorized CPU double arithmetic.
        va=b[3:6,::2].astype(float);vb=b[3:6,1::2].astype(float);wa=b[10:13,::2].astype(float);wb=b[10:13,1::2].astype(float)
        assert r.contacts==n//2 and r.max_degree==1 and r.published==n
        assert np.max(np.abs(va+vb))<2e-5 and np.max(np.abs(va[0]+.8))<2e-5
        assert np.max(np.abs(wa-wb))<2e-5 and np.linalg.norm(wa)>0
        # Independent analytical Coulomb sticking impulse for two equal solid
        # spheres: kt=2+2*r^2/I=7; its magnitude is below mu*lambda_n.
        expected_v=np.array([-.8,.2-.4/7,.3-.6/7]);expected_w=np.array([0,.25*(.6/7)/.025,-.25*(.4/7)/.025])
        assert np.max(np.abs(va-expected_v[:,None]))<2e-5
        assert np.max(np.abs(wa-expected_w[:,None]))<2e-5
        assert np.max(np.abs(np.linalg.norm(b[6:10],axis=0)-1))<2e-5
        assert np.array_equal(b[36:38].view(np.uint32),a[36:38].view(np.uint32))
        e1=float(np.sum((va*va+vb*vb)/2)+.5*.025*np.sum(wa*wa+wb*wb));assert e1<=e0+1e-4*n
        assert np.min(np.linalg.norm(b[:3,::2].astype(float)-b[:3,1::2],axis=0))>=.5-2e-5
        assert np.max(np.abs(b[:3].astype(float)-centers))<.5,'pair isolation certificate'
        timings.append(list(r.phases_us))
        # Fresh copies of the same initial scene, not no-contact later ticks.
        for _ in range(2):
            p.seed(a);sample=p.step(oracle=False);assert sample.contacts==n//2
            assert np.max(np.abs(p.state[3:6,::2]-expected_v[:,None]))<2e-5
            assert np.max(np.abs(p.state[10:13,::2]-expected_w[:,None]))<2e-5
            timings.append(list(sample.phases_us))
        record={'n':n,'contacts':r.contacts,'contacts_per_body':r.contacts/n,'candidate_pairs_tested':r.candidates,'max_degree':r.max_degree,'topology':'N/2 independent 3D moving/frictional two-sphere pairs, separated xyz lattice','adapter':adapter,'gpu_phase_names':['prepare','hash','narrowphase','solve_gather','integrate','validate','publish','total'],'gpu_phases_us':timings,'gpu_total_median_us':float(np.median(np.array(timings)[:,-1])),'sample_count':3,'committed_bytes':r.committed,'energy_before':e0,'energy_after':e1,'independent_validation':'all-body analytical tangential/normal impulse and spin, pair momentum/energy/separation, identities/quaternions and all-object isolation certificate; mandatory GPU KKT checks retained','qualification':False}
    record['wall_seconds_including_init_readback_cpu_oracle']=time.perf_counter()-start
    return record

def main():
    global DLL
    parser=argparse.ArgumentParser();parser.add_argument('--stress',type=int,nargs='*');parser.add_argument('--smoke',action='store_true');args=parser.parse_args()
    E.mkdir(parents=True,exist_ok=True);DLL=library();result={'status':'FAIL','tests':[],'stress':[],'bitwise_replay':'NOT CLAIMED','qualification':False}
    try:
        cases=[axes,impacts,planes_and_rest,grazing_and_multisphere,rejection_and_snapshots,transactional_world_edits,native_replay,debug_validation]
        if args.stress is not None:cases=[]
        for case in cases:
            start=time.perf_counter();details=case();result['tests'].append({'name':case.__name__,'status':'PASS','seconds':time.perf_counter()-start,'details':details});print('PASS',case.__name__,flush=True)
        for n in args.stress or []:
            record=stress(n);result['stress'].append(record);print('PASS stress',n,'contacts',record['contacts'],'GPU us',record['gpu_phases_us'][0][-1],flush=True)
        result['status']='PASS'
    except Exception:
        result['error']=traceback.format_exc();print(result['error'],flush=True)
    finally:
        dest=E/('stress-'+('-'.join(map(str,args.stress)))+'.json' if args.stress else 'tests.json');dest.write_text(json.dumps(result,indent=2));print('RESULT',result['status'],dest,flush=True)
    return result['status']!='PASS'
if __name__=='__main__':raise SystemExit(main())
