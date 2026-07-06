# Provider-Dropdown-Constrained-By-Family Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** In the model create/edit UI, the Provider selector shows only providers that can serve the chosen model family (curated via `ModelFamily.provider_types`), and the Model Identifier field autocompletes from the chosen provider's live catalog.

**Architecture:** The family→provider linkage already exists as `ModelFamily.provider_types` (a seeded list of provider-type strings, already API-exposed). This plan (1) corrects the seed values, (2) enforces the pairing server-side, (3) uses the existing data client-side to filter the provider dropdown, and (4) adds discovery-driven identifier autocomplete. No new endpoint, no migration, no OpenAPI change.

**Tech Stack:** Backend — Python 3.14, FastAPI, SQLAlchemy 2.0, pytest. Frontend — Vue 3 `<script setup>`, Nuxt UI `USelectMenu`, `bun test`, openapi-fetch.

## Global Constraints

- **No commits without explicit user approval** — the repo has a `.claude/hooks/block-git-write.sh` hook that blocks git writes. Treat every "Commit" step as a checkpoint to run only once the user OKs.
- Backend must pass: `uv run ruff format .`, `uv run ruff check . --fix`, `uv run basedpyright`, `uv run pytest`. (Hooks `ruff-fix.sh` / `basedpyright-check.sh` also run on edit.)
- Frontend must pass: `bun test`, `bun run typecheck`, `bun run lint`. (Hooks `format-fix.sh` / `typecheck.sh` run on edit.)
- Frontend UI tests import from `bun:test` and run via `bun test <path>` (see `src/composables/__tests__/useCharacterForm.test.ts`).
- Tailwind: use canonical classes (`shrink-0`, not `flex-shrink-0`).
- `provider_types` is at the **family (base-lineage)** level. A finetune inherits its base family's providers (e.g. a Mistral-Small finetune shows OpenRouter even if that specific finetune isn't hosted there); the identifier-autocomplete step self-resolves it (the provider's catalog won't list it). This granularity is accepted.
- No API surface change → do **not** run `bun run api:gen` / regenerate `openapi.json`.

Repos:
- Backend: `/Users/dwi.elfianto/workspace/github/candlekeep-core`
- Frontend: `/Users/dwi.elfianto/workspace/github/candlekeep-ui`

---

## File Structure

**Backend (candlekeep-core):**
- Modify: `src/fixtures/families/gemma.py`, `src/fixtures/families/mistral.py`, `src/fixtures/families/llama.py` — add `lmstudio` to `provider_types`.
- Create: `tests/model_family/test_seed_provider_types.py` — data-integrity test for the seed.
- Modify: `src/model/service.py` — `create()` and `update()` primary-provider validation.
- Modify: `tests/model/test_service.py` — validation tests.

**Frontend (candlekeep-ui):**
- Create: `src/utils/modelProviderFilter.ts` — pure `providersForFamily()` helper.
- Create: `src/utils/__tests__/modelProviderFilter.test.ts` — `bun test`.
- Modify: `src/views/settings/ModelCreateView.vue` — filter provider by family, reorder, disable-until-family, prefill handling, identifier autocomplete.
- Modify: `src/views/settings/ModelView.vue` — filter provider by family, reorder, identifier autocomplete.

---

## Task 1: Seed `provider_types` — add `lmstudio` wherever `ollama` runs

**Files:**
- Modify: `src/fixtures/families/gemma.py:22`
- Modify: `src/fixtures/families/mistral.py:34`, `src/fixtures/families/mistral.py:65`
- Modify: `src/fixtures/families/llama.py:27`
- Test: `tests/model_family/test_seed_provider_types.py`

**Interfaces:**
- Consumes: `src.fixtures.families.MODEL_FAMILIES_SEED_DATA` (list of `ModelFamilySeedData` dicts, each with `family_identifier: str` and `provider_types: list[str]`).
- Produces: seed rows where every family containing `"ollama"` also contains `"lmstudio"`. Re-seeding on app startup updates existing rows (`seed_model_families.py:42`).

