<script setup lang="ts">
defineProps<{
  type: "user" | "character";
  visible: boolean;
}>();

const emit = defineEmits<{
  action: [type: string];
}>();

const characterActions = [
  { icon: "i-lucide-rotate-ccw", label: "Regenerate", key: "regen" },
  { icon: "i-lucide-copy", label: "Copy", key: "copy" },
  { icon: "i-lucide-bookmark", label: "Bookmark", key: "bookmark" },
];

const userActions = [
  { icon: "i-lucide-pencil", label: "Edit", key: "edit" },
  { icon: "i-lucide-trash-2", label: "Delete", key: "delete" },
];
</script>

<template>
  <div
    class="absolute -top-3 z-20 flex items-center gap-0.5 rounded-lg border border-border bg-card px-1 py-0.5 shadow-md transition-all duration-150"
    :class="[
      type === 'user' ? 'right-0' : 'left-12',
      visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-1 pointer-events-none',
    ]"
  >
    <button
      v-for="action in type === 'character' ? characterActions : userActions"
      :key="action.key"
      :title="action.label"
      class="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
      @click="emit('action', action.key)"
    >
      <UIcon :name="action.icon" class="h-3.5 w-3.5" />
    </button>
  </div>
</template>
