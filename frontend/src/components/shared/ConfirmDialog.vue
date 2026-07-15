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
