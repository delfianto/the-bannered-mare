# Shared UI Primitives

Framework: Vue 3.5 (`<script setup lang="ts">`). Styling: Tailwind CSS v4 + DaisyUI 5 semantic tokens. Icons: global `AppIcon` backed by Lucide.

## AppIcon

- Path: `frontend/src/components/shared/AppIcon.vue`
- Global Lucide icon resolver with legacy name compatibility.

```vue
<script setup lang="ts">
import { computed, type Component } from "vue";
import { icons, fallbackIcon } from "./icons";

// Accepts bare kebab names ("home") and the legacy "i-lucide-home" / "lucide:home"
// forms, so call sites and the icon strings in constants/ need no changes.
const props = defineProps<{ name?: string }>();

const resolved = computed<Component>(() => {
  const key = (props.name ?? "").replace(/^i-lucide-/, "").replace(/^lucide:/, "");
  const icon = icons[key];
  if (!icon && props.name && import.meta.env.DEV) {
    console.warn(`[AppIcon] unknown icon "${props.name}"`);
  }
  return icon ?? fallbackIcon;
});
</script>

<template>
  <component :is="resolved" />
</template>

```

## AppPagination

- Path: `frontend/src/components/shared/AppPagination.vue`
- Reusable pagination controls with compact mobile behavior.

```vue
<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  page: number;
  totalPages: number;
}>();

const emit = defineEmits<{
  "update:page": [page: number];
}>();

// Windowed page list: first + last + neighbours of the current page, with
// "…" markers standing in for the collapsed gaps. e.g. 1 … 3 4 5 … 9
const pages = computed<(number | "…")[]>(() => {
  const total = props.totalPages;
  const current = props.page;
  const delta = 1;

  const range: number[] = [];
  for (let i = Math.max(1, current - delta); i <= Math.min(total, current + delta); i++) {
    range.push(i);
  }

  const result: (number | "…")[] = [];
  if (range[0] > 1) {
    result.push(1);
    if (range[0] > 2) result.push("…");
  }
  result.push(...range);
  const last = range[range.length - 1];
  if (last < total) {
    if (last < total - 1) result.push("…");
    result.push(total);
  }
  return result;
});

function go(p: number) {
  if (p < 1 || p > props.totalPages || p === props.page) return;
  emit("update:page", p);
}
</script>

<template>
  <div class="flex items-center justify-between gap-2">
    <span class="text-xs text-muted-foreground">Page {{ page }} of {{ totalPages }}</span>

    <div class="flex items-center gap-1">
      <button
        class="flex size-8 items-center justify-center rounded-lg border text-muted-foreground transition-colors hover:bg-base-300 disabled:pointer-events-none disabled:opacity-40"
        :disabled="page <= 1"
        aria-label="Previous page"
        @click="go(page - 1)"
      >
        <AppIcon name="i-lucide-chevron-left" class="size-4" />
      </button>

      <template v-for="(p, i) in pages" :key="i">
        <span v-if="p === '…'" class="px-1 text-xs text-muted-foreground/60">…</span>
        <button
          v-else
          class="flex h-8 min-w-8 items-center justify-center rounded-lg border px-2 text-xs font-medium transition-colors"
          :class="
            p === page
              ? 'border-primary/40 bg-primary/10 text-primary'
              : 'text-muted-foreground hover:bg-base-300'
          "
          :aria-current="p === page ? 'page' : undefined"
          @click="go(p as number)"
        >
          {{ p }}
        </button>
      </template>

      <button
        class="flex size-8 items-center justify-center rounded-lg border text-muted-foreground transition-colors hover:bg-base-300 disabled:pointer-events-none disabled:opacity-40"
        :disabled="page >= totalPages"
        aria-label="Next page"
        @click="go(page + 1)"
      >
        <AppIcon name="i-lucide-chevron-right" class="size-4" />
      </button>
    </div>
  </div>
</template>

```

## AppToggle

- Path: `frontend/src/components/shared/AppToggle.vue`
- Accessible DaisyUI switch primitive.

