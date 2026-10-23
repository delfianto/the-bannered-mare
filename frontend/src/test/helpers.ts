import { defineComponent, h } from "vue";
import { mount, type MountingOptions } from "@vue/test-utils";

export function mountComposable<T>(
  factory: () => T,
  options: { global?: MountingOptions<object>["global"] } = {},
) {
  let api!: T;
  const wrapper = mount(
    defineComponent({
      setup() {
        api = factory();
        return () => h("div");
      },
    }),
    options,
  );
  return { api, wrapper };
}

export function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}
