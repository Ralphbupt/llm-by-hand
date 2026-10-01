"""Flag hard English in lessons and exercises (see AUTHORING.md "Plain English").

Many readers learn English as a second language. A dictionary gives them the most common sense of a word,
so metaphors, phrasal verbs and uncommon senses of common words mislead them. This script lists every use of a
blacklisted word or phrase in reader-facing text, with a plainer replacement.

Checked: lesson.en.mdx prose and frontmatter text (title, question, boss, recap lines) (code fences, inline code, math and import lines skipped; JSX lines only in their
`q="…"` / `title="…"` text), exercises.yaml prompt / after / reveal / say / options / hints (template, solution and
tests skipped), the `def:` lines of content/glossary.yaml, the /math/ page, and the visible strings of site/src/components/**/*.svelte
(string literals in <script>, text and attribute values in the markup; <style>, class names and code skipped).
Markdown emphasis (`**`, `*`) is removed before matching, so "its **share**" is still found.

Opt out for a justified use by putting a marker on the same line:
  MDX:  {/* en-ok: catch */}        YAML:  # en-ok: catch        Svelte:  // en-ok: catch   or   <!-- en-ok: catch -->
Use `en-ok: *` to accept every hit on that line.

Glossary senses. A lesson page underlines the first use of each glossary term and shows its card. Some terms are
also everyday words (“shape” of a curve, “seed” of a computation, “bias” of a float exponent), so the card can give
the wrong meaning. Terms with a `senses:` field in content/glossary.yaml are checked: for each page, the line holding
the term's first use (the one that gets the card) must be listed in scripts/glossary_senses.txt. A new or changed line
is reported. Read it: if the card's meaning is right, run with --accept-senses to record it; if not, reword the
line or add the term to the page's `glossarySkip`.

Usage:  python scripts/check_english.py [--only <slug>] [--summary] [--accept-senses] [--bold]
Exit code 1 when there are hits.
"""
import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# (pattern, suggestion). Patterns are case-insensitive regexes matched on word boundaries.
# _P lets a pronoun sit inside a phrasal verb ("work it out").
_P = r"(?:it |them |this |that |these |those |one )?"
BLACKLIST: list[tuple[str, str]] = [
    # phrasal verbs (AUTHORING rule 2)
    (rf"take[sn]? {_P}in|taking {_P}in|took {_P}in", "use / use information from"),
    (rf"work(?:s|ed|ing)? {_P}out", "compute / find"),
    (rf"blow(?:s|ing|n)? {_P}up|blew {_P}up", "grow very large"),
    (r"fall(?:s|ing|en)? apart|fell apart", "fail"),
    (r"run(?:s|ning)? out|ran out", "is not enough"),
    (rf"rul(?:e|es|ed|ing) {_P}out", "give zero probability to / exclude"),
    (r"level(?:s|ed|ing)? off", "stop(s) falling"),
    (r"tell(?:s|ing)? (?:\w+ ){0,3}apart|told (?:\w+ ){0,3}apart", "distinguish"),
    (r"(?:can[’']t|cannot|can not) tell\b", "does not know / cannot see"),
    (rf"hand(?:s|ed|ing)? {_P}over", "give(s)"),
    (r"stand(?:s|ing)? out|stood out", "is much bigger than the others"),
    (r"fall(?:s|ing)? off|fell off", "goes to 0"),
    (r"shoot(?:s|ing)? off|shot off", "becomes huge"),
    (r"keep(?:s|ing)? (?:\w+ )?alive|kept (?:\w+ )?alive", "keep(s)"),
    (r"creep(?:s|ing)? (?:down|up)|crept (?:down|up)", "falls / rises slowly"),
    (r"sit(?:s|ting)? still|sat still", "stays the same"),
    (r"collaps(?:e|es|ed|ing) into", "combine(s) into"),
    (r"put(?:s|ting)? a floor under", "keep(s) … from going below"),
    (r"squeez(?:e|es|ed|ing) through", "pass(es) through a small space"),
    (r"(?:tell(?:s|ing)?|told) [^.;:!?]{1,60}? from\b", "distinguish … from"),
    (r"(?:tell(?:s|ing)?|told) (?:\w+ ){1,4}by (?:its|their|the|a)\b", "… shows which … it is"),
    (r"(?:give|gives|gave|giving|given) out\b", "output(s) / return(s)"),
    (r"(?:bring|brings|bringing|brought) (?:\w+ ){0,4}up to", "make(s) … about the same size as"),
    (r"from\s+(?:\S+\s+){0,2}?on\b(?!\s+(?:the|a|an|each|every|its|this|that|top|both|which|whose|to|one|all|it|them|disk|screen|paper)\b)", "starting at / after"),
    (rf"factor(?:s|ed|ing)? {_P}out", "write … as a product (say which)"),
    (rf"cross(?:es|ed|ing)? {_P}out", "remove"),
    (rf"figur(?:e|es|ed|ing) {_P}out", "find"),
    (rf"(?:leave|leaves|leaving|left) {_P}out", "forget / omit"),
    (r"spread(?:s|ing)? (?:\w+ ){1,3}out", "spread over / store in many places"),
    (r"end(?:s|ed|ing)? up", "become / are finally"),
    (r"turn(?:s|ed|ing)? out", "is / is found to be"),
    (r"(?:make|makes) of\b", "understand / encode"),
    (rf"cancel(?:s|led|ling)? {_P}out", "divide(s) away / disappear(s)"),
    (rf"trip(?:s|ped|ping)? {_P}up", "is a common mistake"),
    (r"carr(?:y|ies|ied|ying) over", "works the same way"),
    (rf"pil(?:e|es|ed|ing) {_P}up", "are added together"),
    (r"part(?:s|ed|ing)? ways", "start to differ"),
    (rf"max(?:es|ed|ing)? {_P}out", "reach the maximum"),
    (rf"g(?:ive|ives|ave|iving|iven) {_P}away", "show / reveal"),
    (rf"g(?:ive|ives|ave|iving|iven) {_P}up", "stop / cannot store"),
    (r"(?:get|gets|got|getting) going", "starts to work"),
    (r"comes? up|came up|coming up", "happens"),
    (r"(?:tak(?:e|es|ing)|took) (?:\w+ ){0,2}off your hands", "does for you"),
    (rf"open(?:s|ed|ing)? {_P}(?:line )?up", "shows / explains"),
    (r"settl(?:e|es|ed|ing) (?:at|on|down|into)", "finally reach"),
    (r"show(?:s|ed|ing)? up", "appears"),
    (r"read(?:s|ing)? on", "continue reading"),
    (r"(?:hold|holds|held|holding) on to", "keeps"),
    (r"(?:give|gives|gave|giving) back", "returns"),
    (r"(?:feed|feeds|fed|feeding) (?:\w+ ){0,3}straight into", "give … directly to"),
    (r"(?:stitch|stitches|stitched|stitching)(?: \w+){0,3} together", "combine"),
    # wide matching for rule 2: verb + particle with any inflection, also split by a pronoun ("switches it on")
    (r"flatten(?:s|ed|ing)? out", "become(s) flat"),
    (r"bottom(?:s|ed|ing)? out", "reach(es) its lowest point"),
    (rf"(?:make|makes|making|made) {_P}up for", "correct(s) for"),
    (r"(?:take|takes|taking|took) over|taken over(?=\s*[.,;:])|taken over from", "is used instead / replaces"),
    (rf"switch(?:es|ed|ing)? {_P}(?:on|off)", "set(s) to 0 / make(s) active"),
    (rf"split(?:s|ting)? {_P}off", "separate(s)"),
    (rf"stack(?:s|ed|ing)? {_P}up", "placed one behind another"),
    (rf"(?:feed|feeds|fed|feeding) {_P}in", "give(s) … to the network"),
    (rf"mix(?:es|ed|ing)? {_P}up", "confuse / mix"),
    (rf"(?:light|lights|lit|lighting) {_P}up", "gives large outputs / is highlighted"),
    (r"turn(?:s|ed|ing)? (?:\w+ ){0,3}(?:back )?(?:up|down)(?: or (?:up|down))?", "rise(s) / fall(s) / make(s) larger or smaller"),
    (r"(?:creep|crept|come|comes|came|go|goes|went|pull|pulls|pulled|bring|brings|brought)(?:ing)? (?:\w+ ){0,3}back (?:up|down)", "rise(s) / fall(s) again"),
    (r"sit(?:s|ting)? out|sat out", "is far from"),
    (r"count(?:s|ed|ing)? on", "rely on / expect"),
    (r"(?:shake|shakes|shaking|shook) (?:\w+ ){0,3}out", "move(s) … away from"),
    (r"build(?:s|ing)? in (?:a|an|the)\b", "contain(s)"),
    (r"adds up(?=\s*[.,;:])", "becomes large"),
    (r"(?:go|goes|going|went) further", "do(es) more / are enough"),
    (rf"cut(?:s|ting)? {_P}off", "set(s) to 0 / remove(s)"),
    (rf"(?:take|takes|taking|took|taken) {_P}out", "remove(d) / subtract(ed)"),
    (r"(?:get|gets|got|getting) through", "pass(es)"),
    (r"(?:come|comes|came|coming) out", "is the result"),
    (rf"scal(?:e|es|ed|ing) {_P}up", "make … bigger"),
    (r"start(?:s|ed|ing)? over", "start again"),
    (rf"pull(?:s|ed|ing)? {_P}(?:up|down)", "make(s) … larger / smaller"),
    (r"line(?:s|d)? (?:them|it|these|the shapes) up|lining (?:them|it) up", "put … in a row / compare (line up is only for shapes that fit)"),
    # round 6/7 list: phrasal verbs, also "verb + object + particle" ("throw the recurrence away")
    (r"(?:feed|feeds|fed|feeding) (?:\w+ ){0,3}back in", "give … as the next input"),
    (r"(?:throw|throws|threw|thrown|throwing) (?:\w+ ){0,3}away", "delete / remove"),
    (rf"(?:make|makes|made|making) {_P}up(?! for)", "are / form / cause"),
    (r"work(?:s|ed|ing)? through", "do … in order"),
    (r"build(?:s|ing)? on|built on", "use / depend on"),
    (r"(?:fill|fills|filled|filling) up", "grow(s)"),
    (r"speed(?:s|ed|ing)? (?:\w+ )?up|sped (?:\w+ )?up", "make … faster"),
    (r"(?:copy|copies|copied|copying) over", "copy"),
    (rf"turn(?:s|ed|ing)? {_P}(?:on|off)", "check / uncheck (a box) / select"),
    (rf"switch(?:es|ed|ing)? {_P}(?:on|off)", "check / uncheck"),
    (r"warm up", "use warmup / start with a small learning rate"),
    (rf"mix(?:es|ed|ing)? {_P}in\b", "add / mix with"),
    (r"push(?:es|ed|ing)? (?:\w+ ){0,4}through", "pass … through / compute … for"),
    (r"(?:come|comes|came|coming) in\b", "is added / arrive(s) / come(s) as"),
    (rf"let(?:s|ting)? {_P}through", "keep(s) / pass(es)"),
    (rf"pass(?:es|ed|ing)? {_P}on\b", "give(s) to / pass(es) through"),
    (r"(?:go|goes|going|went|gone) through", "pass(es) through / is processed by / check"),
    (r"(?:bounc|hopp)(?:e|es|ed|ing|ing) around|(?:bounce|hop)s? around", "move back and forth"),
    (r"(?:set|sets|setting) up(?! (?:a|an|the)\b)", "install / prepare"),
    (r"kept back", "held out (never trained on)"),
    (r"(?:kept|keep|keeps|keeping)[- ]aside|kept separate", "held out"),
    # idioms (rule 1)
    (r"a little off", "a little different from …"),
    (r"turn(?:s|ed|ing)? the tables?", "use(s) the other direction"),
    (r"chas(?:e|es|ed|ing)", "adjust to / follow"),
    (r"(?:built|computed|made) fresh|fresh(?!\s+(?:noise|random|z\b))", "new / computed again"),
    (r"straight away", "at once / as its first …"),
    (r"in a minute", "in about a minute (of training)"),
    (r"brand[- ]new", "new"),
    (r"from the top(?! right| left)", "from step 1 / from the largest"),
    (r"silent|loud", "with no error message / that shows an error"),
    (r"beat(?:s|ing)? (?:a|the) (?:coin flip|boss)", "be better than random guessing / pass the boss"),
    (r"for nothing", "with no result / learning nothing useful"),
    (r"on (?:their|its) own", "alone / separately / by itself"),
    (r"stay(?:s|ed|ing)? put", "does not change"),
    (r"(?:the )?wrong way around", "in the wrong order"),
    (r"scrambled", "in the wrong order"),
    (r"fuzz(?:y|ier|iest)", "less sharp"),
    (r"blobs?", "cloud"),
    (r"lit\b", "highlighted"),
    (r"survives? the trip", "is left after all the layers"),
    (r"the heart of", "the most important part of"),
    (r"like always", "as always"),
    (r"alive", "from shrinking to 0"),
    (r"collaps(?:e|es|ed|ing)(?! into)", "shrink(s) to 0 / fails"),
    (r"putting it together", "the whole …"),
    (r"branch levels?", "side trip (the name the pages use)"),
    (r"climb(?:s|ed|ing)? the loss", "make(s) the loss larger"),
    (r"shuffled apart", "shuffled separately"),
    (r"removes the data size", "so the amount of data cannot be the cause"),
    (r"row-major", "stored row by row"),
    (r"routines?", "functions"),
    (r"speeds", "frequencies (how fast each one repeats)"),
    (r"stop at the score", "look further than the score"),
    # metaphors and idioms (rule 1)
    (r"bookkeeping", "a way to keep track of every number"),
    (r"knobs?", "weight(s) / parameter(s)"),
    (r"nudg(?:e|es|ed|ing)", "change a little"),
    (r"referee", "checker"),
    (r"upstream", "in the earlier layers"),
    (r"sweet spot", "the best value"),
    (r"torn between", "choosing between"),
    (r"drown(?:s|ed|ing)?", "is much bigger than, so it hides"),
    (r"leak(?:s|ed|ing)?", "gives away a little"),
    (r"carv(?:e|es|ed|ing)", "split"),
    (r"drift(?:s|ed|ing)?", "slowly change"),
    (r"where it hurts", "where it is not useful"),
    (r"bag of words", "a set of words with no order"),
    (r"peek(?:s|ed|ing)?", "see / look at"),
    (r"wobbl(?:e|es|ed|ing)", "go up and down"),
    (r"the other way round", "the opposite"),
    (r"weak spot", "weakness"),
    (r"moves the cliff|the cliff", "the length where accuracy drops"),
    (r"radical", "very new"),
    (r"stir(?:s|red|ring)?", "mix"),
    (r"dissolv(?:e|es|ed|ing)", "disappear"),
    (r"lazy guess", "simplest guess"),
    (r"buys? you", "gives you"),
    (r"clash(?:es|ed|ing)?", "conflict"),
    (r"punish(?:es|ed|ing)?", "gets a large loss / gives a large loss to"),
    (r"on two scales", "measured in two ways"),
    (r"running summary", "summary so far"),
    (r"mirror image", "symmetric (the same across the diagonal)"),
    (r"off-limits", "blocked"),
    (r"fetch(?:es|ed|ing)?", "get"),
    (r"filler", "random extra"),
    (r"fad(?:e|es|ed|ing)", "get smaller and smaller"),
    (r"mind the", "check the"),
    (r"wired", "built / written"),
    (r"by heart", "memorize"),
    (r"that is the point|this is the point", "this is why it matters"),
    (r"uphill", "the loss increases"),
    (r"rusty", "new to you or forgotten"),
    (r"bendy", "curved / non-linear"),
    (r"zigzag(?:s|ged|ging)?", "go back and forth"),
    (r"the wrong way round", "swapped"),
    (r"squash(?:es|ed|ing)?", "compress / make smaller"),
    (r"(?:the |a |its )?company (?:they|it|a word) keeps?", "the words around it"),
    (r"(?:leave|leaves|leaving|left) (?:\w+ ){0,2}behind", "stop using"),
    (r"(?:kept|keep|keeps|keeping) aside", "kept separate"),
    (r"(?:bring|brings|bringing|brought) (?:it|them|this) back", "makes it … again"),
    (r"is known by the words", "the meaning comes from the words"),
    (r"for good", "never come back / forever"),
    (r"backfir(?:e|es|ed|ing)", "gives bad results"),
    (r"derail(?:s|ed|ing)?", "make the rest wrong"),
    (r"every so often", "sometimes"),
    (r"long tail", "the many unlikely words"),
    (r"as (?:it|they) goes?", "while it runs / when it is computed"),
    (r"in hand", "(drop it) / known"),
    (r"under way", "running"),
    (r"junk", "unlikely / useless"),
    (r"bland", "plain"),
    (r"clumsy", "does not fit every case"),
    (r"astronomical(?:ly)?", "extremely (give the number)"),
    (r"the line to beat", "the result to do better than"),
    (r"inside out", "start with the innermost part"),
    (r"conveyor", "a moving belt (explain once)"),
    (r"lanes?", "path"),
    (r"crude", "too simple"),
    (r"overshoot(?:s|ing)?", "jump past the lowest point"),
    (r"the road", "the path"),
    (r"steep walls?", "changes fast"),
    (r"holds? no mystery", "you will know what it does"),
    (r"where the bugs live", "where most bugs come from"),
    (r"swept across", "at every value of"),
    (r"one \w+'s worth|one \w+’s worth", "the result of one …"),
    (r"off the scale", "too large to draw"),
    (r"in scale, not in kind", "only in size"),
    (r"retrac(?:e|es|ed|ing)", "go back along"),
    (r"(?:is|are|was) already off|already off\b", "is already wrong"),
    (r"tam(?:e|es|ed|ing)", "make … smooth / keep … small"),
    (r"the odds", "the probabilities"),
    (r"draws? from (?:them|it)", "pick(s) with these probabilities"),
    (r"explod(?:e|es|ed|ing)(?! gradients?)", "grow(s) very large (“exploding gradient” is the term)"),
    (r"healthy", "good / about 1"),
    (r"funnel", "cone of lines"),
    (r"halo", "bright area"),
    (r"scrub(?:s|bed|bing)?", "move through"),
    (r"slabs?", "thin block(s)"),
    (r"lit:", "highlighted:"),
    (r"crawl(?:s|ed|ing)?", "move(s) very slowly"),
    (r"never bends", "has no exceptions"),
    (r"on top(?=\s*[.,;:])", "also"),
    (r"(?:has|have|had) a price|the price", "the cost"),
    (r"forgiving", "works with many settings"),
    (r"tidy", "simple / in one array"),
    (r"the hands of a clock", "the hour hand and the minute hand of a clock"),
    (r"main road|main path|side branch|side path|skip path|identity path|residual stream", "residual path (the plain x) / branch (the layer f)"),
    (r"back to back", "one after the other"),
    (r"(?:are|is|look|looks|often) odd\b", "strange (odd also means not even)"),
    (r"in exchange", "in return"),
    (r"in the way", "the problem / because of"),
    (r"(?:has|have) no idea", "does not know"),
    (r"an edge is an edge", "an edge looks the same"),
    (r"skip(?:s|ped|ping)? every other", "uses every second (0, 2, 4, …)"),
    (r"immune", "not affected"),
    (r"[\w]+-proof", "not affected by …"),
    (r"wiring", "connections"),
    (r"in one go", "in one step"),
    (r"sooner or later", "after enough steps"),
    (r"middle ground", "a value between the two extremes"),
    (r"pay(?:s)? for it", "the cost is"),
    (r"budget buys", "the same number of weights allows"),
    (r"revive", "start learning again"),
    (r"defen[cs]es", "ways to prevent it"),
    (r"jitter", "small back-and-forth moves"),
    (r"stretch of", "part of"),
    (r"glu(?:e|es|ed|ing)", "join(s)"),
    (r"refus(?:e|es|ed|ing) to", "does not"),
    (r"guesser", "the noise-guessing network"),
    (r"bothers you", "you do not want it"),
    # uncommon senses of common words (rule 3)
    # Rule-3 words are matched as the word itself, whatever comes before it ("a second catch", "one share of").
    # Check each hit; a use in the everyday sense the reader knows gets an en-ok marker.
    (r"volume", "strength"),
    (r"effectively", "in practice / almost"),
    (r"floors?", "a lower limit"),
    (r"toys?", "small example"),
    # share as a noun (= fraction), with or without a word in front: "one share of", "a second share", "word’s share".
    # The verb ("the heads share one K/V head") is the common sense and is not flagged.
    (r"(?:a|an|the|its|their|one|each|own|what|that|this|two|three|bigger|biggest|larger|smaller|equal|into)\s+(?:\w*[^s\W]\s+)?shares?"
     r"|\S*[’']s shares?|shares? of|share (?:matters|that|per)", "fraction / part"),
    (r"(?:a|an|the|this|that|second|one|other|another|big|real|main|only)\s+(?:\w+\s+)?catch(?:es)?", "the problem"),
    (r"room", "space / larger values"),
    (r"(?:a |weighted )die\b", "dice (and say what it means)"),
    (r"twist", "difference / change"),
    (r"steady", "stable"),
    (r"\bcap\b|capped", "limit / limited"),
    (r"blur(?:s|red|ry)?", "unclear cloud / not sharp"),
    (r"spec\b", "task description (the exact task and the pass condition)"),
    (r"skeleton", "template file with every function named but empty (explain once)"),
    (r"milestones?", "step(s) (explain once)"),
    (r"affordable", "cheap enough"),
    (r"(?:the |a )?straight (?:formula|way)", "the plain formula / computed directly"),
    (r"spread 1|a spread|valid spread|the spread", "std / how far the numbers are from the mean"),
    # round 9 list
    (rf"look(?:s|ed|ing)? back (?:at|to|over)", "read(s) / attend(s) to / review(s)"),
    (rf"swap(?:s|ped|ping)? {_P}in\b", "use … instead / replace"),
    (rf"(?:lay|lays|laid|laying) {_P}out\b", "arrange(s) / store(s) / show(s)"),
    (rf"(?:fill|fills|filled|filling) {_P}in\b", "write / complete"),
    (r"(?:feed|feeds|fed|feeding) (?:\w+ ){1,4}into", "give(s) … to / pass(es) … to"),
    (r"zero(?:es|ed|ing)\b|zeros? (?:out|it|them|the|its|their|every|all)\b", "set(s) … to 0"),
    (r"add(?:s|ed|ing)? up to(?=\s*[.,;:!?)]|\s*$)", "give(s) … in total (put the number after it)"),
]
COMPILED = [(re.compile(rf"(?<![\w-])(?:{p})(?![\w-])", re.I), s) for p, s in BLACKLIST]

