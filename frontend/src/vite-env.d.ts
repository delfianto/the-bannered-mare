/// <reference types="vite-plus/client" />

interface ImportMetaEnv {
  readonly VITE_USE_MOCKS: string;
  readonly VITE_DEBUG_REQUEST: string;
  // Backend origin for the typed client + reachability probe. Empty (the default)
  // uses same-origin / the dev proxy; set it to point at a split-origin backend.
  readonly VITE_API_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare module "virtual:terminal" {
  export const terminal: {
    log: (...args: any[]) => void;
    warn: (...args: any[]) => void;
    error: (...args: any[]) => void;
    info: (...args: any[]) => void;
    table: (...args: any[]) => void;
    group: (...args: any[]) => void;
    groupEnd: (...args: any[]) => void;
    time: (label: string) => void;
    timeEnd: (label: string) => void;
    clear: () => void;
    count: (label: string) => void;
    assert: (condition: boolean, ...args: any[]) => void;
  };
  export default terminal;
}
