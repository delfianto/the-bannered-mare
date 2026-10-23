import { afterEach, beforeEach, expect, it, vi } from "vite-plus/test";
import { DOMWrapper } from "@vue/test-utils";
import { http, HttpResponse } from "msw";
import ChatView from "../chat/ChatView.vue";
import { installAppApi } from "@/test/appApi";
import { mountView, button, pickOption } from "@/test/views";
import { server } from "@/mocks/server";
import { useSuggestionSettings } from "@/composables/useSuggestionSettings";
import { useToastState } from "@/composables/useToast";
import i18n from "@/i18n";
const t = (k: string) => i18n.global.t(k);
const dialog = () => new DOMWrapper(document.querySelector<HTMLElement>('[role="dialog"]')!);
beforeEach(() => {
  const s = useSuggestionSettings();
  s.replySuggestionsEnabled.value = true;
  s.autoGenerateTones.value = false;
});
afterEach(() => {
  vi.restoreAllMocks();
  useToastState().value = [];
});
function chatApi() {
  const api = installAppApi();
  const suggestions: { mode: string; tone?: string }[] = [];
  let fail = false;
  let sent = false;
  server.use(
    http.get("/api/chats/:id/messages", ({ params }) =>
      HttpResponse.json({
        items: sent
          ? [
              {
                id: "user",
                chat_id: params.id,
                role: "user",
                content: "Hello",
                active_index: 0,
                created_at: new Date().toISOString(),
              },
            ]
          : [
              {
                id: "assistant",
                chat_id: params.id,
                role: "assistant",
                content: "Welcome, traveler.",
                active_index: 0,
                created_at: new Date().toISOString(),
              },
            ],
        meta: { has_more: false, cursor: null },
      }),
    ),
    http.post("/api/chats/:id/messages/suggestions", async ({ request }) => {
      const body = (await request.json()) as { mode: string; tone?: string };
      suggestions.push(body);
      return HttpResponse.json({
        suggestions: fail
          ? []
          : body.mode === "tones"
            ? ["Curious", "Bold"]
            : body.mode === "impersonate"
              ? ["I seek the archive."]
              : ["Tell me more.", "Who are you?"],
      });
    }),
    http.post("/api/chats/:id/messages", () => {
      sent = true;
      return fail
        ? HttpResponse.json({ detail: "Provider unavailable" }, { status: 503 })
        : new HttpResponse(
            'data: {"type":"text","content":"The archive opens."}\n\ndata: [DONE]\n\n',
            { headers: { "Content-Type": "text/event-stream" } },
          );
    }),
    http.post("/api/chats/:id/profile", async ({ params, request }) => {
      const body = (await request.json()) as { profile_id: string };
      const row = api.db.chats.find((c) => c.id === params.id)!;
      row.last_profile_name = api.db.profiles.find((p) => p.id === body.profile_id)?.name;
      return HttpResponse.json(row);
    }),
  );
  return { ...api, suggestions, setFail: (v: boolean) => (fail = v) };
}
it("drafts a toned reply, loads candidates, sends a stream and changes sessions", async () => {
  const { db, suggestions } = chatApi();
  const { wrapper, router } = await mountView(
    ChatView,
    `/chats/${db.chats[0].id}`,
    "/chats/:chatId",
    "chat",
  );
  await vi.waitFor(() => expect(wrapper.text()).toContain("Welcome, traveler."));
  await button(wrapper, t("chat.suggest.tones")).trigger("click");
  await vi.waitFor(() => expect(wrapper.text()).toContain("Curious"));
  await button(wrapper, "Curious").trigger("click");
  await vi.waitFor(() =>
    expect((wrapper.get("textarea").element as HTMLTextAreaElement).value).toBe(
      "I seek the archive.",
    ),
  );
  expect(suggestions.at(-1)).toMatchObject({ mode: "impersonate", tone: "Curious" });
  await button(wrapper, t("chat.suggest.button")).trigger("click");
  await vi.waitFor(() => expect(wrapper.text()).toContain("Tell me more."));
  await button(wrapper, t("chat.suggest.back")).trigger("click");
  await wrapper.get("textarea").trigger("focus");
  await wrapper.get("textarea").trigger("keydown", { key: "Enter", shiftKey: true });
  await wrapper.get("textarea").trigger("keydown", { key: "Enter" });
  await vi.waitFor(() => expect(wrapper.text()).toContain("The archive opens."));
  expect((wrapper.get("textarea").element as HTMLTextAreaElement).value).toBe("");
  const session = wrapper
    .findAll("button")
    .find((b) => b.text().includes(db.chats[1].character.name))!;
  await session.trigger("click");
  await vi.waitFor(() => expect(router.currentRoute.value.params.chatId).toBe(db.chats[1].id));
  await wrapper.get(`button[aria-label="${t("common.goBack")}"]`).trigger("click");
  await vi.waitFor(() => expect(router.currentRoute.value.path).toBe("/chats"));
});
it("shows failed suggestions and generation, supports retry and dismissal", async () => {
  const { db, setFail } = chatApi();
  const { wrapper } = await mountView(
    ChatView,
    `/chats/${db.chats[0].id}`,
    "/chats/:chatId",
    "chat",
  );
  await vi.waitFor(() => expect(wrapper.text()).toContain("Welcome, traveler."));
  setFail(true);
  for (const key of ["chat.suggest.tones", "chat.suggest.button", "chat.moods.boldly"]) {
    await button(wrapper, t(key)).trigger("click");
    await vi.waitFor(() =>
      expect(useToastState().value.at(-1)?.title).toBe(t("chat.suggest.error")),
    );
  }
  await wrapper.get("textarea").setValue("Hello");
  await wrapper.get(`button[aria-label="${t("chat.sendMessage")}"]`).trigger("click");
  await vi.waitFor(() => expect(wrapper.text()).toContain("Provider unavailable"));
  await button(wrapper, t("chat.error.retry")).trigger("click");
  await vi.waitFor(() => expect(wrapper.text()).toContain("Provider unavailable"));
  await button(wrapper, t("chat.error.dismiss")).trigger("click");
  expect(wrapper.text()).not.toContain("Provider unavailable");
});
it("opens every drawer tab, changes settings, renames and deletes the active session", async () => {
  const { db, requests } = chatApi();
  const chat = db.chats[0];
  chat.last_profile_name = db.profiles[0].name;
  const { wrapper, router } = await mountView(
    ChatView,
    `/chats/${chat.id}`,
    "/chats/:chatId",
    "chat",
  );
  await vi.waitFor(() => expect(wrapper.text()).toContain("Welcome, traveler."));
  await wrapper.get(`button[aria-label="${t("chat.sessionMenu")}"]`).trigger("click");
  await vi.waitFor(() => expect(dialog().text()).toContain(chat.character.name));
  await vi.waitFor(() =>
    expect(dialog().text()).toContain(db.characters[0].description!.slice(0, 50)),
  );
  await button(dialog(), t("chat.drawer.tabs.session")).trigger("click");
  await vi.waitFor(() => expect(dialog().text()).toContain("Test model"));
  await button(dialog(), t("chat.drawer.tabs.logs")).trigger("click");
  await vi.waitFor(() => expect(dialog().text()).toContain(db.logs[0].model));
  const logButton = dialog()
    .findAll("button")
    .find((b) => b.text().includes(db.logs[0].model))!;
  await logButton.trigger("click");
  expect(dialog().text()).toContain(t("chat.drawer.logsRequest"));
  await dialog()
    .get(`button[aria-label="${t("chat.drawer.logsRefresh")}"]`)
    .trigger("click");
  await button(dialog(), t("chat.drawer.tabs.settings")).trigger("click");
  await vi.waitFor(() =>
    expect(dialog().findAll('input[type="radio"]').length).toBe(db.profiles.length),
  );
  const menus = dialog().findAll('[aria-haspopup="listbox"]');
  const model = db.models.find((m) => m.enabled && m.id !== chat.model.id)!;
  await pickOption(menus[0]!, model.display_name);
  await vi.waitFor(() =>
    expect(
      requests.some(
        (r) => r.method === "PUT" && (r.body as { model_id?: string })?.model_id === model.id,
      ),
    ).toBe(true),
  );
  await pickOption(menus[1]!, model.display_name);
  await vi.waitFor(() =>
    expect(
      requests.some((r) => (r.body as { task_model_id?: string })?.task_model_id === model.id),
    ).toBe(true),
  );
  await pickOption(menus[1]!, t("chat.model.sameAsChat"));
  await button(dialog(), t("chat.profile.reapply")).trigger("click");
  await dialog().findAll('input[type="radio"]')[1]!.setValue(true);
  await button(dialog(), t("chat.persona.title")).trigger("click");
  await vi.waitFor(() => expect(dialog().text()).toContain(db.personas[0].name));
  const persona = dialog()
    .findAll("button")
    .find((b) => b.text().startsWith(db.personas[0].name))!;
  await persona.trigger("click");
  await button(dialog(), t("chat.persona.none")).trigger("click");
  await button(dialog(), t("chat.drawer.memories")).trigger("click");
  await vi.waitFor(() => expect(dialog().text()).toContain(db.memories[0].name));
  await button(dialog(), t("chat.drawer.lorebooks")).trigger("click");
  await vi.waitFor(() => expect(dialog().text()).toContain(db.lorebooks[0].name));
  const book = dialog()
    .findAll("button")
    .find((b) => b.text().includes(db.lorebooks[0].name))!;
  await book.trigger("click");
  await book.trigger("click");
  await book.trigger("click");
  const rename = dialog().get("input.input-field");
  await rename.setValue("  Renamed adventure  ");
  await rename.trigger("blur");
  await vi.waitFor(() => expect(wrapper.text()).toContain("Renamed adventure"));
  await button(dialog(), t("common.delete")).trigger("click");
  await button(dialog(), t("common.deleteConfirm")).trigger("click");
  await vi.waitFor(() => expect(router.currentRoute.value.params.chatId).toBe(db.chats[0].id));
  document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
});
it("provides an actionable empty chat library", async () => {
  const { db } = chatApi();
  db.chats.splice(0);
  const { wrapper, router } = await mountView(ChatView, "/chats", "/chats", "chats");
  await vi.waitFor(() => expect(wrapper.text()).toContain("No Tales Begun"));
  await button(wrapper, "Browse Characters").trigger("click");
  await vi.waitFor(() => expect(router.currentRoute.value.path).toBe("/characters"));
});
