export const meta = {
  name: 'cra-idea-tournament',
  description: 'Generate ideas from several mining angles, cost-model and pre-emption-check each, judge panel ranks survivors',
  whenToUse: 'Phase P2 ideation',
  phases: [{ title: 'Generate' }, { title: 'Screen' }, { title: 'Judge' }],
}
// args: { project: "/abs/path", problem: "the bottleneck / open problem" }
const P = args.project, Q = args.problem
const IDEAS = { type: 'object', properties: { ideas: { type: 'array', items: { type: 'object', properties: {
  name: { type: 'string' }, mechanism: { type: 'string' }, expected_gain: { type: 'string' }, kill_criterion: { type: 'string' } },
  required: ['name', 'mechanism', 'kill_criterion'] } } }, required: ['ideas'] }
const ANGLES = [
  'free a parameter that prior work fixed, sweep it, look for anomalies (steps 1-4 of idea-mining-loop)',
  'exploit an algebraic structure (automorphisms, characters, subfields, symmetry, sparsity) the baseline ignores',
  'transfer a technique from a neighbouring area (symmetric crypto ↔ FHE ↔ MPC ↔ lattice cryptanalysis)',
  'attack the cost model: which operation dominates, can it be traded for a cheaper one?',
  'lower-bound first: prove what is impossible, then find the gap between bound and best known',
]
phase('Generate')
const ideas = (await parallel(ANGLES.map((a, i) => () => agent(
  `Problem: ${Q}. Read ${P}/LITERATURE.md and ${P}/IDEAS.md. Angle: ${a}. Propose up to 3 concrete ideas.`,
  { agentType: 'idea-miner', phase: 'Generate', label: `angle${i + 1}`, schema: IDEAS })))).filter(Boolean).flatMap(r => r.ideas)
log(`${ideas.length} raw ideas`)
phase('Screen')
const SCREEN = { type: 'object', properties: { alive: { type: 'boolean' }, cost_model_gain: { type: 'string' },
  preempted_by: { type: 'string' }, reason: { type: 'string' } }, required: ['alive', 'reason'] }
const screened = await pipeline(ideas,
  idea => agent(`Cost-model this idea with lib/cryptomath/costmodel on toy params and search ePrint for pre-emption. Kill it if gain < 1.2x or already published. Idea: ${JSON.stringify(idea)}`,
    { agentType: 'falsifier', phase: 'Screen', label: `screen:${idea.name}`, schema: SCREEN }).then(s => ({ ...idea, ...s })))
const alive = screened.filter(Boolean).filter(s => s.alive)
log(`${alive.length}/${ideas.length} survived screening`)
if (!alive.length) return { alive: [], note: 'nothing survived; broaden problem or revisit literature' }
phase('Judge')
const RANK = { type: 'object', properties: { ranking: { type: 'array', items: { type: 'string' } }, rationale: { type: 'string' } }, required: ['ranking'] }
const ranks = (await parallel(['novelty for a top IACR venue', 'feasibility within 8 weeks', 'size of concrete gain'].map(c => () =>
  agent(`Rank these ideas by ${c}. Return names best-first.\n${JSON.stringify(alive)}`, { phase: 'Judge', label: c, schema: RANK })))).filter(Boolean)
const score = {}
ranks.forEach(r => r.ranking.forEach((n, i) => { score[n] = (score[n] || 0) + (alive.length - i) }))
const order = alive.map(a => a.name).sort((a, b) => (score[b] || 0) - (score[a] || 0))
await agent(`Append these ideas to ${P}/IDEAS.md in its template format, ordered: ${order.join(', ')}. Data:\n${JSON.stringify(alive)}`, { label: 'write-ideas', effort: 'low' })
return { order, alive }
