<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { useModel } from "@/composables/useModel";
import { useProviders } from "@/composables/useProviders";
import { useModelFamilies } from "@/composables/useModelFamilies";
import { useAppToast } from "@/composables/useToast";
import Modal from "@/components/shared/Modal.vue";
import ModelForm from "./ModelForm.vue";
import type { components } from "@/api/schema";

// Shared "create a model" modal used both by the Models tab ("New Model") and
// by a provider's "Add as Model" action, so the latter opens in place instead
// of navigating away (cancel just closes and leaves you where you were).
defineProps<{
  show: boolean;
  prefill?: { provider_id?: string; model_identifier?: string; name?: string };
}>();

const emit = defineEmits<{
  close: [];
  created: [];
}>();

const { createModel, saving } = useModel();
const { providers } = useProviders();
const { families } = useModelFamilies({ pageSize: 100 });
const toast = useAppToast();
const { t } = useI18n();

async function onSubmit(payload: components["schemas"]["ModelCreate"]) {
  try {
    await createModel(payload);
    toast.success(t("connections.model.toast.created"));
    emit("created");
    emit("close");
  } catch {
    toast.error(t("connections.model.toast.createFailed"));
  }
}
</script>

<template>
  <Modal :show="show" :title="$t('connections.newModel')" max-width="2xl" @close="emit('close')">
    <ModelForm
      :providers="providers"
      :families="families"
      :prefill="prefill"
      :saving="saving"
      @submit="onSubmit"
      @cancel="emit('close')"
    />
  </Modal>
</template>
