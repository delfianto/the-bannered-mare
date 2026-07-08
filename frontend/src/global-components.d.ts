// Globally-registered components (see main.ts). Declared here so vue-tsc knows
// their types in templates without a per-file import.
declare module "vue" {
  interface GlobalComponents {
    AppIcon: (typeof import("@/components/shared/AppIcon.vue"))["default"];
  }
}

export {};
