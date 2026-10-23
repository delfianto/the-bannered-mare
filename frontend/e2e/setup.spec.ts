import { test, expect } from "./fixtures";

test("creates a provider and a compatible model route through connection dialogs", async ({
  page,
  api,
}) => {
  await page.goto("/connections?tab=providers");
  await page.getByRole("button", { name: "New Provider", exact: true }).click();
  let dialog = page.getByRole("dialog");
  await dialog.getByPlaceholder("Provider name").fill("Browser Provider");
  await dialog.locator('[aria-haspopup="listbox"]').getByRole("button").click();
  await page.getByRole("option", { name: "OpenAI", exact: true }).click();
  api.rejectNext("POST", "/api/providers");
  await dialog.getByRole("button", { name: "Create Provider", exact: true }).click();
  await expect(page.getByText("Failed to create provider", { exact: true })).toBeVisible();
  await expect(dialog.getByPlaceholder("Provider name")).toHaveValue("Browser Provider");
  await dialog.getByRole("button", { name: "Create Provider", exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await expect(page.getByRole("heading", { name: "Browser Provider", exact: true })).toBeVisible();
  const provider = api.db.providers.find((p) => p.name === "Browser Provider")!;
  await page.goto("/connections?tab=models");
  await page.getByRole("button", { name: "New Model", exact: true }).click();
  dialog = page.getByRole("dialog");
  await dialog.getByPlaceholder("Model display name").fill("Browser Model");
  await dialog.getByPlaceholder("e.g. openai/gpt-4o").fill("browser-model");
  await dialog.getByRole("button", { name: "Select a family", exact: true }).click();
  const family = api.db.families.find((f) => f.provider_types?.includes("openai"))!;
  await page.getByRole("option", { name: family.name, exact: true }).click();
  await dialog.getByRole("button", { name: "Select a provider", exact: true }).click();
  await page.getByRole("option", { name: "Browser Provider", exact: true }).click();
  await dialog.getByRole("button", { name: "Create Model", exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await expect(page.getByRole("cell", { name: "Browser Model", exact: true })).toBeVisible();
  expect(
    api.writes.find((r) => r.path === "/api/models" && r.method === "POST")?.body,
  ).toMatchObject({
    display_name: "Browser Model",
    model_family_id: family.id,
    routes: [{ provider_id: provider.id, model_identifier: "browser-model", enabled: true }],
  });
  await page.reload();
  await expect(page.getByRole("cell", { name: "Browser Model", exact: true })).toBeVisible();
});

test("first-run wizard creates a persona and ready profile, then starts a tale", async ({
  page,
  api,
}) => {
  api.db.profiles.splice(0);
  api.db.personas.splice(0);
  await page.goto("/setup");
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: /Create Manually/ }).click();
  await page.getByPlaceholder("Persona name (e.g. your name)").fill("Browser Adventurer");
  api.rejectNext("POST", "/api/personas/");
  await page.getByRole("button", { name: "Create", exact: true }).click();
  await expect(page.getByPlaceholder("Persona name (e.g. your name)")).toHaveValue(
    "Browser Adventurer",
  );
  await expect(page.getByText("Failed to create persona", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Create", exact: true }).click();
  await expect(page.getByPlaceholder("Persona name (e.g. your name)")).not.toBeVisible();
  await page.getByPlaceholder("e.g. Grimdark GM").fill("Browser Campaign");
  const model = api.db.models.find((m) => m.enabled && m.provider_enabled)!;
  await page.getByText("Model", { exact: true }).locator("..").getByRole("button").click();
  await page.getByRole("option", { name: model.display_name, exact: true }).click();
  await page.getByText("Persona", { exact: true }).locator("..").getByRole("button").click();
  await page.getByRole("option", { name: "Browser Adventurer", exact: true }).click();
  await page.getByRole("button", { name: "Create Profile", exact: true }).click();
  await expect(page.getByRole("heading", { name: "You're all set", exact: true })).toBeVisible();
  expect(
    api.writes.find((r) => r.path === "/api/profiles/" && r.method === "POST")?.body,
  ).toMatchObject({
    name: "Browser Campaign",
    is_default: true,
    model_id: model.id,
    persona_id: api.db.personas[0].id,
  });
  await page.getByRole("button", { name: "Done", exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.goto(`/characters/${api.db.characters[0].id}`);
  await page.getByRole("button", { name: "Start Tale", exact: true }).click();
  await expect(page).toHaveURL(/\/chats\/browser-/);
  await expect(page.getByText("Welcome, traveler.", { exact: true })).toBeVisible();
});
