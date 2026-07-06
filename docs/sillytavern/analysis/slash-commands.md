# SillyTavern v1.17.0 -- Slash Command System Analysis

SillyTavern ships a full-fledged scripting language called **STscript** built on top of its slash command infrastructure. What began as simple `/command arg` shortcuts has evolved into a Turing-complete system with closures, lexical scoping, piped execution, flow control, a debugger, and syntax highlighting. This analysis covers the architecture end-to-end.


## 1. Command Registry

### 1.1 The `SlashCommand` Class

Defined in `public/scripts/slash-commands/SlashCommand.js` (437 lines).

Each command is a `SlashCommand` instance with these core properties:

```js
// SlashCommand.js:50-66
name;              // string -- primary name
callback;          // (namedArgs, unnamedArgs) => string|SlashCommandClosure|Promise<...>
helpString;        // HTML help text
splitUnnamedArgument;       // boolean -- split unnamed arg into array
splitUnnamedArgumentCount;  // number -- how many splits
rawQuotes;         // boolean -- preserve wrapping quotes on unnamed arg
aliases;           // string[] -- alternative names
returns;           // string -- return type documentation
namedArgumentList;          // SlashCommandNamedArgument[]
unnamedArgumentList;        // SlashCommandArgument[]
isExtension;       // boolean -- auto-detected from call stack
isThirdParty;      // boolean -- auto-detected (third-party extension)
source;            // string -- file/extension that registered it
```

Commands are created via the static factory `SlashCommand.fromProps({...})` (line 44-47) which uses `Object.assign`.

### 1.2 Registration API

Registration is centralized on `SlashCommandParser` as a static method. The registry is a static dictionary:

```js
// SlashCommandParser.js:44
static commands = {};  // Object.<string, SlashCommand>
```

Two registration paths exist:

| Method | Location | Notes |
|--------|----------|-------|
| `SlashCommandParser.addCommandObject(cmd)` | SlashCommandParser.js:65 | Primary API. Validates reserved prefixes. |
| `SlashCommandParser.addCommand(name, cb, aliases, help)` | SlashCommandParser.js:53 | **Deprecated** legacy wrapper. |

The `addCommandObject` method (line 65-73) enforces reserved name prefixes -- commands cannot start with `/`, `#`, `:`, `parser-flag`, or `breakpoint`. It calls `addCommandObjectUnsafe` which:

1. Warns on duplicate registrations (line 79-81).
2. **Auto-detects origin** by inspecting the call stack for `/scripts/extensions/` or `/scripts/extensions/third-party/` paths (line 83-93).
3. Stores the command under its primary name and all aliases (line 95-101).

### 1.3 Command Count

Across the entire codebase, `SlashCommandParser.addCommandObject()` is called **286 times** across **33 files**. The breakdown by source:

| Source File | Registrations |
|-------------|:---:|
| `slash-commands.js` (core built-ins) | 100 |
| `variables.js` (variable/flow control) | 37 |
| `quick-reply/SlashCommandHandler.js` | 22 |
| `power-user.js` | 12 |
| `world-info.js` | 11 |
| `vectors/index.js` | 9 |
| `attachments/index.js` | 8 |
| `bookmarks.js` | 7 |
| `reasoning.js` | 7 |
| `extensions-slashcommands.js` | 6 |
| `expressions/index.js` | 6 |
| `secrets.js` | 5 |
| `authors-note.js` | 5 |
| `connection-manager/index.js` | 5 |
| `tags.js` | 5 |
| `SlashCommandParser.js` (meta-commands) | 5 |
| `tool-calling.js` | 4 |
| `action-loader-slashcommands.js` | 4 |
| `sysprompt.js` | 4 |
| `stable-diffusion/index.js` | 4 |
| Other files (1-3 each) | 20 |

After accounting for aliases and the parser's own internal commands (`/`, `#`, `breakpoint`, `break`, `parser-flag`), the system ships with approximately **200+ unique command names**.


## 2. Argument System

Defined in `public/scripts/slash-commands/SlashCommandArgument.js` (133 lines).

### 2.1 Argument Types

```js
// SlashCommandArgument.js:10-20
export const ARGUMENT_TYPE = {
    'STRING': 'string',
    'NUMBER': 'number',
    'RANGE': 'range',
    'BOOLEAN': 'bool',
    'VARIABLE_NAME': 'varname',
    'CLOSURE': 'closure',
    'SUBCOMMAND': 'subcommand',
    'LIST': 'list',
    'DICTIONARY': 'dictionary',
};
```