```vue
<script setup lang="ts">
// DaisyUI-styled switch. Supports v-model (boolean) and a `change` event for
// call sites that run a handler (e.g. async enable/disable). Replaces the
// hand-rolled role="switch" toggle divs.
withDefaults(
  defineProps<{
    modelValue?: boolean;
    disabled?: boolean;
    ariaLabel?: string;
  }>(),
  { modelValue: false, disabled: false },
);

const emit = defineEmits<{ "update:modelValue": [value: boolean]; change: [value: boolean] }>();

function onChange(e: Event) {
  const checked = (e.target as HTMLInputElement).checked;
  emit("update:modelValue", checked);
  emit("change", checked);
}
</script>

<template>
  <input
    type="checkbox"
    role="switch"
    class="toggle toggle-primary"
    :checked="modelValue"
    :disabled="disabled"
    :aria-label="ariaLabel"
    @change="onChange"
  />
</template>

```

## AppTooltip

- Path: `frontend/src/components/shared/AppTooltip.vue`
- Teleported tooltip that escapes clipped containers.

```vue
<script setup lang="ts">
import { ref } from "vue";

// Lightweight tooltip: teleports the bubble to <body> so it escapes ancestor
// `overflow-hidden` (e.g. the collapsed sidebar). Positioned on hover/focus
// from the trigger's bounding rect. Replaces Nuxt UI's UTooltip.
const props = withDefaults(
  defineProps<{
    text?: string;
    side?: "top" | "right" | "bottom" | "left";
    disabled?: boolean;
    // Wrap long help text (max-width + normal whitespace) instead of the default
    // single-line label. Use for sentences, not short icon labels.
    wide?: boolean;
  }>(),
  { side: "top", disabled: false, wide: false },
);

const visible = ref(false);
const pos = ref<Record<string, string>>({});
const trigger = ref<HTMLElement | null>(null);
const OFFSET = 8;

function show() {
  if (props.disabled || !props.text || !trigger.value) return;
  const r = trigger.value.getBoundingClientRect();
  const cx = `${r.left + r.width / 2}px`;
  const cy = `${r.top + r.height / 2}px`;
  const map = {
    top: { left: cx, top: `${r.top - OFFSET}px`, transform: "translate(-50%, -100%)" },
    bottom: { left: cx, top: `${r.bottom + OFFSET}px`, transform: "translate(-50%, 0)" },
    right: { left: `${r.right + OFFSET}px`, top: cy, transform: "translate(0, -50%)" },
    left: { left: `${r.left - OFFSET}px`, top: cy, transform: "translate(-100%, -50%)" },
  } as const;
  pos.value = map[props.side];
  visible.value = true;
}

function hide() {
  visible.value = false;
}
</script>

<template>
  <span ref="trigger" @mouseenter="show" @mouseleave="hide" @focusin="show" @focusout="hide">
    <slot />
    <Teleport to="body">
      <span
        v-if="visible"
        role="tooltip"
        class="pointer-events-none fixed z-[100] rounded-md bg-foreground px-2 py-1 text-xs font-medium text-base-100 shadow-md"
        :class="wide ? 'max-w-xs whitespace-normal wrap-break-word' : 'whitespace-nowrap'"
        :style="pos"
      >
        {{ text }}
      </span>
    </Teleport>
  </span>
</template>

```

## CollapsibleSection

- Path: `frontend/src/components/shared/CollapsibleSection.vue`
- Disclosure section with title, icon, and animated content.