- [ ] **Step 1: Write the failing test**

Create `tests/model_family/test_seed_provider_types.py`:

```python
"""Seed-data integrity: local GGUF families must list both local runners."""

from src.fixtures.families import MODEL_FAMILIES_SEED_DATA


def _family(identifier: str) -> dict:
    return next(f for f in MODEL_FAMILIES_SEED_DATA if f["family_identifier"] == identifier)


def test_local_gguf_families_include_lmstudio():
    """Ollama and LM Studio both run local GGUF, so they travel together."""
    for identifier in [
        "google/gemma-4",
        "mistral/mistral-nemo",
        "mistral/mistral-small",
        "meta/llama-3",
    ]:
        provider_types = _family(identifier)["provider_types"]
        assert "ollama" in provider_types, f"{identifier} lost ollama"
        assert "lmstudio" in provider_types, f"{identifier} missing lmstudio"


def test_lmstudio_accompanies_ollama_everywhere():
    """Any family that can run on Ollama can also run on LM Studio."""
    for family in MODEL_FAMILIES_SEED_DATA:
        provider_types = family["provider_types"]
        if "ollama" in provider_types:
            assert "lmstudio" in provider_types, (
                f"{family['family_identifier']} has ollama but not lmstudio"
            )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /Users/dwi.elfianto/workspace/github/candlekeep-core && uv run pytest tests/model_family/test_seed_provider_types.py -v`
Expected: FAIL — `google/gemma-4 missing lmstudio` (current value is `["ollama", "openrouter"]`).

- [ ] **Step 3: Add `lmstudio` to the four families**

In `src/fixtures/families/gemma.py:22` change:
```python
        "provider_types": ["ollama", "openrouter"],
```
to:
```python
        "provider_types": ["ollama", "lmstudio", "openrouter"],
```

In `src/fixtures/families/mistral.py` — both records (`mistral/mistral-nemo` at `:34` and `mistral/mistral-small` at `:65`) — change each:
```python
        "provider_types": ["ollama", "openrouter"],
```
to:
```python
        "provider_types": ["ollama", "lmstudio", "openrouter"],
```

In `src/fixtures/families/llama.py:27` change:
```python
        "provider_types": ["ollama", "openrouter"],
```
to:
```python
        "provider_types": ["ollama", "lmstudio", "openrouter"],
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/model_family/test_seed_provider_types.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Apply to the running DB and confirm**

Re-seeding runs on startup and updates existing rows. Restart the backend, then verify:

Run:
```bash
curl -s "http://localhost:8000/api/model-families?limit=100&provider_type=lmstudio" \
  | python3 -c "import sys,json;print(sorted(f['family_identifier'] for f in json.load(sys.stdin)['items']))"