### 2.2 Named vs Unnamed Arguments

- **`SlashCommandNamedArgument`** extends `SlashCommandArgument`, adding `name` and `aliasList`. Syntax: `key=value`.
- **`SlashCommandArgument`** (unnamed) is positional. Collected as remaining text after named args.

Both support:
- `enumList` -- fixed set of valid values (drives autocomplete)
- `enumProvider` -- dynamic function `(executor, scope) => SlashCommandEnumValue[]`
- `forceEnum` -- restrict input to enum values
- `acceptsMultiple` -- collect into arrays
- `defaultValue` -- fallback when not provided
- `isRequired` -- validation flag

### 2.3 Argument Syntax in Commands

```
/command key1=value1 key2="quoted value" unnamed text here
```

Named arguments are parsed first (anything matching `/^\w+=/`), then the remaining text becomes the unnamed argument. The `splitUnnamedArgument` flag causes it to be split on whitespace into an array, with `splitUnnamedArgumentCount` controlling how many splits occur.


## 3. Parser Architecture

The parser lives in `public/scripts/slash-commands/SlashCommandParser.js` (~1,200 lines). It is a **hand-written recursive descent parser** that produces an AST of `SlashCommandClosure` objects containing `SlashCommandExecutor` nodes.

### 3.1 Parsing Entry Point

```js
// SlashCommandParser.js:708-725
parse(text, verifyCommandNames = true, flags = null, abortController = null, debugController = null) {
    this.text = text;
    this.index = 0;
    this.closureIndex = [];
    this.commandIndex = [];
    this.scopeIndex = [];
    this.macroIndex = [];
    const closure = this.parseClosure(true);
    return closure;
}
```

### 3.2 Parser State Machine

The parser operates character-by-character using `this.index`, `this.char`, `this.ahead`, and `this.behind`. Key methods:

- `take(n)` -- consume n characters, advance index
- `discardWhitespace()` -- skip whitespace
- `testSymbol(seq, offset)` -- lookahead test with escape handling

### 3.3 What Gets Parsed

The `parseClosure` method (line 743-813) is the core loop. For each iteration it tests and dispatches:

| Test | Parser Method | Result |
|------|--------------|--------|
| `/*` | `parseBlockComment()` | Discarded (supports nesting) |
| `//` or `/#` | `parseComment()` | Discarded |
| `/parser-flag` | `parseParserFlag()` | Modifies parser state |
| `/:` | `parseRunShorthand()` | `SlashCommandExecutor` using `run` command |
| `/breakpoint` | `parseBreakPoint()` | `SlashCommandBreakPoint` (debug only) |
| `/break` | `parseBreak()` | `SlashCommandBreak` |
| `/` | `parseCommand()` | `SlashCommandExecutor` |
| `{:` | `parseClosure()` | Nested `SlashCommandClosure` |

### 3.4 Pipe Handling

Pipes (`|`) are the command separator. After each command is parsed, the parser tests for `|`:

```js
// SlashCommandParser.js:793-800
if (this.testSymbol('|')) {
    this.take(); // discard first pipe
    // second pipe indicates no pipe injection for the next command
    if (this.testSymbol('|')) {
        injectPipe = false;
        this.take(); // discard second pipe
    }
}
```

- Single `|` -- normal pipe, the next command receives the previous result.
- Double `||` -- **pipe break**, the next command does NOT receive the pipe value.

### 3.5 Escape Handling

Two modes exist, controlled by `PARSER_FLAG.STRICT_ESCAPING`:

