# SillyTavern v1.17.0 — Chat System Analysis

> Analysis based on reading the SillyTavern source code at commit `1695f8e`.
> All file paths are relative to the SillyTavern repository root.


## 1. Chat Storage Format

SillyTavern stores all chat data as **JSONL files** (one JSON object per line). Each `.jsonl` file represents a single conversation.

### 1.1 File Layout

```
data/default-user/
  chats/
    <character_avatar_name>/     # One directory per character (avatar filename minus .png)
      <chat_name>.jsonl          # Individual chat files
  group chats/
    <chat_id>.jsonl              # Group chat files (flat directory, no nesting)
  groups/
    <group_id>.json              # Group metadata (NOT JSONL -- plain JSON)
  backups/
    chat_<name>_<timestamp>.jsonl  # Automatic backups
  user/files/                    # File attachments uploaded from chat
```

Directory template is defined in `src/constants.js` (line 16):

```js
// src/constants.js:16-48
export const USER_DIRECTORY_TEMPLATE = Object.freeze({
    chats: 'chats',
    groupChats: 'group chats',
    groups: 'groups',
    backups: 'backups',
    files: 'user/files',
    // ... other directories
});
```

### 1.2 JSONL Structure

Every chat file follows this structure:

- **Line 0 (Header):** A metadata-only object with no message content.
- **Lines 1..N (Messages):** One message object per line.

The header is defined by the `ChatHeader` interface (`public/global.d.ts:50-56`):

```ts
interface ChatHeader {
    chat_metadata: ChatMetadata;
    /** @deprecated For backward compatibility ONLY */
    user_name: 'unused';
    /** @deprecated For backward compatibility ONLY */
    character_name: 'unused';
}

interface ChatMetadata {
    tainted?: boolean;      // Set to true once user edits any message
    integrity?: string;     // UUID for integrity checking on save
    scenario?: string;      // Scenario override
    persona?: string;       // Locked persona avatar ID
    main_chat?: string;     // Parent chat name (for bookmarks/branches)
    [key: string]: any;     // Extensible
}
```

The `user_name` and `character_name` fields are historical artifacts -- they are always set to the string `'unused'` in current code (`public/script.js:7329-7333`).

### 1.3 Serialization and Deserialization

**Saving** (`src/endpoints/chats.js:457-468`):

```js
// src/endpoints/chats.js:458
const jsonlData = chatData?.map(m => JSON.stringify(m)).join('\n');
```

The client sends the full chat array (header + messages) via `POST /api/chats/save`. The server joins them with `\n` and writes atomically using `write-file-atomic`.

**Loading** (`src/endpoints/chats.js:502-515`):

```js
// src/endpoints/chats.js:506-510
const chatJSON = tryReadFileSync(chatFilePath) ?? '';
if (chatJSON.length > 0) {
    const lines = chatJSON.split('\n');
    chatData = lines.map(line => tryParse(line)).filter(x => x);
}
```

The server reads the entire file, splits on newlines, parses each line as JSON, and returns the array. The client strips the header element before populating the in-memory `chat` array.


## 2. Chat CRUD Operations

### 2.1 API Endpoints

