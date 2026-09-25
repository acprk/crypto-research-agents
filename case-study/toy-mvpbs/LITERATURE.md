# LITERATURE — related-work matrix (owner: `lit-scout`) — TEACHING EXAMPLE

Only well-known public works; every row is in `refs.bib` and was checked by
`skills/bib-verify/scripts/verify_bib.py` (report: `bib-verify-report.md`, 8/8 VERIFIED,
run 2026-09-25; pages cross-checked on Crossref; LNCS volume numbers deliberately omitted
because they were not machine-verified). No concrete numbers from these papers are quoted
anywhere in this project, so the "concrete numbers" column only says what kind of numbers the
paper reports.

| key | work (public id) | venue/year | setting | core technique | asymptotics | concrete numbers (+source page) | code? | our delta |
|---|---|---|---|---|---|---|---|---|
| CGGI16 | ePrint 2016/870 | ASIACRYPT 2016 | TFHE gate bootstrapping | external product GGSW⊡GLWE, blind rotation with CMux | n external products per bootstrap | bootstrapping timings (not quoted) | tfhe (C++), see references/baselines/MANIFEST.md | our toy uses the same blind rotation |
| CGGI17 | ePrint 2017/430 | ASIACRYPT 2017 | TFHE leveled mode | circuit bootstrapping (LWE → GGSW), CMux-tree LUTs, horizontal/vertical packing | ℓ PBS + key switches per circuit bootstrap | not quoted | – | our `vpack` arm is its vertical packing; its LWE→GGSW cost is why claim C5 is refuted |
| CGGI20 | ePrint 2018/421 / JoC 33 | J. Cryptology 2020 | TFHE (journal version) | all of the above, noise analysis | – | not quoted | – | notation (torus, gadget, CMux) follows this paper |
| DM15 | ePrint 2014/816 | EUROCRYPT 2015 | FHEW | bootstrapping via accumulator / blind rotation | – | not quoted | – | background only |
| CJP21 | ePrint 2021/091 | CSCML 2021 | TFHE programmable bootstrapping | PBS: arbitrary LUT in the test polynomial, padding bit | 1 blind rotation per LUT | not quoted | – | **strongest baseline** (one PBS per output bit) |
| CIM19 | ePrint 2018/622 | CT-RSA 2019 | multi-value bootstrapping | factor the test polynomial T_i = v0 · v_i, one blind rotation for many LUTs of the same input; noise grows with ‖v_i‖ | 1 blind rotation + k cheap products | not quoted | – | **the technique we re-implement** (our d_i play the role of their per-LUT polynomials) |
| GBA21 | ePrint 2020/1071 | TCHES 2021(2) | functional bootstrap in TFHE | tree-based and multi-value approaches for larger LUTs | – | not quoted | – | cited for the "tree" family; we only implement the simpler CMux-tree packing of CGGI17 |
| PRESENT07 | DOI 10.1007/978-3-540-74735-2_31 | CHES 2007 | lightweight block cipher | 4-bit S-box | – | – | – | source of the toy S-box table |

## Pre-emption watch (ePrint last 12 months)
| date checked | query | hits | threat level | note |
|---|---|---|---|---|
| 2026-09-15 | "multi-value bootstrapping S-box TFHE" (skills/eprint-search) | several follow-ups to CIM19 exist | none | teaching toy; we claim **no** novelty, see D-1 |

## Reading notes (short)
- **CIM19 in one line:** if every LUT test polynomial factors as a common v0 times a small
  LUT-specific polynomial, one blind rotation of v0 serves all LUTs; the price is noise growth
  proportional to the norm of the small factor. Our THEORY.md re-derives the factorisation for
  the standard one-padding-bit encoding.
- **Why the strongest baseline is per-bit PBS and not TFHE-rs:** the toy measures an
  *algorithmic* ratio inside one library; a production-library comparison would be a
  different claim (see baselines/MANIFEST.md).
