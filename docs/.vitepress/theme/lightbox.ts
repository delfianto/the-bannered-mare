/**
 * Self-contained diagram lightbox for The Bannered Mare docs.
 *
 * Any `<figure class="tbm-figure">` that contains an <svg> (or <img>) becomes
 * zoomable: an expand affordance is added, and clicking the figure opens a
 * full-screen overlay with scroll-to-zoom, drag-to-pan and keyboard controls.
 *
 * VitePress is an SPA, so this is wired on mount and re-run after every route
 * change rather than once on DOMContentLoaded. All DOM access is guarded so the
 * module is inert during server-side rendering.
 */

const WIRED = 'tbmLbWired'

function media(fig: HTMLElement): SVGElement | HTMLImageElement | null {
  return (
    fig.querySelector<SVGElement>('.tbm-fig-body svg') ??
    fig.querySelector<SVGElement>('svg') ??
    fig.querySelector<HTMLImageElement>('img')
  )
}

function openLightbox(fig: HTMLElement): void {
  const src = media(fig)
  if (!src) return

  // Capture the source's rendered size while it is still laid out inside the
  // figure. An inline SVG that carries only a viewBox (no width/height) has no
  // intrinsic size once cloned into the unconstrained overlay, so it would
  // otherwise collapse to 0×0.
  const srcRect = src.getBoundingClientRect()

  const head = fig.querySelector('.tbm-fig-head')
  const title = head ? (head.textContent || '').trim() : 'Diagram'

  const overlay = document.createElement('div')
  overlay.className = 'tbm-lb-overlay'

  const bar = document.createElement('div')
  bar.className = 'tbm-lb-bar'

  const titleEl = document.createElement('span')
  titleEl.className = 'tbm-lb-title'
  titleEl.textContent = title
  bar.appendChild(titleEl)

  const hint = document.createElement('span')
  hint.className = 'tbm-lb-hint'
  hint.textContent = 'scroll to zoom · drag to pan · Esc to close'
  bar.appendChild(hint)

  const actions: Array<[string, string]> = [
    ['−', 'out'],
    ['Reset', 'reset'],
    ['+', 'in'],
    ['✕', 'close'],
  ]
  for (const [label, action] of actions) {
    const b = document.createElement('button')
    b.className = 'tbm-lb-btn'
    b.type = 'button'
    b.textContent = label
    b.dataset.action = action
    bar.appendChild(b)
  }

  const stage = document.createElement('div')
  stage.className = 'tbm-lb-stage'
  const content = document.createElement('div')
  content.className = 'tbm-lb-content'

  const clone = src.cloneNode(true) as SVGElement | HTMLImageElement
  clone.removeAttribute('style')
  if (srcRect.width > 0) {
    clone.setAttribute('width', String(Math.round(srcRect.width)))
    clone.setAttribute('height', String(Math.round(srcRect.height)))
  }
  content.appendChild(clone)
  stage.appendChild(content)
  overlay.appendChild(bar)
  overlay.appendChild(stage)
  document.body.appendChild(overlay)
  document.body.style.overflow = 'hidden'

  let scale = 1
  let fitScale = 1
  let panX = 0
  let panY = 0

  // translate() is applied before scale() so panning moves in unscaled CSS
  // pixels and is never clipped by the stage's scroll bounds.
  const apply = () => {
    content.style.transform = `translate(${panX}px,${panY}px) scale(${scale})`
  }
  const resetView = (s: number) => {
    scale = s
    panX = 0
    panY = 0
    apply()
  }

  // Fit: upscale small diagrams to fill the stage, never below natural size,
  // capped so a tiny diagram is not blown up past legibility.
  requestAnimationFrame(() => {
    const cw = srcRect.width || clone.getBoundingClientRect().width || 600
    const sw = stage.clientWidth - 64
    fitScale = Math.min(Math.max(sw / cw, 1), 2.6)
    resetView(fitScale)
  })

  const zoom = (d: number) => {
    scale = Math.min(6, Math.max(0.3, +(scale + d).toFixed(2)))
    apply()
  }

  const onMove = (e: MouseEvent) => {
    if (!dragging) return
    panX = startPanX + (e.clientX - startX)
    panY = startPanY + (e.clientY - startY)
    apply()
  }
  const onUp = () => {
    dragging = false
    stage.classList.remove('grabbing')
  }
  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape') close()
    else if (e.key === '+' || e.key === '=') zoom(0.25)
    else if (e.key === '-') zoom(-0.25)
    else if (e.key === '0') resetView(fitScale)
  }
  const close = () => {
    document.body.style.overflow = ''
    overlay.remove()
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
    document.removeEventListener('keydown', onKey)
  }

  bar.addEventListener('click', (e) => {
    const action = (e.target as HTMLElement)?.dataset?.action
    if (action === 'in') zoom(0.25)
    else if (action === 'out') zoom(-0.25)
    else if (action === 'reset') resetView(fitScale)
    else if (action === 'close') close()
  })
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) close()
  })
  stage.addEventListener(
    'wheel',
    (e) => {
      e.preventDefault()
      zoom(e.deltaY < 0 ? 0.2 : -0.2)
    },
    { passive: false }
  )

  let dragging = false
  let startX = 0
  let startY = 0
  let startPanX = 0
  let startPanY = 0
  stage.addEventListener('mousedown', (e) => {
    dragging = true
    startX = e.clientX
    startY = e.clientY
    startPanX = panX
    startPanY = panY
    stage.classList.add('grabbing')
    e.preventDefault()
  })
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
  document.addEventListener('keydown', onKey)
}

function wireFigures(): void {
  const figures = document.querySelectorAll<HTMLElement>('.tbm-figure')
  figures.forEach((fig) => {
    if (fig.dataset[WIRED]) return
    if (!media(fig)) return
    fig.dataset[WIRED] = '1'
    fig.classList.add('tbm-zoomable')

    const btn = document.createElement('button')
    btn.className = 'tbm-lb-expand'
    btn.type = 'button'
    btn.textContent = '⤢'
    btn.title = 'Enlarge diagram'
    btn.setAttribute('aria-label', 'Enlarge diagram')
    btn.addEventListener('click', (e) => {
      e.stopPropagation()
      openLightbox(fig)
    })
    fig.appendChild(btn)

    const body = fig.querySelector('.tbm-fig-body')
    body?.addEventListener('click', (e) => {
      if ((e.target as HTMLElement).closest('a')) return
      openLightbox(fig)
    })
  })
}

/** Called from the theme's client-side setup; no-op during SSR. */
export function wireLightbox(): void {
  if (typeof document === 'undefined') return
  wireFigures()
}
