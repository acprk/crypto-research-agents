# Baseline catalogue (public libraries only)

This catalogue lists public baselines. It does **not** pin anything for your
project. Your project keeps its own `baselines/MANIFEST.md`, owned by
`baseline-engineer`, with one row per baseline you actually use. Each row gives the
exact commit SHA, the build command and flags, the machine, and the date. See
`skills/baseline-pin/SKILL.md`.

Fetch: `references/baselines/fetch.sh DEST NAME...` clones the repository and
records the resolved SHA in `DEST/PINNED.tsv`. The "suggested pin" column shows a
release tag, verified to exist upstream when this catalogue was written, or
`HEAD`. `HEAD` means the project has no suitable release tag, so pin it at fetch
time. Always re-check with `git ls-remote --tags URL`.

Per-library benchmark recipes (parser + typical command) are in `crbench adapters`.

## Project MANIFEST row format (copy into your project)

```markdown
| name | url | commit (full SHA) | tag | build recipe (exact) | compiler + flags | threads | bench command | parser | role / what it is the baseline FOR | fairness notes |
```

## Universal fairness checklist (apply to every comparison)

- [ ] **Same parameters.** Use the same ring dimension, modulus chain, plaintext modulus,
      security level and failure probability. *Print the library's actual parameters at
      runtime.* A library's preset or default set can differ from the one quoted in a
      paper that uses it, and a speed-up computed against the wrong denominator is
      worthless.
- [ ] **Same security estimate.** Run both parameter sets through the same estimator
      commit and cost model.
- [ ] **Same threads.** Use one thread against one thread, and N against N. Set
      `OMP_NUM_THREADS`, `RAYON_NUM_THREADS` and `GOMAXPROCS` explicitly. Report the
      single-thread comparison even if your headline number is parallel.
- [ ] **Same compiler and flags.** For example, `-O3 -march=native` on both arms or on
      neither. Use the same accelerator backend on both arms (HEXL/AVX-512, GPU).
- [ ] **Same machine and session.** Run in interleaved rounds (`crbench run`), not on
      different days. Absolute times drift with machine load, so trust only ratios from
      back-to-back pairs.
- [ ] **Same work.** Check that both arms produce the same output: decrypt and compare,
      or verify the proof or signature. Count the same phases. Report offline
      (key generation, pre-processing) and online time separately.
- [ ] **Strongest baseline.** The best existing implementation is often *not* the one
      the target paper compares against. Search the paper's follow-ups and competing
      libraries, including faster ones in other languages, before you declare a speed-up.
- [ ] **Reproduce cited numbers.** If you cannot reproduce a number cited from a paper
      on your machine, re-measure it yourself before comparing. Never mix your
      measurement with their printed number in one ratio.
- [ ] **Build freshness.** Build from a clean tree at the pinned SHA. Run
      `crbench stale BIN SRC` before timing. Keep a separate build directory per
      configuration, and never reuse an old `build/`.

---

## FHE

