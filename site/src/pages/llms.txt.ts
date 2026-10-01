/** /llms.txt (llmstxt.org): what this site is and where everything is, generated from the lessons at build time. */
import type { APIRoute } from 'astro'
import { allLevels, BRANCH_NAME, type Level } from '@lib/levels'
import { SITE_NAME, SITE_DESCRIPTION, abs } from '../config/site'
import { plain } from '@lib/seo'

const entry = (l: Level) => `- [${l.data.level}. ${l.data.title}](${abs(`/learn/${l.id}.md`)}): ${plain(l.data.question)}`

export const GET: APIRoute = async () => {
  const all = await allLevels()
  const main = all.filter((l) => !l.data.branch)
  const branches = (['internals', 'classic', 'diffusion', 'training'] as const).filter((b) => all.some((l) => l.data.branch === b))
  const lines = [
    `# ${SITE_NAME}`,
    '',
    `> ${SITE_DESCRIPTION}`,
    '',
    'Each level answers one question with an example small enough to check on paper, in an interactive page where the',
    'pictures and the numbers move together; the learner must get each question right to move on. Exercises run in the',
    'browser (Python via Pyodide) or, for a few levels, on the learner\'s computer. Every level is also available as',
    'Markdown at /learn/<slug>.md (prose and question prompts, no answers). Lessons are CC BY-SA 4.0; code is MIT.',
    '',
    '## Main line',
    '',
    ...main.map(entry),
    '',
    '## Side trips',
    '',
    'Optional branches that open along the main line.',
    ...branches.flatMap((b) => ['', `### ${BRANCH_NAME[b]}`, '', ...all.filter((l) => l.data.branch === b).map(entry)]),
    '',
    '## Reference',
    '',
    `- [Glossary](${abs('/glossary/')}): every term the course uses, with a short definition and the level that introduces it`,
    `- [Math you need](${abs('/math/')}): every piece of math the course uses, each with a small worked example`,
    `- [Run it on your computer](${abs('/setup/')}): installing Python, NumPy and PyTorch for the levels that run locally`,
    '',
    '## Optional',
    '',
    `- [All lessons in one file](${abs('/llms-full.txt')}): the full text of every level in reading order, as Markdown`,
    '',
  ]
  return new Response(lines.join('\n'), { headers: { 'Content-Type': 'text/plain; charset=utf-8' } })
}
