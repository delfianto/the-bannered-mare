<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ content: string }>();

interface TextNode {
  type: "action" | "dialogue" | "text" | "break";
  text: string;
  key: string;
}

const nodes = computed<TextNode[]>(() => {
  const result: TextNode[] = [];
  const paragraphs = props.content.split("\n\n");

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
      <em v-else-if="node.type === 'action'" class="italic text-muted-foreground">{{
        node.text
      }}</em>
      <span v-else-if="node.type === 'dialogue'" class="font-normal text-foreground">{{
        node.text
      }}</span>
      <span v-else class="text-foreground">{{ node.text }}</span>
    </template>
  </div>
</template>
