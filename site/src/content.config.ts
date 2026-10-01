import { defineCollection, z } from 'astro:content'
import { glob } from 'astro/loaders'

// Each level is a folder under ../content: lesson.en.mdx + exercises.yaml + demo.py.
// The folder name is the slug, e.g. content/2-theory/attention → /learn/attention/
// Slugs carry no numbers, so adding or reordering levels never breaks a link.
const lessons = defineCollection({
  loader: glob({
    pattern: '**/lesson.en.mdx',
    base: '../content',
    generateId: ({ entry }) => entry.split('/').slice(-2, -1)[0],
  }),
  schema: z.object({
    title: z.string(),
    short: z.string().optional(),                        // shorter title for the sidebar and the map
    level: z.string(),                                   // main line "1".."21"; branches use a letter: "N1", "U1", "D1"
    order: z.number(),                                   // global sort key
    part: z.enum(['foundations', 'theory', 'engineering']),
    branch: z.enum(['classic', 'internals', 'diffusion', 'training']).optional(),  // optional side branch inside a part
    question: z.string(),                                // the one question this level answers
    run: z.enum(['browser', 'local', 'mixed', 'cloud']), // where the hands-on part runs (mixed: browser, last part local)
    checkpoint: z.string(),                              // exercise id that marks the level as cleared
    mustSolve: z.array(z.string()).optional(),           // boss parts that must be solved too before the level counts as cleared (Skip can't pass them)
    boss: z.string().optional(),                         // boss challenge, if this is a boss level
    summary: z.string().optional(),
    glossarySkip: z.array(z.string()).optional(),        // glossary terms not to underline on this page (they mean something else here)
    testOut: z.array(z.string()).optional(),             // exercise ids for "Already know this? Test out" (default: checkpoint + 2)
    recap: z.object({                                    // the recap card at the end of the level
      can: z.array(z.string()),                          // "You can now" (3 short lines)
      keys: z.array(z.string()),                         // "Keep in mind": formulas and shapes ($KaTeX$, `code`)
      mistakes: z.array(z.string()),                     // "Common mistakes" (2)
    }).optional(),
  }),
})

export const collections = { lessons }
