import { conversationCache } from "../loader";

export function registerConversations() {
  // Aetheris Moravayn
  conversationCache.register("chat-aetheris-01", () => import("./scenarios/aetheris.yaml"), 30);

  // Aranwen the Banished
  conversationCache.register("chat-aranwen-01", () => import("./scenarios/aranwen.yaml"), 12);

  // Beeps-With-The-Hist
  conversationCache.register("chat-beeps-01", () => import("./scenarios/beeps.yaml"), 22);

  // Calanwe Sun-Blessed
  conversationCache.register("chat-calanwe-01", () => import("./scenarios/calanwe.yaml"), 18);

  // Drenlyn Uvirith
  conversationCache.register("chat-drenlyn-01", () => import("./scenarios/drenlyn.yaml"), 19);

  // Eloise Montclair
  conversationCache.register("chat-eloise-01", () => import("./scenarios/eloise.yaml"), 5);

  // Finedrin Treemother
  conversationCache.register("chat-finedrin-01", () => import("./scenarios/finedrin.yaml"), 25);

  // Helga Sky-Voice
  conversationCache.register("chat-helga-01", () => import("./scenarios/helga.yaml"), 16);

  // Lilatha of Artaeum
  conversationCache.register("chat-lilatha-01", () => import("./scenarios/lilatha.yaml"), 20);

  // Lynara Frost-Scholar
  conversationCache.register("chat-lynara-01", () => import("./scenarios/lynara.yaml"), 8);

  // Mirelle Shadowfoot
  conversationCache.register("chat-mirelle-01", () => import("./scenarios/mirelle.yaml"), 6);

  // Elara Mavine
  conversationCache.register("chat-elara-01", () => import("./scenarios/elara.yaml"), 28);

  // Nerise Sarethi
  conversationCache.register("chat-nerise-01", () => import("./scenarios/nerise.yaml"), 11);

  // Nerys Dren
  conversationCache.register("chat-nerys-01", () => import("./scenarios/nerys.yaml"), 6);

  // Octavia Maro
  conversationCache.register("chat-octavia-01", () => import("./scenarios/octavia.yaml"), 10);

  // Taneth at-Sentinel
  conversationCache.register("chat-taneth-01", () => import("./scenarios/taneth.yaml"), 14);

  // Valerica's Heir
  conversationCache.register("chat-valerica-01", () => import("./scenarios/valerica.yaml"), 33);

  // Yargol gra-Dushnikh
  conversationCache.register("chat-yargol-01", () => import("./scenarios/yargol.yaml"), 9);

  // Zahrasha the Death-Singer
  conversationCache.register("chat-zahrasha-01", () => import("./scenarios/zahrasha.yaml"), 15);
}

// Initialize registrations immediately
registerConversations();

/**
 * Legacy export for backward compatibility
 */
export const messages: Record<string, any> = new Proxy(
  {},
  {
    get() {
      return undefined;
    },
  },
);
