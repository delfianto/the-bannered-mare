import { createI18n } from "vue-i18n";
import en from "@/locales/en.json";

const i18n = createI18n({
  legacy: false,
  locale: localStorage.getItem("locale") || "en",
  fallbackLocale: "en",
  globalInjection: true,
  messages: { en },
});

export default i18n;
