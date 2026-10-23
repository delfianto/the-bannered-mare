import { afterEach, expect, it, vi } from "vite-plus/test";
import { mount, DOMWrapper, flushPromises } from "@vue/test-utils";
import LogDetailModal from "../LogDetailModal.vue";
import { llmLogs } from "@/mocks/data/llm-logs";
import type { components } from "@/api/schema";
import { button } from "@/test/views";
import i18n from "@/i18n";
const t = (k: string) => i18n.global.t(k);
const dialog = () => new DOMWrapper(document.querySelector<HTMLElement>('[role="dialog"]')!);
afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});
it("handles structured and missing LLM payloads, alternate reasoning keys and copy failures", async () => {
  const write = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue(undefined);
  const log = {
    ...llmLogs[0],
    status: "error",
    estimated_cost_usd: null,
    error_message: "Quota exhausted",
    request_payload: [
      { role: "system", content: "Instruction" },
      { role: 42, content: { text: "structured" } },
      { role: "tool", content: ["result"] },
    ],
    response_payload: { content: "Answer", reasoning_content: "Thought", usage: { tokens: 12 } },
  };
  const wrapper = mount(LogDetailModal, {
    props: { show: true, kind: "llm", log },
    attachTo: document.body,
  });
  expect(dialog().text()).toContain("structured");
  expect(dialog().text()).toContain("unknown");
  expect(dialog().text()).toContain("Thought");
  vi.useFakeTimers();
  await button(dialog(), t("common.copy")).trigger("click");
  await flushPromises();
  expect(write).toHaveBeenCalled();
  expect(dialog().text()).toContain(t("common.copied"));
  await vi.advanceTimersByTimeAsync(1500);
  expect(dialog().text()).not.toContain(t("common.copied"));
  write.mockRejectedValueOnce(new Error("Denied"));
  await button(dialog(), t("common.copy")).trigger("click");
  await flushPromises();
  await wrapper.setProps({
    log: { ...log, request_payload: [], response_payload: { content: 42, reasoning: 42 } },
  });
  expect(dialog().text()).not.toContain("Answer");
  await wrapper.setProps({ log: { ...log, request_payload: [], response_payload: null } });
  expect(dialog().text()).toContain(t("settings.logs.notCaptured"));
  await wrapper.setProps({ show: false, kind: null, log: null });
});
it("shows missing HTTP bodies and sparse error context without empty sections", async () => {
  const log: components["schemas"]["HttpLogResponse"] = {
    id: "http",
    method: "GET",
    path: "/health",
    status_code: 200,
    latency_ms: 1,
    request_id: "request",
    created_at: new Date().toISOString(),
    client_ip: null,
    user_agent: null,
    request_body: null,
    response_body: null,
  };
  const wrapper = mount(LogDetailModal, {
    props: { show: true, kind: "http", log },
    attachTo: document.body,
  });
  expect(dialog().text()).toContain(t("settings.logs.notCaptured"));
  await wrapper.setProps({
    kind: "error",
    log: {
      id: "error",
      error_type: "Error",
      message: "Failure",
      created_at: new Date().toISOString(),
      stack_trace: null,
      context: {},
    },
  });
  expect(dialog().text()).toContain("Failure");
  expect(dialog().text()).not.toContain(t("settings.logs.stackTrace"));
  await dialog()
    .get(`button[aria-label="${t("common.close")}"]`)
    .trigger("click");
  expect(wrapper.emitted("close")).toHaveLength(1);
});
