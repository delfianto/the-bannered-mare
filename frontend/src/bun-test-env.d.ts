// Makes the `bun:test` module + Bun globals (process, etc.) resolvable to
// vue-tsc so the `__tests__` files are type-checked by the gate instead of
// silently rotting (they were previously excluded from tsconfig).
/// <reference types="bun-types" />
