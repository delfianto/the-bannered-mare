// Ambient *.vue module shim for the native TS7 compiler (tsgo), which has no
// Vue SFC support yet. Referenced ONLY by tsconfig.native.json — vue-tsc/Volar
// type-check .vue files precisely and never see this broad shim.
declare module "*.vue" {
  import type { DefineComponent } from "vue";
  const component: DefineComponent<Record<string, never>, Record<string, never>, any>;
  export default component;
}