```vue
<script setup lang="ts">
import { ref } from "vue";

const props = withDefaults(
  defineProps<{
    title: string;
    defaultOpen?: boolean;
    icon?: string;
  }>(),
  { defaultOpen: false },
);

const emit = defineEmits<{
  toggle: [open: boolean];
}>();

const open = ref(props.defaultOpen);

function toggle() {
  open.value = !open.value;
  emit("toggle", open.value);
}
</script>

<template>
  <div class="overflow-hidden rounded-lg border border-border/50 bg-base-100/40">
    <button
      class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition-colors hover:bg-base-300/40"
      @click="toggle"
    >
      <div class="flex min-w-0 items-center gap-2.5">
        <AppIcon v-if="icon" :name="icon" class="size-4 shrink-0 text-muted-foreground" />
        <h3
          class="truncate font-cinzel text-xs font-semibold tracking-widest text-muted-foreground uppercase"
        >
          {{ title }}
        </h3>
        <slot name="badge" />
      </div>
      <AppIcon
        name="i-lucide-chevron-down"
        class="size-4 shrink-0 text-muted-foreground transition-transform"
        :class="{ 'rotate-180': open }"
      />
    </button>

    <div v-if="open" class="border-t border-border/40 px-4 py-3">
      <slot />
    </div>
  </div>
</template>

```

## ConfirmDialog

- Path: `frontend/src/components/shared/ConfirmDialog.vue`
- Compact confirmation dialog primitive.

```vue
<script setup lang="ts">
import { useConfirmState } from "@/composables/useConfirm";
import Modal from "@/components/shared/Modal.vue";

const { state, onConfirm, onCancel } = useConfirmState();
</script>

<template>
  <Modal :show="state.open" :title="state.title" max-width="sm" @close="onCancel">
    <p class="text-sm text-muted-foreground">{{ state.message }}</p>

    <template #footer>
      <button
        class="rounded-lg border px-4 py-2 text-sm text-foreground transition-colors hover:bg-base-300"
        @click="onCancel"
      >
        {{ state.cancelLabel || $t("common.cancel") }}
      </button>
      <button
        class="rounded-lg px-4 py-2 text-sm font-medium transition-colors"
        :class="
          state.danger
            ? 'bg-error text-error-content hover:bg-error/90'
            : 'bg-primary text-primary-content hover:bg-primary/90'
        "
        @click="onConfirm"
      >
        {{ state.confirmLabel || $t("common.confirm") }}
      </button>
    </template>
  </Modal>
</template>

```

## ConfirmModal

- Path: `frontend/src/components/shared/ConfirmModal.vue`
- Modal confirmation surface for destructive actions.

```vue
<script setup lang="ts">
import Modal from "./Modal.vue";

defineProps<{
  show: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  loading?: boolean;
  destructive?: boolean;
}>();

const emit = defineEmits<{
  confirm: [];
  close: [];
}>();
</script>

<template>
  <Modal
    :show="show"
    :title="title"
    max-width="sm"
    :close-on-backdrop="!loading"
    @close="emit('close')"
  >
    <p class="leading-relaxed text-muted-foreground/90">
      {{ message }}
    </p>

    <template #footer>
      <button
        type="button"
        class="h-9 rounded-xl border border-border bg-transparent px-4 text-sm font-medium text-foreground transition-colors hover:bg-base-content/5 disabled:opacity-50"
        :disabled="loading"
        @click="emit('close')"
      >
        {{ cancelText || $t("common.cancel") || "Cancel" }}
      </button>
      <button
        type="button"
        class="flex h-9 items-center gap-2 rounded-xl px-5 text-sm font-medium transition-all active:scale-[0.96] disabled:opacity-50"
        :class="
          destructive
            ? 'bg-error text-error-content hover:bg-error/95 shadow-sm'
            : 'bg-primary text-primary-content hover:bg-primary/95 shadow-sm'
        "
        :disabled="loading"
        @click="emit('confirm')"
      >
        <AppIcon v-if="loading" name="i-lucide-loader-2" class="size-4 animate-spin" />
        <span>{{ confirmText || $t("common.delete") || "Confirm" }}</span>
      </button>
    </template>
  </Modal>
</template>

```

## DataTable

- Path: `frontend/src/components/shared/DataTable.vue`
- Generic responsive data table shell.