All endpoints are defined in `src/endpoints/chats.js`:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/chats/save` | Save an individual character chat |
| POST | `/api/chats/get` | Load an individual character chat |
| POST | `/api/chats/delete` | Delete an individual character chat |
| POST | `/api/chats/rename` | Rename a chat file |
| POST | `/api/chats/export` | Export chat (JSONL or plaintext) |
| POST | `/api/chats/import` | Import chat from various formats |
| POST | `/api/chats/search` | Full-text search across chat files |
| POST | `/api/chats/group/get` | Load a group chat |
| POST | `/api/chats/group/save` | Save a group chat |
| POST | `/api/chats/group/delete` | Delete a group chat |
| POST | `/api/chats/group/import` | Import a group chat |
| POST | `/api/chats/group/info` | Get info about a group chat |

### 2.2 Chat Creation

Chats are created implicitly. When a character is opened and no chat file exists, the client creates a new in-memory array. The first save writes the JSONL file to disk. The chat file name is typically a humanized datetime string (e.g., `2024-4-15@10h30m22s`).

For character chats (`public/script.js:7296-7348`):

```js
const chatHeader = {
    chat_metadata: metadata,
    user_name: 'unused',
    character_name: 'unused',
};
// POST body: { ch_name, file_name, chat: [chatHeader, ...trimmedChat], avatar_url }
```

For group chats (`public/scripts/group-chats.js:623-675`):

```js
// POST body: { id: chatId, chat: [chatHeader, ...chat] }
```

### 2.3 Chat Loading

When a character chat is loaded, the client calls `POST /api/chats/get` with `avatar_url` and `file_name`. The server reads the JSONL file and returns the parsed array. The client then:

1. Strips the header (element at index 0).
2. Extracts `chat_metadata` from the header.
3. Populates the global `chat` array with the remaining messages.
4. Renders the messages in the DOM.

### 2.4 Chat Deletion

`POST /api/chats/delete` deletes the `.jsonl` file from disk. Group deletion (`POST /api/groups/delete` in `src/endpoints/groups.js:203-234`) also cascades to delete all associated group chat JSONL files.

### 2.5 Saving with Integrity Checks

The save path includes an integrity mechanism (`src/endpoints/chats.js:316-335`, `457-468`):

1. On first load, a UUID `integrity` slug is stored in `chat_metadata`.
2. On save, if `checkIntegrity` is enabled (default: `true`), the server reads the first line of the existing file and compares the `integrity` slug.
3. If mismatched, the save is rejected with a `400` status and `error: 'integrity'`.
4. The client then prompts the user to type `OVERWRITE` to force-save, or the page reloads.

This prevents data loss from concurrent edits across browser tabs.


## 3. Message Data Model

The complete `ChatMessage` interface is defined in `public/global.d.ts:66-81`:

```ts
interface ChatMessage {
    name?: string;              // Speaker name (character name or user name)
    mes?: string;               // Message text content (markdown)
    title?: string;             // Tooltip title
    gen_started?: MessageTimestamp;   // When generation began
    gen_finished?: MessageTimestamp;  // When generation completed
    send_date?: MessageTimestamp;     // Display timestamp
    is_user?: boolean;          // true for user messages
    is_system?: boolean;        // true for system/hidden messages
    force_avatar?: string;      // Override avatar URL (used in group chats)
    original_avatar?: string;   // Character's avatar filename (group chats)
    swipes?: string[];          // Array of alternative message texts
    swipe_info?: SwipeInfo[];   // Metadata for each swipe
    swipe_id?: number;          // Currently selected swipe index
    extra?: ChatMessageExtra;   // Extensible metadata bag
}
```

### 3.1 The `extra` Object

The `extra` field is a catch-all for metadata. Its base shape (`public/global.d.ts:90-128`):

```ts
interface BaseMessageExtra {
    api?: string;               // API provider used (e.g., 'openai', 'anthropic')
    model?: string;             // Model name/ID used for generation
    type?: string;              // Message subtype ('narrator', etc.)
    gen_id?: number;            // Generation batch ID (group chats)
    bias?: string;              // Logit bias string
    memory?: string;            // Injected memory/context
    display_text?: string;      // Alternate display text
    token_count?: number;       // Token count of the message
    swipeable?: boolean;        // false to disable swiping
    overswipe_behavior?: string; // Override overswipe behavior
    files?: FileAttachment[];   // Document attachments
    media?: MediaAttachment[];  // Image/video/audio attachments
    inline_image?: boolean;     // Whether media is displayed inline
    media_index?: number;       // Currently displayed media index
    bookmark_link?: string;     // Link to a checkpoint chat
    branches?: string[];        // Links to branch chats
    // Reasoning fields (for models like o1, Claude with extended thinking):
    reasoning?: string;
    reasoning_duration?: number;
    reasoning_signature?: string;
    // Tool calling:
    tool_invocations?: ToolInvocation[];
}
```

### 3.2 Timestamps

The `MessageTimestamp` type can be a string, number, or Date. In practice, `send_date` is stored as an ISO 8601 string or a formatted datetime string from `getMessageTimeStamp()`.


## 4. Message Swipes (Alternatives)

The swipe system allows storing multiple alternative responses for a single message position. This is one of SillyTavern's most distinctive features.

### 4.1 Data Structure

Each message can have:
- `swipes: string[]` -- Array of alternative message texts.
- `swipe_info: SwipeInfo[]` -- Parallel array of metadata for each swipe.
- `swipe_id: number` -- Index of the currently active swipe.

```ts
// public/global.d.ts:83-88
interface SwipeInfo {
    send_date?: MessageTimestamp;
    gen_started?: MessageTimestamp;
    gen_finished?: MessageTimestamp;
    extra?: ChatMessageExtra;  // Each swipe has its own extra metadata
}
```

### 4.2 Swipe Initialization

When a message first receives a swipe, the swipe arrays are lazily created (`public/script.js:10233-10243`):

```js
if (chat[mesId].swipe_id === undefined) {
    chat[mesId].swipe_id = 0;
    chat[mesId].swipes = [];
    chat[mesId].swipe_info = [];
    chat[mesId].swipes[0] = chat[mesId].mes;  // Current text becomes swipe 0
    chat[mesId].swipe_info[0] = {
        'send_date': chat[mesId].send_date,
        'gen_started': chat[mesId].gen_started,
        'gen_finished': chat[mesId].gen_finished,
        'extra': structuredClone(chat[mesId].extra),
    };
}
```

The `ensureSwipes()` function (`public/script.js:6738-6780`) provides a centralized way to guarantee swipe structure exists on a message.

### 4.3 Swipe Navigation

The main `swipe()` function (`public/script.js:9845`) handles both directions:

**Left swipe** (previous alternative):
1. Decrement `swipe_id`.
2. If `< 0`, wrap to the last swipe (loop behavior).
3. Call `syncSwipeToMes()` to copy swipe data into the main message fields.
4. Re-render the message.

**Right swipe** (next alternative / regenerate):
1. Increment `swipe_id`.
2. If within bounds, display the existing swipe.
3. If past the end (overswipe), behavior depends on `getOverswipeBehavior()`:
   - `REGENERATE` (default for AI messages): Clear the message and trigger a new generation.
   - `LOOP`: Wrap back to swipe 0.
   - `PRISTINE_GREETING`: Loop on pristine first messages.
   - `NONE`: Block the swipe.
   - `EDIT_GENERATE`: Allow editing before generating.

Overswipe behavior is determined per-message (`public/script.js:9114-9131`):

```js
export function getOverswipeBehavior(messageId, message) {
    if (typeof message?.extra?.overswipe_behavior == 'string') return message.extra.overswipe_behavior;
    else if (message?.extra?.swipeable === false) return OVERSWIPE_BEHAVIOR.NONE;
    else if (message?.extra?.isSmallSys) return OVERSWIPE_BEHAVIOR.NONE;
    else if (isGreeting && isPristine) return OVERSWIPE_BEHAVIOR.PRISTINE_GREETING;
    else if (!message?.is_user && !message?.is_system) return OVERSWIPE_BEHAVIOR.REGENERATE;
    else { return OVERSWIPE_BEHAVIOR.LOOP; }
}
```

### 4.4 Synchronization Functions

Two critical sync functions keep the swipe array and top-level message fields in sync:

**`syncMesToSwipe()`** (`public/script.js:6797-6842`): Copies the message's current `mes`, `send_date`, `gen_started`, `gen_finished`, and `extra` into the swipe array at the current `swipe_id`. Called before navigating away from the current swipe.

**`syncSwipeToMes()`** (`public/script.js:6855-6916`): Copies data from `swipes[swipe_id]` and `swipe_info[swipe_id]` back onto the top-level message fields. Called when navigating to a different swipe.

### 4.5 Swipe Sources

Swipes can be triggered from multiple sources (`public/scripts/constants.js:173-180`):

```js
export const SWIPE_SOURCE = {
    DELETE: 'delete',          // Deleting a swipe
    KEYBOARD: 'keyboard',     // Arrow key navigation
    BACK: 'back',             // Reverting a swipe
    AUTO_SWIPE: 'auto_swipe', // Automatic swipe (e.g., filter rules)
    SLASH_COMMAND: 'slash_command',
    SWIPE_PICKER: 'swipe_picker',
};
```


## 5. Message Editing

### 5.1 Edit Flow

Message editing is handled client-side in `public/script.js`.

1. **Enter edit mode** (`messageEdit()`, line 8131): Replaces the rendered message HTML with a `<textarea>` populated with the raw `mes` text.

2. **Auto-save on keystroke** (`messageEditAuto()`, line 8109): Called on input events, updates the in-memory `chat[mesId].mes` immediately and triggers a debounced save.

3. **Save edit** (`messageEditDone()`, line 8288): Finalizes the edit, re-renders the message, and saves the chat.

4. **Cancel edit** (`messageEditCancel()`, line 8196): Discards changes by restoring the original `mes` text.

### 5.2 The `updateMessage()` Function

At the core of editing is `updateMessage()` (`public/script.js:8031-8084`):

```js
function updateMessage(div) {
    // Extract text from textarea
    let text = mesBlock.find('.edit_textarea').val();
    const mes = chat[mesElement.attr('mesid')];

    // Apply regex transformations
    text = getRegexedString(text, regexPlacement, { characterOverride, isEdit: true });

    // Trim and substitute macros
    text = substituteParams(text);
    mes.mes = text;

    // If this message has swipes, update the current swipe too
    if (mes.swipe_id !== undefined) {
        ensureSwipes(mes);
        mes.swipes[mes.swipe_id] = text;
    }

    chat_metadata.tainted = true;  // Mark the chat as edited
    return { mesBlock, text, mes, bias };
}
```

Key behavior: editing a message updates both `mes.mes` and `mes.swipes[mes.swipe_id]`, keeping them in sync. The `chat_metadata.tainted` flag is set on any edit, which affects overswipe behavior on greetings.

### 5.3 Message Reordering

Messages can be moved up/down with `messageEditMove()` (`public/script.js:8244-8286`):

```js
async function messageEditMove(sourceId, targetId) {
    // Swap DOM elements
    sourceMessageDiv.insertAfter(targetMessageDiv);  // or insertBefore
    // Swap chat array entries
    [chat[sourceId], chat[targetId]] = [chat[targetId], chat[sourceId]];
    await saveChatConditional();
}
```

### 5.4 Message Deletion

The `deleteMessage()` function (`public/script.js:1616`) supports two modes:

1. **Delete entire message**: Removes the message from the `chat` array and DOM.
2. **Delete single swipe**: If the message has multiple swipes and the user is on the last message, the user can choose to delete only the current swipe rather than the whole message.


## 6. Regeneration

### 6.1 Individual Chat Regeneration

Regeneration in a solo chat works through the swipe mechanism. When the user clicks "regenerate" (or right-swipes past the last swipe on an AI message), the overswipe behavior `REGENERATE` triggers:

```js
// public/script.js:10301-10308
} else if (overswipe == OVERSWIPE_BEHAVIOR.REGENERATE) {
    clearMessageData(chat[mesId]);
    let run_generate = true;
    await animateSwipe(run_generate);  // Shows "..." and triggers Generate('swipe')
}
```

Inside `animateSwipe()` (`public/script.js:10162`), when `run_generate` is true:
1. The message text is replaced with "..." in the DOM.
2. `Generate('swipe')` is called, which sends the context to the LLM API.
3. The response is saved via `saveReply({ type: 'swipe', ... })`.

The `saveReply()` function (`public/script.js:6543`) handles the swipe type by updating `lastMessage.swipes[swipe_id]` with the new text and metadata.

### 6.2 Group Chat Regeneration

Group regeneration (`public/scripts/group-chats.js:167-188`) works differently -- it deletes all messages from the last AI "batch" (identified by `gen_id`), then re-runs `generateGroupWrapper()`:

```js
async function regenerateGroup() {
    let generationId = getLastMessageGenerationId();
    while (chat.length > 0) {
        const lastMes = chat[chat.length - 1];
        const this_generationId = lastMes.extra?.gen_id;
        if ((generationId && this_generationId) && generationId !== this_generationId) break;
        else if (lastMes.is_user || lastMes.is_system) break;
        await deleteLastMessage();
    }
    return generateGroupWrapper(false, 'normal', { signal });
}
```

The `gen_id` is a `Date.now()` timestamp assigned at the start of each group generation batch, so all messages from the same turn share the same ID.


## 7. Chat Branching and Bookmarks

The branching system is implemented in `public/scripts/bookmarks.js`. It provides two related features: **Checkpoints** (bookmarks) and **Branches**.

### 7.1 Checkpoints (Bookmarks)

A checkpoint saves the chat state up to a specific message and creates a new chat file that can be navigated to later.

**Creation** (`createNewBookmark()`, line 253):

1. The user selects a message.
2. A new chat name is generated (e.g., `<base_chat> - Checkpoint #3`).
3. The chat is sliced from message 0 to the selected message (inclusive).
4. A new metadata object is created with `main_chat` pointing to the current chat name.
5. The sliced chat is saved as a new JSONL file.
6. The original message gets `extra.bookmark_link = name` added to it.

