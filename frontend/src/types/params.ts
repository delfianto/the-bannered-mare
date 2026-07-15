/**
 * Provider parameter schema — the shape of a model family's `parameters` entries,
 * an opaque `dict[str, Any]` in the API contract. Recursive: a `list` param carries
 * an `item_schema`, an `object` param a `properties` map. Captures only the fields
 * the param UI reads (see ParamInput.vue's recursive renderer), so it stays an
 * intentional subset rather than an `any`.
 */
export interface ParamSchema {
  type?: string;
  default?: unknown;
  min_value?: number;
  max_value?: number;
  str_values?: string[];
  item_schema?: ParamSchema;
  properties?: Record<string, ParamSchema>;
}
