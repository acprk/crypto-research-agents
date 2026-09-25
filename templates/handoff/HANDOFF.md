# HANDOFF — <campaign: submission | rebuttal | camera-ready | milestone> — <date>

Project: <internal id>  ·  Phase: <P0–P8>  ·  Owner: <agent/human>  ·  Next owner: <...>
Machine(s): <label only, e.g. "bench-1 (16 cores, AVX-512)">; never IPs or usernames in shared copies.

## 1. Deliverables

| file | description | status | checksum (sha256, first 12) |
|---|---|---|---|
| `paper/main.pdf` | submitted/camera-ready PDF | final | |
| `rebuttal/rebuttal_short.md` | submitted rebuttal (<n> words) | final | |
| `artifact/` | anonymous artifact | final | |

## 2. Key results (every number with its evidence)

| claim / number as printed | EVIDENCE id | log path (relative to project) | commit | runs / statistic |
|---|---|---|---|---|
| <stage X a–b× faster on scope S> | E12 | `results/run_2026xxxx/log.txt` | `abc1234` | 5 interleaved, median |

## 3. Reproduction commands

```bash
# build / environment
<commands>
# regenerate Table k
<commands>
```

## 4. Measurement protocol and caveats

- <e.g. only same-session interleaved A/B pairs are trusted; absolute times drift with load>
- <build directories that are stale and must not be used>
- <known fallbacks / error messages that indicate the method does not apply>

## 5. Data corrections in this campaign

| date | what changed | why | superseded evidence ids |
|---|---|---|---|

## 6. Open issues

| id | issue | severity | owner | next step |
|---|---|---|---|---|

## 7. Reviewer / request → response map (rebuttal and camera-ready campaigns)

| request (paraphrased) | where answered |
|---|---|