| name | url | suggested pin | build recipe | typical bench | fairness notes |
|---|---|---|---|---|---|
| OpenFHE | https://github.com/openfheorg/openfhe-development | `v1.5.0` | `cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_BENCHMARKS=ON [-DWITH_NATIVEOPT=ON] && cmake --build build -j4` | `build/bin/benchmark/*` (google-benchmark, parser `gbench`); examples print `... time: X ms` (parser `openfhe`) | Named parameter presets (for example the binfhe `STD128*` family) fix concrete `n, q, Q, B_g`. Print them, because papers often quote different ones. Some methods are only compatible with specific presets. If one arm uses HEXL, the other must too. If several OpenFHE versions are installed, set `LD_LIBRARY_PATH` explicitly so the binary loads the version you pinned. |
| HElib | https://github.com/homenc/HElib | `v2.3.0` | `cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DPACKAGE_BUILD=ON && cmake --build build -j4` (needs NTL + GMP) | example/bench programs; enable timers and `printAllTimers` (parser `helib`) | BGV/CKKS. Bootstrapping parameters come from tables in the example code, so record the `(m, p, r, bits)` set. Record the NTL thread count. Many research artifacts patch HElib, so pin the patched fork too. |
| Microsoft SEAL | https://github.com/microsoft/SEAL | `v4.1.2` | `cmake -S . -B build -DSEAL_BUILD_BENCH=ON -DCMAKE_BUILD_TYPE=Release && cmake --build build -j4` | `build/bin/sealbench` (google-benchmark) | No bootstrapping. Use it for leveled BFV/BGV/CKKS primitives. Record whether HEXL is enabled. |
| Lattigo | https://github.com/tuneinsight/lattigo | `v6.1.0` | `go build ./...` | `go test -run=^$ -bench=. -count=5 ./...` (parser `gobench`) | Pure Go. Set `GOMAXPROCS`. Includes CKKS bootstrapping and multiparty protocols. Compare against C++ libraries using ratios within one library where possible. |
| TFHE-rs | https://github.com/zama-ai/tfhe-rs | `HEAD`, pin a `tfhe-rs-*` release tag | `cargo build --release` (`RUSTFLAGS="-C target-cpu=native"` on both arms or neither) | `cargo bench --bench <name>` (criterion, parser `criterion`) | Internally multi-threaded via rayon, so set `RAYON_NUM_THREADS`. Parameter names encode the message/carry bits and the failure probability. Match the failure probability, not only the bit width. Often much faster than C++ TFHE libraries, so compare against it when you claim state of the art. |
| TFHE (C/C++) | https://github.com/tfhe/tfhe | `HEAD` | `make` (CMake inside) | library tests or your own timing loop (parser `generic`) | The original gate-bootstrapping library, with an older parameter set. Treat it as a historical baseline, not the strongest one. |
| Concrete | https://github.com/zama-ai/concrete | `HEAD`, pin a release tag | pip wheel or the documented docker build | Python circuit timing (parser `generic`) | The compiler/optimizer picks parameters per circuit. Record the optimizer version and the chosen parameters. |
| fheanor | https://github.com/FeanorTheElf/fheanor | `HEAD` | `cargo build --release` | `cargo bench` / examples | Research Rust toolkit for BFV/BGV (incl. bootstrapping) and related schemes. No release tags, so pin the SHA. |

## Lattice cryptanalysis / parameter estimation

| name | url | suggested pin | build recipe | typical bench | fairness notes |
|---|---|---|---|---|---|
| lattice-estimator | https://github.com/malb/lattice-estimator | `HEAD` | none (Sage library): `sage -python -c "import sys; sys.path.insert(0,'PATH'); from estimator import *"` | `LWE.estimate(params)` / `NTRU.estimate` (parser `lattice-estimator`) | Record the commit, the cost model (e.g. `RC.MATZOV`, `RC.BDGL16`) and the secret and error distributions. Output changes between commits. Very large `n` may need local cache-size or performance patches: record them and check that results are unchanged on small cases. |
| fplll | https://github.com/fplll/fplll | `5.4.5` | `./autogen.sh && ./configure && make -j4` | `fplll -a bkz -b 20 < basis` + `/usr/bin/time -v` | Record the precision (`-f`) and the BKZ strategy file. |
| fpylll | https://github.com/fplll/fpylll | `0.6.1` | `pip install fpylll` or build against the pinned fplll | Python timing | Must link to the fplll version you pinned. |
| G6K | https://github.com/fplll/g6k | `HEAD` | `pip install -r requirements.txt && python setup.py build_ext --inplace` | sieving examples; report dimension, time, memory | Parallel sieve: fix the thread count and report peak memory. |

## Symmetric cryptanalysis / SAT / MILP

| name | url | suggested pin | build recipe | typical bench | fairness notes |
|---|---|---|---|---|---|
| CryptoSMT | https://github.com/kste/cryptosmt | `HEAD` | Python + STP/CryptoMiniSat/Boolector per its README | `python3 cryptosmt.py --cipher <c> --rounds R --wordsize W` | Solver and version dominate runtime, so record them. |
| CaDiCaL | https://github.com/arminbiere/cadical | `HEAD`, pin a `rel-*` tag | `./configure && make` | `cadical file.cnf` (parser `sat`) | Fix the seed. Report the CNF hash and the SAT/UNSAT result, not just the time. |
| kissat | https://github.com/arminbiere/kissat | `HEAD`, pin a `rel-*` tag | `./configure && make` | `kissat file.cnf` (parser `sat`) | Solver variance is large, so compare over many instances or seeds, never one. |
| CryptoMiniSat | https://github.com/msoos/cryptominisat | `HEAD`, pin a release tag | `cmake -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build` | `cryptominisat5 file.cnf` (parser `sat`) | Native XOR clauses help ARX/linear layers. State whether XOR-CNF was used. |
| HiGHS | https://github.com/ERGO-Code/HiGHS | `HEAD`, pin a `v*` tag | `cmake -B build && cmake --build build` | `highs model.lp` | Open-source MILP. If you compare with a commercial solver, report both. Set the time limit and the MIP gap explicitly. |

