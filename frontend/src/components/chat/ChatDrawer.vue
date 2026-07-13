<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import type { ChatCharacterInfo } from "@/types/chat";
import type { Profile } from "@/composables/useProfiles";
import { useCharacter } from "@/composables/useCharacter";
import { usePersonas } from "@/composables/usePersonas";
import { useDataBank } from "@/composables/useDataBank";
import { useLorebooks } from "@/composables/useLorebooks";
import { useChatPromptPreview } from "@/composables/useChatPromptPreview";
import { useChatLlmLogs, type LlmAuditLog } from "@/composables/useChatLlmLogs";
import { useCompletionSignal } from "@/composables/useCompletionSignal";
import type { LoreEntryResponse } from "@/composables/useLorebooks";
import Tabs from "@/components/shared/Tabs.vue";
import CollapsibleSection from "@/components/shared/CollapsibleSection.vue";
import CollapsibleField from "@/components/discover/CollapsibleField.vue";
import AppTooltip from "@/components/shared/AppTooltip.vue";

interface PickerModel {
  id: string;
  display_name: string;
}

const props = defineProps<{
  show: boolean;
  character: ChatCharacterInfo;
  chatId?: string;
  sessionTitle: string;
  models: PickerModel[];
  currentModelId?: string | null;
  currentModelName?: string | null;
  currentTaskModelId?: string | null;
  profiles: Profile[];
  currentProfileName?: string | null;
  currentPersonaId?: string | null;
}>();

