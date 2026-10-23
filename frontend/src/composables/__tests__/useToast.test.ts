import { afterEach, beforeEach, describe, expect, it, vi } from "vite-plus/test";
import { useAppToast, useToastState } from "@/composables/useToast";
beforeEach(() => vi.useFakeTimers());
afterEach(() => {
  useToastState().value = [];
  vi.useRealTimers();
});
describe("toast lifecycle", () => {
  it.each(["success", "error", "info", "warning"] as const)(
    "%s notifications are shared and expire after their duration",
    (type) => {
      const toast = useAppToast();
      toast[type]("Title", "Details");
      expect(useToastState().value[0]).toMatchObject({
        type,
        title: "Title",
        description: "Details",
      });
      vi.advanceTimersByTime(3999);
      expect(toast.toasts.value).toHaveLength(1);
      vi.advanceTimersByTime(1);
      expect(toast.toasts.value).toEqual([]);
    },
  );
  it("loading notifications persist until explicitly removed without deleting neighbors", () => {
    const toast = useAppToast();
    toast.loading("Loading");
    toast.info("Loaded later");
    const id = toast.toasts.value[0].id;
    vi.advanceTimersByTime(4000);
    expect(toast.toasts.value.map((t) => t.id)).toEqual([id]);
    toast.removeToast(id);
    expect(toast.toasts.value).toEqual([]);
  });
});
