// Runs FIRST (before ./setup.ts) so `localStorage` exists before any module
// that reads it at import time (e.g. src/i18n.ts). Under `vp test --coverage`,
// Node's experimental native `localStorage` (undefined unless --localstorage-file
// is passed) shadows happy-dom's binding on `globalThis`, so those module-load
// reads throw `Cannot read properties of undefined (reading 'getItem')`. Bind the
// global to happy-dom's `window.localStorage` when present, else a tiny in-memory
// stub. `import` statements hoist above statements, so this must live in its own
// setup file that fully evaluates before setup.ts is imported — it can't sit atop
// setup.ts.
const g = globalThis as unknown as {
  window?: { localStorage?: Storage };
  localStorage?: Storage;
};

if (!g.localStorage || typeof g.localStorage.getItem !== "function") {
  if (g.window?.localStorage && typeof g.window.localStorage.getItem === "function") {
    g.localStorage = g.window.localStorage;
  } else {
    const store = new Map<string, string>();
    g.localStorage = {
      getItem: (k: string) => store.get(k) ?? null,
      setItem: (k: string, v: string) => void store.set(k, String(v)),
      removeItem: (k: string) => void store.delete(k),
      clear: () => store.clear(),
      key: (i: number) => [...store.keys()][i] ?? null,
      get length() {
        return store.size;
      },
    } as Storage;
  }
}
