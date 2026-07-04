import { ref } from "vue";

export interface ToastMessage {
  id: string;
  title: string;
  description?: string;
  type: "success" | "error" | "info" | "warning";
  duration?: number;
}

const toasts = ref<ToastMessage[]>([]);

export function useToastState() {
  return toasts;
}

export function useAppToast() {
  const addToast = (
    type: ToastMessage["type"],
    title: string,
    description?: string,
    duration = 4000,
  ) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
    const toast: ToastMessage = { id, title, description, type, duration };
    toasts.value.push(toast);

    if (duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, duration);
    }
  };

  const removeToast = (id: string) => {
    toasts.value = toasts.value.filter((t) => t.id !== id);
  };

  return {
    toasts,
    addToast,
    removeToast,
    success: (title: string, description?: string) => addToast("success", title, description),
    error: (title: string, description?: string) => addToast("error", title, description),
    info: (title: string, description?: string) => addToast("info", title, description),
    warning: (title: string, description?: string) => addToast("warning", title, description),
    loading: (title: string, description?: string) => addToast("info", title, description, 0), // persistent loading
  };
}