```vue
<script lang="ts">
export interface DataTableColumn {
  /** Row property to render by default, and the slot name suffix: `cell-<key>`. */
  key: string;
  label: string;
  /** Extra classes for this column's <td>. */
  tdClass?: string;
  /** Extra classes for this column's <th>. */
  thClass?: string;
}
</script>

<script setup lang="ts" generic="T extends Record<string, unknown>">
import AppPagination from "@/components/shared/AppPagination.vue";

withDefaults(
  defineProps<{
    columns: DataTableColumn[];
    rows: readonly T[];
    rowKey?: string;
    page?: number;
    totalPages?: number;
  }>(),
  {
    rowKey: "id",
    page: 1,
    totalPages: 1,
  },
);

const emit = defineEmits<{
  rowClick: [row: T];
  "update:page": [page: number];
}>();
</script>

<template>
  <div>
    <div class="overflow-hidden rounded-xl border bg-base-200/50">
      <table class="w-full text-left text-sm">
        <thead>
          <tr class="border-b bg-base-300/30">
            <th
              v-for="col in columns"
              :key="col.key"
              class="px-4 py-2.5 font-cinzel text-3xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
              :class="col.thClass"
            >
              {{ col.label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in rows"
            :key="String(row[rowKey])"
            class="cursor-pointer border-b border-border/50 transition-colors last:border-0 hover:bg-base-300/40"
            @click="emit('rowClick', row)"
          >
            <td v-for="col in columns" :key="col.key" class="px-4 py-2.5" :class="col.tdClass">
              <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">
                {{ row[col.key] }}
              </slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <AppPagination
      v-if="totalPages > 1"
      :page="page"
      :total-pages="totalPages"
      class="mt-5"
      @update:page="emit('update:page', $event)"
    />
  </div>
</template>

```

## EmptyState

- Path: `frontend/src/components/shared/EmptyState.vue`
- Illustrated empty-state pattern with optional action.

```vue
<script setup lang="ts">
interface Props {
  icon?: string;
  title?: string;
  description?: string;
  actionLabel?: string;
  hasFilters?: boolean;
}

withDefaults(defineProps<Props>(), {
  icon: "i-lucide-flame",
  title: "",
  description: "",
  actionLabel: "",
  hasFilters: false,
});

defineEmits<{
  action: [];
}>();
</script>

<template>
  <div
    class="flex w-full flex-1 animate-fade-in-up flex-col items-center justify-start px-4 pt-[12vh] pb-12 text-center"
  >
    <!-- Icon with pulsing glow -->
    <div class="relative mb-6">
      <div class="absolute inset-0 animate-pulse rounded-full bg-primary/20 blur-xl" />
      <div class="relative flex size-16 items-center justify-center rounded-full bg-primary/10">
        <AppIcon :name="icon" class="size-8 text-primary" />
      </div>
    </div>

    <h3 class="mb-2 font-cinzel text-lg font-semibold text-foreground">
      <slot name="title">
        {{ title || (hasFilters ? $t("characters.noFound") : $t("characters.libraryAwaits")) }}
      </slot>
    </h3>
    <p class="mb-6 max-w-sm text-sm text-muted-foreground">
      <slot name="description">
        {{
          description || (hasFilters ? $t("characters.tryFilters") : $t("characters.createFirst"))
        }}
      </slot>
    </p>

    <slot name="action">
      <button
        v-if="actionLabel || (!hasFilters && !title)"
        class="flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-content transition-colors hover:bg-primary/90"
        @click="$emit('action')"
      >
        <AppIcon name="i-lucide-plus" class="size-4" />
        {{ actionLabel || $t("characters.createNew") }}
      </button>
    </slot>
  </div>
</template>

```

## Modal

- Path: `frontend/src/components/shared/Modal.vue`
- Teleported accessible modal/dialog shell.