```js
// public/scripts/bookmarks.js:281-291
const mainChat = characters[this_chid].chat;
const newMetadata = { main_chat: mainChat };
await saveChat({ chatName: name, withMetadata: newMetadata, mesId });
lastMes.extra.bookmark_link = name;
```

**Navigation**: Clicking the bookmark flag icon on a message opens the linked checkpoint chat. The "Back to Main" button reads `chat_metadata.main_chat` to return to the parent chat.

### 7.2 Branches

Branches are similar to checkpoints but automatically navigate to the new chat after creation and use a different naming convention (`<base_chat> - Branch #N`).

**Creation** (`createBranch()`, line 186):

```js
// public/scripts/bookmarks.js:186-243
export async function createBranch(mesId, { swipeId = null } = {}) {
    const branchChatSnapshot = getBranchChatSnapshot(mesId, { swipeId: selectedSwipeId });
    // Save the branch chat
    await saveChat({ chatName: name, withMetadata: newMetadata, mesId, chatData: branchChatSnapshot });
    // Record the branch on the source message
    lastMes.extra.branches.push(name);
    return name;
}
```

Branches support an optional `swipeId` parameter, allowing the user to branch from a specific swipe alternative rather than the currently displayed one. The `getBranchChatSnapshot()` function (line 171) uses `syncSwipeToMes()` to prepare the target swipe before cloning the chat.

