<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useI18n } from "vue-i18n";
import { useTheme } from "@/composables/useTheme";
import { useCustomTheme } from "@/composables/useCustomTheme";
import { useFontSize, MIN_FONT_SIZE, MAX_FONT_SIZE } from "@/composables/useFontSize";
import { useChatWidth, CHAT_WIDTH_ORDER, type ChatWidth } from "@/composables/useChatWidth";
import { COLOR_PRESETS } from "@/constants/colorPresets";
import { SUPPORTED_LOCALES, setLocale } from "@/i18n";
import ThemeEditor from "./ThemeEditor.vue";

const { isDark, toggleTheme, colorScheme, setColorScheme } = useTheme();
const { custom } = useCustomTheme();
const { fontSize, setFontSize, resetFontSize } = useFontSize();
const { chatWidth, setChatWidth } = useChatWidth();
const { locale } = useI18n();

const chatWidthLabels: Record<ChatWidth, string> = {
  narrow: "chatWidthNarrow",
  cozy: "chatWidthCozy",
  wide: "chatWidthWide",
  full: "chatWidthFull",
};

const currentLocale = computed({
  get: () => locale.value,
  set: (val: string) => setLocale(val),
});

const streamResponses = ref(true);
const typingIndicator = ref(true);

onMounted(() => {
  const storedStream = localStorage.getItem("setting-stream-responses");
  if (storedStream !== null) {
    streamResponses.value = storedStream === "true";
  }

  const storedTyping = localStorage.getItem("setting-typing-indicator");
  if (storedTyping !== null) {
    typingIndicator.value = storedTyping === "true";
  }
});

function toggleStream() {
  streamResponses.value = !streamResponses.value;
  localStorage.setItem("setting-stream-responses", String(streamResponses.value));
}

function toggleTyping() {
  typingIndicator.value = !typingIndicator.value;
  localStorage.setItem("setting-typing-indicator", String(typingIndicator.value));
}

function previewBg(preset: (typeof COLOR_PRESETS)[number]) {
  return isDark.value ? preset.preview.backgroundDark : preset.preview.background;
}
</script>

