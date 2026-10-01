/// <reference lib="webworker" />
/**
 * 在 Web Worker 里跑 Pyodide + numpy。
 * 放 Worker 有两个理由:① 读者写了死循环不会卡死页面(直接 terminate 重开);
 * ② 10 MB 的加载不阻塞主线程。
 */
const PYODIDE_VERSION = '314.0.6'
const BASE = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`

// 每道题都在这个前置环境里跑:np 和 softmax 和仓库里 08 的定义一致
const PREAMBLE = `
import numpy as np, json as _json

def softmax(x, axis=-1):
    e = np.exp(x - np.max(x, axis=axis, keepdims=True))
    return e / e.sum(axis=axis, keepdims=True)

def __plain(v):
    # numpy scalars and arrays can sit anywhere: inside lists, tuples or dicts (ids = [np.argmax(...)])
    if isinstance(v, np.ndarray): return __plain(v.tolist())
    if isinstance(v, np.generic): return v.item()
    if isinstance(v, (list, tuple)): return [__plain(x) for x in v]
    if isinstance(v, dict): return {(k.item() if isinstance(k, np.generic) else k): __plain(x) for k, x in v.items()}
    return v

def __to_json(v):
    return _json.dumps(__plain(v), default=lambda o: o.item() if hasattr(o, "item") else o.tolist())
`

export type RunRequest = {
  id: number
  code: string
  tests: { setup?: string; expr: string }[]
}
export type RunResponse = {
  id: number
  stdout: string
  error?: string
  values: { value?: unknown; error?: string }[]
}

/** Pyodide 的 traceback 前面有一堆它自己的栈帧,读者不需要看。只留「你的代码」那几帧 + 最后那句错误。 */
function cleanTraceback(msg: string): string {
  const lines = msg.split('\n')
  if (!/^Traceback/.test(lines[0] ?? '')) return msg.trim()
  const out: string[] = []
  let keep = false
  for (let i = 1; i < lines.length; i++) {
    const l = lines[i]
    const m = l.match(/^\s*File "([^"]+)"/)
    if (m) keep = !/_pyodide|pyodide|importlib|<frozen/.test(m[1])
    else if (/^\S/.test(l)) keep = true // 顶格的那行 = 最后的错误信息
    if (keep) out.push(l.replace('File "<exec>"', 'your code'))
  }
  const body = out.join('\n').trim()
  return body || msg.trim()
}

let ready: Promise<any> | null = null

async function getPyodide() {
  if (!ready) {
    ready = (async () => {
      postMessage({ type: 'status', status: 'loading' })
      const mod = await import(/* @vite-ignore */ `${BASE}pyodide.mjs`)
      const py = await mod.loadPyodide({ indexURL: BASE })
      await py.loadPackage('numpy')
      postMessage({ type: 'status', status: 'ready' })
      return py
    })()
  }
  return ready
}

self.onmessage = async (e: MessageEvent<RunRequest>) => {
  const { id, code, tests } = e.data
  const out: string[] = []
  let py: any
  try {
    py = await getPyodide()
  } catch (err) {
    postMessage({ id, stdout: '', error: `Could not load Python: ${String(err)}`, values: [] } as RunResponse)
    return
  }

  py.setStdout({ batched: (s: string) => out.push(s) })
  py.setStderr({ batched: (s: string) => out.push(s) })

  const globals = py.globals.get('dict')() // 每次跑一个干净的命名空间
  const res: RunResponse = { id, stdout: '', values: [] }
  try {
    py.runPython(PREAMBLE, { globals })
    py.runPython(code, { globals })
    const defineOut = out.splice(0).join('\n') // 定义阶段的打印
    let firstOut = ''
    for (let i = 0; i < tests.length; i++) {
      const t = tests[i]
      out.length = 0 // 每条测试都会重跑一遍读者的函数,只留第一条的打印,不然同样的输出会重复几遍
      try {
        if (t.setup) py.runPython(t.setup, { globals })
        const json = py.runPython(`__to_json(${t.expr})`, { globals })
        res.values.push({ value: JSON.parse(json) })
      } catch (err: any) {
        res.values.push({ error: cleanTraceback(String(err?.message ?? err)) })
      }
      if (i === 0) firstOut = out.join('\n')
    }
    out.length = 0
    out.push([defineOut, firstOut].filter(Boolean).join('\n'))
  } catch (err: any) {
    res.error = cleanTraceback(String(err?.message ?? err))
  } finally {
    globals.destroy?.()
    res.stdout = out.join('\n')
    postMessage(res)
  }
}