### 7.3 Storage

Branches and checkpoints are stored as independent JSONL files in the same directory as the parent chat. Their relationship is tracked through:

- `chat_metadata.main_chat`: Points from child back to parent.
- `message.extra.bookmark_link`: Points from a message to its checkpoint.
- `message.extra.branches`: Array of branch chat names originating from that message.

### 7.4 Solo-to-Group Conversion

The bookmark system also includes `convertSoloToGroupChat()` (`public/scripts/bookmarks.js:328-441`), which converts a solo character chat into a group chat by:

1. Creating a new group with the character as the sole member.
2. Cloning all chat messages, adding `force_avatar`, `original_avatar`, and `extra.gen_id` fields.
3. Saving as a group chat JSONL file.


## 8. Group Chats

Group chats allow multiple AI characters to participate in a conversation. The system is implemented across `src/endpoints/groups.js` (server) and `public/scripts/group-chats.js` (client).

### 8.1 Group Data Model

Groups are stored as JSON files (NOT JSONL) in `groups/`. The schema (`public/global.d.ts:26-43`):

```ts
interface Group {
    id: string;                      // Unique ID (Date.now() at creation)
    name: string;                    // Display name
    members: string[];               // Character avatar filenames
    disabled_members: string[];      // Muted members
    chat_id: string;                 // Current active chat ID
    chats: string[];                 // All chat IDs (references to JSONL files)
    generation_mode?: number;        // SWAP=0, APPEND=1, APPEND_DISABLED=2
    generation_mode_join_prefix?: string;
    generation_mode_join_suffix?: string;
    activation_strategy?: number;    // NATURAL=0, LIST=1, MANUAL=2, POOLED=3
    auto_mode_delay?: number;        // Seconds between auto-mode generations
    allow_self_responses?: boolean;  // Allow same character to respond twice in a row
    avatar_url?: string;
    fav?: boolean;
}
```

