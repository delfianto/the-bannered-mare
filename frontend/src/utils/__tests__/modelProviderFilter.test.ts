import { describe, it, expect } from "bun:test";
import { providersForFamily } from "@/utils/modelProviderFilter";

const P = (id: string, provider_type: string) => ({ id, name: id, provider_type }) as any;
const providers = [
  P("anthropic", "anthropic"),
  P("lmstudio", "lmstudio"),
  P("ollama", "ollama"),
  P("openrouter", "openrouter"),
];

describe("providersForFamily", () => {
  it("keeps only providers whose type is in the family's provider_types", () => {
    const family = { provider_types: ["anthropic", "openrouter"] } as any;
    expect(providersForFamily(providers, family).map((p) => p.id)).toEqual([
      "anthropic",
      "openrouter",
    ]);
  });

  it("handles the Gemma case (ollama/lmstudio/openrouter)", () => {
    const family = { provider_types: ["ollama", "lmstudio", "openrouter"] } as any;
    expect(
      providersForFamily(providers, family)
        .map((p) => p.id)
        .sort(),
    ).toEqual(["lmstudio", "ollama", "openrouter"]);
  });

  it("returns [] when no family is selected", () => {
    expect(providersForFamily(providers, undefined)).toEqual([]);
    expect(providersForFamily(providers, null)).toEqual([]);
  });
});
