import { afterEach, expect, it, vi } from "vite-plus/test";
import { DOMWrapper } from "@vue/test-utils";
import { http, HttpResponse } from "msw";
import ConnectionsView from "../ConnectionsView.vue";
import { installAppApi } from "@/test/appApi";
import { mountView, button, pickOption } from "@/test/views";
import { server } from "@/mocks/server";
import { useToastState } from "@/composables/useToast";
import i18n from "@/i18n";
const t = (k: string) => i18n.global.t(k);
const dialog = () => new DOMWrapper(document.querySelector<HTMLElement>('[role="dialog"]')!);
afterEach(() => {
  vi.restoreAllMocks();
  useToastState().value = [];
});
it("mirrors model filters and pagination into the URL, rolls back failed toggles and opens details", async () => {
  const { db, requests } = installAppApi();
  let fail = false;
  server.use(
    http.patch("/api/models/:id/flags", ({ params }) =>
      fail
        ? HttpResponse.json({ detail: "Denied" }, { status: 403 })
        : HttpResponse.json(db.models.find((m) => m.id === params.id)),
    ),
  );
  const { wrapper, router } = await mountView(
    ConnectionsView,
    "/connections?tab=models",
    "/connections",
  );
  await vi.waitFor(() => expect(wrapper.find("tbody tr").exists()).toBe(true));
  const search = wrapper.get('input[aria-label="Search models"]');
  await search.trigger("focus");
  await search.setValue("GP");
  await search.setValue("GPT");
  await search.trigger("blur");
  await vi.waitFor(() => expect(router.currentRoute.value.query.q).toBe("GPT"));
  await search.setValue("");
  await vi.waitFor(() => expect(router.currentRoute.value.query.q).toBeUndefined());
  const menus = wrapper.findAll('[aria-haspopup="listbox"]');
  await pickOption(menus[0]!, db.providers[0].name);
  await pickOption(menus[0]!, t("connections.allProviders"));
  await pickOption(menus[1]!, db.families[0].name);
  await pickOption(menus[1]!, t("connections.allFamilies"));
  await pickOption(menus[2]!, t("connections.statusDisabled"));
  await pickOption(menus[2]!, t("connections.statusEnabled"));
  await pickOption(menus[2]!, t("connections.allStatuses"));
  await vi.waitFor(() => expect(wrapper.find("tbody tr").exists()).toBe(true));
  const toggle = wrapper.findAll('input[role="switch"]')[0]!;
  const original = (toggle.element as HTMLInputElement).checked;
  fail = true;
  await toggle.setValue(!original);
  await vi.waitFor(() =>
    expect(useToastState().value.at(-1)?.title).toBe(t("connections.model.toast.updateFailed")),
  );
  expect((toggle.element as HTMLInputElement).checked).toBe(original);
  fail = false;
  await toggle.setValue(!original);
  await vi.waitFor(() =>
    expect(requests.filter((r) => r.path === "/api/models").length).toBeGreaterThan(3),
  );
  await wrapper.get('button[aria-label="Next page"]').trigger("click");
  await vi.waitFor(() => expect(router.currentRoute.value.query.page).toBe("2"));
  await vi.waitFor(() => expect(wrapper.find("tbody tr").exists()).toBe(true));
  await wrapper.get("tbody tr").trigger("click");
  await vi.waitFor(() => expect(router.currentRoute.value.path).toMatch(/\/settings\/models\//));
});
it.each(["providers", "model-families"])(
  "creates %s after recovering from server rejection",
  async (tab) => {
    const { requests } = installAppApi();
    let fail = true;
    const endpoint = tab === "providers" ? "/api/providers" : "/api/model-families";
    server.use(
      http.post(endpoint, () =>
        fail ? HttpResponse.json({ detail: "Rejected" }, { status: 400 }) : undefined,
      ),
    );
    const { wrapper } = await mountView(ConnectionsView, `/connections?tab=${tab}`, "/connections");
    await vi.waitFor(() => expect(wrapper.find("h3,tbody tr").exists()).toBe(true));
    await button(
      wrapper,
      t(tab === "providers" ? "connections.newProvider" : "connections.newFamily"),
    ).trigger("click");
    await dialog().get("input").setValue("  Custom connection  ");
    if (tab === "providers") await pickOption(dialog().get('[aria-haspopup="listbox"]'), "OpenAI");
    else {
      await dialog().findAll("input")[1]!.setValue("  custom-id  ");
      await button(dialog(), "OpenAI").trigger("click");
      await button(dialog(), "OpenAI").trigger("click");
      await button(dialog(), "Google").trigger("click");
    }
    const label = tab === "providers" ? "Create Provider" : "Create Family";
    await button(dialog(), label).trigger("click");
    await vi.waitFor(() =>
      expect(useToastState().value.at(-1)?.title).toBe(
        t(`connections.${tab === "providers" ? "provider" : "family"}.toast.createFailed`),
      ),
    );
    fail = false;
    await button(dialog(), label).trigger("click");
    await vi.waitFor(() => expect(wrapper.text()).toContain("Custom connection"));
    expect(requests.find((r) => r.method === "POST")?.body).toMatchObject({
      name: "Custom connection",
    });
    await button(
      wrapper,
      t(tab === "providers" ? "connections.newProvider" : "connections.newFamily"),
    ).trigger("click");
    await button(dialog(), t("common.cancel")).trigger("click");
  },
);
it("filters families by provider type, searches, paginates and opens details", async () => {
  const { db } = installAppApi();
  const { wrapper, router } = await mountView(
    ConnectionsView,
    "/connections?tab=model-families",
    "/connections",
  );
  await vi.waitFor(() => expect(wrapper.find("tbody tr").exists()).toBe(true));
  const search = wrapper.get('input[aria-label="Search model families"]');
  await search.trigger("focus");
  await search.setValue("G");
  await search.setValue("GPT");
  await search.trigger("blur");
  await vi.waitFor(() => expect(router.currentRoute.value.query.q).toBe("GPT"));
  await search.setValue("");
  await vi.waitFor(() => expect(router.currentRoute.value.query.q).toBeUndefined());
  await pickOption(wrapper.get('[aria-haspopup="listbox"]'), db.providers[0].name);
  await pickOption(wrapper.get('[aria-haspopup="listbox"]'), "All providers");
  await vi.waitFor(() =>
    expect(wrapper.find('button[aria-label="Next page"]').exists()).toBe(true),
  );
  await wrapper.get('button[aria-label="Next page"]').trigger("click");
  await vi.waitFor(() => expect(router.currentRoute.value.query.page).toBe("2"));
  await vi.waitFor(() => expect(wrapper.find("tbody tr").exists()).toBe(true));
  await wrapper.get("tbody tr").trigger("click");
  await vi.waitFor(() =>
    expect(router.currentRoute.value.path).toContain("/settings/model-families/"),
  );
});
