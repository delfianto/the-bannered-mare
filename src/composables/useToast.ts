/**
 * Convenience wrapper around Nuxt UI's useToast.
 * The base `useToast` is auto-imported by the Nuxt UI Vite plugin.
 */
export function useAppToast() {
  const toast = useToast();

  return {
    toast,
    success: (message: string, description?: string) => {
      toast.add({ title: message, description, color: "success" });
    },
    error: (message: string, description?: string) => {
      toast.add({ title: message, description, color: "error" });
    },
    info: (message: string, description?: string) => {
      toast.add({ title: message, description, color: "info" });
    },
    warning: (message: string, description?: string) => {
      toast.add({ title: message, description, color: "warning" });
    },
    loading: (message: string, description?: string) => {
      toast.add({ title: message, description, icon: "i-lucide-loader-circle" });
    },
  };
}
