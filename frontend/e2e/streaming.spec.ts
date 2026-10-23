import { test, expect } from "./fixtures";

const composer = "Continue the tale…";
async function send(page: import("@playwright/test").Page, text = "Continue our journey") {
  await page.getByPlaceholder(composer).fill(text);
  await page.getByRole("button", { name: "Send message", exact: true }).click();
}

test("renders successive network chunks before the stream finishes", async ({ page, api }) => {
  const stream = api.holdNextStream();
  await page.goto(`/chats/${api.db.chats[0].id}`);
  await send(page);
  await stream.connected;
  stream.send({ type: "start", message_id: "streamed-reply" });
  stream.send({ type: "text", content: "The door opens." });
  await expect(page.getByText("The door opens.", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Stop generation", exact: true })).toBeVisible();
  await expect(page.getByPlaceholder(composer)).toBeDisabled();
  stream.send({ type: "text", content: " A dragon waits." });
  await expect(page.getByText("The door opens. A dragon waits.", { exact: true })).toBeVisible();
  stream.finish();
  await expect(page.getByPlaceholder(composer)).toBeEnabled();
  await expect(
    page.getByRole("button", { name: "Stop generation", exact: true }),
  ).not.toBeVisible();
});

test("Stop cancels the live socket and keeps already-rendered text", async ({ page, api }) => {
  const stream = api.holdNextStream();
  await page.goto(`/chats/${api.db.chats[0].id}`);
  await send(page);
  await stream.connected;
  stream.send({ type: "text", content: "A half-told tale." });
  await expect(page.getByText("A half-told tale.", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Stop generation", exact: true }).click();
  await stream.closed;
  await expect(page.getByPlaceholder(composer)).toBeEnabled();
  await expect(page.getByText("A half-told tale.", { exact: true })).toBeVisible();
  await send(page, "A fresh request");
  await expect(
    page.getByText("The archive opens. Your journey begins.", { exact: true }),
  ).toBeVisible();
});

test("Stop before the first token leaves no blank assistant reply", async ({ page, api }) => {
  const stream = api.holdNextStream();
  await page.goto(`/chats/${api.db.chats[0].id}`);
  await send(page);
  await stream.connected;
  await page.getByRole("button", { name: "Stop generation", exact: true }).click();
  await stream.closed;
  await expect(page.getByPlaceholder(composer)).toBeEnabled();
  await expect(page.getByText("Continue our journey", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Regenerate", exact: true })).toHaveCount(1);
});

test("switching sessions cancels generation and isolates the new conversation", async ({
  page,
  api,
}, testInfo) => {
  const [first, second] = api.db.chats;
  const stream = api.holdNextStream();
  await page.goto(`/chats/${first.id}`);
  await send(page);
  await stream.connected;
  stream.send({ type: "text", content: "Only the first tale sees this." });
  await expect(page.getByText("Only the first tale sees this.", { exact: true })).toBeVisible();
  if (testInfo.project.name === "mobile-chromium") {
    await page.getByRole("button", { name: "Active Tales", exact: true }).click();
    await page
      .getByRole("option", { name: `${second.character.name} — ${second.title}`, exact: true })
      .click();
  } else await page.getByRole("button").filter({ hasText: second.title! }).click();
  await stream.closed;
  await expect(page).toHaveURL(new RegExp(`/chats/${second.id}$`));
  await expect(page.getByText("Welcome, traveler.", { exact: true })).toBeVisible();
  await expect(page.getByText("Only the first tale sees this.", { exact: true })).not.toBeVisible();
  await expect(page.getByPlaceholder(composer)).toBeEnabled();
});

test("a dropped connection preserves partial text and releases the composer", async ({
  page,
  api,
}) => {
  const stream = api.holdNextStream();
  await page.goto(`/chats/${api.db.chats[0].id}`);
  await send(page);
  await stream.connected;
  stream.send({ type: "text", content: "The interrupted reply." });
  await expect(page.getByText("The interrupted reply.", { exact: true })).toBeVisible();
  stream.disconnect();
  await stream.closed;
  await expect(page.getByPlaceholder(composer)).toBeEnabled();
  await expect(page.getByText("The interrupted reply.", { exact: true })).toBeVisible();
  await send(page, "Recover after disconnect");
  await expect(
    page.getByText("The archive opens. Your journey begins.", { exact: true }),
  ).toBeVisible();
});

test("a streamed provider error offers retry and removes the empty placeholder", async ({
  page,
  api,
}) => {
  const stream = api.holdNextStream();
  await page.goto(`/chats/${api.db.chats[0].id}`);
  await send(page);
  await stream.connected;
  stream.send({ type: "error", message: "Provider refused the scene" });
  stream.finish();
  await expect(page.getByText("Provider refused the scene", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Regenerate", exact: true })
    .filter({ hasText: "Regenerate" })
    .click();
  await expect(
    page.getByText("The archive opens. Your journey begins.", { exact: true }),
  ).toBeVisible();
});

test("stopping a regeneration restores the previous completed reply", async ({ page, api }) => {
  await page.goto(`/chats/${api.db.chats[0].id}`);
  await send(page);
  await expect(
    page.getByText("The archive opens. Your journey begins.", { exact: true }),
  ).toBeVisible();
  const stream = api.holdNextStream();
  await page.getByRole("button", { name: "Regenerate", exact: true }).last().click();
  await stream.connected;
  await page.getByRole("button", { name: "Stop generation", exact: true }).click();
  await stream.closed;
  await expect(page.getByPlaceholder(composer)).toBeEnabled();
  await expect(
    page.getByText("The archive opens. Your journey begins.", { exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Regenerate", exact: true })).toHaveCount(2);
});

test("assembles an SSE frame split across HTTP writes including split UTF-8", async ({
  page,
  api,
}) => {
  const stream = api.holdNextStream();
  await page.goto(`/chats/${api.db.chats[0].id}`);
  await send(page);
  await stream.connected;
  const frame = Buffer.from('data: {"type":"text","content":"A dragon 🐉 wakes."}\n\n');
  const split = frame.indexOf(Buffer.from("🐉")) + 2;
  stream.write(frame.subarray(0, split));
  stream.write(frame.subarray(split, frame.length - 1));
  // The final separator completes the SSE frame.
  stream.write("\n");
  await expect(page.getByText("A dragon 🐉 wakes.", { exact: true })).toBeVisible();
  stream.finish();
  await expect(page.getByPlaceholder(composer)).toBeEnabled();
});
