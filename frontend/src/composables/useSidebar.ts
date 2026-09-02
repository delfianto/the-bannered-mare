import { ref, watch } from "vue";

const collapsed = ref(false);

// Persist to localStorage
const stored = localStorage.getItem("sidebar-collapsed");
if (stored !== null) {
  collapsed.value = stored === "true";
}

watch(collapsed, (val) => {
  localStorage.setItem("sidebar-collapsed", String(val));
});

export function useSidebar() {
  function toggle() {
    collapsed.value = !collapsed.value;
  }

  return { collapsed, toggle };
}
