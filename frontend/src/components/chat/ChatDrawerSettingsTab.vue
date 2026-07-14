<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useModels } from "@/composables/useModels";
import { useProfiles, type Profile } from "@/composables/useProfiles";
import { usePersonas } from "@/composables/usePersonas";
import { useDataBank } from "@/composables/useDataBank";
import { useLorebooks, type LoreEntryResponse } from "@/composables/useLorebooks";
import { useConfirmAction } from "@/composables/useConfirmAction";
import CollapsibleSection from "@/components/shared/CollapsibleSection.vue";
import CollapsibleField from "@/components/discover/CollapsibleField.vue";
import AppTooltip from "@/components/shared/AppTooltip.vue";

const props = defineProps<{
  chatId?: string;
  characterId: string;
  sessionTitle: string;
  currentModelId?: string | null;
  currentModelName?: string | null;
  currentTaskModelId?: string | null;
  currentProfileName?: string | null;
  currentPersonaId?: string | null;
}>();

const emit = defineEmits<{
  changeModel: [modelId: string];
  changeTaskModel: [modelId: string | null];
  applyProfile: [profileId: string];
  changePersona: [personaId: string | null];
  rename: [title: string];
  delete: [];
  close: [];
}>();

const router = useRouter();
const { t } = useI18n();

// Picker lists sourced here (the drawer owns its own model/profile/persona data).
const { personas } = usePersonas();
const { profiles } = useProfiles();
const { models: allModels } = useModels({ pageSize: 100, initialFilters: { enabled: true } });

// Memories = this conversation's data-bank entries. Opt out of the auto-fetch so
// this instance doesn't pull the whole bank; we fetch chat-scoped below.
const {
  entries: memories,
  loading: memoriesLoading,
  fetchEntries: fetchMemories,
} = useDataBank({ autoLoad: false });

// Lorebooks applicable to this chat (character's own + global), each lazily
// expanded to its entries.
const {
  lorebooks,
  loading: lorebooksLoading,
  currentLorebook,
  fetchForChat,
  fetchLorebook,
} = useLorebooks();

// Per-lorebook entry cache so expanding one book doesn't clobber another via the
// shared `currentLorebook`, and re-expanding never refetches.
const lorebookEntries = ref<Record<string, LoreEntryResponse[]>>({});
const lorebookEntriesLoading = ref<Record<string, boolean>>({});

// Fetch memories + lorebooks when this tab mounts and whenever the chat/character
// changes (re-key resets the per-book cache).
watch(
  [() => props.chatId, () => props.characterId],
  ([chatId, characterId]) => {
    lorebookEntries.value = {};
    lorebookEntriesLoading.value = {};
    if (chatId) void fetchMemories(undefined, chatId);
    else memories.value = [];
    if (characterId) void fetchForChat(characterId);
  },
  { immediate: true },
);

async function onLorebookToggle(id: string, open: boolean) {
  if (!open || lorebookEntries.value[id]) return;
  lorebookEntriesLoading.value[id] = true;
  await fetchLorebook(id);
  if (currentLorebook.value?.id === id) {
    lorebookEntries.value[id] = currentLorebook.value.entries;
  }
  lorebookEntriesLoading.value[id] = false;
}

function goManageMemories() {
  emit("close");
  router.push("/memory");
}

function goManageLorebooks() {
  emit("close");
  router.push("/lorebooks");
}

// --- Loadouts (model + profile) ---

// Model selects use the shared searchable SelectMenu (a long model list would
// otherwise make the section a very tall scroll).
const modelItems = computed(() =>
  allModels.value.map((m) => ({ label: m.display_name, value: m.id })),
);

// Task model prepends a "Same as chat model" option; its value is "" (SelectMenu
// deals in strings), mapped back to null on the way out.
const SAME_AS_CHAT = "";
const taskModelItems = computed(() => [
  { label: t("chat.model.sameAsChat"), value: SAME_AS_CHAT },
  ...modelItems.value,
]);

