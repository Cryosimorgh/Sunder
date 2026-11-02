#pragma once
#ifdef __cplusplus
extern "C" {
#endif
#include "physics3.h"
/* Borrowed device, lives until ph3_close. Resource requires a live lease.
 * COMMON promotion/decay permits read-only COPY_SOURCE on consumer DIRECT queue.
 * Track fence before submission, release afterward; never retain without lease. */
void *ph3_native_device(Physics3*);
void *ph3_native_resource(Physics3*,const Ph3Lease*);
#ifdef __cplusplus
}
#endif
