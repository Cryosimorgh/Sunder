#include "physics3.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <limits.h>
typedef struct Lease3 {Ph3Lease value;void *fence;uint64_t completion;int release;} Lease3;
struct Physics3 {
 uint32_t debug_control[64];Ph3Validation validation;StorageDevice *d;uint32_t cache_capacity,n,capacity,iterations,buckets,planes,tick,generation,accepted,seeded,fixed_dt,pending,last_host_error;
 uint64_t context,serial,slots[3],slot_serial[3],trial,grid,contacts,control,free_state,plane,readback,upload,edit,convergence;
 uint64_t state_bytes,grid_bytes,contact_bytes,read_bytes;Lease3 leases[32];
};
static const char *entries[]={"p3_clear","p3_prepare","p3_hash","p3_contacts","p3_solve","p3_gather","p3_integrate","p3_validate","p3_publish","p3_converge_clear","p3_converge_check","p3_converge_finish","p3_cache_clear","p3_cache_publish","p3_color","p3_colored_solve","p3_color_prepare"};
static void collect(Physics3 *p){for(int i=0;i<32;i++){Lease3 *l=&p->leases[i];if(l->value.serial&&l->release&&(!l->fence||s_completion_ready(l->fence,l->completion))){s_resource_unclaim(p->d,l->value.buffer,1);s_completion_release(l->fence);memset(l,0,sizeof(*l));}}}
static int leased(Physics3 *p,unsigned slot){for(int i=0;i<32;i++)if(p->leases[i].value.serial&&p->leases[i].value.slot==slot)return 1;return 0;}
int ph3_close(Physics3 *p){if(!p)return 1;collect(p);for(int i=0;i<32;i++)if(p->leases[i].value.serial)return 0;if(!s_drain(p->d,1000))return 0;uint64_t h[]={p->slots[0],p->slots[1],p->slots[2],p->trial,p->grid,p->contacts,p->control,p->free_state,p->plane,p->readback,p->upload,p->edit,p->convergence};for(unsigned i=0;i<sizeof(h)/sizeof(h[0]);i++)if(h[i]&&!s_retire(p->d,h[i]))return 0;s_collect(p->d);if(!s_try_close(&p->d,1000))return 0;free(p);return 1;}
Physics3 *ph3_open(uint32_t n,uint32_t cap,uint32_t it,int debug,const char *dir){
 /* These bounds follow the 32-bit raw-buffer offsets and 4 GiB resource limit, not benchmark presets. */
 if(!n||!cap||!it||it>4096||!dir||192ull*n+256>0x100000000ull||128ull*cap+256>0x100000000ull)return NULL;
 Physics3 *p=calloc(1,sizeof(*p));if(!p)return NULL;p->d=s_open(debug);if(!p->d){free(p);return NULL;}if(!s_spatial_features(p->d))goto fail;
 p->n=n;p->capacity=cap;p->iterations=it;p->context=s_unique_id();p->buckets=1;while(p->buckets<2*n)p->buckets*=2;
 if(n<=4096){p->cache_capacity=1;while(p->cache_capacity<2ull*cap&&p->cache_capacity<131072)p->cache_capacity*=2;}
 p->state_bytes=192ull*n+256;p->grid_bytes=4ull*p->buckets+32ull*n+256+(n<=4096?4ull*cap:0);p->contact_bytes=128ull*cap+256;
 p->read_bytes=p->contact_bytes>p->state_bytes?p->contact_bytes:p->state_bytes;
 uint64_t sizes[]={p->state_bytes,p->state_bytes,p->state_bytes,p->state_bytes,p->grid_bytes,p->contact_bytes,256,48ull*n+256+64ull*p->cache_capacity,256,p->read_bytes,p->state_bytes,p->state_bytes,8};
 uint64_t total=0;for(unsigned i=0;i<13;i++){uint64_t size=s_allocation(p->d,sizes[i],i==9?2:i==10?1:0);if(size==UINT64_MAX||total>UINT64_MAX-size)goto fail;total+=size;}
 if(!s_admit(p->d,total,0))goto fail;uint64_t *handles[]={&p->slots[0],&p->slots[1],&p->slots[2],&p->trial,&p->grid,&p->contacts,&p->control,&p->free_state,&p->plane,&p->readback,&p->upload,&p->edit,&p->convergence};
 for(unsigned i=0;i<13;i++)if(!(*handles[i]=s_new(p->d,sizes[i],i==9?2:i==10?1:0,"P10 bounded native3D")))goto fail;
 for(unsigned i=0;i<sizeof(entries)/sizeof(entries[0]);i++){char path[1024];snprintf(path,sizeof(path),"%s/%s.dxil",dir,entries[i]);FILE *f=fopen(path,"rb");if(!f)goto fail;fseek(f,0,SEEK_END);long size=ftell(f);rewind(f);if(size<=0||size>16*1024*1024){fclose(f);goto fail;}void *data=malloc(size);if(!data){fclose(f);goto fail;}int ok=fread(data,1,size,f)==(size_t)size;fclose(f);ok=ok&&s_load(p->d,i,data,size);free(data);if(!ok)goto fail;}
 return p;
fail:ph3_close(p);return NULL;
}
static int valid_seed(const float *s,uint32_t n,const float *planes,uint32_t count){
 for(uint32_t p=0;p<count;p++){double norm=0;for(int f=0;f<4;f++)if(!isfinite(planes[4*p+f]))return 0;for(int f=0;f<3;f++)norm+=(double)planes[4*p+f]*planes[4*p+f];if(fabs(norm-1)>2e-6)return 0;}
 for(uint32_t i=0;i<n;i++){
  for(int f=0;f<36;f++)if(!isfinite(s[(uint64_t)f*n+i]))return 0;
  double qn=0;for(int f=6;f<10;f++)qn+=(double)s[(uint64_t)f*n+i]*s[(uint64_t)f*n+i];
  if(fabs(qn-1)>2e-5||s[19ull*n+i]<0||s[20ull*n+i]<=0||s[21ull*n+i]<0||s[21ull*n+i]>1||s[22ull*n+i]<0||s[23ull*n+i]<0)return 0;
  uint32_t id,generation;memcpy(&id,s+36ull*n+i,4);memcpy(&generation,s+37ull*n+i,4);if(id!=i||!generation)return 0;
  if(s[19ull*n+i]==0){for(int f=3;f<6;f++)if(s[(uint64_t)f*n+i]!=0)return 0;for(int f=10;f<13;f++)if(s[(uint64_t)f*n+i]!=0)return 0;continue;}
  double I[3][3],inv[3][3];for(int part=0;part<2;part++){uint32_t b=part?30:24;double (*m)[3]=part?inv:I;m[0][0]=s[(uint64_t)b*n+i];m[1][1]=s[(uint64_t)(b+1)*n+i];m[2][2]=s[(uint64_t)(b+2)*n+i];m[0][1]=m[1][0]=s[(uint64_t)(b+3)*n+i];m[0][2]=m[2][0]=s[(uint64_t)(b+4)*n+i];m[1][2]=m[2][1]=s[(uint64_t)(b+5)*n+i];}
  double a=I[0][0],b=I[1][1],c=I[2][2],d=I[0][1],e=I[0][2],f=I[1][2];if(a<=0||a*b-d*d<=0||a*b*c+2*d*e*f-a*f*f-b*e*e-c*d*d<=0)return 0;
  for(int y=0;y<3;y++){double error2=0;for(int x=0;x<3;x++){double sum=0;for(int k=0;k<3;k++)sum+=I[x][k]*inv[k][y];double error=sum-(x==y);error2+=error*error;}if(error2>4e-10)return 0;}
 }
 return 1;
}
int ph3_seed(Physics3 *p,const float *soa,const float *planes,uint32_t count){
 if(!p||!soa||count>16||(count&&!planes)||p->generation==UINT32_MAX||s_completed(p->d)<s_fence(p->d)||!valid_seed(soa,p->n,planes,count))return 0;collect(p);for(int i=0;i<32;i++)if(p->leases[i].value.serial)return 0;
 void *dst=s_map(p->d,p->upload,p->state_bytes);if(!dst)return 0;memcpy(dst,soa,192ull*p->n);memset((char*)dst+192ull*p->n,0,256);((uint32_t*)dst)[48ull*p->n]=0xbaadc0de;if(!s_unmap(p->d,p->upload,p->state_bytes))return 0;
 if(!s_begin(p->d)||!s_transition(p->d,p->slots[0],2)||!s_copy(p->d,p->slots[0],p->upload,p->state_bytes)||!s_transition(p->d,p->slots[0],5)||!s_transition(p->d,p->trial,2)||!s_copy(p->d,p->trial,p->upload,p->state_bytes)||!s_transition(p->d,p->trial,0))return 0;
 uint64_t guards[]={p->grid,p->contacts,p->free_state};uint64_t offsets[]={4ull*p->buckets+24ull*p->n,p->contact_bytes-256,48ull*p->n};for(int i=0;i<3;i++)if(!s_transition(p->d,guards[i],2)||!s_copy_offset(p->d,guards[i],offsets[i],p->upload,192ull*p->n,256)||!s_transition(p->d,guards[i],0))return 0;
 if(p->cache_capacity){uint64_t h[8]={p->slots[0],p->trial,p->grid,p->contacts,p->control,p->free_state,p->plane,p->slots[0]};uint32_t k[16]={p->n,p->buckets,p->capacity,p->iterations,0,0,0,0,0,0,0,0,1,0,p->cache_capacity,0};if(!s_bind(p->d,h,k)||!s_dispatch(p->d,12,p->cache_capacity))return 0;}
 if(!s_submit(p->d,0)||!s_wait(p->d))return 0;
 dst=s_map(p->d,p->upload,256);if(!dst)return 0;memset(dst,0,256);if(count)memcpy(dst,planes,16*count);if(!s_unmap(p->d,p->upload,256)||!s_begin(p->d)||!s_transition(p->d,p->plane,2)||!s_copy(p->d,p->plane,p->upload,256)||!s_transition(p->d,p->plane,0)||!s_submit(p->d,0)||!s_wait(p->d))return 0;
 p->planes=count;p->accepted=0;p->pending=0;if(p->seeded)p->generation++;p->seeded=1;p->slot_serial[0]=++p->serial;return 1;
}