```vue
<script lang="ts">
// Shared across all Modal instances so only the top-most open dialog traps keys
// (Escape/Tab). Without this, a modal stacked over another (e.g. a confirm over
// an editor) means both keydown handlers fire and fight over focus.
const modalStack: symbol[] = [];
</script>

<script setup lang="ts">
import { nextTick, onUnmounted, ref, useId, watch } from "vue";

const props = withDefaults(
  defineProps<{
    show: boolean;
    title?: string;
    maxWidth?: "sm" | "md" | "lg" | "xl" | "2xl" | "3xl" | "4xl";
    closeOnBackdrop?: boolean;
  }>(),
  {
    maxWidth: "md",
    closeOnBackdrop: true,
  },
);

const emit = defineEmits<{
  close: [];
}>();

const titleId = useId();
const panelRef = ref<HTMLElement | null>(null);
// The element focused before the dialog opened, so focus can return to it on close.
let previouslyFocused: HTMLElement | null = null;
// Identity for this instance in the shared modal stack (top-most traps keys).
const instanceId = Symbol("modal");
function removeFromStack() {
  const i = modalStack.indexOf(instanceId);
  if (i !== -1) modalStack.splice(i, 1);
}
const isTopModal = () => modalStack[modalStack.length - 1] === instanceId;

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

function focusableEls(): HTMLElement[] {
  if (!panelRef.value) return [];
  return Array.from(panelRef.value.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
    (el) => el.offsetParent !== null,
  );
}

// Removal is driven by a plain timer, not a Vue <Transition> leave callback.
// Nested transitions + teleports can drop the leave hook (the modal opens but
// never unmounts); a setTimeout always fires. `visible` gates mounting;
// `entered` drives the enter/leave CSS so the animation still plays.
const DURATION = 200;
const visible = ref(props.show);
const entered = ref(props.show);
let closeTimer: ReturnType<typeof setTimeout> | undefined;

const handleKeyDown = (e: KeyboardEvent) => {
  if (!props.show) return;
  // Only the top-most open modal handles keys; a stacked modal below stays inert.
  if (!isTopModal()) return;
  if (e.key === "Escape") {
    emit("close");
    return;
  }
  // Trap Tab within the panel so focus can't escape to the obscured page behind
  // the backdrop; wrap around at both ends.
  if (e.key === "Tab") {
    const els = focusableEls();
    const active = document.activeElement as HTMLElement | null;
    if (els.length === 0) {
      e.preventDefault();
      panelRef.value?.focus();
      return;
    }
    const first = els[0];
    const last = els[els.length - 1];
    // Recapture to the far end whenever focus is on a boundary element, on the
    // bare panel container, or has escaped the panel entirely — so Tab/Shift+Tab
    // wrap inside the dialog instead of leaking to the page behind the backdrop.
    const onTabbable = !!active && els.includes(active);
    if (e.shiftKey && (active === first || !onTabbable)) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && (active === last || !onTabbable)) {
      e.preventDefault();
      first.focus();
    }
  }
};

watch(
  () => props.show,
  (show) => {
    if (closeTimer) clearTimeout(closeTimer);
    if (show) {
      previouslyFocused = document.activeElement as HTMLElement | null;
      modalStack.push(instanceId);
      visible.value = true;
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
      // Mount at the "from" state, then flip on the next frame so the CSS transition runs.
      entered.value = false;
      requestAnimationFrame(() => requestAnimationFrame(() => (entered.value = true)));
      // Focus the first focusable control (not the bare panel) once rendered, so
      // the tab trap has a real anchor — otherwise the first Shift+Tab, from the
      // untabbable panel, escapes to the page behind the backdrop. Fall back to
      // the panel only when the dialog has no focusable children.
      void nextTick(() => {
        const els = focusableEls();
        (els[0] ?? panelRef.value)?.focus();
      });
    } else {
      entered.value = false;
      removeFromStack();
      // Keep scroll locked while any modal remains open beneath this one.
      document.body.style.overflow = modalStack.length > 0 ? "hidden" : "";
      window.removeEventListener("keydown", handleKeyDown);
      closeTimer = setTimeout(() => (visible.value = false), DURATION);
      // Return focus to whatever launched the dialog (only when we were open).
      if (previouslyFocused) {
        previouslyFocused.focus();
        previouslyFocused = null;
      }
    }
  },
  { immediate: true },
);

onUnmounted(() => {
  if (closeTimer) clearTimeout(closeTimer);
  removeFromStack();
  document.body.style.overflow = modalStack.length > 0 ? "hidden" : "";
  window.removeEventListener("keydown", handleKeyDown);
});

const maxWidthClass = {
  sm: "max-w-sm",
  md: "max-w-md",
  lg: "max-w-lg",
  xl: "max-w-xl",
  "2xl": "max-w-2xl",
  "3xl": "max-w-3xl",
  "4xl": "max-w-4xl",
}[props.maxWidth];
</script>

<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="title ? titleId : undefined"
    >
      <!-- Backdrop -->
      <div
        class="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity duration-200"
        :class="entered ? 'opacity-100' : 'opacity-0'"
        @click="closeOnBackdrop && emit('close')"
      />

      <!-- Panel -->
      <div
        ref="panelRef"
        tabindex="-1"
        :class="[
          'relative z-10 max-h-[90vh] w-full overflow-y-auto rounded-2xl border border-base-content/10 bg-base-200/95 p-6 shadow-2xl backdrop-blur-md transition-all duration-200 ease-out outline-none',
          entered ? 'scale-100 opacity-100' : 'scale-95 opacity-0',
          maxWidthClass,
        ]"
      >
        <!-- Header -->
        <div class="mb-4 flex items-start justify-between gap-4">
          <slot name="header">
            <h2
              v-if="title"
              :id="titleId"
              class="font-cinzel text-lg font-bold tracking-wide text-foreground"
            >
              {{ title }}
            </h2>
          </slot>
          <button
            class="flex size-8 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-all hover:bg-base-content/10 hover:text-foreground active:scale-95"
            :aria-label="$t('common.close')"
            @click="emit('close')"
          >
            <AppIcon name="i-lucide-x" class="size-4" />
          </button>
        </div>

        <!-- Content -->
        <div class="text-sm text-muted-foreground">
          <slot />
        </div>

        <!-- Footer -->
        <div v-if="$slots.footer" class="mt-6 flex items-center justify-end gap-3">
          <slot name="footer" />
        </div>
      </div>
    </div>
  </Teleport>
</template>

```

