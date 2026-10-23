import { readFile } from "node:fs/promises";
import { test, expect } from "./fixtures";

// A valid 1x1 PNG exercises the browser's native file input and Blob URL preview.
const png = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=",
  "base64",
);
test("character upload, export, save and reload", async ({ page, api }) => {
  await page.goto("/characters/create");
  await page.getByPlaceholder("Isolde Fenwick").fill("Browser Archivist");
  await page
    .locator('input[type="file"][accept="image/*"]')
    .first()
    .setInputFiles({ name: "portrait.png", mimeType: "image/png", buffer: png });
  await expect(page.locator('img[src^="blob:"]:visible').first()).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export", exact: true }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("Browser Archivist.json");
  expect(JSON.parse(await readFile((await download.path())!, "utf8"))).toMatchObject({
    name: "Browser Archivist",
  });
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page).toHaveURL(/\/characters$/);
  await expect(page.getByRole("heading", { name: "Browser Archivist", exact: true })).toBeVisible();
  expect(
    api.writes.find((r) => r.method === "POST" && r.path === "/api/characters")?.body,
  ).toMatchObject({
    name: "Browser Archivist",
    avatar: { name: "portrait.png", type: "image/png" },
  });
  await page.reload();
  await expect(page.getByRole("heading", { name: "Browser Archivist", exact: true })).toBeVisible();
});
test("character edits survive a rejected save and can be retried", async ({ page, api }) => {
  const char = api.db.characters[0];
  await page.goto(`/characters/${char.id}/edit`);
  const name = page.getByPlaceholder("Isolde Fenwick");
  await expect(name).toHaveValue(char.name);
  await name.fill("Revised Archivist");
  api.rejectNext("PUT", `/api/characters/${char.id}`);
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByText("Save rejected by test server", { exact: true })).toBeVisible();
  await expect(name).toHaveValue("Revised Archivist");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page).toHaveURL(/\/characters$/);
  await expect(page.getByRole("heading", { name: "Revised Archivist", exact: true })).toBeVisible();
});
test("profile dialog traps focus, restores focus on Escape and preserves a rejected draft", async ({
  page,
  api,
}) => {
  await page.goto("/loadouts?tab=profiles");
  const launcher = page.getByRole("button", { name: "New Profile", exact: true });
  await launcher.click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  const close = dialog.getByRole("button", { name: "Close", exact: true });
  const cancel = dialog.getByRole("button", { name: "Cancel", exact: true });
  await expect(close).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(cancel).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(close).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(launcher).toBeFocused();
  await launcher.click();
  await dialog.locator('input[type="text"]').first().fill("Unsaved browser profile");
  api.rejectNext("POST", "/api/profiles/");
  await dialog.getByRole("button", { name: "Create Profile", exact: true }).click();
  await expect(page.getByText("Could not create profile", { exact: true })).toBeVisible();
  await expect(dialog.locator('input[type="text"]').first()).toHaveValue("Unsaved browser profile");
  await dialog.getByRole("button", { name: "Create Profile", exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Unsaved browser profile", exact: true }),
  ).toBeVisible();
});
test("starts a tale with a chosen profile and receives an SSE reply", async ({ page, api }) => {
  await page.goto(`/characters/${api.db.characters[0].id}`);
  await page.getByRole("button", { name: "Start Tale", exact: true }).click();
  const picker = page.getByRole("dialog", { name: "Choose a Profile" });
  await picker.getByRole("radio", { name: api.db.profiles[1].name, exact: true }).check();
  await picker.getByRole("button", { name: "Start tale", exact: true }).click();
  await expect(page).toHaveURL(/\/chats\/browser-/);
  await expect(page.getByText("Welcome, traveler.", { exact: true })).toBeVisible();
  expect(api.writes.find((r) => r.path === "/api/chats")?.body).toMatchObject({
    character_id: api.db.characters[0].id,
    profile_id: api.db.profiles[1].id,
  });
  await page.getByPlaceholder("Continue the tale…").fill("Open the archive");
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  await expect(
    page.getByText("The archive opens. Your journey begins.", { exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByText("The archive opens. Your journey begins.", { exact: true }),
  ).toBeVisible();
});
test("chat failures offer retry without losing the user turn", async ({ page, api }) => {
  const chat = api.db.chats[0];
  await page.goto(`/chats/${chat.id}`);
  await expect(page.getByText("Welcome, traveler.", { exact: true })).toBeVisible();
  api.failGeneration = true;
  await page.getByPlaceholder("Continue the tale…").fill("Please continue");
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  await expect(page.getByText("Provider unavailable", { exact: true })).toBeVisible();
  await expect(page.getByText("Please continue", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Regenerate", exact: true })
    .filter({ hasText: "Regenerate" })
    .click();
  await expect(
    page.getByText("The archive opens. Your journey begins.", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Please continue", { exact: true })).toBeVisible();
});
test("keyboard selection in a teleported menu persists reading preferences", async ({ page }) => {
  await page.goto("/settings");
  const menus = page.locator('[aria-haspopup="listbox"]');
  await menus.nth(1).getByRole("button").click();
  const listbox = page.getByRole("listbox");
  await expect(listbox).toBeVisible();
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Enter");
  await expect(listbox).not.toBeVisible();
  const slider = page.getByRole("slider", { name: "Text Size", exact: true });
  await slider.focus();
  await page.keyboard.press("Home");
  await page.keyboard.press("ArrowRight");
  await expect(slider).toHaveValue("15");
  await expect.poll(() => page.evaluate(() => localStorage.getItem("font-size"))).toBe("15");
  await page.reload();
  await expect(slider).toHaveValue("15");
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    .toBe(true);
});
test("switches conversations without carrying messages into another tale", async ({
  page,
  api,
}, testInfo) => {
  const [first, second] = api.db.chats;
  await page.goto(`/chats/${first.id}`);
  await page.getByPlaceholder("Continue the tale…").fill("A message for the first tale");
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  await expect(
    page.getByText("The archive opens. Your journey begins.", { exact: true }),
  ).toBeVisible();
  if (testInfo.project.name === "mobile-chromium") {
    await page.getByRole("button", { name: "Active Tales", exact: true }).click();
    await page
      .getByRole("option", { name: `${second.character.name} — ${second.title}`, exact: true })
      .click();
  } else await page.getByRole("button").filter({ hasText: second.title! }).click();
  await expect(page).toHaveURL(new RegExp(`/chats/${second.id}$`));
  await expect(page.getByText("Welcome, traveler.", { exact: true })).toBeVisible();
  await expect(page.getByText("A message for the first tale", { exact: true })).not.toBeVisible();
  await expect(
    page.getByText("The archive opens. Your journey begins.", { exact: true }),
  ).not.toBeVisible();
});

test("recovers a stale chat link by selecting an existing conversation", async ({ page, api }) => {
  await page.goto("/chats/missing-session");
  await page.getByRole("button").filter({ hasText: api.db.chats[1].title! }).click();
  await expect(page).toHaveURL(new RegExp(`/chats/${api.db.chats[1].id}$`));
  await expect(page.getByPlaceholder("Continue the tale…")).toBeVisible();
  await expect(page.getByText("Welcome, traveler.", { exact: true })).toBeVisible();
});