```
Expected: list includes `google/gemma-4`, `mistral/mistral-nemo`, `mistral/mistral-small`, `meta/llama-3`.

- [ ] **Step 6: Commit** (on approval)

```bash
git add src/fixtures/families/gemma.py src/fixtures/families/mistral.py src/fixtures/families/llama.py tests/model_family/test_seed_provider_types.py
git commit -m "fix(fixtures): list lmstudio alongside ollama for local GGUF families"
```

---

## Task 2: Enforce primary provider ∈ family.provider_types (backend)

**Files:**
- Modify: `src/model/service.py:179-198` (create), `src/model/service.py:256-289` (update)
- Test: `tests/model/test_service.py`

**Interfaces:**
- Consumes: `Provider.provider_type` (enum; `.value` is the string), `ModelFamily.provider_types: list[str]`, `self.provider_repo.find_by_id(id) -> Provider | None`.
- Produces: `ModelService.create(...)` / `.update(...)` raise `HTTPException(400)` when the primary provider's type is not in the family's `provider_types`. Mirrors the existing OpenRouter gate.

- [ ] **Step 1: Write the failing tests**

Append to `tests/model/test_service.py` (inside `class TestModelService`):

```python
    def test_create_rejects_provider_type_not_in_family(self, db: Session) -> None:
        """A family that can't run on the chosen provider type is a 400."""
        provider = Provider(name="Local LM Studio", provider_type=ProviderType.LMSTUDIO)
        family = ModelFamily(
            name="Ollama-only Fam",
            family_identifier="test/ollama-only",
            provider_types=["ollama"],
        )
        db.add_all([provider, family])
        db.commit()

        service = ModelService(
            ModelRepository(db), ProviderRepository(db), ModelFamilyRepository(db), ChatRepository(db)
        )
        with pytest.raises(HTTPException) as exc:
            service.create(
                name="X",
                provider_id=provider.id,
                model_identifier="x",
                model_family_id=family.id,
            )
        assert exc.value.status_code == 400
        assert "cannot serve" in exc.value.detail

    def test_create_allows_provider_type_in_family(self, db: Session) -> None:
        """LM Studio is allowed once the family lists it."""
        provider = Provider(name="Local LM Studio", provider_type=ProviderType.LMSTUDIO)
        family = ModelFamily(
            name="Local Fam",
            family_identifier="test/local",
            provider_types=["ollama", "lmstudio"],
        )
        db.add_all([provider, family])
        db.commit()

        service = ModelService(
            ModelRepository(db), ProviderRepository(db), ModelFamilyRepository(db), ChatRepository(db)
        )
        created = service.create(
            name="X", provider_id=provider.id, model_identifier="x", model_family_id=family.id
        )
        assert created.id

    def test_update_rejects_family_change_incompatible_with_provider(self, db: Session) -> None:
        """Switching to a family the current provider can't serve is a 400."""
        provider = Provider(name="Local LM Studio", provider_type=ProviderType.LMSTUDIO)
        ok_family = ModelFamily(
            name="Local Fam2", family_identifier="test/local2", provider_types=["lmstudio"]
        )
        cloud_family = ModelFamily(
            name="Cloud Fam", family_identifier="test/cloud", provider_types=["anthropic"]
        )
        db.add_all([provider, ok_family, cloud_family])
        db.commit()
        service = ModelService(
            ModelRepository(db), ProviderRepository(db), ModelFamilyRepository(db), ChatRepository(db)
        )
        model = service.create(
            name="X", provider_id=provider.id, model_identifier="x", model_family_id=ok_family.id
        )
        with pytest.raises(HTTPException) as exc:
            service.update(model.id, model_family_id=cloud_family.id)
        assert exc.value.status_code == 400
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/model/test_service.py -k "provider_type or incompatible" -v`
Expected: FAIL — `test_create_rejects_...` and `test_update_rejects_...` fail (no validation yet; create currently succeeds).

- [ ] **Step 3: Add the check to `create()`**

In `src/model/service.py`, immediately after the family-existence check (currently ending at line 184, before the `# Validate OpenRouter routing` comment at line 186), insert:

```python
        # The model's own provider must be one the family can actually run on.
        if provider.provider_type.value not in model_family.provider_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Provider '{provider.name}' ({provider.provider_type.value}) cannot serve "
                    f"model family '{model_family.name}'. "
                    f"Supported: {', '.join(model_family.provider_types) or 'none'}."
                ),
            )
```

- [ ] **Step 4: Add the check to `update()`**

In `src/model/service.py`, after the family-change block (ends at line 268, before `new_use_openrouter = ...` at line 270), insert:

```python
        # Re-validate the primary provider whenever the provider or family changes.
        if provider_id is not None or family_changed:
            eff_provider = self.provider_repo.find_by_id(model.provider_id)
            if eff_provider and eff_provider.provider_type.value not in target_family.provider_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Provider '{eff_provider.name}' ({eff_provider.provider_type.value}) "
                        f"cannot serve model family '{target_family.name}'. "
                        f"Supported: {', '.join(target_family.provider_types) or 'none'}."
                    ),
                )
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/model/test_service.py -v`
Expected: PASS (new tests pass; existing tests still pass).