## SearchBar

- Path: `frontend/src/components/shared/SearchBar.vue`
- Home-library search input with focus treatment.

```vue
<script setup lang="ts">
import { ref } from "vue";

const focused = ref(false);
const query = ref("");
</script>

<template>
  <div class="relative">
    <div
      class="flex items-center gap-3 rounded-xl border px-4 py-3 transition-all duration-300"
      :class="
        focused
          ? 'border-primary bg-base-100 shadow-[0_0_0_3px_var(--color-primary)/0.12]'
          : 'border-border bg-base-300/40 hover:border-muted-foreground/30'
      "
    >
      <AppIcon
        name="i-lucide-search"
        class="size-5 shrink-0 transition-colors duration-300"
        :class="focused ? 'text-primary' : 'text-muted-foreground'"
      />
      <input
        v-model="query"
        type="text"
        :placeholder="$t('home.searchPlaceholder')"
        :aria-label="$t('common.search')"
        autocomplete="off"
        class="flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
        @focus="focused = true"
        @blur="focused = false"
      />
    </div>
  </div>
</template>

```

## SelectMenu

- Path: `frontend/src/components/shared/SelectMenu.vue`
- Searchable teleported select/listbox.

```vue
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
        class="fixed z-[80] overflow-hidden rounded-lg border bg-base-200 shadow-lg"
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

```

## Tabs

- Path: `frontend/src/components/shared/Tabs.vue`
- Reusable tab row.

