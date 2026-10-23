import { afterEach, expect, it, vi } from "vite-plus/test";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import { http, HttpResponse } from "msw";
import CharacterTab from "../ChatDrawerCharacterTab.vue";
import SessionTab from "../ChatDrawerSessionTab.vue";
import LogsTab from "../ChatDrawerLogsTab.vue";
import SettingsTab from "../ChatDrawerSettingsTab.vue";
import { installAppApi } from "@/test/appApi";
import { server } from "@/mocks/server";
import { button } from "@/test/views";
import { useCompletionSignal } from "@/composables/useCompletionSignal";
import i18n from "@/i18n";
const t = (k: string) => i18n.global.t(k);
afterEach(() => vi.restoreAllMocks());
it.each(["custom", "minimal", "missing"])(
  "renders %s character details and avatar fallbacks",
  async (mode) => {
    const { db } = installAppApi();
    const char = db.characters[0];
    Object.assign(char, {
      id: `drawer-${mode}`,
      avatar_large: null,
      avatar: null,
      gender: mode === "custom" ? "others" : null,
      custom_gender: "Nonbinary",
      tags: mode === "minimal" ? null : [],
      species: mode === "minimal" ? null : "Elf",
      scenario: "An ancient ruin",
    });
    const wrapper = mount(CharacterTab, {
      props: { characterId: mode === "missing" ? "missing" : char.id },
    });
    await flushPromises();
    expect(wrapper.text()).toContain(mode === "missing" ? t("characters.notFound") : char.name);
    if (mode === "custom") expect(wrapper.text()).toContain("Nonbinary");
    await wrapper.setProps({ characterId: "" });
  },
);
it.each(["empty", "values", "failure"])("renders %s prompt previews", async (mode) => {
  installAppApi();
  server.use(
    http.get("/api/chats/:id/prompt-preview", () =>
      mode === "failure"
        ? HttpResponse.json({ detail: "Denied" }, { status: 403 })
        : HttpResponse.json({
            model_display_name: null,
            provider_name: null,
            model_identifier: null,
            parameters:
              mode === "empty" ? {} : { none: null, object: { mode: "auto" }, boolean: false },
            messages: mode === "empty" ? [] : [{ role: "", content: "Prompt" }],
          }),
    ),
  );
  const wrapper = mount(SessionTab, { props: { chatId: `preview-${mode}` } });
  await flushPromises();
  if (mode === "failure") expect(wrapper.text()).toContain(t("chat.drawer.sessionError"));
  else {
    expect(wrapper.text()).toContain(t("chat.drawer.sessionModelUnknown"));
    if (mode === "empty") expect(wrapper.text()).toContain(t("chat.drawer.sessionPromptEmpty"));
    else expect(wrapper.text()).toContain('{"mode":"auto"}');
  }
  await wrapper.setProps({ chatId: undefined });
});
it.each(["empty", "error", "success"])(
  "renders %s audit logs and refreshes on matching completion",
  async (mode) => {
    const { db } = installAppApi();
    let calls = 0;
    server.use(
      http.get("/admin/logs/llm", () => {
        calls++;
        return mode === "error"
          ? HttpResponse.json({ detail: "Denied" }, { status: 403 })
          : HttpResponse.json({
              items:
                mode === "empty"
                  ? []
                  : [
                      {
                        ...db.logs[0],
                        status: "error",
                        error_message: "Quota exhausted",
                        estimated_cost_usd: null,
                      },
                    ],
            });
      }),
    );
    const wrapper = mount(LogsTab, { props: { chatId: `logs-${mode}` } });
    await flushPromises();
    if (mode === "success") {
      expect(wrapper.text()).toContain("Quota exhausted");
      await wrapper.findAll("button")[1]!.trigger("click");
      await wrapper.findAll("button")[1]!.trigger("click");
    } else
      expect(wrapper.text()).toContain(
        t(mode === "empty" ? "chat.drawer.logsEmpty" : "chat.drawer.logsError"),
      );
    useCompletionSignal().notify("different");
    await flushPromises();
    expect(calls).toBe(1);
    useCompletionSignal().notify(`logs-${mode}`);
    await flushPromises();
    expect(calls).toBe(2);
    await wrapper.setProps({ chatId: undefined });
    await wrapper.get("button").trigger("click");
    expect(calls).toBe(2);
  },
);
it.each([
  ["chat.drawer.manageLoadouts", "/loadouts"],
  ["chat.persona.manage", "/loadouts"],
  ["chat.drawer.manageMemories", "/memory"],
  ["chat.drawer.manageLorebooks", "/lorebooks"],
])("%s closes the drawer and navigates to its management page", async (key, path) => {
  const { db } = installAppApi();
  db.profiles.splice(0);
  db.memories.splice(0);
  db.lorebooks.splice(0);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/:pathMatch(.*)*", component: { template: "<div/>" } }],
  });
  await router.push("/chats/c");
  const wrapper = mount(SettingsTab, {
    props: { characterId: "", sessionTitle: "Title" },
    global: { plugins: [createPinia(), router] },
  });
  await flushPromises();
  expect(wrapper.text()).toContain(t("chat.profile.empty"));
  if (key === "chat.persona.manage")
    await button(wrapper, t("chat.persona.title")).trigger("click");
  if (key.includes("Memories")) await button(wrapper, t("chat.drawer.memories")).trigger("click");
  if (key.includes("Lorebooks")) await button(wrapper, t("chat.drawer.lorebooks")).trigger("click");
  await button(wrapper, t(key)).trigger("click");
  await flushPromises();
  expect(router.currentRoute.value.path).toBe(path);
  expect(wrapper.emitted("close")).toHaveLength(1);
});