- **Loose mode** (default): single backslash escapes the next character.
- **Strict mode**: proper backslash counting -- `\\|` produces a literal `\` then pipes, `\|` produces a literal `|`.

### 3.6 Parser Flags

Set inline with `/parser-flag FLAG_NAME on|off`:

```js
// SlashCommandParser.js:38-41
export const PARSER_FLAG = {
    'STRICT_ESCAPING': 1,
    'REPLACE_GETVAR': 2,
};
```

`REPLACE_GETVAR` causes `{{getvar::name}}` and `{{getglobalvar::name}}` macros to be rewritten into scoped variable accesses at parse time, avoiding double macro substitution.

### 3.7 Syntax Highlighting

The parser registers an `stscript` language with highlight.js (lines 200-461), providing full syntax highlighting for closures, commands, named arguments, macros, pipes, comments, and variables. This is used in the QR editor and command browser.


## 4. Execution Engine

### 4.1 The Closure (`SlashCommandClosure`)

Defined in `public/scripts/slash-commands/SlashCommandClosure.js` (634 lines). This is the fundamental execution unit. Every parsed script becomes a closure.

Key properties:

```js
scope;            // SlashCommandScope -- lexical scope
executeNow;       // boolean -- if true, execute immediately when encountered (syntax: {:...:}())
argumentList;     // named args declared on the closure itself
providedArgumentList;  // args passed when calling the closure
executorList;     // SlashCommandExecutor[] -- the pipeline of commands
abortController;  // pause/abort support
breakController;  // break out of loops
debugController;  // step/breakpoint support
```

### 4.2 Execution Flow

The `execute()` method (line 241-254) creates a **copy** of the closure (to avoid mutation from re-execution) and runs `executeDirect()` as an async generator:

```js
// SlashCommandClosure.js:241-254
async execute() {
    const closure = this.getCopy();
    const gen = closure.executeDirect();
    let step;
    while (!step?.done) {
        step = await gen.next(this.debugController?.testStepping(this) ?? false);
        if (!(step.value instanceof SlashCommandClosureResult) && this.debugController) {
            this.debugController.isStepping = await this.debugController.awaitBreakPoint(step.value.closure, step.value.executor);
        }
    }
    return step.value;
}
```

### 4.3 The Three-Phase Step Executor

Each command in the pipeline goes through three generator yields in `executeStep()` (line 380-458):

1. **Before arguments resolved** -- yields the executor for debugger inspection.
2. **After arguments resolved** -- named/unnamed args are substituted and macro-expanded; yields again for debugger.
3. **After execution** -- the command's callback runs; result goes into `this.scope.pipe`.

The core execution line is:

```js
// SlashCommandClosure.js:438
this.scope.pipe = await executor.command.callback(args, value ?? '');
```

### 4.4 Pipe Propagation

Results flow through `scope.pipe`:

- Each command's return value is assigned to `scope.pipe`.
- The next command in the pipeline receives `scope.pipe` as its unnamed argument (unless `||` was used).
- The `#lintPipe` method (line 625-633) auto-fixes `null`/`undefined` returns to empty strings and non-string/non-closure returns to JSON.

```js
// SlashCommandClosure.js:625-633
#lintPipe(command) {
    if (this.scope.pipe === undefined || this.scope.pipe === null) {
        console.warn(`/${command.name} returned undefined or null. Auto-fixing to empty string.`);
        this.scope.pipe = '';
    } else if (!(typeof this.scope.pipe == 'string' || this.scope.pipe instanceof SlashCommandClosure)) {
        console.warn(`/${command.name} returned illegal type. Auto-fixing to stringified JSON.`);
        this.scope.pipe = JSON.stringify(this.scope.pipe) ?? '';
    }
}
```

### 4.5 Macro Substitution

Before each argument is passed to a command callback, the closure performs macro substitution via `substituteParams()` (line 155-217). Two engines exist:

1. **Legacy regex engine** (default): Iteratively matches `{{pipe}}`, `{{var::name}}`, and custom scope macros against the text.
2. **Experimental macro engine**: Uses the centralized `substituteParams()` with dynamic macro handlers (line 58-147). Enabled via `power_user.experimental_macro_engine`.

Both engines handle closure-valued macros -- if a macro resolves to a `SlashCommandClosure`, the result becomes a list of string/closure parts.

### 4.6 Abort and Pause

The `SlashCommandAbortController` (35 lines) provides:
- `abort(reason, isQuiet)` -- stops execution, optionally silently.
- `pause(reason)` / `continue(reason)` -- suspends/resumes execution.

The closure checks `testAbortController()` and `testPaused()` between each command step.


## 5. Variable System

Variables are implemented across two layers: **scoped variables** (STscript runtime) and **persisted variables** (local/global).

### 5.1 Scope Variables (`SlashCommandScope`)

Defined in `public/scripts/slash-commands/SlashCommandScope.js` (116 lines).

```js
// SlashCommandScope.js:4-8
export class SlashCommandScope {
    variableNames = [];     // string[] -- names declared in this scope
    variables = {};         // object -- name-to-value map
    macros = {};            // object -- custom macro definitions
    parent;                 // SlashCommandScope -- lexical parent
    #pipe;                  // string -- private pipe value
```