### 8.2 Turn Activation Strategies

Four strategies determine which group members respond to a message. Defined in `public/scripts/group-chats.js:122-127`:

```js
export const group_activation_strategy = {
    NATURAL: 0,
    LIST: 1,
    MANUAL: 2,
    POOLED: 3,
};
```

**NATURAL** (`activateNaturalOrder()`, line 1242):
- Scans the input text for character name mentions; mentioned characters are activated.
- Remaining characters roll against their `talkativeness` value (0-1 probability).
- If nobody activates, a random character from the pool is selected.
- The last speaker is "banned" from speaking again (unless `allow_self_responses` is enabled).

```js
// public/scripts/group-chats.js:1282-1285
const rollValue = Math.random();
const talkativeness = isNaN(character.talkativeness)
    ? talkativeness_default : Number(character.talkativeness);
if (talkativeness >= rollValue) { activatedMembers.push(member); }
```

**LIST** (`activateListOrder()`, line 1180):
- All enabled members respond, in their list order.
- Each member generates one message sequentially.

**MANUAL** (line 1029):
- No automatic activation on user input.
- Characters only respond when explicitly triggered (e.g., clicking on them).
- If triggered without user input, a random single member is selected.

**POOLED** (`activatePooledOrder()`, line 1197):
- Selects one member who has NOT spoken since the last user message.
- If all have spoken, picks a random member (excluding the last speaker).

