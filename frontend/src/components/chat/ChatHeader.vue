<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import type { ChatCharacterInfo } from "@/types/chat";
import type { Profile } from "@/composables/useProfiles";
import ChatProfilePicker from "@/components/chat/ChatProfilePicker.vue";
import ChatModelPicker from "@/components/chat/ChatModelPicker.vue";

interface PickerModel {
  id: string;
  display_name: string;
}

const props = defineProps<{
  character: ChatCharacterInfo;
  sessionTitle: string;
  profiles?: Profile[];
  currentProfileName?: string | null;
  models?: PickerModel[];
  currentModelId?: string | null;
  currentModelName?: string | null;
}>();

const emit = defineEmits<{
  back: [];
  rename: [title: string];
  delete: [];
  applyProfile: [profileId: string];
  changeModel: [modelId: string];
}>();

const menuOpen = ref(false);
const renaming = ref(false);
const editTitle = ref("");
const confirmDelete = ref(false);
let deleteTimer: ReturnType<typeof setTimeout> | null = null;
const menuRef = ref<HTMLElement | null>(null);

function avatarSrc(): string {
  return (
    props.character.avatar_thumbnail ||
    props.character.avatar ||
    `https://ui-avatars.com/api/?name=${encodeURIComponent(props.character.name)}&background=C9922E&color=fff&size=80`
  );
}

function toggleMenu() {
  menuOpen.value = !menuOpen.value;
  confirmDelete.value = false;
}

function startRename() {
  editTitle.value = props.sessionTitle;
  renaming.value = true;
  menuOpen.value = false;
}

function saveRename() {
  const trimmed = editTitle.value.trim();
  if (trimmed && trimmed !== props.sessionTitle) {
    emit("rename", trimmed);
  }
  renaming.value = false;
}

function cancelRename() {
  renaming.value = false;
}

function handleRenameKeydown(e: KeyboardEvent) {
  if (e.key === "Enter") {
    e.preventDefault();
    saveRename();
  } else if (e.key === "Escape") {
    cancelRename();
  }
}

function handleDelete() {
  if (confirmDelete.value) {
    emit("delete");
    menuOpen.value = false;
    confirmDelete.value = false;
  } else {
    confirmDelete.value = true;
    if (deleteTimer) clearTimeout(deleteTimer);
    deleteTimer = setTimeout(() => {
      confirmDelete.value = false;
    }, 3000);
  }
}

function handleClickOutside(e: MouseEvent) {
  if (menuRef.value && !menuRef.value.contains(e.target as Node)) {
    menuOpen.value = false;
    confirmDelete.value = false;
  }
}

onMounted(() => {
  document.addEventListener("click", handleClickOutside, true);
});

onUnmounted(() => {
  document.removeEventListener("click", handleClickOutside, true);
  if (deleteTimer) clearTimeout(deleteTimer);
});
</script>

<template>
  <header
    class="z-10 flex h-15.5 shrink-0 items-center justify-between border-b bg-base-100/80 px-5 backdrop-blur-sm"
  >
    <button
      :aria-label="$t('common.goBack')"
      class="flex size-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
      @click="emit('back')"
    >
      <AppIcon name="i-lucide-arrow-left" class="size-5" />
    </button>

    <div class="flex items-center gap-3">
      <div class="relative">
        <img
          :src="avatarSrc()"
          :alt="character.name"
          class="size-9 rounded-full object-cover ring-2 ring-primary/30"
        />
        <div
          class="absolute right-0 bottom-0 size-2.5 rounded-full border-2 border-base-100 bg-emerald-500"
        />
      </div>
      <div class="text-center">
        <h2
          class="font-cinzel text-sm leading-tight font-semibold text-foreground"
          style="letter-spacing: 0.03em"
        >
          {{ character.name }}
        </h2>
        <template v-if="renaming">
          <input
            v-model="editTitle"
            class="mt-0.5 w-full rounded border border-primary/40 bg-base-300/40 px-1.5 py-0.5 text-center text-[0.6875rem] leading-tight text-foreground outline-none focus:ring-1 focus:ring-primary/30"
            autofocus
            @keydown="handleRenameKeydown"
            @blur="saveRename"
          />
        </template>
        <template v-else>
          <p class="mt-0.5 text-[0.6875rem] leading-tight text-muted-foreground">
            {{ sessionTitle }}
          </p>
        </template>
      </div>
    </div>

    <div class="flex items-center gap-2">
      <ChatModelPicker
        :models="models ?? []"
        :current-model-id="currentModelId"
        :current-model-name="currentModelName"
        @change="emit('changeModel', $event)"
      />

      <ChatProfilePicker
        :profiles="profiles ?? []"
        :current-profile-name="currentProfileName"
        @apply="emit('applyProfile', $event)"
      />

      <div ref="menuRef" class="relative">
        <button
          :aria-label="$t('chat.sessionMenu')"
          class="flex size-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
          @click="toggleMenu"
        >
          <AppIcon name="i-lucide-more-horizontal" class="size-5" />
        </button>

        <!-- Dropdown Menu -->
        <div
          v-if="menuOpen"
          class="absolute top-full right-0 mt-1 min-w-40 rounded-lg border bg-base-200 py-1 shadow-lg"
        >
          <button
            class="flex w-full items-center gap-2 px-3 py-2 text-sm text-foreground transition-colors hover:bg-base-300/50"
            @click="startRename"
          >
            <AppIcon name="i-lucide-pencil" class="size-4" />
            {{ $t("chat.rename") }}
          </button>
          <button
            class="flex w-full items-center gap-2 px-3 py-2 text-sm transition-colors hover:bg-base-300/50"
            :class="confirmDelete ? 'text-error font-medium' : 'text-error'"
            @click="handleDelete"
          >
            <AppIcon name="i-lucide-trash-2" class="size-4" />
            {{ confirmDelete ? $t("common.deleteConfirm") : $t("common.delete") }}
          </button>
        </div>
      </div>
    </div>
  </header>
</template>
