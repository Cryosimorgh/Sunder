#pragma once
#include <vector>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <stdexcept>
// CPU authors initial conditions only. All subsequent motion is Physics3.
struct G7Config {int scene=0,count=512,batch=64,seed=7,density=1;float radius=.4f,mass=1,radiusSpread=.03f,massSpread=.1f,gravity=0,spawnHz=8;};
struct G7Scene {
 static constexpr unsigned capacity=1000;
 std::vector<float> authored;
 float extent=6;
 uint32_t rng=7;
 float random(){rng^=rng<<13;rng^=rng>>17;rng^=rng<<5;return float(rng&0xffffff)/16777216.f;}
 float &at(std::vector<float>&s,int f,int i){return s[f*capacity+i];}
 void body(std::vector<float>&s,int i,float x,float y,float z,float vx,float vy,float vz,float radius,float mass,int belt){
  at(s,0,i)=x;at(s,1,i)=y;at(s,2,i)=z;at(s,3,i)=vx;at(s,4,i)=vy;at(s,5,i)=vz;at(s,9,i)=1;at(s,19,i)=mass?1/mass:0;
  at(s,20,i)=radius;at(s,21,i)=.65f;at(s,22,i)=.3f;
  float inertia=.4f*mass*radius*radius;
  for(int j=0;j<3;j++){at(s,24+j,i)=inertia;at(s,30+j,i)=mass?1/inertia:0;}
  uint32_t id=i,gen=1;memcpy(&at(s,36,i),&id,4);memcpy(&at(s,37,i),&gen,4);at(s,38,i)=float(belt);
 }
 void generate(const G7Config&c){
  if(c.count<1||c.count>1000||c.radius<=0||c.radius>.44f)throw std::runtime_error("Scene admission: count 1..1000, radius .1..44");
  rng=uint32_t(c.seed)|1;authored.assign(48*capacity,0);
  int side=int(ceil(cbrt(double(c.count))));while(side*side*side<c.count)side++;
  float pitch=c.radius*(c.density==0?2.8f:2.3f),half=(side-1)*pitch*.5f;
  float scale=cbrtf(float(c.count)/1000),major=7*scale,minor=2.4f*scale,center=minor+1.8f*c.radius;
  extent=c.scene?major+minor+1:half+2;
  for(int i=0;i<c.count;i++){
   float r=c.radius*(1+c.radiusSpread*(2*random()-1)),m=c.mass*(1+c.massSpread*(2*random()-1));
   if(!c.scene){int x=i%side,y=i/side%side,z=i/(side*side);body(authored,i,x*pitch-half,y*pitch-half,z*pitch-half,x%2?-.7f:.7f,0,0,r,m,0);}
   else{
    int belt=i>=(c.count+1)/2;bool found=false;
    for(int attempt=0;attempt<10000&&!found;attempt++){
     float phi=random()*6.2831853f,theta=random()*6.2831853f,rho=minor*sqrtf(random());
     float x=(belt?center:-center)+rho*cosf(theta),ring=major+rho*sinf(theta),y=ring*cosf(phi),z=ring*sinf(phi);found=true;
     for(int j=0;j<i;j++){float dx=x-at(authored,0,j),dy=y-at(authored,1,j),dz=z-at(authored,2,j),rr=r+at(authored,20,j)+.00001f;if(dx*dx+dy*dy+dz*dz<rr*rr){found=false;break;}}
     if(found){float spin=belt?-.025f:.025f;body(authored,i,x,y,z,belt?-.6f:.6f,-spin*z,spin*y,r,m,belt);}
    }
    if(!found)throw std::runtime_error("Scene admission: torus packing exhausted; reduce radius");
   }
  }
 }
 std::vector<float> initial(unsigned active,bool moving){
  auto s=authored;
  for(unsigned i=0;i<capacity;i++){
   if(i>=active){for(int f=0;f<48;f++)at(s,f,i)=0;body(s,i,1000+4*float(i),1000,1000,0,0,0,.1f,0,0);}
   else if(!moving){at(s,19,i)=0;for(int f=3;f<6;f++)at(s,f,i)=0;}
  }
  return s;
 }
};