### 8.3 Generation Modes

Three modes control how character cards are assembled for prompts (`public/scripts/group-chats.js:129-133`):

```js
export const group_generation_mode = {
    SWAP: 0,           // Only the current speaker's card is used
    APPEND: 1,         // All members' cards are combined into the prompt
    APPEND_DISABLED: 2 // Like APPEND but includes disabled members too
};
```

For `APPEND` and `APPEND_DISABLED`, `getGroupCharacterCards()` (line 477) combines descriptions, personalities, scenarios, and example messages from all group members using configurable join prefix/suffix strings.

### 8.4 Group Chat Messages

Group chat messages are structurally identical to solo chat messages but include additional fields:

```js
// public/scripts/bookmarks.js:415-419 (during solo-to-group conversion)
message.force_avatar = getThumbnailUrl('avatar', character.avatar);
message.original_avatar = character.avatar;
message.extra.gen_id = genIdFirst + index;
```

- `force_avatar`: URL of the character's avatar thumbnail, used for display.
- `original_avatar`: Character's avatar filename, used for identity resolution.
- `extra.gen_id`: Shared generation batch ID for all messages in the same turn.

### 8.5 Group Generation Flow

The `generateGroupWrapper()` function (`public/scripts/group-chats.js:945-1092`) orchestrates group generation:

1. Determine the activation strategy and select members.
2. Set `group_generation_id = Date.now()` (shared for the entire batch).
3. For each activated member:
   a. Set the active character.
   b. Call `Generate('normal')` (or 'swipe', 'continue', etc.).
   c. If auto-continue is needed, loop `Generate('continue')`.
4. After all members have generated, clean up state.

For swipes and continues, the system uses `activateSwipe()` (line 1130), which finds the character who sent the last non-user message by checking `original_avatar`.


## 9. Chat Import/Export

### 9.1 Import Formats

SillyTavern supports importing from six formats, all handled in `src/endpoints/chats.js`:

| Format | Detection | Function | Lines |
|--------|-----------|----------|-------|
| **Oobabooga** | `jsonData.data_visible` is an array | `importOobaChat()` | 110-142 |
| **Agnai** | `jsonData.messages` is an array | `importAgnaiChat()` | 151-171 |
| **CAI Tools** | `jsonData.histories` exists | `importCAIChat()` | 180-206 |
| **Kobold Lite** | `jsonData.savedsettings` exists | `importKoboldLiteChat()` | 215-248 |
| **RisuAI** | `jsonData.type === 'risuChat'` | `importRisuChat()` | 288-308 |
| **JSONL (native/Chub)** | File extension `.jsonl` | `flattenChubChat()` | 250-279 |

All import functions normalize messages to the standard format:

```js
{
    name: characterName,
    is_user: false,
    send_date: new Date().toISOString(),
    mes: messageText,
    extra: {},
}
```

The import endpoint (`POST /api/chats/import`, line 696) auto-detects the format based on JSON structure or file extension.

### 9.2 Export Formats

Export (`POST /api/chats/export`, line 604) supports two modes:

- **JSONL**: Raw file download (the native format).
- **Plaintext**: Formatted as `Name: Message\n\n` pairs, with system messages filtered out and `extra.display_text` used when available.