```vue
<script setup lang="ts">
interface Tab {
  key: string;
  label: string;
}

defineProps<{
  tabs: Tab[];
  modelValue: string;
}>();

defineEmits<{
  "update:modelValue": [key: string];
}>();
</script>

<template>
  <div class="flex items-center gap-1 border-b px-2">
    <button
      v-for="tab in tabs"
      :key="tab.key"
      class="relative px-3 py-2.5 text-xs font-medium transition-colors"
      :class="
        modelValue === tab.key ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'
      "
      @click="$emit('update:modelValue', tab.key)"
    >
      <span class="font-cinzel tracking-wide">{{ tab.label }}</span>
      <span
        v-if="modelValue === tab.key"
        class="absolute inset-x-2 bottom-0 h-0.5 rounded-full bg-primary transition-all"
      />
    </button>
  </div>
</template>

```

## ToastContainer

- Path: `frontend/src/components/shared/ToastContainer.vue`
- Global toast surface and transitions.

```vue
<script setup lang="ts">
import { useAppToast } from "@/composables/useToast";

const { toasts, removeToast } = useAppToast();

const getIcon = (type: string) => {
  switch (type) {
    case "success":
      return "i-lucide-circle-check";
    case "error":
      return "i-lucide-circle-alert";
    case "warning":
      return "i-lucide-triangle-alert";
    default:
      return "i-lucide-info";
  }
};

const getTypeClasses = (type: string) => {
  switch (type) {
    case "success":
      return {
        border: "border-emerald-500/20 bg-emerald-50 dark:bg-emerald-950/85",
        text: "text-emerald-900 dark:text-emerald-100",
        desc: "text-emerald-700 dark:text-emerald-300",
        icon: "text-emerald-600/90 dark:text-emerald-400",
      };
    case "error":
      return {
        border: "border-error/20 bg-red-50 dark:bg-red-950/85",
        text: "text-red-900 dark:text-red-100",
        desc: "text-red-700 dark:text-red-300",
        icon: "text-red-600/90 dark:text-red-400",
      };
    case "warning":
      return {
        border: "border-amber-500/20 bg-amber-50 dark:bg-amber-950/85",
        text: "text-amber-900 dark:text-amber-100",
        desc: "text-amber-700 dark:text-amber-300",
        icon: "text-amber-600/90 dark:text-amber-400",
      };
    default:
      return {
        border: "border-stone-200 dark:border-white/10 bg-white dark:bg-stone-900/85",
        text: "text-stone-900 dark:text-stone-100",
        desc: "text-stone-600 dark:text-stone-400",
        icon: "text-primary",
      };
  }
};
</script>

<template>
  <Teleport to="body">
    <div
      class="pointer-events-none fixed top-0 right-0 z-[100] flex w-full max-w-sm flex-col gap-3 p-4 sm:p-6"
    >
      <TransitionGroup
        enter-active-class="transform ease-out duration-300 transition"
        enter-from-class="translate-y-2 opacity-0 sm:translate-y-0 sm:translate-x-2"
        enter-to-class="translate-y-0 opacity-100 sm:translate-x-0"
        leave-active-class="transition ease-in duration-100"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0 font-medium"
      >
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="pointer-events-auto flex w-full overflow-hidden rounded-xl border p-4 shadow-2xl backdrop-blur-md"
          :class="[getTypeClasses(toast.type).border, getTypeClasses(toast.type).text]"
        >
          <div class="flex w-full items-start gap-3">
            <AppIcon
              :name="getIcon(toast.type)"
              class="mt-0.5 size-5 shrink-0"
              :class="getTypeClasses(toast.type).icon"
            />
            <div class="min-w-0 flex-1">
              <h4 class="font-cinzel text-xs font-semibold tracking-wider text-current uppercase">
                {{ toast.title }}
              </h4>
              <p
                v-if="toast.description"
                class="mt-1 text-xs leading-relaxed"
                :class="getTypeClasses(toast.type).desc"
              >
                {{ toast.description }}
              </p>
            </div>
            <button
              class="flex size-5 shrink-0 items-center justify-center rounded text-current/60 transition-colors hover:bg-current/10 hover:text-current active:scale-95"
              @click="removeToast(toast.id)"
            >
              <AppIcon name="i-lucide-x" class="size-3.5" />
            </button>
          </div>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

```


