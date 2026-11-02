#pragma once
#include <vector>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <limits>
#include <unordered_map>

// The Physics3 shader addresses a SoA field with a 32-bit byte offset, while
// D3D12 runtime buffers are at most 4 GiB. This is a representation limit,
// not an application-selected population limit.
static constexpr uint64_t G7_MAX_STATE_SLOTS = (0x100000000ull - 256) / (48ull * sizeof(float));
static constexpr uint64_t G7_MAX_CONTACT_SLOTS = (0x100000000ull - 256) / 128ull;

struct G7Config {
 uint64_t count=512, contactBudget=0; // 0: auto-sized to workload
 uint32_t batch=32, iterations=1024, placementAttempts=10000;
 int scene=2, seed=7, density=1;
 float radius=.30f, mass=1, radiusSpread=.03f, massSpread=.1f;
 float gravity=-19.62f, gravityOther=0, gravityX=0, gravityY=0, spawnHz=4;
 float restitution=-1, friction=-1, initialVz=-7, cell=0; // -1/0: per-scene native defaults
 float cubeSpeed=.7f, beltClosingSpeed=.6f, beltSpin=.025f;
 float beltMajorRadius=0, beltMinorRadius=0; // zero = scale with population
 float emitterWidthX=36, emitterWidthY=24, emitterHeight=28;
 uint32_t contacts() const {
  uint64_t desired=contactBudget;
  if(!desired) {
   if(count>(G7_MAX_CONTACT_SLOTS/12)) throw std::runtime_error("Auto contact budget exceeds the native 4 GiB buffer representation; set a smaller explicit budget");
   desired=std::max<uint64_t>(65536,count*12);
  }
  if(!desired||desired>G7_MAX_CONTACT_SLOTS) throw std::runtime_error("Contact budget exceeds native D3D12 32-bit byte-addressable buffer capacity");
  return uint32_t(desired);
 }
 void validate() const {
  if(!count||count>G7_MAX_STATE_SLOTS) throw std::runtime_error("Body count exceeds the native 4 GiB, 32-bit SoA address limit (not a UI cap)");
  if(!batch||batch>count) throw std::runtime_error("Spawn batch must be positive and not exceed body count");
  if(!iterations||iterations>4096) throw std::runtime_error("Solver iterations must be within the supported native solver envelope (1..4096)");
  if(!placementAttempts) throw std::runtime_error("Placement attempts must be positive");
  if(scene<0||scene>2||density<0||density>1) throw std::runtime_error("Unknown scene or density mode");
  auto finite=[](float x){return std::isfinite(x);};
  if(!finite(radius)||!finite(radiusSpread)||!finite(mass)||!finite(massSpread)||
     !finite(gravity)||!finite(gravityOther)||!finite(gravityX)||!finite(gravityY)||!finite(spawnHz)||
     !finite(restitution)||!finite(friction)||!finite(initialVz)||!finite(cell)||
     !finite(cubeSpeed)||!finite(beltClosingSpeed)||!finite(beltSpin)||
     !finite(beltMajorRadius)||!finite(beltMinorRadius)||!finite(emitterWidthX)||
     !finite(emitterWidthY)||!finite(emitterHeight))
   throw std::runtime_error("Scene settings must be finite numbers");
  if(radius<=0||radiusSpread<0||radiusSpread>=1||mass<=0||massSpread<0||massSpread>=1||
     (restitution<0&&restitution!=-1)||restitution>1||(friction<0&&friction!=-1)||spawnHz<=0||cell<0||beltMajorRadius<0||beltMinorRadius<0||emitterWidthX<=0||emitterWidthY<=0)
   throw std::runtime_error("Invalid physical parameter: radius/mass/cell/rate must be positive, spread in [0,1), restitution in [0,1], friction >=0");
  contacts();
 }
};