## 10. Chat Backup System

### 10.1 Automatic Backups

The backup system is configured via `config.yaml` and implemented in `src/endpoints/chats.js:26-78`:

```js
// src/endpoints/chats.js:26-29
const isBackupEnabled = !!getConfigValue('backups.chat.enabled', true, 'boolean');
const maxTotalChatBackups = Number(getConfigValue('backups.chat.maxTotalBackups', -1, 'number'));
const throttleInterval = Number(getConfigValue('backups.chat.throttleInterval', 10_000, 'number'));
const checkIntegrity = !!getConfigValue('backups.chat.checkIntegrity', true, 'boolean');
```

Backups are created via a **throttled function** (lodash `_.throttle`) with a default 10-second interval. Each user gets their own throttled backup function (`getBackupFunction()`, line 73). The throttle uses `leading: true, trailing: true` to ensure both immediate and delayed saves are captured.

Backup files are named: `chat_<sanitized_name>_<timestamp>.jsonl`

Old backups are cleaned up per-chat (using `removeOldBackups` with the chat-specific prefix) and globally (using `maxTotalChatBackups` across all chat_ prefixed files).

On process exit, all pending throttled backups are flushed (`src/endpoints/chats.js:97-100`):

```js
process.on('exit', () => {
    for (const func of backupFunctions.values()) {
        func.flush();
    }
});
```

### 10.2 Backup Browser

The client-side `BackupsBrowser` class (`public/scripts/chat-backups.js`) provides a UI for:

- **Viewing** backups: Parses the JSONL and displays messages in a read-only textarea.
- **Restoring** backups: Downloads the JSONL file and re-imports it as a new chat using the standard import flow.
- **Deleting** backups: Removes the backup file from disk.

### 10.3 Backup API Endpoints

