<script setup lang="ts">
import { ref, computed, nextTick, useId, watch, onBeforeUnmount } from "vue";
import AppIcon from "./AppIcon.vue";

// Searchable dropdown replacing Nuxt UI's USelectMenu. The default slot is
// the trigger (a hand-styled button); the listbox is teleported to <body> and
// width-matched to the trigger so it escapes ancestor overflow/clipping.
const props = withDefaults(
  defineProps<{
    modelValue?: string | null;
    items: Record<string, any>[];
    valueKey?: string;
    labelKey?: string;
    searchInput?: boolean;
    disabled?: boolean;
  }>(),
  {
    modelValue: null,
    valueKey: "value",
    labelKey: "label",
    searchInput: true,
    disabled: false,
  },
);

const emit = defineEmits<{ "update:modelValue": [value: string] }>();

const open = ref(false);
const query = ref("");
const highlighted = ref(0);
const root = ref<HTMLElement | null>(null);
const trigger = ref<HTMLElement | null>(null);
const menu = ref<HTMLElement | null>(null);
const searchEl = ref<HTMLInputElement | null>(null);
const menuStyle = ref<Record<string, string>>({});

const listboxId = useId();
const optionId = (i: number) => `${listboxId}-opt-${i}`;

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (!q) return props.items;
  return props.items.filter((i) => String(i[props.labelKey]).toLowerCase().includes(q));
});

watch(query, () => (highlighted.value = 0));

function position() {
  // Measure the actual trigger element (the slotted button), not the root — the
  // button carries the real width (w-full fills its field; max-w/compact stays
  // narrow), so the teleported menu matches it in every layout.
  const el =
    (trigger.value?.firstElementChild as HTMLElement | null) ?? trigger.value ?? root.value;
  if (!el) return;
  const r = el.getBoundingClientRect();
  const below = window.innerHeight - r.bottom;
  const openUp = below < 260 && r.top > below;
  menuStyle.value = {
    position: "fixed",
    left: `${r.left}px`,
    width: `${r.width}px`,
    ...(openUp ? { bottom: `${window.innerHeight - r.top + 4}px` } : { top: `${r.bottom + 4}px` }),
  };
}

async function openMenu() {
  if (props.disabled) return;
  query.value = "";
  const idx = props.items.findIndex((i) => i[props.valueKey] === props.modelValue);
  highlighted.value = idx >= 0 ? idx : 0;
  open.value = true;
  await nextTick();
  position();
  if (props.searchInput) searchEl.value?.focus();
}

function closeMenu() {
  open.value = false;
}

function toggle() {
  if (open.value) closeMenu();
  else openMenu();
}

function select(item: Record<string, any>) {
  emit("update:modelValue", item[props.valueKey]);
  closeMenu();
}

function onKeydown(e: KeyboardEvent) {
  if (!open.value) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      openMenu();
    }
    return;
  }
  if (e.key === "Escape") {
    closeMenu();
  } else if (e.key === "ArrowDown") {
    e.preventDefault();
    highlighted.value = Math.min(highlighted.value + 1, filtered.value.length - 1);
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    highlighted.value = Math.max(highlighted.value - 1, 0);
  } else if (e.key === "Enter") {
    e.preventDefault();
    const item = filtered.value[highlighted.value];
    if (item) select(item);
  }
}

function onPointerDown(e: PointerEvent) {
  const t = e.target as Node;
  if (root.value?.contains(t) || menu.value?.contains(t)) return;
  closeMenu();
}

watch(open, (isOpen) => {
  if (isOpen) {
    document.addEventListener("pointerdown", onPointerDown, true);
    window.addEventListener("scroll", position, true);
    window.addEventListener("resize", position);
  } else {
    document.removeEventListener("pointerdown", onPointerDown, true);
    window.removeEventListener("scroll", position, true);
    window.removeEventListener("resize", position);
  }
});

onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", onPointerDown, true);
  window.removeEventListener("scroll", position, true);
  window.removeEventListener("resize", position);
});
</script>

<template>
  <div ref="root" class="relative" @keydown="onKeydown">
    <div
      ref="trigger"
      aria-haspopup="listbox"
      :aria-expanded="open"
      :aria-controls="listboxId"
      @click.prevent="toggle"
    >
      <slot />
    </div>
    <Teleport to="body">
      <div
        v-if="open"
        ref="menu"
        class="fixed z-80 overflow-hidden rounded-lg border bg-base-200 shadow-lg"
        :style="menuStyle"
      >
        <div v-if="searchInput" class="border-b p-1.5">
          <!-- The search input is the focused control while open, so the combobox
               semantics (incl. aria-activedescendant) must live here — not on the
               non-focusable trigger wrapper — for screen readers to announce the
               active option as the user arrows. -->
          <input
            ref="searchEl"
            v-model="query"
            type="text"
            role="combobox"
            aria-autocomplete="list"
            :aria-expanded="open"
            :aria-controls="listboxId"
            :aria-activedescendant="filtered.length ? optionId(highlighted) : undefined"
            placeholder="Search…"
            class="h-8 w-full rounded-md border bg-base-300/40 px-2.5 text-sm text-foreground outline-none placeholder:text-muted-foreground"
          />
        </div>
        <ul :id="listboxId" role="listbox" class="max-h-60 overflow-y-auto p-1">
          <li
            v-for="(item, i) in filtered"
            :id="optionId(i)"
            :key="item[valueKey]"
            role="option"
            :aria-selected="item[valueKey] === modelValue"
            class="flex cursor-pointer items-center gap-2 rounded-md px-2.5 py-1.5 text-sm transition-colors"
            :class="i === highlighted ? 'bg-base-300 text-foreground' : 'text-muted-foreground'"
            @click="select(item)"
            @mouseenter="highlighted = i"
          >
            <AppIcon
              v-if="item[valueKey] === modelValue"
              name="i-lucide-check"
              class="size-3.5 shrink-0 text-primary"
            />
            <span class="truncate">{{ item[labelKey] }}</span>
          </li>
          <li v-if="filtered.length === 0" class="px-2.5 py-1.5 text-sm text-muted-foreground">
            No results
          </li>
        </ul>
      </div>
    </Teleport>
  </div>
</template>
