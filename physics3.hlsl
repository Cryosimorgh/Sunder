// Native 3D module; the planar shaders/layout remain byte-for-byte untouched.
ByteAddressBuffer source : register(t0);
RWByteAddressBuffer trial : register(u1);
RWByteAddressBuffer grid : register(u2);
RWByteAddressBuffer contacts : register(u3);
RWByteAddressBuffer control : register(u4);
RWByteAddressBuffer freeState : register(u5);
RWByteAddressBuffer accepted : register(u0);
RWByteAddressBuffer planes : register(u6);
cbuffer Config : register(b0) {
 uint n,buckets,contactCapacity,iterations,dtBits,gxBits,gyBits,gzBits;
 uint cellBits,flags,planeCount,tick,stage,sleepFrames,unused0,unused1;
};
static const uint NONE=0xffffffffu;
uint idx(uint3 g,uint lane){return (g.x+65535u*g.y)*256u+lane;}
float sf(uint i,uint f){return asfloat(source.Load(4*(f*n+i)));}
float tf(uint i,uint f){return asfloat(trial.Load(4*(f*n+i)));}
void put(uint i,uint f,float v){trial.Store(4*(f*n+i),asuint(v));}
double3 sv(uint i,uint f){return double3(sf(i,f),sf(i,f+1),sf(i,f+2));}
double3 tv(uint i,uint f){return double3(tf(i,f),tf(i,f+1),tf(i,f+2));}
void pv(uint i,uint f,double3 v){put(i,f,float(v.x));put(i,f+1,float(v.y));put(i,f+2,float(v.z));}
double rd(RWByteAddressBuffer b,uint o){uint2 w=b.Load2(o);return asdouble(w.x,w.y);}
void wd(RWByteAddressBuffer b,uint o,double v){uint lo,hi;asuint(v,lo,hi);b.Store2(o,uint2(lo,hi));}
double3 cr(uint o){return double3(rd(contacts,o),rd(contacts,o+8),rd(contacts,o+16));}
void cw(uint o,double3 v){wd(contacts,o,v.x);wd(contacts,o+8,v.y);wd(contacts,o+16,v.z);}
double3 fv(uint i,uint f){uint o=48*i+8*f;return double3(rd(freeState,o),rd(freeState,o+8),rd(freeState,o+16));}
void fw(uint i,uint f,double3 v){uint o=48*i+8*f;wd(freeState,o,v.x);wd(freeState,o+8,v.y);wd(freeState,o+16,v.z);}
double ddot(double3 a,double3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
double ddot(double4 a,double4 b){return a.x*b.x+a.y*b.y+a.z*b.z+a.w*b.w;}
double3 dcross(double3 a,double3 b){return double3(a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x);}
int floorInt(double x){int v=int(x);return x<double(v)?v-1:v;}
int3 cellOf(double3 p){double3 v=p/double(asfloat(cellBits));return int3(floorInt(v.x),floorInt(v.y),floorInt(v.z));}
#include "physics-math.hlsl"
double norm(double3 v){return dsqrt(ddot(v,v));}
double4 planeEq(uint i){double4 p=double4(asfloat(planes.Load4(16*i)));return p/norm(p.xyz);}
double4 sq(uint i){return double4(sf(i,6),sf(i,7),sf(i,8),sf(i,9));}
double3 rotate(double4 q,double3 v){return v+2*dcross(q.xyz,dcross(q.xyz,v)+q.w*v);}
double3 tensor(uint i,uint base,double3 v){double a=sf(i,base),b=sf(i,base+1),c=sf(i,base+2),d=sf(i,base+3),e=sf(i,base+4),f=sf(i,base+5);return double3(a*v.x+d*v.y+e*v.z,d*v.x+b*v.y+f*v.z,e*v.x+f*v.y+c*v.z);}
double3 worldTensor(uint i,uint base,double3 v){double4 q=sq(i);return rotate(q,tensor(i,base,rotate(double4(-q.xyz,q.w),v)));}
double3 invI(uint i,double3 v){return sf(i,19)>0?worldTensor(i,30,v):double3(0,0,0);}
double invBound(uint i){if(sf(i,19)==0)return 0;return max(sf(i,30)+abs(sf(i,33))+abs(sf(i,34)),max(sf(i,31)+abs(sf(i,33))+abs(sf(i,35)),sf(i,32)+abs(sf(i,34))+abs(sf(i,35))));}
uint nextOffset(){return 4*buckets;}
uint cellOffset(){return 4*buckets+4*n;}
uint degreeOffset(){return 4*buckets+16*n;}
uint headOffset(){return 4*buckets+20*n;}
uint hash(int3 c){return (uint(c.x)*73856093u^uint(c.y)*19349663u^uint(c.z)*83492791u)&(buckets-1);}
void fail(uint code){control.InterlockedOr(0,code);}
bool stopped(){return control.Load(0)!=0;}
double tolerance(double3 a,double3 b,double target){return 64.0*1.1920928955078125e-7*max(.001,max(abs(target),max(norm(a),norm(b))));}
[numthreads(256,1,1)]void p3_clear(uint3 g:SV_GroupID,uint lane:SV_GroupIndex){uint i=idx(g,lane);if(i<buckets)grid.Store(4*i,NONE);if(i<n){grid.Store(headOffset()+4*i,NONE);grid.Store(degreeOffset()+4*i,0);}if(i<64)control.Store(4*i,0);}
[numthreads(256,1,1)]void p3_prepare(uint3 g:SV_GroupID,uint lane:SV_GroupIndex){uint i=idx(g,lane);if(i>=n)return;for(uint f=0;f<48;f++)trial.Store(4*(f*n+i),source.Load(4*(f*n+i)));double dt=asfloat(dtBits),mass=sf(i,19),r=sf(i,20);double4 q=sq(i);bool valid=true;for(uint f=0;f<36;f++)if(!isfinite(sf(i,f)))valid=false;
 if(!valid||mass<0||r<=0||sf(i,21)<0||sf(i,21)>1||sf(i,22)<0||abs(ddot(q,q)-1)>2e-5||sf(i,23)<0){fail(2);return;}
 if(mass>0){double a=sf(i,24),b=sf(i,25),c=sf(i,26),d=sf(i,27),e=sf(i,28),f=sf(i,29);if(a<=0||a*b-d*d<=0||a*b*c+2*d*e*f-a*f*f-b*e*e-c*d*d<=0){fail(2);return;}
  for(uint k=0;k<3;k++){double3 unit=double3(k==0,k==1,k==2);if(norm(tensor(i,24,tensor(i,30,unit))-unit)>2e-5){fail(2);return;}}
 }
 double3 v=sv(i,3),w=sv(i,10);if(mass>0){v+=dt*(double3(asfloat(gxBits),asfloat(gyBits),asfloat(gzBits))+mass*sv(i,13));w+=dt*invI(i,sv(i,16));}
 if(mass==0&&(norm(v)>0||norm(w)>0)){fail(2);return;}
 double cell=asfloat(cellBits);if(!isfinite(cell)||cell<=0||2*r+2*norm(v)*dt>cell||any(abs(sv(i,0)/cell)>1000000)){fail(2);return;}
 pv(i,3,v);pv(i,10,w);fw(i,0,v);fw(i,3,w);
 if(i==0)for(uint p=0;p<planeCount;p++){float4 pl=asfloat(planes.Load4(16*p));if(any(!isfinite(pl))||abs(ddot(pl.xyz,pl.xyz)-1)>2e-6)fail(2);}
}
[numthreads(256,1,1)]void p3_hash(uint3 g:SV_GroupID,uint lane:SV_GroupIndex){uint i=idx(g,lane);if(i>=n||stopped())return;int3 c=cellOf(sv(i,0));grid.Store3(cellOffset()+12*i,asuint(c));uint prev;grid.InterlockedExchange(4*hash(c),i,prev);grid.Store(nextOffset()+4*i,prev);}
void append(uint a,uint b,double3 normal,double gap){double ma=sf(a,19),mb=b<n?sf(b,19):0,kn=ma+mb;if(kn==0)return;double3 va=fv(a,0),vb=b<n?fv(b,0):double3(0,0,0);double vn=ddot(va-vb,normal),dt=asfloat(dtBits);double reach=b<n?double(asfloat(cellBits))-sf(a,20)-sf(b,20):double(asfloat(cellBits))*.5-sf(a,20);if(gap>reach)return;
 double restitution=b<n?min(sf(a,21),sf(b,21)):sf(a,21);double target=gap>0&&vn>=-gap/dt?-gap/dt:max(-gap/dt,vn<-.5?-restitution*vn:0.0);
 uint k;control.InterlockedAdd(4,1,k);if(k>=contactCapacity){fail(1);return;}uint o=128*k,pa,pb=NONE;grid.InterlockedExchange(headOffset()+4*a,k,pa);if(b<n)grid.InterlockedExchange(headOffset()+4*b,k,pb);contacts.Store4(o,uint4(a,b,pa,pb));wd(contacts,o+16,0);cw(o+24,double3(0,0,0));wd(contacts,o+48,target);cw(o+56,normal);wd(contacts,o+80,gap);wd(contacts,o+88,b<n?min(sf(a,22),sf(b,22)):sf(a,22));wd(contacts,o+96,kn);double ra=sf(a,20),rb=b<n?sf(b,20):0;wd(contacts,o+104,kn+ra*ra*invBound(a)+(b<n?rb*rb*invBound(b):0));uint old;grid.InterlockedAdd(degreeOffset()+4*a,1,old);if(b<n)grid.InterlockedAdd(degreeOffset()+4*b,1,old);}
[numthreads(256,1,1)]void p3_contacts(uint3 g:SV_GroupID,uint lane:SV_GroupIndex){uint i=idx(g,lane);if(i>=n||stopped())return;int3 cell=asint(grid.Load3(cellOffset()+12*i));double3 p=sv(i,0);for(int z=-1;z<=1;z++)for(int y=-1;y<=1;y++)for(int x=-1;x<=1;x++){int3 c=cell+int3(x,y,z);uint j=grid.Load(4*hash(c)),hops=0;while(j!=NONE){if(j>=n||hops++>=n){fail(16);return;}if(j>i&&all(asint(grid.Load3(cellOffset()+12*j))==c)){control.InterlockedAdd(24,1);double3 delta=p-sv(j,0);double d=norm(delta),r=sf(i,20)+sf(j,20);if(d==0){fail(2);return;}append(i,j,delta/d,d-r);}j=grid.Load(nextOffset()+4*j);}}
 if(sf(i,19)>0)for(uint plane=0;plane<planeCount;plane++){double4 pl=planeEq(plane);append(i,n+plane,pl.xyz,ddot(p,pl.xyz)-pl.w-sf(i,20));}}
double3 relative(uint a,uint b,double3 normal){double3 ra=-normal*double(sf(a,20)),u=tv(a,3)+dcross(tv(a,10),ra);if(b<n)u-=tv(b,3)+dcross(tv(b,10),normal*double(sf(b,20)));return u;}
double3 solvedRelative(uint a,uint b,double3 normal){double3 u=tv(a,3)+dcross(fv(a,3),-normal*double(sf(a,20)));if(b<n)u-=tv(b,3)+dcross(fv(b,3),normal*double(sf(b,20)));return u;}
double3 projectT(double3 t,double cap){double length=norm(t);return length>cap&&length>0?t*(cap/length):t;}
[numthreads(256,1,1)]void p3_solve(uint3 g:SV_GroupID,uint lane:SV_GroupIndex){uint k=idx(g,lane);if(k>=min(control.Load(4),contactCapacity)||stopped())return;uint o=128*k,a=contacts.Load(o),b=contacts.Load(o+4);double3 normal=cr(o+56),u=relative(a,b,normal);double vn=ddot(u,normal),ln=rd(contacts,o+16),kn=rd(contacts,o+96),target=rd(contacts,o+48),kt=rd(contacts,o+104);uint degree=max(grid.Load(degreeOffset()+4*a),b<n?grid.Load(degreeOffset()+4*b):0);double relax=1.0/double(max(1u,degree));double next=max(0.0,ln-relax*(vn-target)/kn);double3 lt=cr(o+24);lt=projectT(lt-relax*(u-vn*normal)/kt,rd(contacts,o+88)*next);wd(contacts,o+16,next);cw(o+24,lt);}
[numthreads(256,1,1)]void p3_gather(uint3 g:SV_GroupID,uint lane:SV_GroupIndex){uint i=idx(g,lane);if(i>=n||stopped())return;double3 v=fv(i,0),w=fv(i,3);uint k=grid.Load(headOffset()+4*i),hops=0;while(k!=NONE){if(k>=contactCapacity||hops++>=contactCapacity){fail(16);return;}uint o=128*k,a=contacts.Load(o),b=contacts.Load(o+4);double3 normal=cr(o+56),impulse=normal*rd(contacts,o+16)+cr(o+24);bool first=i==a;double sign=first?1:-1;double3 arm=normal*double(sf(i,20))*(-sign);v+=sign*double(sf(i,19))*impulse;w+=invI(i,dcross(arm,sign*impulse));k=contacts.Load(o+(first?8:12));}pv(i,3,v);pv(i,10,w);}
[numthreads(256,1,1)]void p3_integrate(uint3 g:SV_GroupID,uint lane:SV_GroupIndex){uint i=idx(g,lane);if(i>=n||stopped())return;if(sf(i,19)==0)return;double dt=asfloat(dtBits);pv(i,0,sv(i,0)+dt*tv(i,3));double3 w=tv(i,10);fw(i,3,w);double3 angularMomentum=worldTensor(i,24,w);double angle=norm(w)*dt;double4 q=sq(i),dq=angle>1e-12?double4(w*(double(sin(float(angle*.5)))/norm(w)),double(cos(float(angle*.5)))):double4(w*(dt*.5),1);double4 result=double4(dq.w*q.xyz+q.w*dq.xyz+dcross(dq.xyz,q.xyz),dq.w*q.w-ddot(dq.xyz,q.xyz));result/=dsqrt(ddot(result,result));for(uint f=0;f<4;f++)put(i,6+f,float(result[f]));w=rotate(result,tensor(i,30,rotate(double4(-result.xyz,result.w),angularMomentum)));pv(i,10,w);double speed=norm(tv(i,3))+norm(w);put(i,23,speed<1e-5?min(float(sleepFrames),sf(i,23)+1):0);if(speed>=1e-5)control.InterlockedAdd(28,1);}
[numthreads(256,1,1)]void p3_validate(uint3 g:SV_GroupID,uint lane:SV_GroupIndex){uint i=idx(g,lane);if(stopped())return;if(i<n){for(uint f=0;f<36;f++)if(!isfinite(tf(i,f)))fail(8);double4 q=double4(tf(i,6),tf(i,7),tf(i,8),tf(i,9));if(abs(ddot(q,q)-1)>2e-5)fail(8);if(2*sf(i,20)+2*norm(tv(i,3))*double(asfloat(dtBits))>double(asfloat(cellBits)))fail(2);uint degree=grid.Load(degreeOffset()+4*i);control.InterlockedMax(20,degree);}
 if(i<min(control.Load(4),contactCapacity)){uint o=128*i,a=contacts.Load(o),b=contacts.Load(o+4);double3 normal=cr(o+56),u=solvedRelative(a,b,normal);double vn=ddot(u,normal),ln=rd(contacts,o+16),kn=rd(contacts,o+96),kt=rd(contacts,o+104),target=rd(contacts,o+48),mu=rd(contacts,o+88);double3 lt=cr(o+24);double rn=normalResidual(vn-target,kn,ln),rt=norm(lt-projectT(lt-(u-vn*normal)/kt,mu*ln))*kt;double tol=tolerance(tv(a,3),b<n?tv(b,3):double3(0,0,0),target);if(rn>tol){control.InterlockedAdd(32,1);control.InterlockedMax(52,asuint(float(rn/tol)));}if(rt>tol){control.InterlockedAdd(36,1);control.InterlockedMax(56,asuint(float(rt/tol)));}if(!isfinite(ln)||!isfinite(rn)||!isfinite(rt)||any(!isfinite(lt))||!isfinite(target)||!isfinite(kn)||!isfinite(kt)||kn<=0||kt<=0||ln<0||rn>tol||rt>tol||norm(lt)>mu*ln+tol/kt)fail(4);
 double gap;if(b<n)gap=norm(tv(a,0)-tv(b,0))-sf(a,20)-sf(b,20);else{double4 pl=planeEq(b-n);gap=ddot(tv(a,0),pl.xyz)-pl.w-sf(a,20);}double posTol=16.0*1.1920928955078125e-7*max(1.0,norm(tv(a,0))+(b<n?norm(tv(b,0)):0));if(gap < -posTol){control.InterlockedAdd(40,1);control.InterlockedMax(60,asuint(float(-gap)));}if(!isfinite(gap)||gap < -posTol)fail(8);}
 if(i==0){if(flags!=0)fail(16);if(source.Load(192*n)!=0xbaadc0de||trial.Load(192*n)!=0xbaadc0de||grid.Load(4*buckets+24*n)!=0xbaadc0de||contacts.Load(128*contactCapacity)!=0xbaadc0de||freeState.Load(48*n)!=0xbaadc0de)fail(16);}}
[numthreads(256,1,1)]void p3_publish(uint3 g:SV_GroupID,uint lane:SV_GroupIndex){uint i=idx(g,lane);if(stopped())return;if(i<n){for(uint f=0;f<48;f++)accepted.Store(4*(f*n+i),trial.Load(4*(f*n+i)));control.InterlockedAdd(8,1);}if(i==0){accepted.Store(192*n,0xbaadc0de);control.Store(16,tick);}}