Defined in `src/endpoints/backups.js`:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/backups/chat/get` | List all chat backups with metadata |
| POST | `/api/backups/chat/delete` | Delete a specific backup file |
| POST | `/api/backups/chat/download` | Download a backup file |


## 11. Persona System

Personas represent different user identities, each with a name, avatar, and description. They are managed in `public/scripts/personas.js`.

### 11.1 Persona Data

Personas are stored in the user's settings (`power_user`), not in individual files:

```js
power_user.personas[avatarId] = personaName;           // Avatar ID -> Name map
power_user.persona_descriptions[avatarId] = {
    description: '',
    position: persona_description_positions.IN_PROMPT,  // Where to inject in prompt
    depth: 2,                                           // Prompt depth for injection
    role: 0,                                            // system=0, user=1, assistant=2
    lorebook: '',                                       // Associated World Info book
    connections: [],                                    // Character/group connections
    title: '',
};
```

### 11.2 Locking Mechanisms

Three levels of persona locking exist (`PersonaLockType` at line 50):

**Chat Lock** (`type: 'chat'`):
- Stored in `chat_metadata.persona = avatarId`.
- The persona is bound to a specific chat file.
- Checked first when loading a chat (`loadPersonaForCurrentChat()`, line 1441).

```js
// public/scripts/personas.js:1462
if (chat_metadata.persona) {
    console.log(`Using locked persona ${chat_metadata.persona}`);
    chatPersona = chat_metadata.persona;
}
```

**Character Lock** (`type: 'character'`):
- Stored in `power_user.persona_descriptions[avatarId].connections[]`.
- Each connection is a `{ type: 'character' | 'group', id: string }` object.
- Binds a persona to a specific character or group.

```js
// public/scripts/personas.js:1036-1038
power_user.persona_descriptions[user_avatar].connections = [...connections, newConnection];
```

**Default Lock** (`type: 'default'`):
- Stored in `power_user.default_persona`.
- Used as a fallback when no chat or character lock applies.

### 11.3 Persona Resolution Order

When a chat is opened (`loadPersonaForCurrentChat()`, line 1441):

1. Check `chat_metadata.persona` (chat lock) -- highest priority.
2. Check character/group connections (`getConnectedPersonas()`).
3. If multiple character connections exist and `persona_allow_multi_connections` is enabled, prompt the user to choose.
4. Fall back to `power_user.default_persona`.
5. If none found, keep the current persona.

### 11.4 Auto-Lock

When `power_user.persona_auto_lock` is enabled, selecting a persona automatically sets `chat_metadata.persona` to lock it to the current chat (`public/scripts/personas.js:839, 874-876`).


## 12. File Attachments in Chat

### 12.1 Attachment Types

SillyTavern supports two categories of attachments on chat messages:

**Media Attachments** (`extra.media[]`): Images, videos, audio. Defined by `MediaAttachment` in `public/global.d.ts:130-151`:

```ts
interface MediaAttachmentProps {
    url: string;        // Path to the file
    title?: string;     // Display name
    type: string;       // MEDIA_TYPE enum value
    source?: string;    // MEDIA_SOURCE (UPLOAD, API, etc.)
}
```

**File Attachments** (`extra.files[]`): Documents (PDF, DOCX, TXT, etc.). Defined by `FileAttachment` in `public/scripts/chats.js:62-68`:

```ts
interface FileAttachment {
    url: string;     // Server path to the file
    size: number;    // File size in bytes
    name: string;    // Original filename
    created: number; // Timestamp
    text?: string;   // Extracted text content (optional, for inline storage)
}
```

### 12.2 Upload Flow

The `populateFileAttachment()` function (`public/scripts/chats.js:198-266`) processes file uploads:

1. Read the file from the `<input>` element.
2. Check if the file is a media type (image/video/audio):
   - If yes: Save via `saveBase64AsFile()`, push to `message.extra.media[]`.
3. If it is a document:
   - Check if the MIME type has a converter (PDF, HTML, Markdown, EPUB, DOCX, XLSX, PPTX, ODS, ODP).
   - If convertible: Extract text using the appropriate converter function.
   - Upload the text content as a `.txt` file to `/api/files/upload`.
   - Push the file metadata to `message.extra.files[]`.

Supported document converters (`public/scripts/chats.js:86-97`):

```js
const converters = {
    'application/pdf': extractTextFromPDF,
    'text/html': extractTextFromHTML,
    'text/markdown': extractTextFromMarkdown,
    'application/epub+zip': extractTextFromEpub,
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': extractTextFromOffice,
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': extractTextFromOffice,
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': extractTextFromOffice,
    // ... ODS, ODP
};
```

The file size limit is 350 MB (`public/scripts/chats.js:76`).

### 12.3 Image Attachments from API

When the LLM returns images (e.g., from image generation), `saveImageToMessage()` (`public/script.js:6927-6937`) adds them to `extra.media[]`:

```js
function saveImageToMessage(img, mes) {
    mes.extra.media.push({
        url: img.image,
        type: MEDIA_TYPE.IMAGE,
        title: img.title,
        source: MEDIA_SOURCE.API,
    });
    mes.extra.inline_image = img.inline;
}
```

### 12.4 Attachment Storage

All uploaded files are stored under `user/files/` in the user's data directory. The server endpoint `POST /api/files/upload` (`src/endpoints/files.js:28-52`) writes base64 data directly to disk and returns a relative URL path.

Attachments are stored at three scopes (`ATTACHMENT_SOURCE` in `public/scripts/chats.js:77-81`):
- **GLOBAL**: Accessible from any chat.
- **CHARACTER**: Tied to a specific character.
- **CHAT**: Tied to the current chat (stored in `extra.files[]` on messages).


## 13. Summary of Key Architectural Patterns

1. **JSONL as the persistence format**: Every chat is a flat text file. No database. Atomic writes prevent corruption. This makes the system simple and portable but limits querying capability.

2. **Full-state saves**: The client sends the entire chat array on every save, not incremental diffs. The server overwrites the file entirely. Integrity slugs protect against race conditions.

3. **In-memory global state**: The client maintains a global `chat[]` array that is the single source of truth during a session. All operations (edit, swipe, delete, branch) mutate this array directly.

4. **Swipe-as-version-control**: The swipe system functions as a lightweight version control mechanism for individual messages, with full metadata snapshots per alternative.

5. **Branching via file duplication**: Checkpoints and branches create new JSONL files containing a copy of the chat up to the branch point. There is no shared history -- each branch is fully self-contained.

6. **No server-side message logic**: The server is a thin file I/O layer. All message manipulation (ordering, swipe management, metadata enrichment) happens client-side in JavaScript.
