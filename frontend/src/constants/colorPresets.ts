export interface ColorPreset {
  id: string;
  name: string;
  description: string;
  cssClass: string;
  preview: {
    primary: string;
    background: string;
    backgroundDark: string;
  };
}

export const COLOR_PRESETS: ColorPreset[] = [
  {
    id: "amber",
    name: "Amber Dawn",
    description: "Warm gold & parchment",
    cssClass: "",
    preview: { primary: "#C9922E", background: "#FFFFFF", backgroundDark: "#0F0D0B" },
  },
  {
    id: "emerald",
    name: "Emerald Glade",
    description: "Sage green & earth",
    cssClass: "theme-emerald",
    preview: { primary: "#5C8A6C", background: "#FAFAF8", backgroundDark: "#0E0E0C" },
  },
  {
    id: "sapphire",
    name: "Sapphire Archive",
    description: "Scholarly ink & paper",
    cssClass: "theme-sapphire",
    preview: { primary: "#4A7AAF", background: "#F9F9F8", backgroundDark: "#0C0D10" },
  },
  {
    id: "crimson",
    name: "Crimson Sanctum",
    description: "Wine & aged leather",
    cssClass: "theme-crimson",
    preview: { primary: "#8B4D50", background: "#FAF9F8", backgroundDark: "#100C0C" },
  },
  {
    id: "violet",
    name: "Violet Arcane",
    description: "Moonlight indigo",
    cssClass: "theme-violet",
    preview: { primary: "#6E64A8", background: "#FAF9FB", backgroundDark: "#0D0C10" },
  },
  {
    id: "obsidian",
    name: "Obsidian Night",
    description: "Antique bronze & shadow",
    cssClass: "theme-obsidian",
    preview: { primary: "#A0926B", background: "#F5F5F0", backgroundDark: "#0C0C0C" },
  },
];