/* The upload is fence-owned until the GPU copy completes. No accepted slot is
 * mutated, including on an invalid input, allocation, copy or device error.
 * The source buffer is separate from all three consumer-leased slots. */
int ph3_stage(Physics3 *p,const float *soa){
 if(!p||!p->seeded||!soa||!valid_seed(soa,p->n,NULL,0)||
    s_completed(p->d)<s_fence(p->d))return 0;
 void *dst=s_map(p->d,p->upload,p->state_bytes);
 if(!dst)return 0;
 memcpy(dst,soa,192ull*p->n);
 memset((char*)dst+192ull*p->n,0,256);
 ((uint32_t*)dst)[48ull*p->n]=0xbaadc0de;
 if(!s_unmap(p->d,p->upload,p->state_bytes))return 0;
 if(!s_begin(p->d)||!s_transition(p->d,p->edit,2)||
    !s_copy(p->d,p->edit,p->upload,p->state_bytes)||
    !s_transition(p->d,p->edit,5)||!s_submit(p->d,0)||
    !s_wait(p->d)){s_abort(p->d);return 0;}
 p->pending=1;
 return 1;
}
int ph3_drop_stage(Physics3 *p){
 if(!p||!p->seeded||s_completed(p->d)<s_fence(p->d))return 0;
 p->pending=0;
 return 1;
}
static uint32_t bits(float f){uint32_t u;memcpy(&u,&f,4);return u;}
static int dispatch3(Physics3 *p,unsigned pass,uint32_t count,const uint64_t *h,const uint32_t *k){return s_bind(p->d,h,k)&&s_dispatch(p->d,pass,count?count:1);}
int ph3_resume_clock(Physics3 *p,uint32_t accepted_ticks,float dt){
 if(!p||!p->seeded||p->tick||p->fixed_dt||!isfinite(dt)||dt<=0||
    accepted_ticks==UINT32_MAX||s_completed(p->d)<s_fence(p->d))return 0;
 uint32_t fixed;memcpy(&fixed,&dt,sizeof(fixed));
 p->tick=accepted_ticks;p->fixed_dt=fixed;
 return 1;
}
uint32_t ph3_last_host_error(Physics3 *p){return p?p->last_host_error:3;}
static int control_wait3(Physics3 *p,uint32_t *header){
 if(!s_transition(p->d,p->control,1)||!s_copy(p->d,p->readback,p->control,256)||!s_transition(p->d,p->control,0)||!s_submit(p->d,0)||!s_wait(p->d))return 0;
 const void *mapped=s_map(p->d,p->readback,256);if(!mapped)return 0;memcpy(header,mapped,256);return s_unmap(p->d,p->readback,0);
}
static int convergence3(Physics3 *p,uint32_t count,const uint64_t *h,const uint32_t *k){
 uint64_t check[8];memcpy(check,h,sizeof(check));check[0]=p->convergence;
 return dispatch3(p,9,1,h,k)&&dispatch3(p,10,count,h,k)&&s_predicate_zero(p->d,0,0)&&s_transition(p->d,p->convergence,0)&&dispatch3(p,11,1,check,k)&&s_transition(p->d,p->convergence,4)&&s_predicate_zero(p->d,p->convergence,0);
}
int ph3_tick(Physics3 *p,float dt,const float *gravity,float cell,uint32_t inject,Ph3Result *r){
 if(p)p->last_host_error=1;
 if(!p||!p->seeded||!r||!gravity||!isfinite(dt)||dt<=0||!isfinite(cell)||cell<=0||p->tick==UINT32_MAX||p->generation==UINT32_MAX||(p->fixed_dt&&p->fixed_dt!=bits(dt)))return 0;
 for(int i=0;i<3;i++)if(!isfinite(gravity[i]))return 0;
 p->last_host_error=2;
 collect(p);unsigned out=3;for(unsigned i=0;i<3;i++)if(i!=p->accepted&&!leased(p,i)){out=i;break;}if(out==3)return 0;
 p->last_host_error=3;
 memset(r,0,sizeof(*r));uint32_t k[16]={p->n,p->buckets,p->capacity,p->iterations,bits(dt),bits(gravity[0]),bits(gravity[1]),bits(gravity[2]),bits(cell),inject,p->planes,p->tick,0,32,p->cache_capacity,0};
 uint64_t h[8]={p->slots[out],p->trial,p->grid,p->contacts,p->control,p->free_state,p->plane,p->pending?p->edit:p->slots[p->accepted]};
 if(!s_begin(p->d)||!s_transition(p->d,p->slots[out],0)||!s_stamp(p->d,0))return 0;
 int ok=dispatch3(p,0,p->buckets>p->n?p->buckets:p->n,h,k)&&dispatch3(p,1,p->n,h,k)&&s_stamp(p->d,1)&&dispatch3(p,2,p->n,h,k)&&s_stamp(p->d,2)&&dispatch3(p,3,p->n,h,k)&&dispatch3(p,5,p->n,h,k)&&dispatch3(p,16,p->capacity,h,k)&&dispatch3(p,14,1,h,k)&&s_stamp(p->d,3);
 uint32_t metadata[64]={0},colors=0,count=p->capacity;
 if(ok&&p->n<=4096){ok=control_wait3(p,metadata)&&s_begin(p->d);count=metadata[1]<p->capacity?metadata[1]:p->capacity;colors=metadata[19];}
 if(colors){
  unsigned sweeps=0;while(ok&&sweeps<p->iterations){unsigned batch=p->iterations-sweeps;if(batch>8)batch=8;
   ok=convergence3(p,count,h,k);
   for(unsigned it=0;ok&&it<batch;it++){
    for(uint32_t color=0;ok&&color<colors;color++){k[12]=color;ok=dispatch3(p,15,count,h,k);}k[12]=0;
    ok=ok&&dispatch3(p,5,p->n,h,k)&&convergence3(p,count,h,k);
   }
   sweeps+=batch;ok=ok&&s_predicate_zero(p->d,0,0)&&dispatch3(p,16,count,h,k)&&dispatch3(p,14,1,h,k)&&control_wait3(p,metadata)&&s_begin(p->d);colors=metadata[19];if(metadata[16])break;if(!colors){ok=0;break;}
  }
 }else if(count&&!metadata[16])for(unsigned it=0;ok&&it<p->iterations;it++){
  if(it%8==0)ok=convergence3(p,count,h,k);
  if(ok)ok=dispatch3(p,4,count,h,k)&&dispatch3(p,5,p->n,h,k);
 }
 ok=ok&&s_predicate_zero(p->d,0,0)&&s_stamp(p->d,4)&&dispatch3(p,6,p->n,h,k)&&s_stamp(p->d,5)&&dispatch3(p,7,p->capacity>p->n?p->capacity:p->n,h,k)&&dispatch3(p,12,p->cache_capacity,h,k)&&dispatch3(p,13,p->capacity,h,k)&&s_stamp(p->d,6)&&dispatch3(p,8,p->n,h,k)&&s_transition(p->d,p->slots[out],5)&&s_stamp(p->d,7)&&s_transition(p->d,p->control,1)&&s_copy(p->d,p->readback,p->control,256)&&s_transition(p->d,p->control,0)&&s_submit(p->d,8)&&s_wait(p->d);
 if(!ok){s_abort(p->d);return 0;}const uint32_t *header=s_map(p->d,p->readback,256);if(!header)return 0;memcpy(p->debug_control,header,256);r->error=header[0];r->contacts=header[1];r->published=header[2];r->max_degree=header[5];r->candidates=header[6];r->awake=header[7];p->validation.normal=header[8];p->validation.tangent=header[9];p->validation.penetration=header[10];memcpy(&p->validation.normal_ratio,header+13,12);s_unmap(p->d,p->readback,0);
 double q[8];if(!s_times_count(p->d,q,8)||s_errors(p->d))return 0;for(unsigned i=0;i<7;i++)r->phases_us[i]=q[i+1]-q[i];r->phases_us[7]=q[7]-q[0];Memory m;if(!s_memory(p->d,&m))return 0;r->committed=m.committed;
 if(!r->error){if(r->published!=p->n)return 0;p->accepted=out;p->pending=0;p->fixed_dt=bits(dt);p->generation++;p->slot_serial[out]=++p->serial;p->tick++;}else if(r->published)return 0;r->generation=p->generation;r->tick=p->tick;p->last_host_error=0;return 1;
}
static int read_buffer(Physics3 *p,uint64_t handle,uint64_t bytes,void *out,int restore){if(!s_begin(p->d)||!s_transition(p->d,handle,1)||!s_copy(p->d,p->readback,handle,bytes)||!s_transition(p->d,handle,restore)||!s_submit(p->d,0)||!s_wait(p->d))return 0;const void *data=s_map(p->d,p->readback,bytes);if(!data)return 0;memcpy(out,data,bytes);return s_unmap(p->d,p->readback,0);}
int ph3_read(Physics3 *p,float *out){if(!p||!p->seeded||!out)return 0;collect(p);if(leased(p,p->accepted))return 0;return read_buffer(p,p->slots[p->accepted],192ull*p->n,out,5);}
int ph3_contacts(Physics3 *p,void *records,uint32_t count){return p&&records&&count<=p->capacity&&read_buffer(p,p->contacts,128ull*count,records,0);}
int ph3_acquire(Physics3 *p,Ph3Lease *out){if(!p||!p->seeded||!out)return 0;collect(p);for(unsigned i=0;i<32;i++)if(!p->leases[i].value.serial){if(!s_resource_claim(p->d,p->slots[p->accepted],1))return 0;Ph3Lease v={p->context,++p->serial,p->slots[p->accepted],p->accepted,p->generation};p->leases[i].value=v;*out=v;return 1;}return 0;}
static Lease3 *find(Physics3 *p,const Ph3Lease *v){if(!p||!v||v->context!=p->context)return NULL;for(unsigned i=0;i<32;i++)if(p->leases[i].value.serial&&!memcmp(&p->leases[i].value,v,sizeof(*v)))return &p->leases[i];return NULL;}
int ph3_track(Physics3 *p,const Ph3Lease *v,void *fence,uint64_t value){Lease3 *l=find(p,v);if(!l||l->fence||l->release||!value||value==UINT64_MAX)return 0;l->fence=s_completion_retain(p->d,fence);if(!l->fence)return 0;l->completion=value;return 1;}
int ph3_release(Physics3 *p,const Ph3Lease *v){Lease3 *l=find(p,v);if(!l||l->release)return 0;l->release=1;collect(p);return 1;}
const char *ph3_adapter(Physics3 *p){return p?s_name(p->d):"";}
int ph3_reader_test(Physics3 *p){
 if(!p||!p->seeded)return 0;unsigned char *state=malloc(p->state_bytes);if(!state)return 0;
 if(!read_buffer(p,p->slots[p->accepted],p->state_bytes,state,5)){free(state);return 0;}
 uint64_t expected=1469598103934665603ull;for(uint64_t i=0;i<p->state_bytes;i++){expected^=state[i];expected*=1099511628211ull;}free(state);
 Ph3Lease lease;if(!ph3_acquire(p,&lease))return 0;void *fence=NULL;void *reader=s_test_reader(p->d,lease.buffer,p->state_bytes,&fence);if(!reader)return 0;
 if(!ph3_track(p,&lease,fence,1)||!s_test_reader_start(reader)||!ph3_release(p,&lease))return 0;
 float gravity[3]={0};Ph3Result r;if(!ph3_tick(p,1.f/128,gravity,2,0,&r)||r.error||!find(p,&lease))return 0;
 uint64_t actual;if(!s_test_reader_finish(reader,&actual)||actual!=expected)return 0;collect(p);return !find(p,&lease);
}

