import { afterEach, beforeEach, describe, expect, it, vi } from "vite-plus/test";
import { effectScope } from "vue";
import { useConfirmAction, useKeyedConfirmAction } from "@/composables/useConfirmAction";
import { useConfirm, useConfirmState } from "@/composables/useConfirm";

beforeEach(() => vi.useFakeTimers());
afterEach(() => {
  vi.useRealTimers();
  useConfirmState().onCancel();
});

describe("destructive action confirmation", () => {
  it("requires two clicks within the timeout, then disarms", () => {
    const scope = effectScope();
    const action = vi.fn();
    const api = scope.run(() => useConfirmAction(action))!;
    api.trigger();
    expect(api.armed.value).toBe(true);
    expect(action).not.toHaveBeenCalled();
    api.trigger();
    expect(action).toHaveBeenCalledTimes(1);
    expect(api.armed.value).toBe(false);
    vi.runAllTimers();
    expect(action).toHaveBeenCalledTimes(1);
    scope.stop();
  });

  it("expired or explicitly reset confirmation requires another first click", () => {
    const scope = effectScope();
    const action = vi.fn();
    const api = scope.run(() => useConfirmAction(action, { timeout: 100 }))!;
    api.trigger();
    vi.advanceTimersByTime(100);
    expect(api.armed.value).toBe(false);
    api.trigger();
    api.reset();
    api.trigger();
    expect(action).not.toHaveBeenCalled();
    scope.stop();
    expect(vi.getTimerCount()).toBe(0);
  });

  it("a different row replaces the armed row and only the second click on that row runs", () => {
    const scope = effectScope();
    const api = scope.run(() => useKeyedConfirmAction({ timeout: 100 }))!;
    const remove = vi.fn();
    api.trigger("a", remove);
    api.trigger("b", remove);
    expect(api.isArmed("a")).toBe(false);
    expect(api.isArmed("b")).toBe(true);
    api.trigger("b", remove);
    expect(remove).toHaveBeenCalledTimes(1);
    expect(api.armedKey.value).toBeNull();
    api.trigger("c", remove);
    vi.advanceTimersByTime(100);
    expect(api.armedKey.value).toBeNull();
    api.trigger("d", remove);
    api.reset();
    expect(api.armedKey.value).toBeNull();
    scope.stop();
    expect(vi.getTimerCount()).toBe(0);
  });

  it("a new dialog cancels the previous promise and only the latest answer settles", async () => {
    const { confirm } = useConfirm();
    const ui = useConfirmState();
    const first = confirm({ message: "Delete A?", danger: true });
    const second = confirm({ message: "Delete B?" });
    expect(await first).toBe(false);
    expect(ui.state.value.message).toBe("Delete B?");
    expect(ui.state.value.danger).toBeUndefined();
    ui.onConfirm();
    expect(await second).toBe(true);
    expect(ui.state.value.open).toBe(false);
    ui.onCancel();
  });

  it("cancel resolves false and closes the dialog", async () => {
    const pending = useConfirm().confirm({ message: "Delete?" });
    useConfirmState().onCancel();
    expect(await pending).toBe(false);
  });
});
