/**
 * Normalize a Vue Router `route.params.*` value (typed `string | string[]`) to a
 * single string. The array form only occurs for repeatable params — none are
 * declared here — so this replaces the ad-hoc `route.params.x as string` casts.
 */
export function routeParam(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] : (value ?? "");
}