// Fall back to the chat's snapshot model name so a model that isn't in the
// enabled list (e.g. a disabled/legacy one) still shows its real name here.
const currentModelLabel = computed(
  () =>
    allModels.value.find((m) => m.id === props.currentModelId)?.display_name ??
    props.currentModelName ??
    t("chat.model.none"),
);
const currentTaskModelLabel = computed(
  () =>
    allModels.value.find((m) => m.id === props.currentTaskModelId)?.display_name ??
    t("chat.model.sameAsChat"),
);

function chooseModel(id: string) {
  if (id && id !== props.currentModelId) emit("changeModel", id);
}

// "" (Same as chat model) clears the override → null. No-op when unchanged.
function chooseTaskModel(value: string) {
  const next = value === SAME_AS_CHAT ? null : value;
  if (next !== (props.currentTaskModelId ?? null)) emit("changeTaskModel", next);
}

// The chat snapshots a loadout by NAME (last_profile_name), so we resolve the
// active loadout by name to power the footer "Re-apply" button.
const activeProfile = computed(
  () => profiles.value.find((p) => p.name === props.currentProfileName) ?? null,
);

// Selecting a different loadout switches to it (the radio only fires on change,
// so re-selecting the active one is a no-op — no accidental reset).
function chooseProfile(p: Profile) {
  if (p.name !== props.currentProfileName) emit("applyProfile", p.id);
}

// Explicit re-apply of the ACTIVE loadout (footer button) — re-pulls its current
// settings, resetting manual per-chat overrides.
function reapplyActiveProfile() {
  if (activeProfile.value) emit("applyProfile", activeProfile.value.id);
}

// `null` = "None" (clears the persona). No-op when unchanged.
function choosePersona(id: string | null) {
  if (id !== (props.currentPersonaId ?? null)) emit("changePersona", id);
}

function goManageLoadouts() {
  emit("close");
  router.push("/loadouts");
}

function goManagePersonas() {
  emit("close");
  router.push({ path: "/loadouts", query: { tab: "personas" } });
}

// --- Rename & Delete (relocated from ChatHeader) ---

const editTitle = ref(props.sessionTitle);
// Two-step delete confirm (auto-disarms + clears its timer on unmount).
const { armed: confirmDelete, trigger: handleDelete } = useConfirmAction(() => emit("delete"));

