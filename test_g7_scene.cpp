#include "g7_scene.h"
#include <cassert>
#include <cmath>
#include <cstring>
#include <iostream>
#include <stdexcept>
static bool rejects(G7Config c){
 try{G7Scene s;s.generate(c);return false;}catch(const std::exception&){return true;}
}
int main(){
 G7Config c;
 assert(c.count==512 && c.contacts()==65536);
 c.count=100001;c.batch=128;c.scene=2;
 G7Scene large;large.generate(c);
 assert(large.capacity==100001);
 assert(large.authored.size()==48ull*c.count);
 auto initial=large.initial(0,false);
 assert(initial.size()==48ull*c.count);
 for(uint32_t j: {0u,999u,1000u,99999u,100000u}){
  assert(std::isfinite(initial[j]));
  assert(initial[j]>=1000 && initial[j]<=4996);
  assert(initial[large.capacity*19ull+j]==0);
 }
 auto first=large.initial(1,true);
 assert(first[large.capacity*19ull]>0);
 c.count=G7_MAX_STATE_SLOTS+1;assert(rejects(c));
 c.count=UINT64_MAX;assert(rejects(c));
 c.count=1;c.batch=2;assert(rejects(c));
 c.batch=1;c.radius=0;assert(rejects(c));
 c.radius=.3f;c.mass=-1;assert(rejects(c));
 c.mass=1;c.radiusSpread=2;assert(rejects(c));
 c.radiusSpread=.03f;c.restitution=1.1f;assert(rejects(c));
 c.restitution=-1;c.friction=-.1f;assert(rejects(c));
 c.friction=-1;c.contactBudget=G7_MAX_CONTACT_SLOTS+1;assert(rejects(c));
 G7Config torus;torus.scene=1;torus.count=120;torus.batch=60;torus.gravity=0;
 G7Scene a,b;a.generate(torus);b.generate(torus);
 assert(a.authored==b.authored);
 for(uint32_t i=0;i<a.capacity;i++)for(uint32_t j=i+1;j<a.capacity;j++){
  double x=a.at(a.authored,0,i)-a.at(a.authored,0,j);
  double y=a.at(a.authored,1,i)-a.at(a.authored,1,j);
  double z=a.at(a.authored,2,i)-a.at(a.authored,2,j);
  double r=a.at(a.authored,20,i)+a.at(a.authored,20,j);
  assert(x*x+y*y+z*z>=r*r);
 }
 std::cout<<"PASS: population >100K, native address limits, invalid edits, deterministic non-overlap\n";
}
