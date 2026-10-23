import { h, nextTick, type Component } from "vue";
import { mount, type VueWrapper } from "@vue/test-utils";
import { createPinia } from "pinia";
import { createMemoryHistory, createRouter, RouterView } from "vue-router";

export async function mountView(component: Component, path: string, routePath = path) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: routePath, component },
      {
        path: "/chats/:chatId",
        name: "chat",
        component: { template: "<div>Chat destination</div>" },
      },
      { path: "/:pathMatch(.*)*", component: { template: "<div>Destination</div>" } },
    ],
  });
  await router.push(path);
  await router.isReady();
  const root = mount(
    { render: () => h(RouterView) },
    { attachTo: document.body, global: { plugins: [createPinia(), router] } },
  );
  return { wrapper: root.findComponent(component), root, router };
}

export function button(wrapper: Pick<VueWrapper, "findAll">, text: string) {
  const match = wrapper.findAll<HTMLButtonElement>("button").find((b) => b.text() === text);
  if (!match) throw new Error(`Button not found: ${text}`);
  return match;
}

export async function pickOption(
  trigger: { trigger: (event: string) => Promise<void> },
  text: string,
) {
  await trigger.trigger("click");
  const option = Array.from(document.querySelectorAll<HTMLElement>('[role="option"]')).find(
    (el) => el.textContent?.trim() === text,
  );
  if (!option) throw new Error(`Option not found: ${text}`);
  option.click();
  await nextTick();
}