Key behaviors:
- **Lexical scoping**: `getVariable()` and `setVariable()` walk the parent chain.
- **`let` semantics**: `letVariable()` throws `SlashCommandScopeVariableExistsError` if the name already exists in the current scope.
- **Indexed access**: `getVariable(key, index)` and `setVariable(key, value, index, type)` support JSON array/object indexing.
- **Pipe inheritance**: `get pipe()` falls through to parent if the current scope has no pipe set.

### 5.2 Persisted Variables (Local and Global)

Defined in `public/scripts/variables.js` (2,348 lines).

| Scope | Storage | Persistence |
|-------|---------|-------------|
| **Local** (chat) | `chat_metadata.variables` | Saved with chat via `saveMetadataDebounced()` |
| **Global** | `extension_settings.variables.global` | Saved with settings via `saveSettingsDebounced()` |
| **Scope** | `SlashCommandScope.variables` | Runtime only, not persisted |

### 5.3 Variable Resolution Order

The `resolveVariable()` function (variables.js:218-232) defines the lookup:

```js
export function resolveVariable(name, scope = null) {
    if (scope?.existsVariable(name)) return scope.getVariable(name);
    if (existsLocalVariable(name)) return getLocalVariable(name);
    if (existsGlobalVariable(name)) return getGlobalVariable(name);
    return name;  // fall back to string literal
}
```

### 5.4 Variable Macros

Variables can be accessed via macro syntax in any text that undergoes substitution:

```
{{getvar::name}}          -- local variable
{{getglobalvar::name}}    -- global variable
{{setvar::name::value}}   -- set local (returns empty)
{{addvar::name::value}}   -- add to local
{{incvar::name}}          -- increment local by 1
{{decvar::name}}          -- decrement local by 1
{{var::name}}             -- scope variable (STscript only)
{{var::name::index}}      -- indexed scope variable
{{pipe}}                  -- current pipe value
```

These macros are defined in `getVariableMacros()` (variables.js:238-261) as regex-replace pairs.

### 5.5 Variable Commands

The full set of registered variable commands from `variables.js`:

| Command | Description |
|---------|-------------|
| `/let name value` | Declare new scope variable |
| `/var name value` | Get or set scope variable |
| `/setvar key=name value` | Set local (chat) variable |
| `/getvar name` | Get local variable |
| `/addvar key=name value` | Add to local variable |
| `/setglobalvar key=name value` | Set global variable |
| `/getglobalvar name` | Get global variable |
| `/addglobalvar key=name value` | Add to global variable |
| `/incvar name` | Increment local variable |
| `/decvar name` | Decrement local variable |
| `/incglobalvar name` | Increment global variable |
| `/decglobalvar name` | Decrement global variable |
| `/flushvar name` | Delete local variable |
| `/flushglobalvar name` | Delete global variable |
| `/listvar` | List all variables |


## 6. Flow Control

The variable system in `variables.js` registers full flow control primitives.

### 6.1 Conditionals (`/if`)

```text
/if left=score right=10 rule=gte "/speak You win"
/if left=score right=10 rule=gte {: /speak You win :} else={: /speak Try again :}
```

Comparison rules: `eq`, `neq`, `in`, `nin`, `gt`, `gte`, `lt`, `lte`, `not`.

The `else` is a named argument accepting a closure or subcommand. Both branches return their result down the pipe.

### 6.2 While Loops (`/while`)

```text
/setvar key=i 0 | /while left=i right=10 rule=lte "/addvar key=i 1"
```

- Default iteration limit: **100** (`MAX_LOOPS` constant, variables.js:20).
- Pass `guard=off` to disable the limit.
- Supports `break` to exit early.

### 6.3 Counted Loops (`/times`)

```text
/times 5 "/echo {{timesIndex}}"
```

- The iteration index is available as `{{timesIndex}}` (zero-based).
- Same 100-iteration guard applies.

### 6.4 Break and Abort

- `/break [value]` -- exits the current loop or closure executed via `/run` or `/:`. Optionally passes a value into the pipe.
- `/abort [reason]` -- stops all script execution. Has `quiet` argument for silent abort.

### 6.5 Closures as First-Class Values

Closures can be assigned to variables, passed as arguments, and called dynamically:

```text
/let myFunc {: x=1 /echo x is {{var::x}} :}
/:myFunc x=hello
```

