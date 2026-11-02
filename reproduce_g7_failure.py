"""Preserve the original unsupported seed-7 radial cube failure and GPU witnesses.

This uses the old diagnostic authoring sequence to reproduce its exact activation
transition. It does not launch Tk or replace the native capabilities application.
"""
import ctypes as C
import json
import numpy as np
from g7_visual_demo import NativeVisualWorld

class Validation(C.Structure):
    _fields_ = [(n, C.c_uint32) for n in ('normal', 'tangent', 'penetration')] + [
        (n, C.c_float) for n in ('normal_ratio', 'tangent_ratio', 'max_penetration')]

def main():
    w = NativeVisualWorld()
    try:
        w.reset('cube', 'dense', 512, 64, 7)
        previous = None
        for attempt in range(1, 10):
            result = w.advance()
            if result['status'] != 'ACCEPTED':
                break
            previous = w.world._backend.read()
        backend = w.world._backend
        read = backend.dll.ph3_validation
        read.argtypes = [C.c_void_p, C.POINTER(Validation)]
        read.restype = C.c_int
        v = Validation()
        if not read(backend.ptr, C.byref(v)):
            raise RuntimeError('native validation witness unavailable')
        rollback = (previous is not None and np.array_equal(previous.view(np.uint32), backend.read().view(np.uint32))) if result['status'] != 'ACCEPTED' else None
        report = {k: result[k] for k in ('status', 'tick', 'active', 'error_bits', 'contacts', 'max_degree', 'gpu_us')}
        report.update(attempt=attempt, accepted_bytes_unchanged=rollback,
                      witnesses={name: getattr(v, name) for name, _ in v._fields_},
                      qualification='ACTIVATION PROBE ONLY; sustained radial stress remains unqualified',
                      original_baseline_reproduced=(result['error_bits'] == 12 and result['tick'] == 8))
        print(json.dumps(report))
        return 0 if result['status'] == 'ACCEPTED' or rollback else 1
    finally:
        w.close()

if __name__ == '__main__':
    raise SystemExit(main())
