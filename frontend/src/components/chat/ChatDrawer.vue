<script setup lang="ts">
import { onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import type { ChatCharacterInfo } from "@/types/chat";
import type { Profile } from "@/composables/useProfiles";
import { useCharacter } from "@/composables/useCharacter";
import Tabs from "@/components/shared/Tabs.vue";
import CollapsibleSection from "@/components/shared/CollapsibleSection.vue";
import CollapsibleField from "@/components/discover/CollapsibleField.vue";

interface PickerModel {
  id: string;
  display_name: string;
}

const props = defineProps<{
  show: boolean;
  character: ChatCharacterInfo;
  sessionTitle: string;
  models: PickerModel[];
  currentModelId?: string | null;
  profiles: Profile[];
  currentProfileName?: string | null;
}>();

const emit = defineEmits<{
  close: [];
  changeModel: [modelId: string];
  applyProfile: [profileId: string];
  rename: [title: string];
  delete: [];
}>();

const router = useRouter();
const { t } = useI18n();

// Mirror Modal.vue's timer-driven open/close: `visible` gates mounting,
// `entered` drives the slide/fade CSS (nested transitions can drop leave hooks).
const DURATION = 200;
const visible = ref(props.show);
const entered = ref(props.show);
let closeTimer: ReturnType<typeof setTimeout> | undefined;

const tabs = [
  { key: "character", label: t("chat.drawer.tabs.character") },
  { key: "settings", label: t("chat.drawer.tabs.settings") },
  { key: "session", label: t("chat.drawer.tabs.session") },
  { key: "logs", label: t("chat.drawer.tabs.logs") },
];
const activeTab = ref("character");

const { character: fullCharacter, loading: characterLoading, load: loadCharacter } = useCharacter();

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === "Escape" && props.show) emit("close");
}

watch(
  () => props.show,
  (show) => {
    if (closeTimer) clearTimeout(closeTimer);
    if (show) {
      visible.value = true;
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
      entered.value = false;
      requestAnimationFrame(() => requestAnimationFrame(() => (entered.value = true)));
    } else {
      entered.value = false;
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleKeyDown);
      closeTimer = setTimeout(() => (visible.value = false), DURATION);
    }
  },
  { immediate: true },
);

// Lazy-fetch the full character only while the Character tab is on screen; the
// composable dedupes by id so reopening the drawer won't refetch, but switching
// chats (new id) will.
watch(
  [() => props.show, activeTab, () => props.character.id],
  ([show, tab, id]) => {
    if (show && tab === "character" && id) void loadCharacter(id);
  },
  { immediate: true },
);

onUnmounted(() => {
  if (closeTimer) clearTimeout(closeTimer);
  document.body.style.overflow = "";
  window.removeEventListener("keydown", handleKeyDown);
});

// --- Character tab helpers ---

function portraitSrc(): string {
  const c = fullCharacter.value;
  if (!c) return "";
  // Large tier (<=512px): the drawer portrait renders a few hundred px wide, so
  // the large avatar stays sharp while far lighter than the original.
  return (
    c.avatar_large ||
    c.avatar ||
    `https://ui-avatars.com/api/?name=${encodeURIComponent(c.name)}&background=C9922E&color=fff&size=400`
  );
}

function genderLabel(): string {
  const c = fullCharacter.value;
  if (!c?.gender) return "";
  if (c.gender === "others" && c.custom_gender) return c.custom_gender;
  return c.gender.charAt(0).toUpperCase() + c.gender.slice(1);
}

// --- Loadouts (model + profile) ---

function chooseModel(m: PickerModel) {
  if (m.id !== props.currentModelId) emit("changeModel", m.id);
}

function chooseProfile(p: Profile) {
  // Always (re-)apply — re-applying the current profile re-pulls its latest axes.
  emit("applyProfile", p.id);
}

function goManageLoadouts() {
  emit("close");
  router.push("/loadouts");
}

// --- Rename & Delete (relocated from ChatHeader) ---

const editTitle = ref(props.sessionTitle);
const confirmDelete = ref(false);
let deleteTimer: ReturnType<typeof setTimeout> | null = null;

// Keep the rename field in sync when the drawer (re)opens or the title changes
// elsewhere — the input is persistent, not remounted per open.
watch(
  () => [props.show, props.sessionTitle] as const,
  ([show]) => {
    if (show) editTitle.value = props.sessionTitle;
  },
);

function saveRename() {
  const trimmed = editTitle.value.trim();
  if (trimmed && trimmed !== props.sessionTitle) emit("rename", trimmed);
}

function handleRenameKeydown(e: KeyboardEvent) {
  if (e.key === "Enter") {
    e.preventDefault();
    (e.target as HTMLInputElement).blur();
  }
}

function handleDelete() {
  if (confirmDelete.value) {
    emit("delete");
    confirmDelete.value = false;
  } else {
    confirmDelete.value = true;
    if (deleteTimer) clearTimeout(deleteTimer);
    deleteTimer = setTimeout(() => (confirmDelete.value = false), 3000);
  }
}

