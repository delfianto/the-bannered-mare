import { createI18n } from "vue-i18n";
import en from "@/locales/en.json";
import fr from "@/locales/fr.json";
import de from "@/locales/de.json";
import es from "@/locales/es.json";
import pt from "@/locales/pt.json";

export const SUPPORTED_LOCALES: { code: string; name: string }[] = [
  { code: "en", name: "English" },
  { code: "fr", name: "Français" },
  { code: "de", name: "Deutsch" },
  { code: "es", name: "Español" },
  { code: "pt", name: "Português" },
];

const i18n = createI18n({
  legacy: false,
  locale: localStorage.getItem("locale") || "en",
  fallbackLocale: "en",
  globalInjection: true,
  messages: { en, fr, de, es, pt },
});

export function setLocale(locale: string) {
  (i18n.global.locale as any).value = locale;
  localStorage.setItem("locale", locale);
  document.documentElement.setAttribute("lang", locale);
}

export default i18n;
