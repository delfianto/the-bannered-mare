import { nextTick } from "vue";
import { afterEach, expect, it, vi } from "vite-plus/test";
import { http, HttpResponse } from "msw";
import SettingsView from "../settings/SettingsView.vue";
import { installAppApi } from "@/test/appApi";
import { mountView, button, pickOption } from "@/test/views";
import { server } from "@/mocks/server";
import { setLocale } from "@/i18n";
import i18n from "@/i18n";
import { useFontSize } from "@/composables/useFontSize";
const t = (k: string) => i18n.global.t(k);
afterEach(() => {
  setLocale("en");
  vi.restoreAllMocks();
});
it("updates reading, suggestions, typography, language and custom colors", async () => {
  installAppApi();
  const { wrapper } = await mountView(SettingsView, "/settings");
  const slider = wrapper.get('input[type="range"]');
  vi.spyOn(slider.element, "getBoundingClientRect").mockReturnValue({
    left: 10,
    width: 100,
  } as DOMRect);
  await slider.trigger("pointermove", { clientX: 50 });
  await slider.trigger("pointerdown", { clientX: 60, pointerId: 1 });
  expect(useFontSize().fontSize.value).toBe(19);
  await slider.trigger("pointermove", { clientX: 200 });
  expect(useFontSize().fontSize.value).toBe(24);
  await slider.trigger("pointerup");
  await slider.setValue(17);
  expect(useFontSize().fontSize.value).toBe(17);
  await slider.trigger("pointercancel");
  for (const key of ["Narrow", "Cozy", "Wide", "Full"])
    await button(wrapper, t(`settings.interface.chatWidth${key}`)).trigger("click");
  const reply = wrapper.get('input[aria-label="Enable reply suggestions"]');
  await reply.setValue(false);
  expect(
    wrapper.get('input[aria-label="Auto-generate tone"]').attributes("disabled"),
  ).toBeDefined();
  await reply.setValue(true);
  await wrapper.get('input[aria-label="Auto-generate tone"]').setValue(false);
  await wrapper
    .get(`input[aria-label="${t("settings.interface.narrativeItalics")}"]`)
    .setValue(false);
  const menus = wrapper.findAll('[aria-haspopup="listbox"]');
  await pickOption(menus[1]!, t("settings.interface.typographyModern"));
  await pickOption(menus[2]!, t("settings.interface.chatFontGeorgia"));
  await wrapper.get('input[aria-label="Dark mode"]').setValue(false);
  await wrapper.get('input[aria-label="Dark mode"]').setValue(true);
  await wrapper.findAll('button[aria-label^="Select "]')[1]!.trigger("click");
  await wrapper.get('button[aria-label="Custom theme"]').trigger("click");
  await wrapper.get('input[type="color"]').setValue("#123456");
  await wrapper.get('input[spellcheck="false"]').setValue("#ABCDEF");
  await wrapper.get('input[spellcheck="false"]').trigger("change");
  expect((wrapper.get('input[type="color"]').element as HTMLInputElement).value).toBe("#abcdef");
  await wrapper.get('input[spellcheck="false"]').setValue("invalid");
  await wrapper.get('input[spellcheck="false"]').trigger("change");
  await button(wrapper, "Reset").trigger("click");
  await pickOption(menus[0]!, "Deutsch");
  expect(i18n.global.locale.value).toBe("de");
  setLocale("en");
  await nextTick();
  await button(wrapper, t("settings.tabs.about")).trigger("click");
  expect(wrapper.text()).toContain("The Bannered Mare");
});
const now = Date.now();
function logsApi(empty = false) {
  const { db } = installAppApi();
  const httpLogs = [0, 120000, 7200000, 172800000, 864000000].map((age, i) => ({
    id: `http-${i}`,
    method: ["GET", "POST", "PUT", "DELETE", "PATCH"][i],
    path: `/example/${i}`,
    status_code: [200, 302, 404, 500, 204][i],
    latency_ms: i * 1000,
    request_id: `req-${i}`,
    created_at: new Date(now - age).toISOString(),
    client_ip: "127.0.0.1",
    user_agent: "Test browser",
    request_body: { query: "dragon" },
    response_body: { ok: true },
  }));
  const errors = [
    {
      id: "error",
      error_type: "ValueError",
      message: "Invalid dragon",
      stack_trace: "Traceback: dragon",
      context: { chat_id: "chat" },
      created_at: new Date().toISOString(),
    },
  ];
  const stats = [0, 1, 2, 3].map((i) => ({
    provider: ["anthropic", "openai", "unknown", "google"][i],
    model: `Model ${i}`,
    total_calls: i * 100,
    success_count: i === 1 ? 100 : 0,
    total_tokens: [0, 2500, 20000, 2000000][i],
    total_cost_usd: [0, 0.01, 3, null][i],
    avg_latency_ms: i * 1000,
  }));
  server.use(
    http.get("/admin/logs/http", () => HttpResponse.json({ items: empty ? [] : httpLogs })),
    http.get("/admin/logs/errors", () => HttpResponse.json({ items: empty ? [] : errors })),
    http.get("/admin/logs/llm/stats", () => HttpResponse.json({ stats: empty ? [] : stats })),
    http.get("/admin/logs/llm", () => HttpResponse.json({ items: empty ? [] : db.logs })),
  );
  return { db };
}
it("aggregates usage and opens HTTP, LLM and error log details", async () => {
  logsApi();
  const write = vi.fn().mockResolvedValue(undefined);
  vi.spyOn(navigator.clipboard, "writeText").mockImplementation(write);
  const { wrapper } = await mountView(SettingsView, "/settings");
  await button(wrapper, t("settings.tabs.logs")).trigger("click");
  await vi.waitFor(() => expect(wrapper.text()).toContain("2.0M"));
  expect(wrapper.text()).toContain("100% ok");
  expect(wrapper.text()).toContain("$3.00");
  await wrapper
    .findAll("button")
    .find((b) => b.text().includes("/example/0"))!
    .trigger("click");
  await vi.waitFor(() =>
    expect(document.querySelector('[role="dialog"]')?.textContent).toContain("dragon"),
  );
  const copy = Array.from(
    document.querySelectorAll<HTMLButtonElement>('[role="dialog"] button'),
  ).find((b) => b.textContent?.trim() === t("common.copy"))!;
  copy.click();
  await vi.waitFor(() => expect(write).toHaveBeenCalled());
  document
    .querySelector<HTMLButtonElement>(`[role="dialog"] button[aria-label="${t("common.close")}"]`)!
    .click();
  await button(wrapper, t("settings.logs.llmLogs")).trigger("click");
  await wrapper
    .findAll("button")
    .find((b) => b.text().includes(" in /"))!
    .trigger("click");
  await vi.waitFor(() =>
    expect(document.querySelector('[role="dialog"]')?.textContent).toContain(
      t("settings.logs.request"),
    ),
  );
  document
    .querySelector<HTMLButtonElement>(`[role="dialog"] button[aria-label="${t("common.close")}"]`)!
    .click();
  await button(wrapper, t("settings.logs.errorLogs")).trigger("click");
  await wrapper
    .findAll("button")
    .find((b) => b.text().includes("Invalid dragon"))!
    .trigger("click");
  await vi.waitFor(() =>
    expect(document.querySelector('[role="dialog"]')?.textContent).toContain("Traceback: dragon"),
  );
  vi.unstubAllGlobals();
});
it("renders empty log categories and zero-request statistics", async () => {
  logsApi(true);
  const { wrapper } = await mountView(SettingsView, "/settings");
  await button(wrapper, t("settings.tabs.logs")).trigger("click");
  await vi.waitFor(() => expect(wrapper.text()).toContain(t("settings.logs.noHttpLogs")));
  for (const [tab, empty] of [
    ["llmLogs", "noLlmLogs"],
    ["errorLogs", "noErrorLogs"],
  ]) {
    await button(wrapper, t(`settings.logs.${tab}`)).trigger("click");
    expect(wrapper.text()).toContain(t(`settings.logs.${empty}`));
  }
  expect(wrapper.text()).toContain("0%");
});