The `/:` shorthand (run shorthand) parses to the `run` command. The `/run` callback (slash-commands.js:4212-4262) handles three cases:

1. **Closure argument**: execute directly.
2. **Scope variable**: retrieve closure from scope, pass provided arguments.
3. **Quick Reply name**: delegate to `executeQuickReplyByName`.

Closures support declared parameters and can be immediately invoked with `()`:

```text
{: x=default /echo {{var::x}} :}(x=actual)
```

### 6.6 Import

The `/import` command (QR SlashCommandHandler, line 680) allows importing named closures from other Quick Replies:

```text
/import from=MySet.MyQR myFunction as localName
```

It parses the target QR's message, finds `/let` or `/var` declarations whose values are closures, and injects them into the current scope.

### 6.7 Closure Serialization

Closures can be serialized to strings for persistence in variables:

```text
/closure-serialize {: /echo hello :} | /setvar key=myClosure
/closure-deserialize {{getvar::myClosure}} | /let fn {{pipe}} | /:fn
```


## 7. Built-in Command Categories

The ~100 commands in `slash-commands.js` plus ~37 in `variables.js` cover these categories:

### 7.1 Chat & Message Control

| Command | Purpose |
|---------|---------|
| `/send` | Send a user message |
| `/sendas name=X` | Send message as a character |
| `/sys` | Send a system/narrator message |
| `/comment` | Send a comment/note message |
| `/sysname` | Set the narrator name |
| `/messages N` | Get message(s) by index/range |
| `/setinput text` | Set chat input textarea |
| `/trigger N` | Trigger a message action |
| `/hide N` | Hide a message |
| `/unhide N` | Unhide a message |
| `/delswipe` | Delete a swipe |
| `/addswipe` | Add a swipe to the last message |
| `/swipe direction` | Navigate swipes |

### 7.2 Generation Control

| Command | Purpose |
|---------|---------|
| `/gen` | Trigger AI generation |
| `/genraw` | Generate without full prompt template |
| `/sysgen` | Generate with a system prompt |
| `/ask name=X` | Ask a character for a response |
| `/continue` | Continue the last AI message |
| `/regenerate` | Regenerate the last AI message |
| `/impersonate` | Generate as the user persona |
| `/stop` | Stop current generation |

### 7.3 Character Management

| Command | Purpose |
|---------|---------|
| `/go name` | Switch to a character |
| `/character-create` | Create a character from args |
| `/character-update` | Update character fields |
| `/character-delete` | Delete a character |
| `/character-get` | Get character data fields |
| `/delname name` | Delete a character by name |

### 7.4 Chat Session

| Command | Purpose |
|---------|---------|
| `/closechat` | Close current chat |
| `/tempchat` | Open a temporary chat |
| `/delchat` | Delete current chat |
| `/renamechat` | Rename current chat |
| `/getchatname` | Get current chat name |
| `/forcesave` | Force save the chat |
| `/single` / `/bubble` / `/flat` | Toggle chat styles |

### 7.5 API & Model Management

| Command | Purpose |
|---------|---------|
| `/api name` | Switch API provider |
| `/api-url url` | Set API URL |
| `/model name` | Switch model |
| `/tokenizer` | Get/set tokenizer |
| `/tokens` | Count tokens in text |
| `/instruct name` | Switch instruct preset |
| `/context name` | Switch context preset |

### 7.6 UI & Display

| Command | Purpose |
|---------|---------|
| `/echo` | Show toast notification (with severity, timeout, CSS class, color options) |
| `/popup` | Show a popup dialog |
| `/input` | Show input dialog |
| `/buttons labels=["a","b"]` | Show button selection dialog |
| `/panels` | Toggle UI panels |
| `/bg name` | Set background |
| `/beep` | Play notification sound |

### 7.7 Text Processing

| Command | Purpose |
|---------|---------|
| `/upper` | Convert to uppercase |
| `/lower` | Convert to lowercase |
| `/substr` | Substring extraction |
| `/replace` | Regex/string replace |
| `/test` | Regex test (returns bool) |
| `/match` | Regex match (returns array) |
| `/trimtokens` | Trim text to token count |
| `/trimstart` | Trim sentence start |
| `/trimend` | Trim sentence end |
| `/len` | Get string/array length |
| `/sort` | Sort a JSON array |
| `/fuzzy` | Fuzzy search in a list |

### 7.8 Math Operations

