<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useTheme } from "@/composables/useTheme";

const { isDark, toggleTheme } = useTheme();

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
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-8 animate-fade-in-up">
    <!-- Theme Section -->
    <section>
      <h3 class="mb-3 font-cinzel text-sm font-semibold uppercase tracking-widest text-muted-foreground">
        Theme
      </h3>
      <div class="rounded-xl border bg-card/50 p-5">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <UIcon
              :name="isDark ? 'i-lucide-moon' : 'i-lucide-sun'"
              class="h-5 w-5 text-primary"
            />
            <div>
              <p class="text-sm font-medium text-foreground">Appearance</p>
              <p class="text-xs text-muted-foreground">Switch between light and dark mode</p>
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
      </div>
    </section>

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
  </div>
</template>
