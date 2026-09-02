<script setup lang="ts">
import DOMPurify from "dompurify";
import { computed } from "vue";

const props = defineProps<{ content: string }>();

interface TextNode {
  type: "action" | "dialogue" | "text" | "break" | "gfx";
  /** For gfx nodes this is sanitized HTML, injected via v-html. */
  text: string;
  key: string;
}

// Mirrors the backend's normalize.py (defense in depth): the backend cleans
// replies before storing, but we normalize on render too so streaming partials
// and pre-existing messages get the same treatment.
//
// GFX blocks — `<!-- GFX_START --><div style="…">…</div><!-- GFX_END -->` cards
// some presets (e.g. ST Freaky Frankenstein) instruct the model to draw — are
// intentional visuals: extracted and rendered as sanitized HTML. Stray HTML
// *outside* the markers is stripped, and smart quotes become ASCII so the
// dialogue regex below keys on `"…"` reliably.
const GFX_RE = /<!--\s*GFX_START\s*-->([\s\S]*?)<!--\s*GFX_END\s*-->/g;
// An unterminated GFX tail is a block still streaming in — hidden until complete.
const GFX_PARTIAL_RE = /<!--\s*GFX_START\s*-->[\s\S]*$/;

// Presentational allowlist matching the backend's nh3 config: layout + inline
// styling only, no links/media/handlers.
const GFX_SANITIZE = {
  ALLOWED_TAGS: ["div", "span", "p", "br", "hr", "b", "strong", "i", "em", "u", "s", "small"],
  ALLOWED_ATTR: ["style"],
};

function normalizeQuotes(raw: string): string {
  return raw.replace(/[‘’‚‛＇]/g, "'").replace(/[“”„‟＂]/g, '"');
}

// A tag must start with a letter, so a stray `<` in "5 < 10" survives.
function stripHtml(raw: string): string {
  return raw
    .replace(/<!--[\s\S]*?-->/g, "")
    .replace(/<\/?[a-zA-Z][^>]*>/g, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

interface Segment {
  kind: "prose" | "gfx";
  body: string;
}

function splitGfx(raw: string): Segment[] {
  const segments: Segment[] = [];
  let last = 0;
  for (const match of raw.matchAll(GFX_RE)) {
    segments.push({ kind: "prose", body: raw.slice(last, match.index) });
    segments.push({ kind: "gfx", body: match[1] ?? "" });
    last = match.index + match[0].length;
  }
  segments.push({ kind: "prose", body: raw.slice(last).replace(GFX_PARTIAL_RE, "") });
  return segments;
}

const nodes = computed<TextNode[]>(() => {
  const result: TextNode[] = [];

  splitGfx(props.content).forEach((segment, sIdx) => {
    if (segment.kind === "gfx") {
      const html = DOMPurify.sanitize(segment.body, GFX_SANITIZE);
      if (html.trim()) {
        result.push({ type: "gfx", text: html, key: `g-${sIdx}` });
      }
      return;
    }

    const cleaned = normalizeQuotes(stripHtml(segment.body));
    if (!cleaned) return;

    cleaned.split("\n\n").forEach((para, pIdx) => {
      if (pIdx > 0) {
        result.push({ type: "break", text: "", key: `br-${sIdx}-${pIdx}` });
      }
      const regex = /(\*[^*]+\*)|("(?:[^"\\]|\\.)*")/g;
      let lastIndex = 0;
      const trimmed = para.trim();
      let match;

      while ((match = regex.exec(trimmed)) !== null) {
        if (match.index > lastIndex) {
          result.push({
            type: "text",
            text: trimmed.slice(lastIndex, match.index),
            key: `t-${sIdx}-${pIdx}-${lastIndex}`,
          });
        }
        const matched = match[0];
        if (matched.startsWith("*") && matched.endsWith("*")) {
          result.push({
            type: "action",
            text: matched.slice(1, -1),
            key: `a-${sIdx}-${pIdx}-${match.index}`,
          });
        } else if (matched.startsWith('"')) {
          result.push({
            type: "dialogue",
            text: matched,
            key: `d-${sIdx}-${pIdx}-${match.index}`,
          });
        }
        lastIndex = match.index + matched.length;
      }
      if (lastIndex < trimmed.length) {
        result.push({
          type: "text",
          text: trimmed.slice(lastIndex),
          key: `r-${sIdx}-${pIdx}-${lastIndex}`,
        });
      }
    });
  });
  return result;
});
</script>

<template>
  <div class="font-story text-story leading-[1.75] whitespace-pre-wrap">
    <template v-for="node in nodes" :key="node.key">
      <div v-if="node.type === 'break'" class="h-3" />
      <!-- GFX blocks: model-drawn HTML cards, sanitized (nh3 server-side +
           DOMPurify here) before injection. whitespace-normal so the block's
           own newlines don't add pre-wrap gaps. -->
      <!-- eslint-disable-next-line vue/no-v-html -->
      <div
        v-else-if="node.type === 'gfx'"
        class="my-2 whitespace-normal not-italic"
        v-html="node.text"
      />
      <!-- Narration / *actions*: the descriptive prose — italic, dimmed, so it
           reads as stage direction. Spoken "dialogue" stays upright, full
           strength, and a touch heavier so it stands out (RP convention). -->
      <em v-else-if="node.type === 'action'" class="text-muted-foreground italic">{{
        node.text
      }}</em>
      <span v-else-if="node.type === 'dialogue'" class="font-medium text-dialogue">{{
        node.text
      }}</span>
      <span v-else class="text-muted-foreground italic">{{ node.text }}</span>
    </template>
  </div>
</template>