All in `variables.js`: `/add`, `/sub`, `/mul`, `/div`, `/mod`, `/pow`, `/sin`, `/cos`, `/log`, `/abs`, `/sqrt`, `/round`, `/min`, `/max`, `/rand`.

### 7.9 Data Operations

| Command | Purpose |
|---------|---------|
| `/pass` | Pass value through pipe unchanged |
| `/array-wrap` | Wrap value into JSON array |
| `/array-unwrap` | Extract first element of array |
| `/closure-serialize` | Serialize closure to string |
| `/closure-deserialize` | Deserialize string to closure |

### 7.10 Prompt Engineering

| Command | Purpose |
|---------|---------|
| `/inject` | Inject text into prompt at position/depth |
| `/listinjects` | List active injections |
| `/flushinject` | Remove an injection |
| `/getpromptentry` | Get prompt toggle state |
| `/setpromptentry` | Toggle prompt entries |

### 7.11 Miscellaneous

| Command | Purpose |
|---------|---------|
| `/run` (aliases: `/call`, `/exec`) | Execute a closure or QR |
| `/:name` | Run shorthand |
| `/delay ms` | Wait for N milliseconds |
| `/pass` | Identity pipe passthrough |
| `/help` | Show help page |
| `/reroll-pick` | Reroll `{{pick}}` macro choices |


## 8. Autocomplete System

### 8.1 Architecture

The autocomplete is triggered in `setSlashCommandAutoComplete()` (slash-commands.js:7155-7169):

```js
const ac = new AutoComplete(
    textarea,
    () => ac.text[0] == '/' && (/* enabled check */),
    async (text, index) => await parser.getNameAt(text, index),
    isFloating,
);
```

It uses the parser's `getNameAt()` method (SlashCommandParser.js:473-552) which:

1. Parses the full text (silently catching errors).
2. Finds the executor at the cursor position via `commandIndex`.
3. For `/:` (run shorthand), offers **scope variables** and **Quick Reply names**.
4. For regular commands, returns a `SlashCommandAutoCompleteNameResult` that provides:
   - All command names as primary completions.
   - Named argument names and their enum values as secondary completions.
   - Unnamed argument enum values.

### 8.2 `SlashCommandAutoCompleteNameResult`

Defined in `SlashCommandAutoCompleteNameResult.js`. Extends `AutoCompleteNameResult` with:

- `getSecondaryNameAt()` -- returns combined named + unnamed argument suggestions.
- `getNamedArgumentAt()` -- suggests named arg names and values.
- `getUnnamedArgumentAt()` -- suggests unnamed arg values.

### 8.3 Specialized Auto-Complete Options

Each argument type has its own autocomplete option class:

- `SlashCommandCommandAutoCompleteOption` -- for command names.
- `SlashCommandEnumAutoCompleteOption` -- for enum values.
- `SlashCommandNamedArgumentAutoCompleteOption` -- for named arg keys.
- `SlashCommandVariableAutoCompleteOption` -- for variable names in scope.
- `SlashCommandQuickReplyAutoCompleteOption` -- for QR set.label names.

### 8.4 Command Browser

The `SlashCommandBrowser` class (SlashCommandBrowser.js) provides a searchable UI that:

1. Lists all registered commands, filtered to exclude aliases (`filter(key => commands[key].name === key)`).
2. Supports fuzzy search and quoted literal search across command names, argument names, descriptions, enum values, help strings, and aliases.
3. Renders detailed help panels with argument specs, types, defaults, return types, and source indicators (core vs extension vs third-party).

### 8.5 Enum Providers

The `SlashCommandCommonEnumsProvider.js` exports a `commonEnumProviders` object with reusable dynamic enum generators:

- `variables('local'|'global'|'scope'|'all')` -- all variable names
- `characters()` -- all character names
- `groups()` -- all group names
- `messages()` -- chat message indices
- `boolean('onOff'|'trueFalse')` -- boolean options
- `numbersAndVariables` -- numbers plus variable names
- `types` -- type conversion options


## 9. Quick Reply Integration

Quick Replies are the primary way users create reusable STscript programs.

### 9.1 QR Structure

`QuickReply` (QuickReply.js) stores:

```js
id;              // number
label;           // string -- button label
message;         // string -- the slash command script body
contextList;     // QuickReplyContextLink[]
// Auto-execution flags:
executeOnStartup;
executeOnUser;
executeOnAi;
executeOnChatChange;
executeOnNewChat;
executeOnGroupMemberDraft;
executeBeforeGeneration;
automationId;    // string -- for WI-triggered auto-execution
```