- [ ] **Step 6: Guard against pre-existing violators**

Existing models must not become un-editable. Check for current violations:

```bash
uv run python - <<'PY'
import os, psycopg2
from dotenv import load_dotenv
load_dotenv("/Users/dwi.elfianto/workspace/github/candlekeep-core/.env")
cur = psycopg2.connect(os.environ["DATABASE_URL"]).cursor()
cur.execute("""
  SELECT m.name, p.provider_type, f.family_identifier, f.provider_types
  FROM models m JOIN providers p ON p.id=m.provider_id
  JOIN model_families f ON f.id=m.model_family_id
  WHERE NOT (p.provider_type = ANY(f.provider_types))
""")
rows = cur.fetchall()
print("VIOLATORS:", rows or "none")
PY
```
Expected after Task 1: `none` (the LM Studio Gemma models are legal once `google/gemma-4` includes `lmstudio`). If any remain, either correct that family's `provider_types` (Task 1 pattern) or the model's provider before shipping the validation.

- [ ] **Step 7: Commit** (on approval)

```bash
git add src/model/service.py tests/model/test_service.py
git commit -m "feat(model): validate primary provider against family provider_types"
```

---

## Task 3: `providersForFamily()` helper (frontend, unit-tested)

**Files:**
- Create: `src/utils/modelProviderFilter.ts`
- Test: `src/utils/__tests__/modelProviderFilter.test.ts`

**Interfaces:**
- Consumes: `components["schemas"]["ProviderResponse"]` (has `id`, `name`, `provider_type: string`), `components["schemas"]["ModelFamilyListResponse"]`/`ModelFamilyResponse` (has `provider_types: string[]`).
- Produces: `providersForFamily(providers, family): Provider[]` — providers whose `provider_type` is in `family.provider_types`; `[]` when `family` is nullish. Imported by both views in Tasks 4–5.

- [ ] **Step 1: Write the failing test**

Create `src/utils/__tests__/modelProviderFilter.test.ts`:

```ts
import { describe, it, expect } from "bun:test";
import { providersForFamily } from "@/utils/modelProviderFilter";

const P = (id: string, provider_type: string) => ({ id, name: id, provider_type }) as any;
const providers = [
  P("anthropic", "anthropic"),
  P("lmstudio", "lmstudio"),
  P("ollama", "ollama"),
  P("openrouter", "openrouter"),
];

describe("providersForFamily", () => {
  it("keeps only providers whose type is in the family's provider_types", () => {
    const family = { provider_types: ["anthropic", "openrouter"] } as any;
    expect(providersForFamily(providers, family).map((p) => p.id)).toEqual([
      "anthropic",
      "openrouter",
    ]);
  });

  it("handles the Gemma case (ollama/lmstudio/openrouter)", () => {
    const family = { provider_types: ["ollama", "lmstudio", "openrouter"] } as any;
    expect(providersForFamily(providers, family).map((p) => p.id).sort()).toEqual([
      "lmstudio",
      "ollama",
      "openrouter",
    ]);
  });

  it("returns [] when no family is selected", () => {
    expect(providersForFamily(providers, undefined)).toEqual([]);
    expect(providersForFamily(providers, null)).toEqual([]);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /Users/dwi.elfianto/workspace/github/candlekeep-ui && bun test src/utils/__tests__/modelProviderFilter.test.ts`
Expected: FAIL — cannot resolve `@/utils/modelProviderFilter`.

- [ ] **Step 3: Implement the helper**

Create `src/utils/modelProviderFilter.ts`:

```ts
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `bun test src/utils/__tests__/modelProviderFilter.test.ts`
Expected: PASS (3 pass).

- [ ] **Step 5: Commit** (on approval)

```bash
git add src/utils/modelProviderFilter.ts src/utils/__tests__/modelProviderFilter.test.ts
git commit -m "feat(ui): add providersForFamily helper"
```

---

## Task 4: Wire the create view (ModelCreateView.vue)

**Files:**
- Modify: `src/views/settings/ModelCreateView.vue`

**Interfaces:**
- Consumes: `providersForFamily` (Task 3), `useProviders().providers`, `useModelFamilies().families` (each family item carries `provider_types`).
- Produces: provider dropdown filtered by selected family; family shown before provider; provider disabled until a family is chosen; prefilled provider (from `?provider_id=`) restored once a compatible family is picked.

- [ ] **Step 1: Import the helper**

In `src/views/settings/ModelCreateView.vue`, after line 6 (`import { useModelFamilies } ...`) add:
```ts
import { providersForFamily } from "@/utils/modelProviderFilter";
```

- [ ] **Step 2: Replace the items/name computeds (lines 37–52)**

Replace:
```ts
const providerItems = computed(() =>
  [...providers.value]
    .sort((a: any, b: any) => a.name.localeCompare(b.name))
    .map((p: any) => ({ label: p.name, value: p.id })),
);
const familyItems = computed(() =>
  [...families.value]
    .sort((a: any, b: any) => a.name.localeCompare(b.name))
    .map((f: any) => ({ label: f.name, value: f.id })),
);
const providerName = computed(
  () => providerItems.value.find((i) => i.value === form.provider_id)?.label || "Select a provider",
);
const familyName = computed(
  () => familyItems.value.find((i) => i.value === form.model_family_id)?.label || "Select a family",
);
```
with:
```ts
const selectedFamily = computed(() =>
  families.value.find((f: any) => f.id === form.model_family_id),
);
const providerItems = computed(() =>
  providersForFamily(providers.value as any, selectedFamily.value as any)
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((p) => ({ label: p.name, value: p.id })),
);
const familyItems = computed(() =>
  [...families.value]
    .sort((a: any, b: any) => a.name.localeCompare(b.name))
    .map((f: any) => ({ label: f.name, value: f.id })),
);
// Fall back to the full provider list so a prefilled provider still displays
// before its family is chosen.
const providerName = computed(
  () => providers.value.find((p: any) => p.id === form.provider_id)?.name || "Select a provider",
);
const familyName = computed(
  () => familyItems.value.find((i) => i.value === form.model_family_id)?.label || "Select a family",
);
```

- [ ] **Step 3: Add the family-change watch (after line 66, the openrouter watch)**

```ts
// Provider is constrained by the family. On family change, drop an incompatible
// provider; restore a prefilled provider (from the "Add as Model" flow) once a
// compatible family is chosen.
const prefilledProviderId = (route.query.provider_id as string) || "";
watch(
  () => form.model_family_id,
  () => {
    const valid = providerItems.value.some((i) => i.value === form.provider_id);
    if (form.provider_id && !valid) form.provider_id = "";
    if (
      !form.provider_id &&
      prefilledProviderId &&
      providerItems.value.some((i) => i.value === prefilledProviderId)
    ) {
      form.provider_id = prefilledProviderId;
    }
  },
);
```

- [ ] **Step 4: Reorder template — Model Family before Provider**

In the template, move the entire **Model Family** `<label>` block (currently lines 226–246) to directly **above** the **Provider** `<label>` block (currently starts line 204). Family first, provider second.

- [ ] **Step 5: Disable the provider trigger until a family is chosen**

In the Provider block, replace the `<USelectMenu>` opening + button (currently lines 211–223) with:
```html
              <USelectMenu
                v-model="form.provider_id"
                :items="providerItems"
                value-key="value"
                class="w-full"
                :ui="selectUi"
                :disabled="!form.model_family_id"
              >
                <button
                  :disabled="!form.model_family_id"
                  class="flex h-11 w-full items-center rounded-lg border bg-muted/40 px-4 text-sm text-foreground outline-none transition-all hover:border-muted-foreground/30 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {{ form.model_family_id ? providerName : "Select a family first" }}
                </button>
              </USelectMenu>