## MPC / PSI / OT

| name | url | suggested pin | build recipe | typical bench | fairness notes |
|---|---|---|---|---|---|
| MP-SPDZ | https://github.com/data61/MP-SPDZ | `HEAD`, pin a `v*` tag | `make -j4 <protocol>-party.x` (see its README) | `Scripts/<protocol>.sh prog` (parser `mpspdz`) | Report time **and** communication and rounds. Simulate LAN/WAN with `tc netem` using the same settings on both arms. Keep the security model (semi-honest or malicious) and the number of parties identical. |
| emp-toolkit (emp-tool, emp-ot, emp-sh2pc) | https://github.com/emp-toolkit | `HEAD` | `cmake . && make` for each component in dependency order | two processes (party 1/2) on localhost or two hosts | Measure the slower party. Report communication. |
| APSI | https://github.com/microsoft/APSI | `HEAD`, pin a `v*` tag | vcpkg/CMake per README (depends on SEAL) | sender/receiver CLI | Unbalanced PSI. Report the set sizes, sender pre-processing and online query time separately. |
| libOTe | https://github.com/osu-crypto/libOTe | `HEAD` | `python3 build.py --all --boost --sodium` | `frontend` binary with OT/VOLE benchmarks | Silent OT and VOLE backends vary, so record which one is used. |
| VOLE-PSI | https://github.com/Visa-Research/volepsi | `HEAD` | `python3 build.py` (pulls libOTe) | `frontend -perf -psi -nn <log n>` | Record the threads and whether the malicious variant is enabled. |

## Zero-knowledge

| name | url | suggested pin | build recipe | typical bench | fairness notes |
|---|---|---|---|---|---|
| arkworks (algebra) | https://github.com/arkworks-rs/algebra | `HEAD`, pin a `v*` tag | `cargo build --release` | `cargo bench` (criterion) | Curve and field choice, and the `asm`/`parallel` features, change results. Record them. |
| gnark | https://github.com/Consensys/gnark | `HEAD`, pin a `v*` tag | `go build ./...` | `go test -bench` (parser `gobench`) | Report the constraint count alongside time, and state the backend (Groth16 / PLONK). |
| circom | https://github.com/iden3/circom | `HEAD`, pin a `v*` tag | `cargo build --release` | compile + snarkjs/rapidsnark prove | Compiler and prover are separate tools. Pin both. |

## Post-quantum

| name | url | suggested pin | build recipe | typical bench | fairness notes |
|---|---|---|---|---|---|
| liboqs | https://github.com/open-quantum-safe/liboqs | `HEAD`, pin a release tag | `cmake -GNinja -B build -DCMAKE_BUILD_TYPE=Release && ninja -C build` | `build/tests/speed_kem`, `speed_sig` | Distinguish reference from AVX2 implementations. Compare cycles (median) at a fixed CPU frequency. |
| PQClean | https://github.com/PQClean/PQClean | `HEAD` | per-scheme `make` in `crypto_*/<scheme>/<impl>` | your own harness (cycle counter) | Clean, portable implementations that are not speed-optimised. Do not use them as the "fastest" baseline. |

## How a baseline enters a project

1. `baseline-engineer` fetches it with `fetch.sh` and copies the resolved SHA into the
   project's `baselines/MANIFEST.md`.
2. It builds the baseline with the exact recipe and records the compiler and flags.
3. It runs the library's own tests, including a correctness check (decrypt equals
   expected output, verification passes).
4. It prints the actual runtime parameters and diffs them against the paper being
   compared with.
5. It runs `crbench run` with the baseline as its only arm, repeated at least 3 times,
   to get a reference median.
6. It hands the recipe to `experimenter`.
