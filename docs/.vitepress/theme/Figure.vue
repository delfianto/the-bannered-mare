<script setup lang="ts">
/**
 * A captioned, zoomable diagram container.
 *
 * Usage in markdown:
 *
 *   <Figure tag="Figure 1" title="System map" id="fig-system-map">
 *     <svg ...>...</svg>
 *     <template #caption>Explanatory caption with **markdown**.</template>
 *   </Figure>
 *
 * The lightbox (see ./lightbox.ts) discovers figures by the `.tbm-figure`
 * class and makes any figure containing an <svg>/<img> click-to-enlarge.
 */
defineProps<{
  /** Short label shown in the header, e.g. "Figure 1". */
  tag?: string
  /** Figure title shown after the tag. */
  title?: string
  /** Optional anchor id for deep-linking. */
  id?: string
}>()
</script>

<template>
  <figure class="tbm-figure" :id="id">
    <figcaption v-if="tag || title" class="tbm-fig-head">
      <span v-if="tag" class="tbm-figtag">{{ tag }}</span>
      <span v-if="tag && title" class="tbm-fig-sep"> · </span>
      <span v-if="title" class="tbm-fig-title">{{ title }}</span>
    </figcaption>
    <div class="tbm-fig-body">
      <slot />
    </div>
    <figcaption v-if="$slots.caption" class="tbm-fig-cap">
      <slot name="caption" />
    </figcaption>
  </figure>
</template>
