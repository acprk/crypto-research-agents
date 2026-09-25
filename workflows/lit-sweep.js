export const meta = {
  name: 'cra-lit-sweep',
  description: 'Multi-modal literature sweep (ePrint, DBLP, citation graph, library code) → verified related-work matrix',
  whenToUse: 'Phase P1, and before submission as a pre-emption check',
  phases: [{ title: 'Sweep' }, { title: 'Verify' }, { title: 'Synthesize' }],
}
// args: { project: "/abs/path", topic: "short topic description", since: "YYYY-MM" }
const P = args.project, T = args.topic, S = args.since || 'last 24 months'
const HITS = { type: 'object', properties: { works: { type: 'array', items: { type: 'object', properties: {
  id: { type: 'string', description: 'ePrint id / DOI / arXiv id' }, title: { type: 'string' }, venue_year: { type: 'string' },
  relevance: { type: 'string' }, technique: { type: 'string' } }, required: ['id', 'title', 'relevance'] } } }, required: ['works'] }
const MODES = [
  `keyword search on IACR ePrint (use skills/eprint-search) for "${T}" since ${S}`,
  `DBLP venue search: CRYPTO/EUROCRYPT/ASIACRYPT/TCC/PKC/CHES/FSE/CCS/S&P/USENIX for "${T}"`,
  `citation-graph walk: start from the 3 most-cited works on "${T}" and follow forward citations`,
  `code-first: find public libraries/artifacts implementing "${T}" and the papers they cite`,
]
phase('Sweep')
const found = (await parallel(MODES.map((m, i) => () =>
  agent(`Topic: ${T}. Mode: ${m}. Return only works you actually saw on a web page this session.`,
    { agentType: 'lit-scout', phase: 'Sweep', label: `mode${i + 1}`, schema: HITS })))).filter(Boolean).flatMap(r => r.works)
const uniq = [...new Map(found.map(w => [w.id.toLowerCase(), w])).values()]
log(`${found.length} hits, ${uniq.length} unique`)
phase('Verify')
const verified = await pipeline(uniq, w => agent(
  `Verify that ${w.id} "${w.title}" exists (fetch its ePrint/DOI page) and return {exists, bibtex, one_line_summary}.`,
  { agentType: 'lit-scout', phase: 'Verify', label: `verify:${w.id}`, effort: 'low', schema: { type: 'object', properties: {
    exists: { type: 'boolean' }, bibtex: { type: 'string' }, one_line_summary: { type: 'string' } }, required: ['exists'] } })
  .then(v => ({ ...w, ...v })))
const ok = verified.filter(Boolean).filter(v => v.exists)
log(`${ok.length}/${uniq.length} verified; unverifiable entries dropped`)
phase('Synthesize')
return await agent(`Project ${P}. Merge these verified works into ${P}/LITERATURE.md (matrix format already in the file) and append bibtex to ${P}/refs.bib (no duplicates). ` +
  `Then write a 10-line "threat assessment": which works pre-empt or weaken our thesis in ${P}/STATE.md?\n${JSON.stringify(ok)}`,
  { agentType: 'lit-scout', label: 'synthesize' })
