export const meta = {
  name: 'cra-falsify-round',
  description: 'Adversarially attack every open claim in CLAIMS.md with diverse-lens falsifiers; majority vote decides',
  whenToUse: 'Phase P6 gate, or whenever CLAIMS.md has open claims',
  phases: [{ title: 'Load' }, { title: 'Attack' }, { title: 'Ledger' }],
}
// args: { project: "/abs/path/to/research-project" }
const P = (args && args.project) || '.'
const CLAIMS = { type: 'object', properties: { claims: { type: 'array', items: { type: 'object',
  properties: { id: { type: 'string' }, text: { type: 'string' } }, required: ['id', 'text'] } } }, required: ['claims'] }
const VERDICT = { type: 'object', properties: {
  verdict: { type: 'string', enum: ['survived', 'weakened', 'refuted'] },
  weakened_wording: { type: 'string' }, evidence: { type: 'string' }, script_or_log: { type: 'string' } },
  required: ['verdict', 'evidence'] }
const LENSES = [
  'definitions & quantifiers: is the statement even well-posed, are hidden assumptions needed?',
  'numeric recomputation: re-derive every number with an independent script (cryptomath / sage) on small and edge parameters',
  'baseline fairness & literature pre-emption: is the comparison fair, is the strongest baseline used, is it already published (search ePrint last 12 months)?',
]
phase('Load')
const { claims } = await agent(`Read ${P}/CLAIMS.md and return every row whose status is "open".`, { schema: CLAIMS, effort: 'low' })
log(`${claims.length} open claims`)
phase('Attack')
const results = await pipeline(claims, c => parallel(LENSES.map((lens, i) => () =>
  agent(`Project: ${P}. Try hard to REFUTE claim ${c.id}: "${c.text}". Lens: ${lens}. ` +
        `Read EVIDENCE.md/THEORY.md for context. Write any script you run under ${P}/falsify/${c.id}/. ` +
        `If uncertain, answer weakened with a precise weaker wording that you CAN defend.`,
        { agentType: 'falsifier', phase: 'Attack', label: `${c.id}:lens${i + 1}`, schema: VERDICT })))
  .then(vs => {
    const v = vs.filter(Boolean)
    const refuted = v.filter(x => x.verdict === 'refuted').length
    const weakened = v.filter(x => x.verdict === 'weakened')
    const status = refuted >= 2 ? 'refuted' : (refuted + weakened.length >= 1 ? 'weakened' : 'survived')
    return { ...c, status, votes: v }
  }))
phase('Ledger')
await agent(`Update ${P}/CLAIMS.md: for each claim below set status and append falsifier evidence (short, with script/log paths). ` +
  `For weakened claims put the weakened wording. Do not delete rows.\n${JSON.stringify(results.filter(Boolean), null, 1)}`,
  { label: 'write-ledger', effort: 'low' })
return results.filter(Boolean).map(r => ({ id: r.id, status: r.status }))