# words after "en-ok:" (or a lone "*"); the closing "*/" of an MDX comment is not part of the list
OPT_OUT = re.compile(r"en-ok:\s*(\*|[\w, -]+)")


def opted_out(line: str, word: str) -> bool:
    m = OPT_OUT.search(line)
    if not m:
        return False
    allowed = [w.strip().lower() for w in m.group(1).split(",")]
    return "*" in allowed or any(a and a in word.lower() for a in allowed)


def hits_in(text: str, raw_line: str):
    text = re.sub(r"\*+", "", text)  # Markdown emphasis: "its **share**" → "its share"
    for rx, sug in COMPILED:
        for m in rx.finditer(text):
            if not opted_out(raw_line, m.group(0)):
                yield m.group(0), sug


def strip_inline(line: str) -> str:
    line = re.sub(r"`[^`]*`", " ", line)
    line = re.sub(r"\$\$.*?\$\$", " ", line)
    line = re.sub(r"\$[^$]*\$", " ", line)
    line = re.sub(r"\{/\*.*?\*/\}", " ", line)
    line = re.sub(r"https?://\S+", " ", line)
    return line


def check_mdx(path: pathlib.Path):
    lines = path.read_text().splitlines()
    fence = math = False
    front = 0
    for n, raw in enumerate(lines, start=1):
        st = raw.strip()
        if n == 1 and st == "---":
            front = 1
            continue
        if front == 1:
            if st == "---":
                front = 2
                continue
            # frontmatter: only the reader-facing fields
            m = re.match(r"(title|short|question|boss):\s*(.*)", st)
            if m:
                yield from ((n, w, s) for w, s in hits_in(m.group(2), raw))
            elif st.startswith('- "'):  # recap lines
                yield from ((n, w, s) for w, s in hits_in(strip_inline(st[2:]), raw))
            continue
        if st.startswith("```"):
            fence = not fence
            continue
        if st == "$$":
            math = not math
            continue
        if fence or math or st.startswith(("import ", "export ")):
            continue
        if st.startswith("<"):
            # JSX: check only the visible attribute text
            for attr in re.findall(r'(?:q|title)="([^"]*)"', st):
                yield from ((n, w, s) for w, s in hits_in(attr, raw))
            continue
        yield from ((n, w, s) for w, s in hits_in(strip_inline(raw), raw))