// Keep the rename field in sync if the title changes elsewhere (e.g. auto-title).
watch(
  () => props.sessionTitle,
  (title) => {
    editTitle.value = title;
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
</script>

<template>
  <div class="space-y-3 p-4">
    <!-- Loadouts -->
    <CollapsibleSection
      :title="$t('chat.drawer.loadouts')"
      icon="i-lucide-layers"
      :default-open="true"
    >
      <div class="space-y-3">
        <!-- Main model -->
        <div>
          <div
            class="px-1 py-1 text-[0.625rem] font-semibold tracking-wider text-muted-foreground uppercase"
          >
            {{ $t("chat.model.mainModel") }}
          </div>
          <SelectMenu
            :model-value="currentModelId ?? null"
            :items="modelItems"
            @update:model-value="chooseModel"
          >
            <button
              class="flex h-9 w-full items-center justify-between gap-1.5 rounded-lg border bg-base-300/40 px-3 text-sm text-foreground outline-none transition-colors hover:border-muted-foreground/30"
            >
              <span class="min-w-0 truncate">{{ currentModelLabel }}</span>
              <AppIcon
                name="i-lucide-chevron-down"
                class="size-3.5 shrink-0 text-muted-foreground"
              />
            </button>
          </SelectMenu>
          <p class="px-1 py-1 text-[0.625rem] leading-snug text-muted-foreground/70">
            {{ $t("chat.model.overrideHint") }}
          </p>
        </div>

        <!-- Task model -->
        <div>
          <div
            class="px-1 py-1 text-[0.625rem] font-semibold tracking-wider text-muted-foreground uppercase"
          >
            {{ $t("chat.model.taskModel") }}
          </div>
          <SelectMenu
            :model-value="currentTaskModelId ?? ''"
            :items="taskModelItems"
            @update:model-value="chooseTaskModel"
          >
            <button
              class="flex h-9 w-full items-center justify-between gap-1.5 rounded-lg border bg-base-300/40 px-3 text-sm text-foreground outline-none transition-colors hover:border-muted-foreground/30"
            >
              <span class="min-w-0 truncate">{{ currentTaskModelLabel }}</span>
              <AppIcon
                name="i-lucide-chevron-down"
                class="size-3.5 shrink-0 text-muted-foreground"
              />
            </button>
          </SelectMenu>
        </div>

        <div class="h-px bg-border" />

        <!-- Profile -->
        <div>
          <div
            class="px-1 py-1 text-[0.625rem] font-semibold tracking-wider text-muted-foreground uppercase"
          >
            {{ $t("chat.profile.title") }}
          </div>
          <label
            v-for="p in profiles"
            :key="p.id"
            class="flex cursor-pointer items-start gap-2.5 rounded-lg border px-2.5 py-2 transition-colors"
            :class="
              p.name === currentProfileName
                ? 'border-primary/50 bg-base-300/30'
                : 'border-transparent hover:bg-base-300/50'
            "
          >
            <input
              type="radio"
              name="chat-profile"
              class="radio radio-sm radio-primary mt-0.5 shrink-0"
              :checked="p.name === currentProfileName"
              :aria-label="p.name"
              @change="chooseProfile(p)"
            />
            <span class="min-w-0 flex-1">
              <span class="block truncate text-sm font-medium text-foreground">{{ p.name }}</span>
              <span
                v-if="p.description"
                class="block truncate text-[0.6875rem] text-muted-foreground"
              >
                {{ p.description }}
              </span>
            </span>
          </label>
          <div
            v-if="profiles.length === 0"
            class="px-2 py-2 text-center text-xs text-muted-foreground"
          >
            {{ $t("chat.profile.empty") }}
          </div>
          <p class="px-1 pt-1.5 text-[0.625rem] leading-snug text-muted-foreground/70">
            {{ $t("chat.profile.hint") }}
          </p>
        </div>

        <!-- Loadout actions: manage, and re-apply the active loadout -->
        <div class="flex items-center justify-between gap-2">
          <button
            class="flex items-center gap-2 rounded-lg px-2 py-2 text-sm text-muted-foreground transition-colors hover:bg-base-300/50 hover:text-foreground"
            @click="goManageLoadouts"
          >
            <AppIcon name="i-lucide-settings-2" class="size-4" />
            {{ $t("chat.drawer.manageLoadouts") }}
          </button>
          <AppTooltip :text="$t('chat.profile.reapplyTooltip')" side="left" wide>
            <button
              :disabled="!activeProfile"
              :aria-label="$t('chat.profile.reapplyTooltip')"
              class="flex items-center gap-1.5 rounded-lg px-2 py-2 text-sm text-muted-foreground transition-colors hover:bg-base-300/50 hover:text-foreground disabled:pointer-events-none disabled:opacity-40"
              @click="reapplyActiveProfile"
            >
              <AppIcon name="i-lucide-rotate-ccw" class="size-3.5" />
              {{ $t("chat.profile.reapply") }}
            </button>
          </AppTooltip>
        </div>
      </div>
    </CollapsibleSection>

    <!-- Persona -->
    <CollapsibleSection :title="$t('chat.persona.title')" icon="i-lucide-user-circle">
      <div>
        <!-- None -->
        <button
          class="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left transition-colors hover:bg-base-300/50"
          @click="choosePersona(null)"
        >
          <AppIcon
            name="i-lucide-check"
            class="size-3.5 shrink-0"
            :class="!currentPersonaId ? 'text-primary' : 'text-transparent'"
          />
          <span class="block min-w-0 truncate text-sm font-medium text-foreground">
            {{ $t("chat.persona.none") }}
          </span>
        </button>
        <button
          v-for="p in personas"
          :key="p.id"
          class="flex w-full items-start gap-2 rounded-lg px-2 py-2 text-left transition-colors hover:bg-base-300/50"
          @click="choosePersona(p.id)"
        >
          <AppIcon
            name="i-lucide-check"
            class="mt-0.5 size-3.5 shrink-0"
            :class="p.id === currentPersonaId ? 'text-primary' : 'text-transparent'"
          />
          <span class="min-w-0 flex-1">
            <span class="block truncate text-sm font-medium text-foreground">{{ p.name }}</span>
            <span
              v-if="p.description"
              class="block truncate text-[0.6875rem] text-muted-foreground"
            >
              {{ p.description }}
            </span>
          </span>
        </button>

        <button
          class="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm text-muted-foreground transition-colors hover:bg-base-300/50 hover:text-foreground"
          @click="goManagePersonas"
        >
          <AppIcon name="i-lucide-settings-2" class="size-4" />
          {{ $t("chat.persona.manage") }}
        </button>
      </div>
    </CollapsibleSection>

    <!-- Memories (this conversation's data-bank entries) -->
    <CollapsibleSection :title="$t('chat.drawer.memories')" icon="i-lucide-brain">
      <div class="space-y-2">
        <div v-if="memoriesLoading && memories.length === 0" class="flex justify-center py-3">
          <AppIcon
            name="i-lucide-loader-circle"
            class="size-4 animate-spin text-muted-foreground"
          />
        </div>
        <template v-else-if="memories.length">
          <CollapsibleField
            v-for="m in memories"
            :key="m.id"
            :label="m.name"
            :content="m.content"
          />
        </template>
        <p v-else class="px-1 py-2 text-xs text-muted-foreground/70">
          {{ $t("chat.drawer.memoriesEmpty") }}
        </p>

        <button
          class="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm text-muted-foreground transition-colors hover:bg-base-300/50 hover:text-foreground"
          @click="goManageMemories"
        >
          <AppIcon name="i-lucide-settings-2" class="size-4" />
          {{ $t("chat.drawer.manageMemories") }}
        </button>
      </div>
    </CollapsibleSection>

    <!-- Lorebooks (character's own + global, expandable to entries) -->
    <CollapsibleSection :title="$t('chat.drawer.lorebooks')" icon="i-lucide-book-open">
      <div class="space-y-2">
        <div v-if="lorebooksLoading && lorebooks.length === 0" class="flex justify-center py-3">
          <AppIcon
            name="i-lucide-loader-circle"
            class="size-4 animate-spin text-muted-foreground"
          />
        </div>
        <template v-else-if="lorebooks.length">
          <CollapsibleSection
            v-for="lb in lorebooks"
            :key="lb.id"
            :title="lb.name"
            @toggle="onLorebookToggle(lb.id, $event)"
          >
            <template #badge>
              <span
                class="shrink-0 rounded-full bg-base-300 px-2.5 py-0.5 text-[0.625rem] font-medium tracking-wide text-base-content uppercase"
              >
                {{
                  lb.is_global
                    ? $t("chat.drawer.lorebookGlobal")
                    : $t("chat.drawer.lorebookCharacter")
                }}
              </span>
            </template>

            <div v-if="lorebookEntriesLoading[lb.id]" class="flex justify-center py-2">
              <AppIcon
                name="i-lucide-loader-circle"
                class="size-4 animate-spin text-muted-foreground"
              />
            </div>
            <ul v-else-if="lorebookEntries[lb.id]?.length" class="space-y-2">
              <li v-for="entry in lorebookEntries[lb.id]" :key="entry.id">
                <p class="truncate text-sm text-foreground">{{ entry.name }}</p>
                <p
                  v-if="entry.keys?.length"
                  class="mt-0.5 truncate text-[0.6875rem] text-muted-foreground"
                >
                  {{ $t("chat.drawer.lorebookTriggers") }}: {{ entry.keys.join(", ") }}
                </p>
              </li>
            </ul>
            <p v-else class="py-1 text-xs text-muted-foreground/70">
              {{ $t("chat.drawer.lorebookEntriesEmpty") }}
            </p>
          </CollapsibleSection>
        </template>
        <p v-else class="px-1 py-2 text-xs text-muted-foreground/70">
          {{ $t("chat.drawer.lorebooksEmpty") }}
        </p>

        <button
          class="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm text-muted-foreground transition-colors hover:bg-base-300/50 hover:text-foreground"
          @click="goManageLorebooks"
        >
          <AppIcon name="i-lucide-settings-2" class="size-4" />
          {{ $t("chat.drawer.manageLorebooks") }}
        </button>
      </div>
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
</template>
