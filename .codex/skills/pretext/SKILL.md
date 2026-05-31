---
name: pretext
description: |
  Fast, accurate & comprehensive pure-arithmetic text measurement & layout engine.
  Zero DOM reads, instant measurement, proportional font precision for all languages.
---

# pretext

> Pure-arithmetic text measurement & layout engine by chenglou. 48k+ GitHub stars.
> MIT License. `npm install @chenglou/pretext`

## What It Does

Pretext side-steps DOM measurements (`getBoundingClientRect`, `offsetHeight`) which trigger expensive layout reflow. It implements its own text measurement logic using the browser's font engine as ground truth via Canvas 2D `measureText`.

**Core capability:** Measure paragraph height and lay out lines **without ever touching the DOM**, using only pure arithmetic on pre-cached segment widths.

## When To Use

- **Virtualization/occlusion** without guesstimates & caching
- **Masonry layouts** where card height depends on text content
- **Chat bubbles** that keep consistent line count with minimal wasted area
- **Editorial layouts** with multi-column flow, obstacle-aware title routing
- **Accordion/expandable sections** with predictable height animation
- **Shrinkwrap** — finding the tightest container width for multiline text
- **Rich-text inline flow** with chips, mentions, code spans, and atomic pills
- **Canvas/SVG/WebGL rendering** where DOM is not available
- **Server-side rendering** (upcoming)
- **Preventing layout shift** when new text loads
- **Development-time verification** that labels don't overflow (AI-friendly)

## Installation

```bash
npm install @chenglou/pretext
# or
bun add @chenglou/pretext
```

## Two Use Cases

### Use Case 1: Measure Paragraph Height (Fast Path)

The simplest and most common use. Get height without DOM reads.

```typescript
import { prepare, layout } from '@chenglou/pretext'

// One-time preparation (normalizes whitespace, segments, measures segments)
const prepared = prepare('AGI 春天到了. بدأت الرحلة 🚀', '16px Inter')

// Cheap hot path: pure arithmetic, no DOM, no canvas calls
const { height, lineCount } = layout(prepared, 320, 20) // 320px max width, 20px line height
```

**Key insight:** `prepare()` does the expensive one-time work. `layout()` is the cheap resize hot path — call it freely on window resize, but **never re-run `prepare()`** for the same text.

### Use Case 2: Manual Line Layout

Full control over each line. Render to Canvas, SVG, WebGL, or any custom target.

```typescript
import { prepareWithSegments, layoutWithLines } from '@chenglou/pretext'

const prepared = prepareWithSegments('AGI 春天到了. بدأت الرحلة 🚀', '18px "Helvetica Neue"')
const { lines } = layoutWithLines(prepared, 320, 26)

for (let i = 0; i < lines.length; i++) {
  ctx.fillText(lines[i].text, 0, i * 26)
}
```

## API Reference

### Core APIs (Use Case 1 — Height Measurement)

```typescript
prepare(
  text: string,
  font: string,
  options?: {
    whiteSpace?: 'normal' | 'pre-wrap'
    wordBreak?: 'normal' | 'keep-all'
    letterSpacing?: number  // CSS px value
  }
): PreparedText

layout(
  prepared: PreparedText,
  maxWidth: number,
  lineHeight: number
): { height: number, lineCount: number }
```

- `font` uses Canvas font shorthand format: `'16px Inter'`, `'500 17px "Helvetica Neue"'`
- `letterSpacing` matches CSS `letter-spacing` in pixels
- `layout()` with empty string returns `{ lineCount: 0, height: 0 }`. Browsers size empty blocks to one `line-height`, so clamp with `Math.max(1, lineCount) * lineHeight` if needed.

### Manual Layout APIs (Use Case 2 — Line Control)

```typescript
prepareWithSegments(text, font, options?): PreparedTextWithSegments

// High-level: returns all lines at a fixed width
layoutWithLines(prepared, maxWidth, lineHeight): { height, lineCount, lines: LayoutLine[] }

// Low-level: walk lines without building text strings (shrinkwrap, stats)
walkLineRanges(prepared, maxWidth, onLine: (line: LayoutLineRange) => void): number

// Stats-only: avoid line/string allocations
measureLineStats(prepared, maxWidth): { lineCount, maxLineWidth }

// Widest forced line (hard breaks count)
measureNaturalWidth(prepared): number

// Iterator-like: lay out each line with DIFFERENT width
layoutNextLine(prepared, start: LayoutCursor, maxWidth): LayoutLine | null
layoutNextLineRange(prepared, start: LayoutCursor, maxWidth): LayoutLineRange | null

// Convert range to full line with text
materializeLineRange(prepared, line: LayoutLineRange): LayoutLine
```

### Variable-Width Layout Pattern

This is the key pattern for flowing text around obstacles (images, pull quotes, etc.):

