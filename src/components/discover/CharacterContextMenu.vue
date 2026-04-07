<script setup lang="ts">
import { ref } from "vue";

defineEmits<{
  action: [name: string];
}>();

const open = ref(false);

const actions = [
  { name: "start-tale", label: "Start Tale", icon: "i-lucide-book-open" },
  { name: "edit", label: "Edit", icon: "i-lucide-pencil" },
  { name: "duplicate", label: "Duplicate", icon: "i-lucide-copy" },
  { name: "export-json", label: "Export JSON", icon: "i-lucide-file-json" },
  { name: "delete", label: "Delete", icon: "i-lucide-trash-2", destructive: true },
];
</script>

<template>
  <div class="relative">
    <button
      class="flex h-7 w-7 items-center justify-center rounded-md transition-colors hover:bg-white/20"
      @click.stop="open = !open"
    >
      <UIcon name="i-lucide-ellipsis-vertical" class="h-4 w-4" />
    </button>

    <Transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="scale-95 opacity-0"
      enter-to-class="scale-100 opacity-100"
      leave-active-class="transition duration-100 ease-in"
      leave-from-class="scale-100 opacity-100"
      leave-to-class="scale-95 opacity-0"
    >
      <div
        v-if="open"
        class="absolute right-0 bottom-full z-50 mb-1 w-44 origin-bottom-right rounded-lg border border-border bg-popover py-1 shadow-lg"
        @blur.capture="open = false"
        tabindex="-1"
        ref="menuRef"
      >
        <div
          class="fixed inset-0 z-[-1]"
          @click.stop="open = false"
        />
        <button
          v-for="item in actions"
          :key="item.name"
          class="flex w-full items-center gap-2 px-3 py-1.5 text-sm transition-colors"
          :class="
            item.destructive
              ? 'text-destructive hover:bg-destructive/10'
              : 'text-popover-foreground hover:bg-muted/60'
          "
          @click.stop="
            $emit('action', item.name);
            open = false;
          "
        >
          <UIcon :name="item.icon" class="h-3.5 w-3.5" />
          {{ item.label }}
        </button>
      </div>
    </Transition>
  </div>
</template>
