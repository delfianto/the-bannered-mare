<script setup lang="ts">
import { ref } from "vue";

defineProps<{
  avatarUrl: string;
}>();

const emit = defineEmits<{
  change: [file: File];
}>();

const dragOver = ref(false);
const inputRef = ref<HTMLInputElement | null>(null);

function handleFile(file: File) {
  if (!file.type.startsWith("image/")) return;
  emit("change", file);
}

function onDrop(e: DragEvent) {
  e.preventDefault();
  dragOver.value = false;
  const file = e.dataTransfer?.files[0];
  if (file) handleFile(file);
}

function onChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (file) handleFile(file);
}
</script>

<template>
  <div class="space-y-2">
    <label class="pl-0.5 text-sm font-medium text-foreground">Portrait</label>
    <div
      class="relative aspect-3/4 w-full max-w-50 cursor-pointer overflow-hidden rounded-xl transition-all hover:scale-[1.01]"
      :class="
        avatarUrl
          ? 'border-2 border-border'
          : `border-2 border-dashed ${dragOver ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/40'}`
      "
      @click="inputRef?.click()"
      @dragover.prevent="dragOver = true"
      @dragleave="dragOver = false"
      @drop="onDrop"
    >
      <template v-if="avatarUrl">
        <img
          :src="avatarUrl"
          alt="Character portrait"
          class="absolute inset-0 size-full object-cover object-top"
        />
        <div
          class="group absolute inset-0 flex items-center justify-center bg-black/0 transition-colors hover:bg-black/40"
        >
          <div
            class="flex flex-col items-center gap-1.5 opacity-0 transition-opacity group-hover:opacity-100"
          >
            <AppIcon name="i-lucide-camera" class="size-6 text-white" />
            <span class="text-xs font-medium text-white">Change</span>
          </div>
        </div>
      </template>
      <template v-else>
        <div class="absolute inset-0 flex flex-col items-center justify-center gap-3 px-4">
          <div class="flex size-12 items-center justify-center rounded-full bg-base-300">
            <AppIcon
              name="i-lucide-image-plus"
              class="size-6"
              :class="dragOver ? 'text-primary' : 'text-muted-foreground'"
            />
          </div>
          <div class="text-center">
            <p class="text-xs font-medium text-foreground">Drop image here</p>
            <p class="mt-0.5 text-2xs text-muted-foreground">or click to browse</p>
          </div>
        </div>
      </template>
      <input ref="inputRef" type="file" accept="image/*" class="hidden" @change="onChange" />
    </div>
  </div>
</template>