int ph3_validation(Physics3 *p,Ph3Validation *v){if(!p||!v)return 0;*v=p->validation;return 1;}

extern void *s_native_device(StorageDevice*);
extern void *s_native_read_resource(StorageDevice*,uint64_t);
void *ph3_native_device(Physics3 *p){return p?s_native_device(p->d):NULL;}
void *ph3_native_resource(Physics3 *p,const Ph3Lease *v){Lease3 *l=find(p,v);return l&&!l->release?s_native_read_resource(p->d,v->buffer):NULL;}

int ph3_stage_append(Physics3 *p,const float *soa,uint32_t first,uint32_t end){
 if(!p||!p->seeded||!soa||first>=end||end>p->n||!valid_seed(soa,p->n,NULL,0)||s_completed(p->d)<s_fence(p->d))return 0;
 void *dst=s_map(p->d,p->upload,p->state_bytes);if(!dst)return 0;
 memcpy(dst,soa,192ull*p->n);memset((char*)dst+192ull*p->n,0,256);((uint32_t*)dst)[48ull*p->n]=0xbaadc0de;
 if(!s_unmap(p->d,p->upload,p->state_bytes)||!s_begin(p->d)||!s_transition(p->d,p->edit,2))return 0;
 // Accepted buffers stay COMMON. Read-only CopyBufferRegion promotion/decay
 // permits a concurrent tracked renderer read without changing producer state.
 int ok=s_copy(p->d,p->edit,p->slots[p->accepted],p->state_bytes);
 for(uint32_t f=0;ok&&f<48;f++){uint64_t o=4ull*(f*p->n+first);ok=s_copy_offset(p->d,p->edit,o,p->upload,o,4ull*(end-first));}
 ok=ok&&s_transition(p->d,p->edit,5)&&s_submit(p->d,0)&&s_wait(p->d);
 if(!ok){s_abort(p->d);return 0;}p->pending=1;return 1;
}

int ph3_debug_control(Physics3 *p,void *out){if(!p||!out)return 0;memcpy(out,p->debug_control,256);return 1;}
