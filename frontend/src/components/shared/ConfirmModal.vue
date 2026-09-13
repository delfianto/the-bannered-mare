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
        class="flex h-9 items-center gap-2 rounded-xl px-5 text-sm font-medium transition-all active:scale-0.96 disabled:opacity-50"
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