```

- [ ] **Step 6: Verify typecheck + lint**

Run: `bun run typecheck && bun run lint`
Expected: no errors.

- [ ] **Step 7: Manual check**

With both servers running, open `/settings/models/new`: Provider is disabled until a family is picked. Choose **Claude 4.5 Haiku** → Provider lists Anthropic (+ OpenRouter). Choose **Gemma 4** → Ollama, LM Studio, OpenRouter. Switch family to a cloud one → an incompatible provider selection clears.

- [ ] **Step 8: Commit** (on approval)

```bash
git add src/views/settings/ModelCreateView.vue
git commit -m "feat(ui): constrain create-model provider dropdown by family"
```

---

## Task 5: Wire the edit view (ModelView.vue)

**Files:**
- Modify: `src/views/settings/ModelView.vue`

**Interfaces:**
- Consumes: `providersForFamily` (Task 3), `useSettingsStore().providers`, `useModelFamilies().families`, `model.value.model_family` (fallback family with `provider_types`).
- Produces: provider dropdown filtered by the model's (possibly changed) family; family before provider; provider clears if a family change makes it incompatible.

- [ ] **Step 1: Import the helper**

After line 8 (`import { useModelFamilies } ...`) add:
```ts
import { providersForFamily } from "@/utils/modelProviderFilter";
```

- [ ] **Step 2: Replace `providerItems` (lines 87–91)**

Replace:
```ts
const providerItems = computed(() =>
  [...settingsStore.providers]
    .sort((a: any, b: any) => a.name.localeCompare(b.name))
    .map((p: any) => ({ label: p.name, value: p.id })),
);
```
with:
```ts
const selectedFamily = computed(
  () =>
    families.value.find((f: any) => f.id === form.model_family_id) ||
    (model.value?.model_family as any),
);
const providerItems = computed(() =>
  providersForFamily(settingsStore.providers as any, selectedFamily.value as any)
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((p) => ({ label: p.name, value: p.id })),
);
```
(`providerName` at lines 98–101 already falls back to `settingsStore.providers`; leave it.)

- [ ] **Step 3: Add the family-change watch (after the openrouter watch, ~line 79)**

```ts
// Drop a provider that the newly chosen family can't serve.
watch(
  () => form.model_family_id,
  () => {
    if (form.provider_id && !providerItems.value.some((i) => i.value === form.provider_id)) {
      form.provider_id = "";
    }
  },
);
```

- [ ] **Step 4: Reorder template — Model Family before Provider**

Move the **Model Family** `<label>` block (currently lines 326–346) to directly **above** the **Provider selector** block (currently starts line 303).

- [ ] **Step 5: Disable the provider trigger until a family is chosen**

In the Provider block, add `:disabled="!form.model_family_id"` to the `<USelectMenu>` (currently line 310–316) and to its `<button>` (line 318), and append `disabled:cursor-not-allowed disabled:opacity-50` to the button class. (Existing models always have a family, so it stays enabled in practice; this only guards a cleared selection.)

- [ ] **Step 6: Verify typecheck + lint**

Run: `bun run typecheck && bun run lint`
Expected: no errors.

- [ ] **Step 7: Manual check**

Open the Gemma 4 model created earlier (`/settings/models/G9GwSyHHKyhO`): Provider lists Ollama / LM Studio / OpenRouter, with LM Studio selected. Change family to a Claude family → provider clears (LM Studio no longer valid).

- [ ] **Step 8: Commit** (on approval)

```bash
git add src/views/settings/ModelView.vue
git commit -m "feat(ui): constrain edit-model provider dropdown by family"
```

---

## Task 6 (optional, Phase 2): Discovery autocomplete for Model Identifier

Turns the free-text Model Identifier into a `<datalist>` populated from the chosen provider's live catalog — the discovery half of the hybrid. Skip if you only need provider gating.

**Files:**
- Modify: `src/views/settings/ModelCreateView.vue` (and optionally `ModelView.vue`)

**Interfaces:**
- Consumes: `useProvider().fetchAvailableModels(providerId)` → populates `availableModels: Ref<DiscoveredModel[]>` (`DiscoveredModel` has `identifier`, `display_name`, `state`), plus `modelsLoading: Ref<boolean>`.
- Produces: identifier `<input>` backed by a `<datalist>` of the provider's discovered identifiers.

- [ ] **Step 1: Import and instantiate the composable**

In `ModelCreateView.vue` script, add:
```ts
import { useProvider } from "@/composables/useProvider";
```
and inside `<script setup>`:
```ts
const { availableModels, modelsLoading, fetchAvailableModels } = useProvider();
```

- [ ] **Step 2: Fetch when provider changes**

Add a watch (after the family-change watch from Task 4 Step 3):
```ts
// Pull the provider's live catalog so the identifier field can autocomplete.
watch(
  () => form.provider_id,
  (id) => {
    if (id) fetchAvailableModels(id);
  },
);
```

- [ ] **Step 3: Add a datalist option computed**

```ts
const identifierOptions = computed(() =>
  availableModels.value.map((m) => m.identifier),
);
```

- [ ] **Step 4: Bind the identifier input to a datalist**

Replace the Model Identifier `<input>` (currently lines 196–201) with:
```html
              <input
                v-model="form.model_identifier"
                type="text"
                list="model-identifier-options"
                :placeholder="modelsLoading ? 'Loading provider catalog…' : 'e.g. openai/gpt-4o'"
                class="h-11 w-full rounded-lg border bg-muted/40 px-4 font-mono text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
              />
              <datalist id="model-identifier-options">
                <option v-for="opt in identifierOptions" :key="opt" :value="opt" />
              </datalist>
