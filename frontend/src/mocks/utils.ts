const NOW = new Date();

export function daysAgo(daysAgo: number, additionalMs: number = 0): string {
  return new Date(NOW.getTime() - daysAgo * 24 * 60 * 60 * 1000 + additionalMs).toISOString();
}

export function daysFromNow(daysFromNow: number, additionalMs: number = 0): string {
  return new Date(NOW.getTime() + daysFromNow * 24 * 60 * 60 * 1000 + additionalMs).toISOString();
}

export function hoursAgo(hoursAgo: number): string {
  return new Date(NOW.getTime() - hoursAgo * 60 * 60 * 1000).toISOString();
}

export function minutesAgo(minutesAgo: number): string {
  return new Date(NOW.getTime() - minutesAgo * 60 * 1000).toISOString();
}

export function secondsAgo(secondsAgo: number): string {
  return new Date(NOW.getTime() - secondsAgo * 1000).toISOString();
}

export function now(): string {
  return NOW.toISOString();
}

export function randomDateInRange(minDaysAgo: number, maxDaysAgo: number): string {
  const min = minDaysAgo * 24 * 60 * 60 * 1000;
  const max = maxDaysAgo * 24 * 60 * 60 * 1000;
  const randomOffset = Math.floor(Math.random() * (max - min + 1)) + min;
  return new Date(NOW.getTime() - randomOffset).toISOString();
}

export function datePair(
  createdDaysAgo: number,
  updatedDaysAgo: number = 0,
): {
  created_at: string;
  updated_at: string;
} {
  return {
    created_at: daysAgo(createdDaysAgo),
    updated_at: updatedDaysAgo === 0 ? now() : daysAgo(updatedDaysAgo),
  };
}

/**
 * Generate sequential message timestamps for a chat session
 * @param startDaysAgo - Days ago the chat started
 * @param messageCount - Number of messages
 * @param averageDelayMinutes - Average delay between messages (default: 5)
 */
export function chatMessageTimestamps(
  startDaysAgo: number,
  messageCount: number,
  averageDelayMinutes: number = 5,
): string[] {
  const startTime = NOW.getTime() - startDaysAgo * 24 * 60 * 60 * 1000;
  const timestamps: string[] = [];

  let currentTime = startTime;
  for (let i = 0; i < messageCount; i++) {
    timestamps.push(new Date(currentTime).toISOString());
    // Add random delay between 1 minute and 2x average delay
    const delay = (Math.random() * averageDelayMinutes * 2 + 1) * 60 * 1000;
    currentTime += delay;
  }

  return timestamps;
}

export function randomId(min: number = 1000, max: number = 9999): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

export function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

/**
 * Generate character ID in format: [random_number]-[url-friendly-char-name-slug]
 */
export function generateCharacterId(name: string): string {
  return `${randomId()}-${slugify(name)}`;
}

/**
 * Generate chat ID in format: [char_id]_[random_number]
 */
export function generateChatId(characterId: string): string {
  return `${characterId}_${randomId()}`;
}

/**
 * Generate message ID in format: [chat_id]_[sequence_number]
 */
export function generateMessageId(chatId: string, sequence: number): string {
  return `${chatId}_${sequence}`;
}

export const dateMock = {
  now,
  daysAgo,
  daysFromNow,
  hoursAgo,
  minutesAgo,
  secondsAgo,
  randomDateInRange,
  datePair,
  chatMessageTimestamps,
};

export const idMock = {
  randomId,
  slugify,
  generateCharacterId,
  generateChatId,
  generateMessageId,
};
