import type { components } from "@/api/schema";

type Provider = components["schemas"]["ProviderResponse"];
type Family =
  | components["schemas"]["ModelFamilyListResponse"]
  | components["schemas"]["ModelFamilyResponse"];

/**
 * Providers the given family can actually run on, gated by the curated
 * `provider_types` list on the family. Returns [] when no family is selected.
 */
export function providersForFamily(
  providers: Provider[],
  family: Family | null | undefined,
): Provider[] {
  if (!family) return [];
  const allowed = new Set(family.provider_types);
  return providers.filter((p) => allowed.has(p.provider_type));
}
