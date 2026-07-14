// Global harness for component tests. Mirrors main.ts's app wiring so
// `mount()` gets i18n + the three globally-registered primitives without each
// test repeating the setup.
import { config } from "@vue/test-utils";
import i18n from "@/i18n";
import AppIcon from "@/components/shared/AppIcon.vue";
import SelectMenu from "@/components/shared/SelectMenu.vue";
import AppToggle from "@/components/shared/AppToggle.vue";

config.global.plugins = [i18n];
config.global.components = { AppIcon, SelectMenu, AppToggle };