```typescript
import { layoutNextLineRange, materializeLineRange, prepareWithSegments, type LayoutCursor } from '@chenglou/pretext'

const prepared = prepareWithSegments(article, '16px Inter')
let cursor: LayoutCursor = { segmentIndex: 0, graphemeIndex: 0 }
let y = 0

// Flow text around a floated image
while (true) {
  const width = y < image.bottom ? columnWidth - image.width : columnWidth
  const range = layoutNextLineRange(prepared, cursor, width)
  if (range === null) break

  const line = materializeLineRange(prepared, range)
  ctx.fillText(line.text, 0, y)
  cursor = range.end
  y += 26
}
```

### Shrinkwrap Pattern

Find the tightest width that fits text in N lines:

```typescript
import { walkLineRanges, measureLineStats, prepareWithSegments } from '@chenglou/pretext'

const prepared = prepareWithSegments(text, '16px Inter')

// Binary search for tightest width that produces 2 lines
let lo = 50, hi = 800
while (lo < hi) {
  const mid = (lo + hi) >> 1
  const { lineCount } = measureLineStats(prepared, mid)
  if (lineCount <= 2) hi = mid
  else lo = mid + 1
}
// lo is now the tightest width for 2 lines

// Or use walkLineRanges to find actual max line width
let maxW = 0
walkLineRanges(prepared, lo, line => { if (line.width > maxW) maxW = line.width })
// maxW is the tightest container width that still fits the text
```

### Rich-Text Inline Flow

For mixed-font text with chips, mentions, code spans, and atomic pills:

```typescript
import {
  prepareRichInline,
  walkRichInlineLineRanges,
  materializeRichInlineLineRange
} from '@chenglou/pretext/rich-inline'

const prepared = prepareRichInline([
  { text: 'Ship ', font: '500 17px Inter' },
  { text: '@maya', font: '700 12px Inter', break: 'never', extraWidth: 22 },
  { text: "'s rich-note", font: '500 17px Inter' },
])

walkRichInlineLineRanges(prepared, 320, range => {
  const line = materializeRichInlineLineRange(prepared, range)
  line.fragments.forEach(f => {
    // f.itemIndex, f.text, f.gapBefore, f.occupiedWidth
  })
})
```

**RichInlineItem fields:**
- `text` — raw author text, boundary spaces collapsible
- `font` — Canvas font shorthand
- `letterSpacing?` — extra horizontal spacing per grapheme (CSS px)
- `break?: 'never'` — atomic items like chips/mentions stay whole
- `extraWidth?` — caller-owned chrome (padding + border width)

### Other Helpers

```typescript
clearCache()           // Release accumulated segment metrics cache
setLocale(locale?)     // Set locale for future prepare() calls, clears cache
```

## Types

```typescript
type LayoutCursor = {
  segmentIndex: number
  graphemeIndex: number
}

type LayoutLine = {
  text: string           // Full text content, e.g. 'hello world'
  width: number          // Measured width, e.g. 87.5
  start: LayoutCursor    // Inclusive start
  end: LayoutCursor      // Exclusive end
}

type LayoutLineRange = {
  width: number
  start: LayoutCursor
  end: LayoutCursor
}

type RichInlineItem = {
  text: string
  font: string
  letterSpacing?: number
  break?: 'normal' | 'never'
  extraWidth?: number
}

type RichInlineFragment = {
  itemIndex: number
  text: string
  gapBefore: number
  occupiedWidth: number
  start: LayoutCursor
  end: LayoutCursor
}

type RichInlineLine = {
  fragments: RichInlineFragment[]
  width: number
  end: RichInlineCursor
}
```

## Options

### `whiteSpace: 'pre-wrap'`

For textarea-like text where ordinary spaces, `\t` tabs, and `\n` hard breaks stay visible:

```typescript
const prepared = prepare(textareaValue, '16px Inter', { whiteSpace: 'pre-wrap' })
```

### `wordBreak: 'keep-all'`

CSS-like `word-break: keep-all` for CJK/Hangul text. Keeps same `overflow-wrap: break-word` fallback for overlong runs.

### `letterSpacing`

Matches CSS `letter-spacing` in pixels:

```typescript
const prepared = prepare(text, '16px Inter', { letterSpacing: 1.5 })
```

## Hyphenation

Pretext does **not** build in automatic hyphenation. For manual layout, insert soft hyphens (`­`) before `prepare()`:

- Unchosen soft hyphens stay invisible
- Chosen breaks materialize as trailing `-`
- For mixed-language/app text, prefer conservative, locale-aware insertion

## Caveats

- Supports `white-space: normal` and `pre-wrap`
- Supports `word-break: normal` and `keep-all`
- `overflow-wrap: break-word` behavior (narrow widths break at grapheme boundaries)
- `line-break: auto`
- Tabs use browser default `tab-size: 8`
- `system-ui` is **unsafe** for accuracy on macOS — use a named font
- Requires `Intl.Segmenter` and Canvas 2D text measurement
- CSS features beyond canvas `font` shorthand (`font-optical-sizing`, `font-feature-settings`, `font-variation-settings`) are not modeled separately
- `prepare()` / `prepareWithSegments()` do horizontal-only work; `lineHeight` is a layout-time input
- Segment widths are browser-canvas widths for line breaking, not exact glyph-position data

