declare module "*.yaml" {
  const data: Record<string, any>;
  export default data;
  export const messages: Array<{ role: "user" | "assistant"; content: string }>;
}

declare module "*.yml" {
  const data: Record<string, any>;
  export default data;
  export const messages: Array<{ role: "user" | "assistant"; content: string }>;
}
