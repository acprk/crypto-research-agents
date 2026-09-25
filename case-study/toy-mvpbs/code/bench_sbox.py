# TOY: not secure
"""One benchmark execution (called by crbench as a subprocess; one arm = one method).

    python3 code/bench_sbox.py --method mvpbs --k 4 --params T1 --inputs 16

Prints, in crbench's `generic` parser format,
    sbox_eval time: <ms> ms          (mean process-CPU time of ONE evaluation, k output bits)
    sbox_wall elapsed: <ms> ms       (same, wall clock)
    RESULT name=<method> correct=<c> total=<t> blind_rotations=<br> cmux=<cm>
Only the homomorphic evaluation is timed (key generation and input encryption are not),
identically for every method.  Exit code 1 if any output decrypts wrongly at T1.
"""
from __future__ import annotations

import argparse
import sys
import time

from sbox_fhe import (PARAMS, P_IN, PRESENT_SBOX, TFHE, luts, mv_pbs, per_bit_pbs,
                      vpack_encrypt_input, vpack_eval)
from cryptomath.costmodel.counter import Counter, PBS, CMUX


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", required=True, choices=["perbit", "mvpbs", "vpack"])
    ap.add_argument("--k", type=int, default=4, help="number of LUTs (4 S-box bits, then extra random Boolean LUTs)")
    ap.add_argument("--params", default="T1", choices=sorted(PARAMS))
    ap.add_argument("--inputs", type=int, default=16, help="evaluate inputs 0..inputs-1")
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args(argv)

    tf = TFHE(PARAMS[a.params], seed=a.seed)
    fs = luts(a.k)
    if a.method == "vpack" and a.k > 4:
        ap.error("vpack packs only the 4 S-box bits")
    ms = list(range(a.inputs))
    if a.method == "vpack":
        cts = [vpack_encrypt_input(tf, m) for m in ms]
        run = lambda c: vpack_eval(tf, c, PRESENT_SBOX, a.k)  # noqa: E731
    else:
        cts = [tf.encrypt(m, P_IN) for m in ms]
        fn = mv_pbs if a.method == "mvpbs" else per_bit_pbs
        run = lambda c: fn(tf, c, fs)  # noqa: E731
    run(cts[0])  # in-process warm-up (numpy caches)

    with Counter() as cnt:
        c0, t0 = time.process_time(), time.perf_counter()
        outs = [run(c) for c in cts]
        dc, dt = time.process_time() - c0, time.perf_counter() - t0
    correct = sum(tf.decrypt(o, P_IN) == fs[i](m) for m, os_ in zip(ms, outs) for i, o in enumerate(os_))
    total = len(ms) * a.k
    # primary metric = process CPU time (robust on a shared machine, see DECISIONS D3);
    # wall time is logged too.
    print(f"sbox_eval time: {1e3 * dc / len(ms):.3f} ms")
    print(f"sbox_wall elapsed: {1e3 * dt / len(ms):.3f} ms")
    print(f"RESULT name={a.method} correct={correct} total={total} "
          f"blind_rotations={cnt[PBS] // len(ms)} cmux={cnt[CMUX] // len(ms)}")
    if a.params == "T1" and correct != total:
        print("ERROR: wrong output at noise-free parameter set T1", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