<template>
  <div class="mx-auto max-w-5xl animate-fade-in-up space-y-8">
    <!-- Text Size + Behavior sit side by side on desktop -->
    <div class="grid items-start gap-8 lg:grid-cols-2">
      <!-- Text Size Section -->
      <section>
        <h3
          class="mb-3 font-cinzel text-sm font-semibold tracking-widest text-muted-foreground uppercase"
        >
          {{ $t("settings.interface.textSize") }}
        </h3>
        <div class="space-y-4 rounded-xl border bg-base-200/50 p-5">
          <div class="flex items-start gap-3">
            <AppIcon name="i-lucide-type" class="mt-0.5 size-5 text-primary" />
            <div class="min-w-0 flex-1">
              <p class="text-sm font-medium text-foreground">
                {{ $t("settings.interface.textSize") }}
              </p>
              <p class="text-xs text-muted-foreground">
                {{ $t("settings.interface.textSizeDescription") }}
              </p>
            </div>
          </div>

          <!-- Slider — dragging rescales the whole app live -->
          <div class="flex items-center gap-3">
            <span class="text-xs text-muted-foreground">A</span>
            <input
              type="range"
              :min="MIN_FONT_SIZE"
              :max="MAX_FONT_SIZE"
              step="1"
              :value="fontSize"
              class="h-1.5 flex-1 cursor-pointer appearance-none rounded-full bg-base-300 accent-primary"
              :aria-label="$t('settings.interface.textSize')"
              @input="setFontSize(Number(($event.target as HTMLInputElement).value))"
            />
            <span class="text-lg text-muted-foreground">A</span>
            <span class="w-11 shrink-0 text-right text-sm font-medium text-foreground tabular-nums"
              >{{ fontSize }}px</span
            >
          </div>

          <!-- Live sample -->
          <div class="rounded-lg border bg-base-100/50 p-4">
            <p class="leading-relaxed text-foreground">
              {{ $t("settings.interface.textSizeSample") }}
            </p>
          </div>

          <div class="flex justify-end">
            <button
              type="button"
              class="text-xs font-medium text-muted-foreground transition-colors hover:text-primary"
              @click="resetFontSize"
            >
              {{ $t("settings.interface.resetTextSize") }}
            </button>
          </div>

          <div class="h-px bg-border" />

          <!-- Chat width -->
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div class="flex items-center gap-3">
              <AppIcon name="i-lucide-move-horizontal" class="size-5 text-primary" />
              <div>
                <p class="text-sm font-medium text-foreground">
                  {{ $t("settings.interface.chatWidth") }}
                </p>
                <p class="text-xs text-muted-foreground">
                  {{ $t("settings.interface.chatWidthDescription") }}
                </p>
              </div>
            </div>
            <div class="flex items-center gap-0.5 rounded-lg border bg-base-300/40 p-0.5">
              <button
                v-for="opt in CHAT_WIDTH_ORDER"
                :key="opt"
                type="button"
                class="rounded-md px-3 py-1.5 text-xs font-medium transition-colors"
                :class="
                  chatWidth === opt
                    ? 'bg-primary text-primary-content'
                    : 'text-muted-foreground hover:text-foreground'
                "
                @click="setChatWidth(opt)"
              >
                {{ $t(`settings.interface.${chatWidthLabels[opt]}`) }}
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- Behavior Section -->
      <section>
        <h3
          class="mb-3 font-cinzel text-sm font-semibold tracking-widest text-muted-foreground uppercase"
        >
          {{ $t("settings.interface.behavior") }}
        </h3>
        <div class="space-y-5 rounded-xl border bg-base-200/50 p-5">
          <!-- Stream Responses -->
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <AppIcon name="i-lucide-radio" class="size-5 text-primary" />
              <div>
                <p class="text-sm font-medium text-foreground">
                  {{ $t("settings.interface.streamResponses") }}
                </p>
                <p class="text-xs text-muted-foreground">
                  {{ $t("settings.interface.streamDescription") }}
                </p>
              </div>
            </div>
            <AppToggle
              :model-value="streamResponses"
              aria-label="Stream responses"
              @change="toggleStream"
            />
          </div>

          <!-- Divider -->
          <div class="h-px bg-border" />

          <!-- Show Typing Indicator -->
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <AppIcon name="i-lucide-pen-tool" class="size-5 text-primary" />
              <div>
                <p class="text-sm font-medium text-foreground">
                  {{ $t("settings.interface.typingIndicator") }}
                </p>
                <p class="text-xs text-muted-foreground">
                  {{ $t("settings.interface.typingDescription") }}
                </p>
              </div>
            </div>
            <AppToggle
              :model-value="typingIndicator"
              aria-label="Typing indicator"
              @change="toggleTyping"
            />
          </div>

          <!-- Divider -->
          <div class="h-px bg-border" />

          <!-- Language -->
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <AppIcon name="i-lucide-languages" class="size-5 text-primary" />
              <div>
                <p class="text-sm font-medium text-foreground">
                  {{ $t("settings.interface.language") }}
                </p>
                <p class="text-xs text-muted-foreground">
                  {{ $t("settings.interface.languageDescription") }}
                </p>
              </div>
            </div>
            <SelectMenu
              v-model="currentLocale"
              :items="SUPPORTED_LOCALES.map((l) => ({ label: l.name, value: l.code }))"
              value-key="value"
              :search-input="false"
            >
              <button
                class="flex h-9 min-w-35 items-center gap-1.5 rounded-lg border bg-base-300/40 px-3 text-sm text-foreground transition-all outline-none hover:border-muted-foreground/30"
              >
                {{ SUPPORTED_LOCALES.find((l) => l.code === currentLocale)?.name }}
                <AppIcon name="i-lucide-chevron-down" class="size-3.5 text-muted-foreground" />
              </button>
            </SelectMenu>
          </div>
        </div>
      </section>
    </div>

    <!-- Color Scheme — full width below, room for many themes -->
    <section>
      <h3
        class="mb-3 font-cinzel text-sm font-semibold tracking-widest text-muted-foreground uppercase"
      >
        {{ $t("settings.interface.colorScheme") }}
      </h3>
      <div class="space-y-5 rounded-xl border bg-base-200/50 p-5">
        <!-- Dark mode toggle -->
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <AppIcon
              :name="isDark ? 'i-lucide-moon' : 'i-lucide-sun'"
              class="size-5 text-primary"
            />
            <div>
              <p class="text-sm font-medium text-foreground">
                {{ $t("settings.interface.darkMode") }}
              </p>
              <p class="text-xs text-muted-foreground">
                {{ $t("settings.interface.darkModeDescription") }}
              </p>
            </div>
          </div>
          <AppToggle :model-value="isDark" aria-label="Dark mode" @change="toggleTheme" />
        </div>

        <!-- Divider -->
        <div class="h-px bg-border" />

        <!-- Preset grid -->
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
          <button
            v-for="preset in COLOR_PRESETS"
            :key="preset.id"
            class="group relative flex flex-col items-center gap-2 rounded-xl p-2.5 transition-all"
            :class="
              colorScheme === preset.id
                ? 'ring-2 ring-primary bg-base-300/30'
                : 'hover:bg-base-300/20'
            "
            :aria-label="`Select ${preset.name} color scheme`"
            @click="setColorScheme(preset.id)"
          >
            <!-- Mini UI mockup -->
            <div
              class="aspect-4/3 w-full overflow-hidden rounded-lg border transition-transform group-hover:scale-[1.02]"
            >
              <div class="flex h-full">
                <!-- Sidebar strip -->
                <div class="w-2.5 shrink-0" :style="{ backgroundColor: previewBg(preset) }">
                  <div
                    class="mx-auto mt-2 size-1.5 rounded-full"
                    :style="{ backgroundColor: preset.preview.primary }"
                  />
                </div>
                <!-- Main content area -->
                <div class="flex flex-1 flex-col" :style="{ backgroundColor: previewBg(preset) }">
                  <!-- Header bar -->
                  <div class="h-1.5 w-full" :style="{ backgroundColor: preset.preview.primary }" />
                  <!-- Content placeholder -->
                  <div class="flex-1 p-1.5">
                    <div
                      class="mb-1 h-1 w-3/4 rounded-full opacity-40"
                      :style="{ backgroundColor: preset.preview.primary }"
                    />
                    <div class="flex gap-1">
                      <div
                        class="size-3 rounded opacity-20"
                        :style="{ backgroundColor: preset.preview.primary }"
                      />
                      <div
                        class="size-3 rounded opacity-20"
                        :style="{ backgroundColor: preset.preview.primary }"
                      />
                      <div
                        class="size-3 rounded opacity-20"
                        :style="{ backgroundColor: preset.preview.primary }"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Active checkmark -->
            <div
              v-if="colorScheme === preset.id"
              class="absolute top-1.5 right-1.5 flex size-5 items-center justify-center rounded-full bg-primary text-primary-content"
            >
              <AppIcon name="i-lucide-check" class="size-3" />
            </div>

            <!-- Label -->
            <div class="text-center">
              <p class="font-cinzel text-[0.6875rem] font-semibold tracking-wide text-foreground">
                {{ preset.name }}
              </p>
              <p class="text-[0.5625rem] text-muted-foreground">{{ preset.description }}</p>
            </div>
          </button>

          <!-- Custom theme card -->
          <button
            class="group relative flex flex-col items-center gap-2 rounded-xl p-2.5 transition-all"
            :class="
              colorScheme === 'custom'
                ? 'bg-base-300/30 ring-2 ring-primary'
                : 'hover:bg-base-300/20'
            "
            aria-label="Custom theme"
            @click="setColorScheme('custom')"
          >
            <div
              class="aspect-4/3 w-full overflow-hidden rounded-lg border transition-transform group-hover:scale-[1.02]"
            >
              <div class="flex h-full" :style="{ backgroundColor: custom.base100 }">
                <div class="w-2.5 shrink-0" :style="{ backgroundColor: custom.base200 }">
                  <div
                    class="mx-auto mt-2 size-1.5 rounded-full"
                    :style="{ backgroundColor: custom.primary }"
                  />
                </div>
                <div class="flex flex-1 flex-col">
                  <div class="h-1.5 w-full" :style="{ backgroundColor: custom.primary }" />
                  <div class="flex flex-1 items-center justify-center">
                    <AppIcon
                      name="i-lucide-palette"
                      class="size-4"
                      :style="{ color: custom.primary }"
                    />
                  </div>
                </div>
              </div>
            </div>

            <!-- Active checkmark -->
            <div
              v-if="colorScheme === 'custom'"
              class="absolute top-1.5 right-1.5 flex size-5 items-center justify-center rounded-full bg-primary text-primary-content"
            >
              <AppIcon name="i-lucide-check" class="size-3" />
            </div>

            <!-- Label -->
            <div class="text-center">
              <p class="font-cinzel text-[0.6875rem] font-semibold tracking-wide text-foreground">
                Custom
              </p>
              <p class="text-[0.5625rem] text-muted-foreground">Your own palette</p>
            </div>
          </button>
        </div>

        <ThemeEditor v-if="colorScheme === 'custom'" />
      </div>
    </section>
  </div>
</template>
