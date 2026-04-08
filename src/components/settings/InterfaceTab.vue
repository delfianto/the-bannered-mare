<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useTheme } from "@/composables/useTheme";
import { COLOR_PRESETS } from "@/constants/colorPresets";

const { isDark, toggleTheme, colorScheme, setColorScheme } = useTheme();

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
  <div class="mx-auto max-w-2xl space-y-8 animate-fade-in-up">
    <!-- Behavior Section -->
    <section>
      <h3 class="mb-3 font-cinzel text-sm font-semibold uppercase tracking-widest text-muted-foreground">
        Behavior
      </h3>
      <div class="rounded-xl border bg-card/50 p-5 space-y-5">
        <!-- Stream Responses -->
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <UIcon name="i-lucide-radio" class="h-5 w-5 text-primary" />
            <div>
              <p class="text-sm font-medium text-foreground">Stream Responses</p>
              <p class="text-xs text-muted-foreground">Show AI responses as they're generated</p>
            </div>
          </div>
          <button
            class="flex h-[22px] w-10 items-center rounded-full px-[3px] transition-colors duration-300"
            :class="streamResponses ? 'bg-primary' : 'bg-muted-foreground/40'"
            role="switch"
            :aria-checked="streamResponses"
            aria-label="Stream responses"
            @click="toggleStream"
          >
            <span
              class="h-4 w-4 rounded-full shadow-sm transition-transform duration-300"
              :class="streamResponses ? 'translate-x-4 bg-background' : 'translate-x-0 bg-white'"
            />
          </button>
        </div>

        <!-- Divider -->
        <div class="h-px bg-border" />

        <!-- Show Typing Indicator -->
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <UIcon name="i-lucide-pen-tool" class="h-5 w-5 text-primary" />
            <div>
              <p class="text-sm font-medium text-foreground">Show Typing Indicator</p>
              <p class="text-xs text-muted-foreground">Show quill animation while AI is composing</p>
            </div>
          </div>
          <button
            class="flex h-[22px] w-10 items-center rounded-full px-[3px] transition-colors duration-300"
            :class="typingIndicator ? 'bg-primary' : 'bg-muted-foreground/40'"
            role="switch"
            :aria-checked="typingIndicator"
            aria-label="Typing indicator"
            @click="toggleTyping"
          >
            <span
              class="h-4 w-4 rounded-full shadow-sm transition-transform duration-300"
              :class="typingIndicator ? 'translate-x-4 bg-background' : 'translate-x-0 bg-white'"
            />
          </button>
        </div>
      </div>
    </section>

    <!-- Color Scheme Section -->
    <section>
      <h3 class="mb-3 font-cinzel text-sm font-semibold uppercase tracking-widest text-muted-foreground">
        Color Scheme
      </h3>
      <div class="rounded-xl border bg-card/50 p-5 space-y-5">
        <!-- Dark mode toggle -->
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <UIcon
              :name="isDark ? 'i-lucide-moon' : 'i-lucide-sun'"
              class="h-5 w-5 text-primary"
            />
            <div>
              <p class="text-sm font-medium text-foreground">Dark Mode</p>
              <p class="text-xs text-muted-foreground">Switch between light and dark appearance</p>
            </div>
          </div>
          <button
            class="flex h-[22px] w-10 items-center rounded-full px-[3px] transition-colors duration-300"
            :class="isDark ? 'bg-primary' : 'bg-muted-foreground/40'"
            role="switch"
            :aria-checked="isDark"
            aria-label="Dark mode"
            @click="toggleTheme"
          >
            <span
              class="h-4 w-4 rounded-full shadow-sm transition-transform duration-300"
              :class="isDark ? 'translate-x-4 bg-background' : 'translate-x-0 bg-white'"
            />
          </button>
        </div>

        <!-- Divider -->
        <div class="h-px bg-border" />

        <!-- Preset grid -->
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <button
            v-for="preset in COLOR_PRESETS"
            :key="preset.id"
            class="group relative flex flex-col items-center gap-2 rounded-xl p-2.5 transition-all"
            :class="
              colorScheme === preset.id
                ? 'ring-2 ring-primary bg-accent/30'
                : 'hover:bg-accent/20'
            "
            :aria-label="`Select ${preset.name} color scheme`"
            @click="setColorScheme(preset.id)"
          >
            <!-- Mini UI mockup -->
            <div
              class="aspect-[4/3] w-full overflow-hidden rounded-lg border transition-transform group-hover:scale-[1.02]"
            >
              <div class="flex h-full">
                <!-- Sidebar strip -->
                <div
                  class="w-[10px] flex-shrink-0"
                  :style="{ backgroundColor: previewBg(preset) }"
                >
                  <div
                    class="mx-auto mt-2 h-1.5 w-1.5 rounded-full"
                    :style="{ backgroundColor: preset.preview.primary }"
                  />
                </div>
                <!-- Main content area -->
                <div class="flex flex-1 flex-col" :style="{ backgroundColor: previewBg(preset) }">
                  <!-- Header bar -->
                  <div
                    class="h-[6px] w-full"
                    :style="{ backgroundColor: preset.preview.primary }"
                  />
                  <!-- Content placeholder -->
                  <div class="flex-1 p-1.5">
                    <div
                      class="mb-1 h-1 w-3/4 rounded-full opacity-40"
                      :style="{ backgroundColor: preset.preview.primary }"
                    />
                    <div class="flex gap-1">
                      <div
                        class="h-3 w-3 rounded opacity-20"
                        :style="{ backgroundColor: preset.preview.primary }"
                      />
                      <div
                        class="h-3 w-3 rounded opacity-20"
                        :style="{ backgroundColor: preset.preview.primary }"
                      />
                      <div
                        class="h-3 w-3 rounded opacity-20"
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
              class="absolute right-1.5 top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-primary text-primary-foreground"
            >
              <UIcon name="i-lucide-check" class="h-3 w-3" />
            </div>

            <!-- Label -->
            <div class="text-center">
              <p class="font-cinzel text-[11px] font-semibold tracking-wide text-foreground">
                {{ preset.name }}
              </p>
              <p class="text-[9px] text-muted-foreground">{{ preset.description }}</p>
            </div>
          </button>
        </div>
      </div>
    </section>

  </div>
</template>