struct G7Scene {
 uint32_t capacity=0;
 std::vector<float> authored;
 float extent=6;
 uint32_t rng=7;
 float random(){rng^=rng<<13;rng^=rng>>17;rng^=rng<<5;return float(rng&0xffffff)/16777216.f;}
 float &at(std::vector<float>&s,uint32_t f,uint32_t i){return s[size_t(f)*capacity+i];}
 struct Cell {
  int64_t x,y,z;
  bool operator==(const Cell &r)const{return x==r.x&&y==r.y&&z==r.z;}
 };
 struct CellHash {
  size_t operator()(const Cell &c) const noexcept {
   uint64_t h=1469598103934665603ull;
   for(auto v:{uint64_t(c.x),uint64_t(c.y),uint64_t(c.z)}){h^=v;h*=1099511628211ull;}
   return size_t(h);
  }
 };
 void body(std::vector<float>&s,uint32_t i,float x,float y,float z,float vx,float vy,float vz,float radius,float mass,int belt,float restitution,float friction){
  at(s,0,i)=x;at(s,1,i)=y;at(s,2,i)=z;at(s,3,i)=vx;at(s,4,i)=vy;at(s,5,i)=vz;at(s,9,i)=1;at(s,19,i)=mass?1/mass:0;
  at(s,20,i)=radius;at(s,21,i)=restitution;at(s,22,i)=friction;
  float inertia=.4f*mass*radius*radius;
  for(int j=0;j<3;j++){at(s,24+j,i)=inertia;at(s,30+j,i)=mass?1/inertia:0;}
  uint32_t id=i,gen=1;memcpy(&at(s,36,i),&id,4);memcpy(&at(s,37,i),&gen,4);at(s,38,i)=float(belt);
 }
 void generate(const G7Config&c){
  c.validate();
  capacity=uint32_t(c.count);
  rng=uint32_t(c.seed)|1;
  if(size_t(capacity)>std::vector<float>().max_size()/48) throw std::runtime_error("Scene exceeds CPU addressable storage");
  authored.assign(size_t(48)*capacity,0);
  uint32_t side=uint32_t(std::ceil(std::cbrt(double(c.count))));
  while(uint64_t(side)*side*side<c.count)++side;
  float pitch=c.radius*(c.density==0?2.8f:2.3f),half=(side-1)*pitch*.5f;
  float scale=std::cbrt(float(c.count)/1000),major=c.beltMajorRadius>0?c.beltMajorRadius:7*scale*(c.density==0?1.15f:1),minor=c.beltMinorRadius>0?c.beltMinorRadius:2.4f*scale*(c.density==0?1.15f:1),center=minor+1.8f*c.radius;
  extent=c.scene==2?24:(c.scene?major+minor+1:half+2);
  // Cell hashing replaces the old O(N^2) torus-placement scan.
  float cellWidth=2*c.radius*(1+c.radiusSpread)+.00001f;
  std::unordered_map<Cell,std::vector<uint32_t>,CellHash> occupied;
  auto cellOf=[&](float x,float y,float z)->Cell{return {int64_t(std::floor(double(x)/cellWidth)),int64_t(std::floor(double(y)/cellWidth)),int64_t(std::floor(double(z)/cellWidth))};};
  float materialR=c.restitution<0?(c.scene==2?.92f:.65f):c.restitution;
  float materialMu=c.friction<0?(c.scene==2?0.f:.3f):c.friction;
  for(uint32_t i=0;i<capacity;i++){
   float r=c.radius*(1+c.radiusSpread*(2*random()-1)),m=c.mass*(1+c.massSpread*(2*random()-1));
   if(c.scene==2){
    uint32_t columns=uint32_t(std::ceil(std::sqrt(double(c.batch)))),emitter=i%c.batch;
    float middle=(columns-1)*.5f;
    float dx=(emitter%columns-middle)*(c.emitterWidthX*(c.density==0?1.15f:1)/std::max(1u,columns-1));
    float dy=(emitter/columns-middle)*(c.emitterWidthY*(c.density==0?1.15f:1)/std::max(1u,columns-1));
    body(authored,i,dx,dy,c.emitterHeight+(i/c.batch%2)*.05f,(random()-.5f)*.4f,(random()-.5f)*.4f,c.initialVz,r,m,0,materialR,materialMu);
   }else if(c.scene==0){
    uint32_t x=i%side,y=(i/side)%side,z=uint32_t(uint64_t(i)/(uint64_t(side)*side));
    body(authored,i,x*pitch-half,y*pitch-half,z*pitch-half,x%2?-c.cubeSpeed:c.cubeSpeed,0,0,r,m,0,materialR,materialMu);
   }else{
    int belt=i>=uint32_t((c.count+1)/2);
    bool found=false;
    for(uint32_t attempt=0;attempt<c.placementAttempts&&!found;attempt++){
     float phi=random()*6.2831853f,theta=random()*6.2831853f,rho=minor*std::sqrt(random());
     float x=(belt?center:-center)+rho*std::cos(theta),ring=major+rho*std::sin(theta),y=ring*std::cos(phi),z=ring*std::sin(phi);
     Cell key=cellOf(x,y,z);found=true;
     for(int dz=-1;dz<=1&&found;dz++)for(int dy=-1;dy<=1&&found;dy++)for(int dx=-1;dx<=1&&found;dx++){
      auto hit=occupied.find({key.x+dx,key.y+dy,key.z+dz});
      if(hit==occupied.end())continue;
      for(uint32_t j:hit->second){
       float a=x-at(authored,0,j),b=y-at(authored,1,j),d=z-at(authored,2,j),rr=r+at(authored,20,j)+.00001f;
       if(a*a+b*b+d*d<rr*rr){found=false;break;}
      }
     }
     if(found){
      float spin=belt?-c.beltSpin:c.beltSpin;
      body(authored,i,x,y,z,belt?-c.beltClosingSpeed:c.beltClosingSpeed,-spin*z,spin*y,r,m,belt,materialR,materialMu);
      occupied[key].push_back(i);
     }
    }
    if(!found)throw std::runtime_error("Scene admission: torus packing exhausted at configurable placement attempt budget; reduce packing or increase attempts");
   }
  }
 }
 std::vector<float> planes(int scene){if(scene!=2)return {};return {0,0,1,-8, .6f,0,.8f,-9.6f, -.6f,0,.8f,-9.6f, 0,1,0,-16, 0,-1,0,-16};}
 std::vector<float> initial(uint32_t active,bool moving){
  if(active>capacity)throw std::runtime_error("Scene active count exceeds physical allocation");
  auto s=authored;
  for(uint32_t i=0;i<capacity;i++){
   if(i>=active){for(uint32_t f=0;f<48;f++)at(s,f,i)=0;body(s,i,1000+4*float(i%1000),1000+4*float((i/1000)%1000),1000+4*float(i/1000000),0,0,0,.1f,0,0,.92f,0);}
   else if(!moving){at(s,19,i)=0;for(uint32_t f=3;f<6;f++)at(s,f,i)=0;}
  }
  return s;
 }
};
