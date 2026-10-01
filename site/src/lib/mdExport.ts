/**
 * Build time: a level as clean Markdown, for /learn/<slug>.md, /llms-full.txt and AI assistants.
 * Prose, headings, math and code stay. Each question becomes its prompt (with a Predict's options and a code
 * question's template); answers, hints, `after` notes, solutions and boss references are never written.
 * Labs become one line: "[Interactive lab: … — open the page to use it]".
 */
import { loadExercises, type Exercise } from './quiz'
import { BRANCH_NAME, PART_NAME, RUN_NAME, type Level } from './levels'
import { abs, SITE_NAME } from '../config/site'

const attr = (tag: string, name: string) => tag.match(new RegExp(`${name}="([^"]*)"`))?.[1]

/** "SoftmaxJacobianLab" → "Softmax jacobian" */
function labName(component: string): string {
  const words = component.replace(/Lab$/, '').replace(/([a-z0-9])([A-Z])/g, '$1 $2').replace(/([A-Z])([A-Z][a-z])/g, '$1 $2').split(' ')
  return words.map((w, i) => (i === 0 ? w : /^[A-Z0-9]{2,}/.test(w) ? w : w.toLowerCase())).join(' ')
}

function question(kind: string, ex: Exercise | undefined, id: string): string {
  if (!ex) return `**Question** (${id}): open the page to answer it.`
  const head = kind === 'Predict' ? '**Predict.**' : kind === 'CodeBlank' ? '**Code question.**' : '**Question.**'
  const out = [`${head} ${ex.prompt.trim()}`]
  if (ex.type === 'predict') out.push('', ...ex.options.map((o, i) => `${String.fromCharCode(65 + i)}. ${o}`))
  if (ex.type === 'code') out.push('', 'Fill in the blank (`____`):', '', '```python', ex.template.replace(/\s+$/, ''), '```')
  if (ex.type === 'number' && ex.unit) out.push(`(Answer in ${ex.unit}.)`)
  out.push('', '*Answer it on the page to check your work.*')
  return out.join('\n')
}

/** The lesson body (MDX) as Markdown. */
export function bodyToMarkdown(body: string, slug: string): string {
  const exercises = loadExercises(slug)
  const text = body.replace(/\{\/\*[\s\S]*?\*\/\}/g, '')
  const out: string[] = []
  let fence = false
  for (const line of text.split('\n')) {
    const t = line.trim()
    if (/^(```|~~~)/.test(t)) fence = !fence
    if (fence || /^(```|~~~)/.test(t)) { out.push(line); continue }
    if (/^import\s.+from\s/.test(t) || /^export\s/.test(t)) continue
    if (/^<\/?Gate\b/.test(t)) continue
    let m: RegExpMatchArray | null
    if ((m = t.match(/^<(Blank|CodeBlank|Predict)\b[^>]*\/>$/))) {
      const id = attr(t, 'id') ?? ''
      out.push(question(m[1], exercises[id], id))
      continue
    }
    if (/^<Stuck\b/.test(t)) { out.push(`**If you are stuck: ${attr(t, 'q') ?? ''}**`); continue }
    if (/^<Deeper\b/.test(t)) { out.push(`**Deeper: ${attr(t, 'title') ?? 'more on this'}**`); continue }
    if (/^<TryIt\b/.test(t)) { const ti = attr(t, 'title'); out.push(ti ? `**Try it: ${ti}**` : '**Try it**'); continue }
    if (/^<\/(Stuck|Deeper|TryIt)>$/.test(t)) continue
    if ((m = t.match(/^<([A-Z][A-Za-z0-9]*)\b[^>]*\/>$/))) {
      out.push(`*[Interactive lab: ${labName(m[1])} — open the page to use it]*`)
      continue
    }
    if (/^<\/?[A-Z]/.test(t)) continue // any other component tag
    out.push(line.replace(/<span[^>]*>/g, '').replace(/<\/span>/g, ''))
  }
  return out.join('\n').replace(/\n{3,}/g, '\n\n').trim()
}

/** A whole level: title, question, where it sits, the boss challenge, the lesson, and "You can now". */
export function levelToMarkdown(l: Level): string {
  const d = l.data
  const where = d.branch ? `${PART_NAME[d.part]} · side trip: ${BRANCH_NAME[d.branch]}` : PART_NAME[d.part]
  const parts = [
    `# ${d.level}. ${d.title}`,
    '',
    `> ${d.question}`,
    '',
    `${SITE_NAME} · ${where} · ${RUN_NAME[d.run]} · interactive page: ${abs(`/learn/${l.id}/`)}`,
  ]
  if (d.boss) parts.push('', `**Boss challenge.** ${d.boss}`)
  parts.push('', bodyToMarkdown(l.body ?? '', l.id))
  if (d.recap?.can?.length) parts.push('', '## You can now', '', ...d.recap.can.map((c) => `- ${c}`))
  return parts.join('\n') + '\n'
}
