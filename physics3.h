#pragma once
#include "runtime.h"
#define PH3_FIELDS 48
#define PH3_CONTACT_BYTES 128
#define PH3_SLOTS 3
/* Internal vertical-slice harness ABI, deliberately not a public world API.
 * Calls are serialized by one CPU owner. Do not concurrently mutate a context.
 * Leases are read-only. Track the native completion fence BEFORE GPU submit;
 * release without tracking promises that no GPU work uses the lease.
 * SoA words: p[0:3],v[3:6],q_xyzw[6:10],w[10:13],force[13:16],
 * torque[16:19],invMass[19],radius[20],restitution[21],mu[22],sleep[23],
 * I_body(xx,yy,zz,xy,xz,yz)[24:30], inverse[30:36], id/generation[36:38].
 * Plane: float4(unit inward normal, offset), n dot p >= offset + radius.
 */
#ifdef _WIN32
#define PH3_API __declspec(dllexport)
#else
#define PH3_API
#endif
typedef struct Physics3 Physics3;
typedef struct Ph3Result {
 uint32_t error,contacts,published,generation,tick,max_degree,candidates,awake;
 double phases_us[8];
 uint64_t committed;
} Ph3Result;
typedef struct Ph3Lease {uint64_t context,serial,buffer;uint32_t slot,generation;} Ph3Lease;
PH3_API Physics3 *ph3_open(uint32_t n,uint32_t contacts,uint32_t iterations,int debug,const char *shader_dir);
PH3_API int ph3_close(Physics3*);
PH3_API int ph3_seed(Physics3*,const float *soa,const float *planes,uint32_t plane_count);
/* Transactional replacement source for the NEXT tick. It never changes accepted
 * state until GPU validation and the publication fence succeed. Existing planes
 * remain unchanged. On failed tick, call ph3_drop_stage to discard the edit. */
PH3_API int ph3_stage(Physics3*,const float *soa);
PH3_API int ph3_drop_stage(Physics3*);
/* Restore the global fixed clock after capacity migration into a fresh context. */
PH3_API int ph3_resume_clock(Physics3*,uint32_t accepted_ticks,float dt);
/* Host failure classifier: 0 none, 1 invalid call, 2 lease backpressure,
 * 3 device/record/submission/readback failure. GPU validation is result.error. */
PH3_API uint32_t ph3_last_host_error(Physics3*);
PH3_API int ph3_tick(Physics3*,float dt,const float *gravity,float cell,uint32_t inject,Ph3Result*);
PH3_API int ph3_read(Physics3*,float *soa);
PH3_API int ph3_contacts(Physics3*,void *records,uint32_t capacity);
PH3_API int ph3_acquire(Physics3*,Ph3Lease*);
PH3_API int ph3_track(Physics3*,const Ph3Lease*,void *native_fence,uint64_t);
PH3_API int ph3_release(Physics3*,const Ph3Lease*);
PH3_API int ph3_reader_test(Physics3*);
PH3_API const char *ph3_adapter(Physics3*);