CODE_KEYS = {"template", "solution", "reference", "wrong", "tests", "setup", "expr", "expect", "when", "answer", "tol", "type", "unit"}


def check_yaml(path: pathlib.Path):
    lines = path.read_text().splitlines()
    skip_indent = None
    for n, raw in enumerate(lines, start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if skip_indent is not None:
            if indent > skip_indent:
                continue
            skip_indent = None
        m = re.match(r"\s*-?\s*([A-Za-z_]+):\s*(.*)", raw)
        if m and m.group(1) in CODE_KEYS:
            if m.group(2).strip() in ("|", ">", "|-", ">-", "") or m.group(1) == "tests":
                skip_indent = indent
            continue
        if m and indent == 0:
            continue  # exercise id
        text = m.group(2) if m else raw.strip().lstrip("- ")
        text = text.split(" # en-ok")[0]
        yield from ((n, w, s) for w, s in hits_in(strip_inline(text), raw))


def check_glossary(path: pathlib.Path):
    for n, raw in enumerate(path.read_text().splitlines(), start=1):
        m = re.match(r"\s*def:\s*(.*)", raw)
        if m:
            yield from ((n, w, s) for w, s in hits_in(strip_inline(m.group(1)), raw))


# Svelte: attributes whose value is code or styling, never shown as text
_SV_SKIP_ATTR = re.compile(
    r"""\b(?:class|style|id|for|type|href|src|d|viewBox|xmlns|fill|stroke|transform|points|role|bind:\w+|on:\w+|(?:in|out|transition|animate):\w+|class:[\w-]+|use:\w+|data-[\w-]+|key|name|lang|width|height|x|y|x1|x2|y1|y2|cx|cy|r|rx|ry)\s*=\s*(?:"[^"]*"|'[^']*'|\{[^}]*\})"""
)
_SV_STRING = re.compile(r"""'((?:[^'\\\n]|\\.)*)'|"((?:[^"\\\n]|\\.)*)"|`((?:[^`\\]|\\.)*)`""")


def _visible(s: str) -> bool:
    """A string literal is probably shown to the reader if it has a space or starts with a capital letter."""
    s = re.sub(r"\$\{[^}]*\}", " ", s).strip()
    return bool(s) and (" " in s or s[0].isupper()) and not s.startswith(("http", "#", ".", "--", "var("))


def check_svelte(path: pathlib.Path, text: str | None = None):
    text = path.read_text() if text is None else text
    text = re.sub(r"<style[\s\S]*?</style>", lambda m: "\n" * m.group(0).count("\n"), text)
    lines = text.splitlines()
    raw_lines = path.read_text().splitlines()
    in_script = False
    for n, line in enumerate(lines, start=1):
        raw = raw_lines[n - 1] if n - 1 < len(raw_lines) else line
        st = line.strip()
        if st.startswith("<script"):
            in_script = True
        if in_script:
            code = re.sub(r"//.*$", "", line) if "//" in line and "://" not in line else line
            for g in _SV_STRING.findall(code):
                lit = next(x for x in g if x is not None) if any(g) else ""
                if _visible(lit):
                    yield from ((n, w, s) for w, s in hits_in(strip_inline(lit), raw))
            if "</script>" in line:
                in_script = False
            continue
        # markup: drop comments and non-text attributes, then check the rest (text nodes, titles, labels)
        vis = re.sub(r"<!--.*?-->", " ", line)
        vis = _SV_SKIP_ATTR.sub(" ", vis)
        # strings inside {…} expressions
        parts = []
        for g in _SV_STRING.findall(vis):
            lit = next((x for x in g if x), "")
            if _visible(lit):
                parts.append(lit)
        vis = _SV_STRING.sub(" ", vis)
        vis = re.sub(r"\{[^}]*\}", " ", vis)
        vis = re.sub(r"</?[\w:.-]+", " ", vis)
        parts.append(vis)
        for t in parts:
            yield from ((n, w, s) for w, s in hits_in(strip_inline(t), raw))


# ---------------------------------------------------------------- glossary senses

SENSES_FILE = ROOT / "scripts" / "glossary_senses.txt"


def _term_forms(t: dict) -> list[str]:
    """The same forms the site matches (lib/glossary.ts): the term, its aliases, and a plain plural."""
    out = []
    for f in [t["term"], *(t.get("aliases") or [])]:
        out.append(f)
        if re.search(r"[a-z]$", f, re.I) and not re.search(r"s$", f, re.I):
            out.append(f + "s")
        if re.search(r"(x|ch|sh)$", f, re.I):
            out.append(f + "es")
    return out


def _prose_lines(path: pathlib.Path):
    """(line number, text) of the lines whose text the site can underline: prose, list items, table cells.
    Headings, frontmatter, code, math and JSX tag lines are skipped, as on the site."""
    lines = path.read_text().splitlines()
    fence = math = False
    front = 0
    for n, raw in enumerate(lines, start=1):
        st = raw.strip()
        if n == 1 and st == "---":
            front = 1
            continue
        if front == 1:
            if st == "---":
                front = 2
            continue
        if st.startswith("```"):
            fence = not fence
            continue
        if st == "$$":
            math = not math
            continue
        if fence or math or not st or st.startswith(("import ", "export ", "#", "<")):
            continue
        yield n, re.sub(r"\*+", "", strip_inline(raw))


def _skip_list(path: pathlib.Path) -> set[str]:
    m = re.search(r"^glossarySkip:\s*\[([^\]]*)\]", path.read_text(), re.M)
    return {w.strip().strip("'\"").lower() for w in m.group(1).split(",")} if m else set()


def sense_entries(only: str | None = None):
    """(slug, term, line number, line text) for the first use of every `senses:` term on every page."""
    import yaml

    all_terms = [t for t in yaml.safe_load((ROOT / "content/glossary.yaml").read_text()) if t.get("mark", True) is not False]
    out = []
    for d in sorted(ROOT.glob("content/*/*/")):
        f = d / "lesson.en.mdx"
        if not f.exists() or (only and only not in d.name):
            continue
        # a term with `only:` is underlined only on those pages (as in LessonLayout.astro)
        terms = [t for t in all_terms if not t.get("only") or d.name in t["only"]]
        owner: dict[str, int] = {}
        for i, t in enumerate(terms):
            for form in _term_forms(t):
                owner.setdefault(form.lower(), i)
        alts = sorted(owner, key=len, reverse=True)
        rx = re.compile(r"(?<![\w-])(" + "|".join(re.escape(a) for a in alts) + r")(?![\w-])", re.I)
        skip = _skip_list(f)
        seen: set[int] = set()
        for n, text in _prose_lines(f):
            for m in rx.finditer(text):
                i = owner[m.group(1).lower()]
                if i in seen:
                    continue
                seen.add(i)
                t = terms[i]
                if t.get("senses") and t["term"].lower() not in skip:
                    out.append((d.name, t["term"], n, " ".join(text.split())))
    return out


def check_senses(only: str | None, accept: bool):
    entries = sense_entries(only)
    keys = {f"{slug}\t{term}\t{line}" for slug, term, _, line in entries}
    known = set(SENSES_FILE.read_text().splitlines()) if SENSES_FILE.exists() else set()
    if accept:
        # keep the other pages' entries when only one page was checked; otherwise start fresh (drops stale lines)
        known = {k for k in known if only not in k.split("\t")[0]} if only else set()
        SENSES_FILE.write_text("\n".join(sorted(known | keys)) + "\n")
        print(f"recorded {len(keys)} first uses in {SENSES_FILE.relative_to(ROOT)}")
        return []
    hits = []
    for slug, term, n, line in entries:
        if f"{slug}\t{term}\t{line}" not in known:
            hits.append(f"{slug}/lesson.en.mdx:{n}: glossary card “{term}” (check the sense): {line[:160]}")
    return hits


def bold_without_card(only: str | None = None):
    """Words written in **bold** (1–3 words, the way a new term is introduced) that match no glossary term or alias.
    Not every bold word is a term, so this is a list to read, not a failure."""
    import yaml

    forms = {f.lower() for t in yaml.safe_load((ROOT / "content/glossary.yaml").read_text()) for f in _term_forms(t)}
    out = []
    for d in sorted(ROOT.glob("content/*/*/")):
        f = d / "lesson.en.mdx"
        if not f.exists() or (only and only not in d.name):
            continue
        for n, raw in enumerate(f.read_text().splitlines(), start=1):
            for m in re.finditer(r"\*\*([A-Za-z][\w’' -]{1,40}?)\*\*", strip_inline(raw)):
                w = m.group(1).strip().lower()
                if len(w.split()) <= 3 and w not in forms and w.rstrip("s") not in forms:
                    out.append(f"{d.name}/lesson.en.mdx:{n}: **{m.group(1)}** has no glossary card")
    return out


def check_astro(path: pathlib.Path):
    """An .astro page: drop the frontmatter code and <script> blocks (keeping line numbers), then check it like markup."""
    blank = lambda m: "\n" * m.group(0).count("\n")
    text = re.sub(r"\A---[\s\S]*?\n---", blank, path.read_text())
    text = re.sub(r"<script[\s\S]*?(?:</script>|/>)", blank, text)
    yield from check_svelte(path, text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--summary", action="store_true", help="only print the number of hits per page")
    ap.add_argument("--accept-senses", action="store_true", help="record the current first uses of `senses:` terms as checked")
    ap.add_argument("--bold", action="store_true", help="list bold words with no glossary card (a list to read; never fails)")
    args = ap.parse_args()
    if args.bold:
        print("\n".join(bold_without_card(args.only)))
        return

    sense_hits = check_senses(args.only, args.accept_senses)
    for h in sense_hits:
        print(h)

    total = 0
    per_page: dict[str, int] = {}
    for d in sorted(ROOT.glob("content/*/*/")):
        if args.only and args.only not in d.name:
            continue
        for f, fn in ((d / "lesson.en.mdx", check_mdx), (d / "exercises.yaml", check_yaml)):
            if not f.exists():
                continue
            for n, word, sug in fn(f):
                total += 1
                per_page[d.name] = per_page.get(d.name, 0) + 1
                if not args.summary:
                    print(f"{d.name}/{f.name}:{n}: “{word}” → {sug}")
    extra = [(ROOT / "content/glossary.yaml", check_glossary)]
    extra += [(f, check_svelte) for f in sorted((ROOT / "site/src/components").rglob("*.svelte"))]
    extra += [(ROOT / "site/src/pages/math.astro", check_astro)]  # the math page is all prose
    for f, fn in extra:
        rel = f.relative_to(ROOT).as_posix()
        if args.only and args.only not in rel:
            continue
        for n, word, sug in fn(f):
            total += 1
            per_page[rel] = per_page.get(rel, 0) + 1
            if not args.summary:
                print(f"{rel}:{n}: “{word}” → {sug}")
    if args.summary or total:
        print()
        for page, k in sorted(per_page.items(), key=lambda x: -x[1]):
            print(f"{k:4d}  {page}")
    if sense_hits:
        print(f"\n{len(sense_hits)} glossary first uses to check (see the docstring: --accept-senses records them)")
    print(f"\n{total} hard-English hits" if total else "plain English ok")
    sys.exit(1 if total or sense_hits else 0)


if __name__ == "__main__":
    main()
