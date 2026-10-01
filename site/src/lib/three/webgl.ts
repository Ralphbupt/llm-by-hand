/**
 * WebGL availability, without importing three, so plain components (LabFrame) can ask cheaply.
 * stage.ts re-exports it.
 */
let glOk: boolean | undefined
/**
 * Can this browser draw WebGL 2 (three r170 needs it)? Cached. `?no3d` in the URL or localStorage
 * `llmbh-no3d = 1` simulates a browser without it (to check the fallbacks).
 */
export function webglAvailable(): boolean {
  if (glOk !== undefined) return glOk
  if (typeof document === 'undefined') return true // server render: assume yes, the client decides
  try {
    if (new URLSearchParams(location.search).has('no3d') || localStorage.getItem('llmbh-no3d') === '1') return (glOk = false)
  } catch { /* storage blocked: test for real */ }
  try {
    const gl = document.createElement('canvas').getContext('webgl2')
    glOk = !!gl
    gl?.getExtension('WEBGL_lose_context')?.loseContext()
  } catch {
    glOk = false
  }
  return glOk
}