### 9.2 QR Slash Commands

The `SlashCommandHandler` (22 registrations) provides a full CRUD API:

| Command | Purpose |
|---------|---------|
| `/qr N` | Execute QR by index |
| `/qr-set`, `/qr-set-on`, `/qr-set-off` | Toggle global QR sets |
| `/qr-chat-set`, `/qr-chat-set-on`, `/qr-chat-set-off` | Toggle chat QR sets |
| `/qr-set-list` | List QR set names |
| `/qr-list` | List QRs in a set |
| `/qr-create` | Create a new QR |
| `/qr-get` | Get QR properties |
| `/qr-update` | Update QR properties |
| `/qr-delete` | Delete a QR |
| `/qr-set-create`, `/qr-set-update`, `/qr-set-delete` | Manage QR sets |
| `/qr-presets` | List/set QR presets |
| `/qr-arg` | Set QR argument defaults |
| `/import from=SetName.Label varName` | Import closures from QR |

### 9.3 Auto-Execution

The `AutoExecuteHandler` (AutoExecuteHandler.js, 104 lines) handles automatic QR execution on events:

```js
// AutoExecuteHandler.js:47-80
async handleStartup()   { await this.performAutoExecute(this.getCommands('executeOnStartup')); }
async handleUser()      { await this.performAutoExecute(this.getCommands('executeOnUser')); }
async handleAi()        { await this.performAutoExecute(this.getCommands('executeOnAi')); }
async handleChatChanged() { ... }
async handleGroupMemberDraft() { ... }
async handleNewChat()   { ... }
async handleBeforeGeneration() { ... }
async handleWIActivation(entries) { ... }  // Triggered by World Info
```

The handler collects QRs from global, chat, and character configs that have the matching flag enabled. Each QR is executed with `preventAutoExecute` stack management to avoid infinite recursion.

### 9.4 QR Execution

When a QR's button is clicked or its label is used in `/run SetName.QRLabel`, the QR's `message` field is parsed and executed as an STscript closure. The QR editor includes:

- Full syntax highlighting via the `stscript` highlight.js language.
- Autocomplete support via `setSlashCommandAutoComplete(textarea, true)`.
- A built-in debugger with step, step-into, step-out, and breakpoint support.
- A progress bar and execution result display.


## 10. Extension Integration

### 10.1 How Extensions Register Commands

Extensions register commands identically to core code:

```js
import { SlashCommandParser } from '../../../slash-commands/SlashCommandParser.js';
import { SlashCommand } from '../../../slash-commands/SlashCommand.js';

SlashCommandParser.addCommandObject(SlashCommand.fromProps({
    name: 'my-ext-command',
    callback: myCallback,
    helpString: 'Does something',
    namedArgumentList: [...],
    unnamedArgumentList: [...],
}));
```

The system auto-detects that the call originates from an extension by inspecting the JavaScript call stack for `/scripts/extensions/` paths (SlashCommandParser.js:84-93). Third-party extensions are further distinguished by checking for `/scripts/extensions/third-party/`.

### 10.2 Extension Commands in the Wild

| Extension | Commands |
|-----------|----------|
| Quick Reply | 22 commands (`/qr-*`, `/import`) |
| Vectors (RAG) | 9 commands (`/vectors-*`) |
| Attachments | 8 commands |
| Reasoning | 7 commands |
| Expressions | 6 commands |
| Connection Manager | 5 commands |
| Stable Diffusion | 4 commands (`/sd-*`) |
| Regex | 3 commands |
| TTS | 1 command (`/tts`) |
| Translate | 1 command |
| Caption | 1 command |
| Token Counter | 1 command |
| Gallery | 2 commands |
| Memory (Summarize) | 1 command |

### 10.3 Global API Surface

Extensions can also provide dynamic autocomplete entries by setting functions on `globalThis`:

```js
// Quick Reply exposes its executable QR list
globalThis.qrEnumProviderExecutables = localEnumProviders.qrExecutables;

// And its execution function
globalThis.executeQuickReplyByName = ...;
```


## 11. Debugger

The `SlashCommandDebugController` (SlashCommandDebugController.js) provides a full step debugger for STscript:

