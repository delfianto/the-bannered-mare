<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ content: string }>();

interface TextNode {
  type: "action" | "dialogue" | "text" | "break";
  text: string;
  key: string;
}

// Defense-in-depth mirror of the backend's normalize.sanitize_narrative: some
// models (uncensored finetunes) inject raw HTML "graphics" blocks — e.g.
// `<!-- GFX_START --><div style="…">…</div>`. The backend strips these before
// storing, but we also strip on render to cover streaming partials and any
// pre-existing messages. A tag must start with a letter, so a stray `<` in
// "5 < 10" survives.
function stripHtml(raw: string): string {
  return raw
    .replace(/<!--[\s\S]*?-->/g, "")
    .replace(/<\/?[a-zA-Z][^>]*>/g, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

const nodes = computed<TextNode[]>(() => {
  const result: TextNode[] = [];
  const paragraphs = stripHtml(props.content).split("\n\n");

  paragraphs.forEach((para, pIdx) => {
    if (pIdx > 0) {
      result.push({ type: "break", text: "", key: `br-${pIdx}` });
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
          key: `t-${pIdx}-${lastIndex}`,
        });
      }
      const matched = match[0];
      if (matched.startsWith("*") && matched.endsWith("*")) {
        result.push({
          type: "action",
          text: matched.slice(1, -1),
          key: `a-${pIdx}-${match.index}`,
        });
      } else if (matched.startsWith('"')) {
        result.push({
          type: "dialogue",
          text: matched,
          key: `d-${pIdx}-${match.index}`,
        });
      }
      lastIndex = match.index + matched.length;
    }
    if (lastIndex < trimmed.length) {
      result.push({
        type: "text",
        text: trimmed.slice(lastIndex),
        key: `r-${pIdx}-${lastIndex}`,
      });
    }
  });
  return result;
});
</script>

<template>
  <div class="text-[14px] leading-[1.7] whitespace-pre-wrap">
    <template v-for="node in nodes" :key="node.key">
      <div v-if="node.type === 'break'" class="h-3" />
      <em v-else-if="node.type === 'action'" class="text-muted-foreground italic">{{
        node.text
      }}</em>
      <span v-else-if="node.type === 'dialogue'" class="font-normal text-foreground">{{
        node.text
      }}</span>
      <span v-else class="text-foreground">{{ node.text }}</span>
    </template>
  </div>
</template>
