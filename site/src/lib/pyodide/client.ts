/** 主线程这边的封装:Promise 接口 + 超时重启 + 加载状态 */
import type { RunRequest, RunResponse } from './worker'
import { track } from '../analytics'

export type PyStatus = 'idle' | 'loading' | 'ready' | 'running'

type Pending = { resolve: (r: RunResponse) => void; reject: (e: Error) => void; timer: number }

class PyRunner {
  private worker: Worker | null = null
  private seq = 0
  private pending = new Map<number, Pending>()
  private listeners = new Set<(s: PyStatus) => void>()
  status: PyStatus = 'idle'

  onStatus(fn: (s: PyStatus) => void): () => void {
    this.listeners.add(fn)
    fn(this.status)
    return () => this.listeners.delete(fn)
  }

  private setStatus(s: PyStatus) {
    this.status = s
    this.listeners.forEach((f) => f(s))
  }

  private ensure(): Worker {
    if (this.worker) return this.worker
    const w = new Worker(new URL('./worker.ts', import.meta.url), { type: 'module' })
    w.onmessage = (e: MessageEvent<any>) => {
      if (e.data?.type === 'status') {
        this.setStatus(e.data.status === 'ready' ? 'ready' : 'loading')
        return
      }
      const res = e.data as RunResponse
      const p = this.pending.get(res.id)
      if (!p) return
      clearTimeout(p.timer)
      this.pending.delete(res.id)
      this.setStatus('ready')
      track('code_run', { result: res.error ? 'error' : 'ok' })
      p.resolve(res)
    }
    w.onerror = (e) => this.failAll(new Error(e.message || 'The Python worker crashed.'))
    this.worker = w
    return w
  }

  private failAll(err: Error) {
    this.pending.forEach((p) => {
      clearTimeout(p.timer)
      p.reject(err)
    })
    this.pending.clear()
    this.worker?.terminate()
    this.worker = null
    this.setStatus('idle')
  }

  run(code: string, tests: RunRequest['tests'], timeoutMs = 5000): Promise<RunResponse> {
    const w = this.ensure()
    const id = ++this.seq
    if (this.status !== 'ready') this.setStatus('loading')
    return new Promise<RunResponse>((resolve, reject) => {
      const timer = window.setTimeout(() => {
        // 死循环了:直接杀掉 Worker,下次调用会重新加载
        this.failAll(new Error(`Still running after ${timeoutMs / 1000} s. Is there an infinite loop?`))
      }, timeoutMs + (this.status === 'ready' ? 0 : 60_000)) // 首次加载额外给 60 秒
      this.pending.set(id, { resolve, reject, timer })
      this.setStatus('running')
      w.postMessage({ id, code, tests } satisfies RunRequest)
    })
  }
}

export const py = new PyRunner()
