import { afterEach, expect, it, vi } from "vite-plus/test";
import { defineComponent, nextTick } from "vue";
import { mount, DOMWrapper, flushPromises } from "@vue/test-utils";
import { createPinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import App from "@/App.vue";
import AppShell from "../AppShell.vue";
import ServerStatusBanner from "../ServerStatusBanner.vue";
import { installAppApi } from "@/test/appApi";
import { button } from "@/test/views";
import { useSidebar } from "@/composables/useSidebar";
import { useServerStatus } from "@/composables/useServerStatus";
import { useAppToast, useToastState } from "@/composables/useToast";
import { useConfirm, useConfirmState } from "@/composables/useConfirm";
import router from "@/router";
import i18n from "@/i18n";
const t = (k: string) => i18n.global.t(k);
afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
  useServerStatus().reportResponse(200);
  useToastState().value = [];
  useConfirmState().onCancel();
  useSidebar().collapsed.value = false;
});
it("loads every production route and preserves sidebar navigation in both layouts", async () => {
  const { db } = installAppApi();
  await router.push("/");
  await router.isReady();
  const wrapper = mount(App, {
    attachTo: document.body,
    global: { plugins: [createPinia(), router] },
  });
  await vi.waitFor(() => expect(wrapper.text()).toContain(db.characters[0].name));
  const paths = [
    "/chats",
    `/chats/${db.chats[0].id}`,
    "/characters",
    "/characters/create",
    `/characters/${db.characters[0].id}/edit`,
    `/characters/${db.characters[0].id}`,
    "/bookmarks",
    "/memory",
    "/connections",
    "/loadouts",
    "/persona",
    "/setup",
    "/lorebooks",
    "/settings",
    `/settings/providers/${db.providers[0].id}`,
    `/settings/models/${db.models[0].id}`,
    `/settings/model-families/${db.families[0].id}`,
    "/settings/templates/create",
    `/settings/templates/${db.templates[0].id}`,
    "/settings/fragments/create",
    `/settings/fragments/${db.fragments[0].id}`,
    `/settings/presets/${db.presets[0].id}`,
    "/missing-page",
  ];
  for (const path of paths) {
    await router.push(path);
    await flushPromises();
    await nextTick();
    expect(router.currentRoute.value.matched.length).toBeGreaterThan(0);
    expect(wrapper.text()).not.toContain(t("common.errorBoundary.title"));
  }
  await router.push("/settings");
  await wrapper.get(`button[aria-label="${t("nav.collapseSidebar")}"]`).trigger("click");
  expect(useSidebar().collapsed.value).toBe(true);
  await wrapper.get('button[aria-label="Toggle theme"]').trigger("click");
  await wrapper.get('button[aria-label="Toggle theme"]').trigger("click");
  await wrapper.get('a[href="/characters"]').trigger("click");
  await vi.waitFor(() => expect(router.currentRoute.value.path).toBe("/characters"));
  await wrapper.get(`button[aria-label="${t("nav.expandSidebar")}"]`).trigger("click");
  await wrapper.get('input[aria-label="Toggle theme"]').setValue(false);
  await flushPromises();
  wrapper.unmount();
  await flushPromises();
});
it("contains rendering errors and recovers after navigating elsewhere", async () => {
  installAppApi();
  const Broken = defineComponent({
    setup() {
      throw new Error("View crashed");
    },
    template: "<div/>",
  });
  const memoryRouter = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/broken", component: { template: "<div>Healthy</div>" } },
      { path: "/other", component: { template: "<div>Recovered</div>" } },
      { path: "/:pathMatch(.*)*", component: { template: "<div>Destination</div>" } },
    ],
  });
  await memoryRouter.push("/broken");
  const wrapper = mount(AppShell, { global: { plugins: [createPinia(), memoryRouter] } });
  await flushPromises();
  memoryRouter.addRoute({ path: "/throws", component: Broken });
  await memoryRouter.push("/throws");
  await nextTick();
  expect(wrapper.text()).toContain(t("common.errorBoundary.title"));
  const reload = vi.spyOn(window.location, "reload").mockImplementation(() => {});
  await button(wrapper, t("common.errorBoundary.reload")).trigger("click");
  expect(reload).toHaveBeenCalledOnce();
  await memoryRouter.push("/other");
  await nextTick();
  expect(wrapper.text()).not.toContain(t("common.errorBoundary.title"));
});
it("shows server failures, retries, polls and cleans up on recovery", async () => {
  installAppApi();
  const state = useServerStatus();
  state.reportResponse(200);
  const wrapper = mount(ServerStatusBanner);
  vi.useFakeTimers();
  const fetchSpy = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValue(new Response("[]", { status: 200 }));
  state.reportNetworkError();
  await nextTick();
  expect(wrapper.get('[role="alert"]').text()).toContain(t("common.serverUnreachable"));
  await button(wrapper, t("common.retry")).trigger("click");
  await flushPromises();
  expect(state.reachable.value).toBe(true);
  state.reportNetworkError();
  await nextTick();
  await vi.advanceTimersByTimeAsync(5000);
  expect(fetchSpy).toHaveBeenCalledTimes(2);
  wrapper.unmount();
});
it("renders toast variants and settles confirmations through actual dialog buttons", async () => {
  installAppApi();
  await router.push("/");
  const wrapper = mount(App, {
    attachTo: document.body,
    global: { plugins: [createPinia(), router] },
  });
  const toast = useAppToast();
  toast.success("Saved", "Done");
  toast.error("Failed");
  toast.warning("Warning");
  toast.info("Info");
  await nextTick();
  expect(document.body.textContent).toContain("Saved");
  const close = document.querySelector<HTMLButtonElement>(".pointer-events-auto button")!;
  close.click();
  await nextTick();
  expect(useToastState().value).toHaveLength(3);
  const pending = useConfirm().confirm({
    message: "Delete this?",
    danger: true,
    confirmLabel: "Discard",
    cancelLabel: "Keep",
  });
  await nextTick();
  let dialog = new DOMWrapper(document.querySelector<HTMLElement>('[role="dialog"]')!);
  await button(dialog, "Keep").trigger("click");
  expect(await pending).toBe(false);
  const confirmed = useConfirm().confirm({ message: "Continue?" });
  await nextTick();
  dialog = new DOMWrapper(document.querySelector<HTMLElement>('[role="dialog"]')!);
  await button(dialog, t("common.confirm")).trigger("click");
  expect(await confirmed).toBe(true);
  await flushPromises();
  wrapper.unmount();
  await flushPromises();
});
it("reloads failed lazy chunks once per URL and leaves ordinary failures to the boundary", async () => {
  const assign = vi.spyOn(window.location, "assign").mockImplementation(() => {});
  const remove = router.addRoute({
    path: "/broken-chunk",
    component: () => Promise.reject(new Error("Failed to fetch dynamically imported module")),
  });
  sessionStorage.removeItem("chunk-reload:/broken-chunk");
  await expect(router.push("/broken-chunk")).rejects.toThrow("Failed to fetch");
  expect(assign).toHaveBeenCalledOnce();
  await expect(router.push("/broken-chunk")).rejects.toThrow("Failed to fetch");
  expect(assign).toHaveBeenCalledOnce();
  remove();
  const removeOrdinary = router.addRoute({
    path: "/ordinary-error",
    component: () => Promise.reject(new Error("View initialization failed")),
  });
  await expect(router.push("/ordinary-error")).rejects.toThrow("View initialization failed");
  expect(assign).toHaveBeenCalledOnce();
  removeOrdinary();
  sessionStorage.removeItem("chunk-reload:/broken-chunk");
});