onUnmounted(() => {
  if (deleteTimer) clearTimeout(deleteTimer);
});
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="fixed inset-0 z-50" role="dialog" aria-modal="true">
      <!-- Backdrop -->
      <div
        class="fixed inset-0 bg-black/50 backdrop-blur-[2px] transition-opacity duration-200"
        :class="entered ? 'opacity-100' : 'opacity-0'"
        @click="emit('close')"
      />

      <!-- Panel (slides in from the right) -->
      <div
        class="fixed inset-y-0 right-0 flex w-96 max-w-full flex-col border-l bg-base-200 shadow-2xl transition-transform duration-200 ease-out"
        :class="entered ? 'translate-x-0' : 'translate-x-full'"
      >
        <!-- Header -->
        <div class="flex h-15.5 shrink-0 items-center justify-between border-b px-4">
          <h2
            class="min-w-0 truncate font-cinzel text-sm font-semibold tracking-wide text-foreground"
          >
            {{ character.name }}
          </h2>
          <button
            :aria-label="$t('common.close')"
            class="flex size-8 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
            @click="emit('close')"
          >
            <AppIcon name="i-lucide-x" class="size-4" />
          </button>
        </div>

        <!-- Tabs -->
        <Tabs v-model="activeTab" :tabs="tabs" class="shrink-0" />

        <!-- Body -->
        <div class="flex-1 overflow-y-auto">
          <!-- Character tab -->
          <div v-if="activeTab === 'character'" class="p-4">
            <div v-if="characterLoading && !fullCharacter" class="flex justify-center py-12">
              <AppIcon
                name="i-lucide-loader-circle"
                class="size-6 animate-spin text-muted-foreground"
              />
            </div>

            <div v-else-if="fullCharacter" class="space-y-4">
              <!-- Portrait -->
              <div class="overflow-hidden rounded-xl border bg-base-100/50">
                <img
                  :src="portraitSrc()"
                  :alt="fullCharacter.name"
                  class="aspect-3/4 w-full object-cover object-top"
                />
              </div>

              <div class="text-center">
                <h3 class="font-cinzel text-base font-semibold tracking-wide text-foreground">
                  {{ fullCharacter.name }}
                </h3>
              </div>

              <!-- Gender / species / tags chips -->
              <div
                v-if="genderLabel() || fullCharacter.species || fullCharacter.tags?.length"
                class="flex flex-wrap justify-center gap-1.5"
              >
                <span
                  v-if="genderLabel()"
                  class="rounded-full bg-base-300 px-2.5 py-0.5 text-[0.625rem] font-medium tracking-wide text-base-content uppercase"
                >
                  {{ genderLabel() }}
                </span>
                <span
                  v-if="fullCharacter.species"
                  class="rounded-full bg-base-300 px-2.5 py-0.5 text-[0.625rem] font-medium tracking-wide text-base-content uppercase"
                >
                  {{ fullCharacter.species }}
                </span>
                <span
                  v-for="tag in fullCharacter.tags ?? []"
                  :key="tag"
                  class="rounded-full bg-base-300 px-2.5 py-0.5 text-[0.625rem] font-medium tracking-wide text-base-content uppercase"
                >
                  {{ tag }}
                </span>
              </div>

              <!-- Long-form fields (only when present) -->
              <div class="space-y-2">
                <CollapsibleField
                  v-if="fullCharacter.description"
                  :label="$t('characters.detail.description')"
                  :content="fullCharacter.description"
                />
                <CollapsibleField
                  v-if="fullCharacter.personality"
                  :label="$t('characters.detail.personality')"
                  :content="fullCharacter.personality"
                />
                <CollapsibleField
                  v-if="fullCharacter.scenario"
                  :label="$t('characters.detail.scenario')"
                  :content="fullCharacter.scenario"
                />
              </div>
            </div>

            <div v-else class="py-12 text-center text-xs text-muted-foreground">
              {{ $t("characters.notFound") }}
            </div>
          </div>

          <!-- Settings tab -->
          <div v-else-if="activeTab === 'settings'" class="space-y-3 p-4">
            <!-- Loadouts -->
            <CollapsibleSection
              :title="$t('chat.drawer.loadouts')"
              icon="i-lucide-layers"
              :default-open="true"
            >
              <div class="space-y-3">
                <!-- Model -->
                <div>
                  <div
                    class="px-1 py-1 text-[0.625rem] font-semibold tracking-wider text-muted-foreground uppercase"
                  >
                    {{ $t("chat.model.title") }}
                  </div>
                  <button
                    v-for="m in models"
                    :key="m.id"
                    class="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left transition-colors hover:bg-base-300/50"
                    @click="chooseModel(m)"
                  >
                    <AppIcon
                      name="i-lucide-check"
                      class="size-3.5 shrink-0"
                      :class="m.id === currentModelId ? 'text-primary' : 'text-transparent'"
                    />
                    <span class="block min-w-0 truncate font-cinzel text-sm text-foreground">
                      {{ m.display_name }}
                    </span>
                  </button>
                  <div
                    v-if="models.length === 0"
                    class="px-2 py-2 text-center text-xs text-muted-foreground"
                  >
                    {{ $t("chat.model.empty") }}
                  </div>
                  <p class="px-1 py-1 text-[0.625rem] leading-snug text-muted-foreground/70">
                    {{ $t("chat.model.overrideHint") }}
                  </p>
                </div>

                <div class="h-px bg-border" />

                <!-- Profile -->
                <div>
                  <div
                    class="px-1 py-1 text-[0.625rem] font-semibold tracking-wider text-muted-foreground uppercase"
                  >
                    {{ $t("chat.profile.title") }}
                  </div>
                  <button
                    v-for="p in profiles"
                    :key="p.id"
                    class="flex w-full items-start gap-2 rounded-lg px-2 py-2 text-left transition-colors hover:bg-base-300/50"
                    @click="chooseProfile(p)"
                  >
                    <AppIcon
                      name="i-lucide-check"
                      class="mt-0.5 size-3.5 shrink-0"
                      :class="p.name === currentProfileName ? 'text-primary' : 'text-transparent'"
                    />
                    <span class="min-w-0 flex-1">
                      <span class="block truncate font-cinzel text-sm text-foreground">{{
                        p.name
                      }}</span>
                      <span
                        v-if="p.description"
                        class="block truncate text-[0.6875rem] text-muted-foreground"
                      >
                        {{ p.description }}
                      </span>
                    </span>
                    <span
                      v-if="p.name === currentProfileName"
                      class="mt-0.5 shrink-0 text-[0.625rem] font-medium tracking-wider text-primary uppercase"
                    >
                      {{ $t("chat.profile.reapply") }}
                    </span>
                  </button>
                  <div
                    v-if="profiles.length === 0"
                    class="px-2 py-2 text-center text-xs text-muted-foreground"
                  >
                    {{ $t("chat.profile.empty") }}
                  </div>
                </div>

                <button
                  class="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm text-muted-foreground transition-colors hover:bg-base-300/50 hover:text-foreground"
                  @click="goManageLoadouts"
                >
                  <AppIcon name="i-lucide-settings-2" class="size-4" />
                  {{ $t("chat.drawer.manageLoadouts") }}
                </button>
              </div>
            </CollapsibleSection>

            <!-- Persona (stub) -->
            <CollapsibleSection :title="$t('chat.drawer.persona')" icon="i-lucide-user-circle">
              <p class="text-xs text-muted-foreground/70">{{ $t("chat.drawer.comingSoon") }}</p>
            </CollapsibleSection>

            <!-- Memories (stub) -->
            <CollapsibleSection :title="$t('chat.drawer.memories')" icon="i-lucide-brain">
              <p class="text-xs text-muted-foreground/70">{{ $t("chat.drawer.comingSoon") }}</p>
            </CollapsibleSection>

            <!-- Lorebooks (stub) -->
            <CollapsibleSection :title="$t('chat.drawer.lorebooks')" icon="i-lucide-book-open">
              <p class="text-xs text-muted-foreground/70">{{ $t("chat.drawer.comingSoon") }}</p>
            </CollapsibleSection>

            <div class="h-px bg-border" />

            <!-- Rename -->
            <div>
              <label
                class="mb-1.5 block font-cinzel text-xs font-semibold tracking-widest text-muted-foreground uppercase"
              >
                {{ $t("chat.rename") }}
              </label>
              <input
                v-model="editTitle"
                class="h-11 w-full rounded-lg border bg-base-300/40 px-4 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                @keydown="handleRenameKeydown"
                @blur="saveRename"
              />
            </div>

            <!-- Delete -->
            <button
              class="flex w-full items-center justify-center gap-2 rounded-lg border border-error/40 px-4 py-2.5 text-sm transition-colors hover:bg-error/10"
              :class="confirmDelete ? 'font-medium text-error' : 'text-error'"
              @click="handleDelete"
            >
              <AppIcon name="i-lucide-trash-2" class="size-4" />
              {{ confirmDelete ? $t("common.deleteConfirm") : $t("common.delete") }}
            </button>
          </div>

          <!-- Session tab (stub) -->
          <div v-else-if="activeTab === 'session'" class="p-4">
            <p class="py-8 text-center text-xs text-muted-foreground/70">
              {{ $t("chat.drawer.comingSoon") }}
            </p>
          </div>

          <!-- Logs tab (stub) -->
          <div v-else-if="activeTab === 'logs'" class="p-4">
            <p class="py-8 text-center text-xs text-muted-foreground/70">
              {{ $t("chat.drawer.comingSoon") }}
            </p>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