const emit = defineEmits<{
  close: [];
  changeModel: [modelId: string];
  changeTaskModel: [modelId: string | null];
  applyProfile: [profileId: string];
  changePersona: [personaId: string | null];
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

// Personas for the Persona section. usePersonas fetches on mount; the drawer is
// mounted with the chat header, so the list is warm by the time it opens.
const { personas } = usePersonas();

// Memories = this conversation's data-bank entries. Opt out of the auto-fetch so
// this instance doesn't pull the whole bank; we fetch chat-scoped on open.
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

// Fetch Memories + Lorebooks lazily: only while the drawer is open on the
// Settings tab, and only once per chat/character (re-key to refetch on switch).
const loadedKey = ref<string | null>(null);

watch(
  [() => props.show, activeTab, () => props.chatId, () => props.character.id],
  ([show, tab, chatId, characterId]) => {
    if (!show || tab !== "settings") return;
    const key = `${chatId ?? ""}::${characterId ?? ""}`;
    if (loadedKey.value === key) return;
    loadedKey.value = key;
    lorebookEntries.value = {};
    lorebookEntriesLoading.value = {};
    if (chatId) void fetchMemories(undefined, chatId);
    else memories.value = [];
    void fetchForChat(characterId);
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

// Session tab: resolved prompt scaffolding + effective params. The composable
// caches by chat id, so this only hits the network the first time a given chat's
// Session tab is opened (and again after switching chats).
const {
  preview,
  loading: previewLoading,
  error: previewError,
  load: loadPreview,
} = useChatPromptPreview();

watch(
  [() => props.show, activeTab, () => props.chatId],
  ([show, tab, chatId]) => {
    if (show && tab === "session" && chatId) void loadPreview(chatId);
  },
  { immediate: true },
);

// Effective sampler params as a sorted key/value list; objects/arrays render as
// compact JSON, scalars plainly.
const paramEntries = computed(() => {
  const params = preview.value?.parameters ?? {};
  return Object.keys(params)
    .sort()
    .map((key) => ({ key, value: formatParamValue(params[key]) }));
});

function formatParamValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function roleLabel(role: string): string {
  return role ? role.charAt(0).toUpperCase() + role.slice(1) : role;
}

// Logs tab: this conversation's LLM audit records. Cached by chat id, so it only
// hits the network the first time a given chat's Logs tab is opened (and again
// after switching chats).
const {
  logs,
  loading: logsLoading,
  error: logsError,
  load: loadLogs,
  invalidate: invalidateLogs,
} = useChatLlmLogs();

watch(
  [() => props.show, activeTab, () => props.chatId],
  ([show, tab, chatId]) => {
    if (show && tab === "logs" && chatId) void loadLogs(chatId);
  },
  { immediate: true },
);

function refreshLogs() {
  if (props.chatId) void loadLogs(props.chatId, true);
}

// When a model call for this chat settles, refresh the visible Logs tab in the
// background; if the tab isn't showing, just drop the cache so the next open
// refetches instead of serving stale rows.
const completionSignal = useCompletionSignal();
watch(completionSignal.tick, () => {
  if (completionSignal.chatId.value !== props.chatId) return;
  if (props.show && activeTab.value === "logs") refreshLogs();
  else invalidateLogs();
});

// Newest first, regardless of the order the API hands them back.
const sortedLogs = computed(() =>
  logs.value.slice().sort((a, b) => b.created_at.localeCompare(a.created_at)),
);

// Per-row expansion for the (lazily stringified) request/response payloads.
const expandedLogs = ref<Record<string, boolean>>({});

function toggleLog(id: string) {
  expandedLogs.value[id] = !expandedLogs.value[id];
}

function isErrorLog(log: LlmAuditLog): boolean {
  return log.status.toLowerCase() !== "success" || !!log.error_message;
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(n >= 10_000 ? 0 : 1)}k`;
  return String(n);
}

function formatLatency(ms: number): string {
  return ms >= 1_000 ? `${(ms / 1_000).toFixed(2)}s` : `${Math.round(ms)}ms`;
}

function formatCost(usd: number | null): string {
  if (!usd) return "";
  return usd >= 1 ? `$${usd.toFixed(2)}` : `$${usd.toFixed(4)}`;
}

function formatLogTime(iso: string): string {
  const date = new Date(iso);
  const diffMs = Date.now() - date.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  const diffHr = Math.floor(diffMs / 3_600_000);
  const diffDay = Math.floor(diffMs / 86_400_000);
  if (diffMin < 1) return t("time.justNow");
  if (diffMin < 60) return t("time.minutesAgo", { count: diffMin });
  if (diffHr < 24) return t("time.hoursAgo", { count: diffHr });
  if (diffDay < 7) return t("time.daysAgo", { count: diffDay });
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function formatJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

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

// Model selects use the shared searchable SelectMenu (a long model list would
// otherwise make the section a very tall scroll).
const modelItems = computed(() =>
  props.models.map((m) => ({ label: m.display_name, value: m.id })),
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
    props.models.find((m) => m.id === props.currentModelId)?.display_name ??
    props.currentModelName ??
    t("chat.model.none"),
);
const currentTaskModelLabel = computed(
  () =>
    props.models.find((m) => m.id === props.currentTaskModelId)?.display_name ??
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
  () => props.profiles.find((p) => p.name === props.currentProfileName) ?? null,
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
                      <span class="block truncate text-sm font-medium text-foreground">{{
                        p.name
                      }}</span>
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
                    <span class="block truncate text-sm font-medium text-foreground">{{
                      p.name
                    }}</span>
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
                <div
                  v-if="memoriesLoading && memories.length === 0"
                  class="flex justify-center py-3"
                >
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
                <div
                  v-if="lorebooksLoading && lorebooks.length === 0"
                  class="flex justify-center py-3"
                >
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

          <!-- Session tab -->
          <div v-else-if="activeTab === 'session'" class="p-4">
            <div v-if="previewLoading && !preview" class="flex justify-center py-12">
              <AppIcon
                name="i-lucide-loader-circle"
                class="size-6 animate-spin text-muted-foreground"
              />
            </div>

            <div v-else-if="previewError" class="py-12 text-center text-xs text-muted-foreground">
              {{ $t("chat.drawer.sessionError") }}
            </div>

            <div v-else-if="preview" class="space-y-4">
              <!-- Resolved model -->
              <div class="rounded-xl border bg-base-100/50 p-4">
                <h3 class="text-base font-semibold text-foreground">
                  {{ preview.model_display_name || $t("chat.drawer.sessionModelUnknown") }}
                </h3>
                <p
                  v-if="preview.provider_name || preview.model_identifier"
                  class="mt-1 flex flex-wrap items-center gap-x-1.5 text-xs text-muted-foreground"
                >
                  <span v-if="preview.provider_name">{{ preview.provider_name }}</span>
                  <span
                    v-if="preview.provider_name && preview.model_identifier"
                    class="text-muted-foreground/40"
                    >·</span
                  >
                  <span v-if="preview.model_identifier" class="font-mono text-muted-foreground/80">
                    {{ preview.model_identifier }}
                  </span>
                </p>
              </div>

              <!-- Effective parameters -->
              <div>
                <h4
                  class="mb-2 font-cinzel text-xs font-semibold tracking-widest text-muted-foreground uppercase"
                >
                  {{ $t("chat.drawer.sessionParameters") }}
                </h4>
                <dl
                  v-if="paramEntries.length"
                  class="overflow-hidden rounded-lg border border-border/50 bg-base-100/40"
                >
                  <div
                    v-for="(entry, i) in paramEntries"
                    :key="entry.key"
                    class="flex items-start justify-between gap-3 px-3 py-2"
                    :class="i > 0 ? 'border-t border-border/40' : ''"
                  >
                    <dt class="shrink-0 text-xs text-muted-foreground">{{ entry.key }}</dt>
                    <dd class="min-w-0 text-right font-mono text-xs break-words text-foreground">
                      {{ entry.value }}
                    </dd>
                  </div>
                </dl>
                <p v-else class="px-1 py-2 text-xs text-muted-foreground/70">
                  {{ $t("chat.drawer.sessionParametersEmpty") }}
                </p>
              </div>

              <!-- Assembled prompt scaffolding -->
              <div>
                <h4
                  class="mb-2 font-cinzel text-xs font-semibold tracking-widest text-muted-foreground uppercase"
                >
                  {{ $t("chat.drawer.sessionPrompt") }}
                </h4>
                <div v-if="preview.messages.length" class="space-y-2">
                  <CollapsibleField
                    v-for="(msg, i) in preview.messages"
                    :key="i"
                    :label="roleLabel(msg.role)"
                    :content="msg.content"
                    mono
                  />
                </div>
                <p v-else class="px-1 py-2 text-xs text-muted-foreground/70">
                  {{ $t("chat.drawer.sessionPromptEmpty") }}
                </p>
              </div>
            </div>
          </div>

          <!-- Logs tab -->
          <div v-else-if="activeTab === 'logs'" class="p-4">
            <div class="mb-3 flex items-center justify-between">
              <span
                class="font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground"
              >
                {{ $t("chat.drawer.tabs.logs") }}
              </span>
              <AppTooltip :text="$t('chat.drawer.logsRefresh')" side="left">
                <button
                  class="flex size-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-base-300/40 hover:text-foreground disabled:opacity-50"
                  :disabled="logsLoading"
                  :aria-label="$t('chat.drawer.logsRefresh')"
                  @click="refreshLogs"
                >
                  <AppIcon
                    name="i-lucide-refresh-cw"
                    class="size-3.5"
                    :class="{ 'animate-spin': logsLoading && sortedLogs.length }"
                  />
                </button>
              </AppTooltip>
            </div>

            <!-- Full spinner only on the first fetch; a background refresh keeps
                 the current rows on screen (the button icon spins instead). -->
            <div v-if="logsLoading && !sortedLogs.length" class="flex justify-center py-12">
              <AppIcon
                name="i-lucide-loader-circle"
                class="size-6 animate-spin text-muted-foreground"
              />
            </div>

            <div v-else-if="logsError" class="py-12 text-center text-xs text-muted-foreground">
              {{ $t("chat.drawer.logsError") }}
            </div>

            <div v-else-if="sortedLogs.length" class="space-y-2">
              <div
                v-for="log in sortedLogs"
                :key="log.id"
                class="overflow-hidden rounded-lg border border-border/50 bg-base-100/40"
              >
                <!-- Summary row -->
                <button
                  class="flex w-full items-start justify-between gap-3 px-4 py-3 text-left transition-colors hover:bg-base-300/40"
                  @click="toggleLog(log.id)"
                >
                  <div class="min-w-0 flex-1">
                    <div class="flex items-center gap-2">
                      <span class="min-w-0 truncate text-sm font-medium text-foreground">
                        {{ log.model }}
                      </span>
                      <span
                        class="shrink-0 rounded-full px-2 py-0.5 text-[0.625rem] font-medium tracking-wide uppercase"
                        :class="
                          isErrorLog(log) ? 'bg-error/15 text-error' : 'bg-success/15 text-success'
                        "
                      >
                        {{
                          isErrorLog(log)
                            ? $t("chat.drawer.logsStatusError")
                            : $t("chat.drawer.logsStatusSuccess")
                        }}
                      </span>
                    </div>
                    <p
                      class="mt-0.5 flex flex-wrap items-center gap-x-1.5 text-[0.6875rem] text-muted-foreground"
                    >
                      <span>{{ log.provider }}</span>
                      <span class="text-muted-foreground/40">·</span>
                      <span>{{ formatLogTime(log.created_at) }}</span>
                    </p>
                  </div>
                  <AppIcon
                    name="i-lucide-chevron-down"
                    class="mt-0.5 size-4 shrink-0 text-muted-foreground transition-transform"
                    :class="{ 'rotate-180': expandedLogs[log.id] }"
                  />
                </button>

                <!-- Metrics -->
                <div
                  class="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-border/40 px-4 py-2 text-[0.6875rem] text-muted-foreground"
                >
                  <span class="flex items-center gap-1">
                    <AppIcon name="i-lucide-hash" class="size-3 text-muted-foreground/60" />
                    {{ $t("chat.drawer.logsTokens") }}:
                    <span class="tabular-nums text-foreground">
                      {{ formatTokens(log.prompt_tokens) }} →
                      {{ formatTokens(log.completion_tokens) }}
                    </span>
                    <span class="text-muted-foreground/50">
                      ({{ formatTokens(log.total_tokens) }})
                    </span>
                  </span>
                  <span class="flex items-center gap-1">
                    <AppIcon name="i-lucide-timer" class="size-3 text-muted-foreground/60" />
                    <span class="tabular-nums text-foreground">{{
                      formatLatency(log.latency_ms)
                    }}</span>
                  </span>
                  <span v-if="formatCost(log.estimated_cost_usd)" class="flex items-center gap-1">
                    <AppIcon name="i-lucide-coins" class="size-3 text-muted-foreground/60" />
                    <span class="tabular-nums text-foreground">{{
                      formatCost(log.estimated_cost_usd)
                    }}</span>
                  </span>
                </div>

                <!-- Error message -->
                <p
                  v-if="log.error_message"
                  class="border-t border-border/40 px-4 py-2 text-[0.6875rem] leading-snug text-error"
                >
                  {{ log.error_message }}
                </p>

                <!-- Expandable payloads (stringified only when open) -->
                <div v-if="expandedLogs[log.id]" class="space-y-2 border-t border-border/40 p-3">
                  <CollapsibleField
                    :label="$t('chat.drawer.logsRequest')"
                    :content="formatJson(log.request_payload)"
                    mono
                  />
                  <CollapsibleField
                    :label="$t('chat.drawer.logsResponse')"
                    :content="formatJson(log.response_payload)"
                    mono
                  />
                </div>
              </div>
            </div>

            <p v-else class="py-8 text-center text-xs text-muted-foreground/70">
              {{ $t("chat.drawer.logsEmpty") }}
            </p>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