## Demos & References

### Official Demos (chenglou.me/pretext)

| Demo | What It Shows |
|------|---------------|
| **Accordion** | Expand/collapse sections with height from Pretext |
| **Bubbles** | Tight multiline message bubbles, same line count, less wasted area |
| **Dynamic Layout** | Fixed-height editorial spread with obstacle-aware title routing |
| **Variable Typographic ASCII** | Particle-driven ASCII art comparing proportional vs monospace |
| **Editorial Engine** | Animated orbs, live text reflow, pull quotes, multi-column flow |
| **Justification Comparison** | CSS greedy, hyphenated, and Knuth-Plass side by side |
| **Rich Text** | Inline text, code spans, links, chips with natural wrapping |
| **Markdown Chat** | Virtualized chat with marked parsing + rich-inline flow |
| **Masonry** | Text-card occlusion with height from Pretext |

Live: https://chenglou.me/pretext/ and https://somnai-dreams.github.io/pretext-demos/

### Community Demos

| Demo | What It Shows |
|------|---------------|
| **Fluid Smoke** | Full-screen fluid simulation as proportional ASCII |
| **Shrinkwrap Showdown** | CSS fit-content vs pretext tightest width |

## Project Structure

```
src/
├── layout.ts          # Core library — keep layout() fast and allocation-light
├── analysis.ts        # Normalization, segmentation, glue rules
├── measurement.ts     # Canvas measurement, segment cache, emoji correction
├── line-break.ts      # Internal line-walking core
├── bidi.ts            # Simplified bidi metadata helper
├── rich-inline.ts     # Inline-only rich-text flow helper
├── layout.test.ts     # Small durable invariant tests
└── test-data.ts       # Shared corpus for accuracy/benchmarks

pages/
├── accuracy.ts        # Browser sweep + per-line diagnostics
├── benchmark.ts       # Performance comparisons
└── demos/
    ├── index.html     # Demo landing page
    ├── bubbles.ts     # Bubble shrinkwrap demo
    ├── dynamic-layout.ts  # Editorial spread demo
    ├── editorial-engine.ts # Multi-column flow demo
    ├── markdown-chat.ts   # Chat virtualization demo
    └── rich-note.ts       # Rich inline demo
```

## Development

```bash
bun install              # Install dependencies
bun start                # Dev server at localhost:3000
bun run check            # Typecheck + lint + dead-code scan
bun test                 # Invariant tests
bun run build:package    # Build dist/ for publishing
bun run accuracy-check   # Chrome accuracy sweep
bun run benchmark-check  # Chrome benchmark snapshot
```

## Integration Patterns

### With React/Virtualization

```typescript
// Pre-calculate heights for virtual list items
const heights = items.map(item => {
  const prepared = prepare(item.text, '16px Inter')
  return layout(prepared, containerWidth, 20).height
})
```

### With Canvas Rendering

```typescript
const prepared = prepareWithSegments(text, '18px Georgia')
const { lines } = layoutWithLines(prepared, canvas.width, 28)

lines.forEach((line, i) => {
  ctx.fillStyle = '#333'
  ctx.fillText(line.text, padding, padding + i * 28)
})
```

### With Dynamic Width (Obstacle Avoidance)

Use `layoutNextLineRange()` to flow text around images, pull quotes, or any obstacle:

```typescript
let cursor = { segmentIndex: 0, graphemeIndex: 0 }
let y = 0

while (true) {
  const width = isInObstacleZone(y) ? narrowWidth : fullWidth
  const range = layoutNextLineRange(prepared, cursor, width)
  if (!range) break
  renderLine(materializeLineRange(prepared, range), y)
  cursor = range.end
  y += lineHeight
}
```

### With SSR (Server-Side)

Pretext requires Canvas 2D for measurement. For SSR, you'll need a Node.js Canvas implementation (e.g. `canvas` package) or pre-compute heights client-side. Full SSR support is planned.

## Key Principles

1. **prepare() once, layout() many** — never re-prepare for the same text
2. **layout() is the hot path** — no DOM, no canvas, pure arithmetic
3. **Font string must match CSS** — `'16px Inter'` in prepare must match your CSS
4. **lineHeight is layout-time** — not baked into prepare
5. **Use `prepareWithSegments`** when you need line-level control
6. **Use `walkLineRanges`** for shrinkwrap/stats without string allocation
7. **Use `layoutNextLineRange`** for variable-width flow around obstacles

## Credits

Sebastian Markbage planted the seed with [text-layout](https://github.com/chenglou/text-layout). His design — canvas `measureText` for shaping, bidi from pdf.js, streaming line breaking — informed the architecture.

## Resources

- GitHub: https://github.com/chenglou/pretext (48k+ stars)
- Docs: https://chenglou.me/pretext/
- Demos: https://chenglou.me/pretext/ and https://somnai-dreams.github.io/pretext-demos/
- npm: `@chenglou/pretext`