```js
export class SlashCommandDebugController {
    stack = [];          // closure call stack
    cmdStack = [];       // current executor per closure
    stepStack = [];      // stepping state per closure level
    isStepping = false;
    isSteppingInto = false;
    isSteppingOut = false;
    namedArguments;      // inspectable after resolution
    unnamedArguments;    // inspectable after resolution
}
```

Supported operations:
- **Resume** (`resume()`) -- run until next breakpoint.
- **Step** (`step()`) -- execute one command.
- **Step Into** (`stepInto()`) -- enter a closure call.
- **Step Out** (`stepOut()`) -- finish the current closure.

Breakpoints are set with `/breakpoint` in the script text. The debugger integrates with the QR editor UI, showing the current execution position, resolved arguments, and pipe value.


## 12. Error Handling

### 12.1 Parser Errors

`SlashCommandParserError` (SlashCommandParserError.js) provides rich context:
- Line and column numbers calculated from the parse index.
- A visual `hint` showing surrounding lines with a `^^^^^` pointer at the error position.

### 12.2 Execution Errors

`SlashCommandExecutionError` (SlashCommandExecutionError.js, 59 lines) wraps command callback failures:

```js
constructor(cause, message, commandName, start, end, commandText, fullText) {
    super(message, { cause });
    this.commandName = commandName;
    this.start = start;
    this.end = end;
    this.commandText = commandText;
    this.text = fullText;
}
```

Like parser errors, it computes `line`, `column`, and a `hint` property from the position.

### 12.3 Error Display

The `executeSlashCommandsOnChatInput()` function (slash-commands.js:6955-7038) handles errors visually:

1. **Progress bar** on the chat input shows execution progress.
2. On error: `form_sheld` gets `script_error` CSS class; a toast shows the error with line/column and a code hint.
3. On abort: `script_aborted` CSS class.
4. On success: `script_success` CSS class, auto-cleared after 1 second.

Clicking a toast error opens a popup with the full error details and context.

### 12.4 Closure Result

`SlashCommandClosureResult` (10 lines) is the universal return type:

```js
export class SlashCommandClosureResult {
    interrupt = false;
    pipe;                // string -- the final pipe value
    isBreak = false;     // was /break used
    isAborted = false;   // was /abort used
    isQuietlyAborted = false;
    abortReason;
    isError = false;
    errorMessage;
}
```


## 13. Return Value Routing

The `SlashCommandReturnHelper` (SlashCommandReturnHelper.js, 82 lines) standardizes how commands return values to the user. Commands that support a `return=` named argument use this:

```js
// SlashCommandReturnHelper.js:8
/** @typedef {'pipe'|'object'|'chat-html'|'chat-text'|'popup-html'|'popup-text'|
 *            'toast-html'|'toast-text'|'console'|'none'} SlashCommandReturnType */
```

| Return Type | Behavior |
|-------------|----------|
| `pipe` | Pass string down the pipe (default for most) |
| `object` | JSON-stringify and pass down pipe |
| `chat-html` | Send as system message with HTML rendering |
| `chat-text` | Send as system message, escaped text |
| `popup-html` | Show in a popup with markdown-to-HTML |
| `popup-text` | Show in a popup, escaped text |
| `toast-html` | Toast notification with HTML |
| `toast-text` | Toast notification, escaped text |
| `console` | Log to browser console |
| `none` | Discard the value |


## 14. Summary of Key Design Patterns

1. **Static singleton registry**: All commands live in `SlashCommandParser.commands`, a single flat dictionary. No namespacing -- name conflicts are warned but not prevented.

2. **Recursive descent parser**: The hand-written parser avoids regex-based parsing fragility and supports nested closures, escape sequences, and parser flags.

3. **Generator-based execution**: The three-phase yield pattern in `executeStep()` enables the debugger to inspect state between argument resolution and command execution without restructuring the control flow.

4. **Copy-on-execute closures**: `execute()` always runs on a copy of the closure, making closures safely re-callable (important for loops and `/run`).

5. **Pipe as implicit argument**: The Unix-like pipe model (`|`) means commands are composable by default. The `||` (pipe break) provides an escape hatch.

6. **Auto-detection of extensions**: The stack trace introspection for source detection is clever but fragile -- it relies on file path conventions in the call stack.

7. **Three variable scopes with different lifetimes**: Scope variables (runtime), local variables (chat-persistent), and global variables (settings-persistent) cover the full spectrum of storage needs.