```

- [ ] **Step 5: Verify + manual**

Run: `bun run typecheck && bun run lint`
Manual: pick Gemma 4 → LM Studio → the identifier field suggests `google/gemma-4-31b-qat` and the other local ids. It stays free-text (finetunes not in the catalog can still be typed).

- [ ] **Step 6: Commit** (on approval)

```bash
git add src/views/settings/ModelCreateView.vue
git commit -m "feat(ui): autocomplete model identifier from provider catalog"
```

---

## Task 7: Full verification

- [ ] **Step 1: Backend gate**

Run:
```bash
cd /Users/dwi.elfianto/workspace/github/candlekeep-core
uv run ruff format . && uv run ruff check . --fix && uv run basedpyright && uv run pytest
```
Expected: format/lint clean, basedpyright 0 errors, pytest all pass.

- [ ] **Step 2: Frontend gate**

Run:
```bash
cd /Users/dwi.elfianto/workspace/github/candlekeep-ui
bun test && bun run typecheck && bun run lint
```
Expected: all pass.

- [ ] **Step 3: End-to-end matrix (manual, both servers up)**

| Family | Expected providers in dropdown |
|---|---|
| Claude 4.5 Haiku | Anthropic, OpenRouter |
| Gemma 4 | Ollama, LM Studio, OpenRouter |
| Mistral Small 24B (Skyfall's base) | Ollama, LM Studio, OpenRouter* |

\* OpenRouter appears at the family level; on the identifier step OpenRouter's catalog won't list the Skyfall finetune (accepted granularity).

- [ ] **Step 4: Confirm no OpenAPI drift**

Run: `cd /Users/dwi.elfianto/workspace/github/candlekeep-core && git status --short openapi.json`
Expected: no output (unchanged — no API surface change).

---

## Self-Review

- **Spec coverage:** (1) seed fix → Task 1; (2) backend validation → Task 2; (3) provider dropdown by family → Tasks 3–5; (4) discovery autocomplete → Task 6; (5) verify → Task 7. The scoped "resolver endpoint" was intentionally dropped — client-side filtering over already-loaded `providers` + `families` covers gating with no new API; server-side integrity lives in Task 2.
- **Placeholders:** none — every code step carries full code; commands include expected output.
- **Type consistency:** `providersForFamily(providers, family)` defined in Task 3 is consumed with the same signature in Tasks 4–5; `fetchAvailableModels(id)` / `availableModels` / `modelsLoading` match `useProvider.ts`.
