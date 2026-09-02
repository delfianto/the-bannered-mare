# Key Page Dependency Trees

These trees trace local imports recursively. Shared application shell dependencies apply to every route: `App.vue → AppShell.vue → AppSidebar.vue + ServerStatusBanner.vue + RouterView`.

## / — Home

Entry: `frontend/src/views/HomeView.vue`

- frontend/src/views/HomeView.vue
  - frontend/src/components/layout/PageContainer.vue
  - frontend/src/components/shared/SearchBar.vue
  - frontend/src/components/shared/ContinueTaleSection.vue
    - frontend/src/utils/avatar.ts
    - frontend/src/utils/date.ts
  - frontend/src/components/shared/DiscoverSection.vue
    - frontend/src/components/shared/HomeCharacterCard.vue
      - frontend/src/utils/avatar.ts
  - frontend/src/components/shared/SetupPromptBanner.vue
    - frontend/src/composables/useProfiles.ts
      - frontend/src/stores/listStore.ts
      - frontend/src/api/client.ts
  - frontend/src/components/shared/EmptyState.vue
  - frontend/src/composables/useChatSessions.ts
    - frontend/src/composables/useCursorList.ts
    - frontend/src/api/client.ts
  - frontend/src/composables/useCharacters.ts
    - frontend/src/composables/usePaginatedList.ts
    - frontend/src/api/client.ts
  - frontend/src/constants/discoverData.ts

## /chats and /chats/:chatId — Conversation

Entry: `frontend/src/views/chat/ChatView.vue`

- frontend/src/views/chat/ChatView.vue
  - frontend/src/components/chat/ChatSessionList.vue
  - frontend/src/components/chat/ChatHeader.vue
  - frontend/src/components/chat/ChatDrawer.vue
    - frontend/src/components/shared/Tabs.vue
    - frontend/src/components/chat/ChatDrawerCharacterTab.vue
      - frontend/src/components/discover/CollapsibleField.vue
    - frontend/src/components/chat/ChatDrawerSettingsTab.vue
      - frontend/src/components/shared/CollapsibleSection.vue
      - frontend/src/components/shared/AppTooltip.vue
    - frontend/src/components/chat/ChatDrawerSessionTab.vue
    - frontend/src/components/chat/ChatDrawerLogsTab.vue
  - frontend/src/components/chat/MessageBubble.vue
    - frontend/src/components/chat/NarrativeText.vue
    - frontend/src/components/chat/QuillTypingIndicator.vue
  - frontend/src/components/chat/MoodChips.vue
  - frontend/src/components/chat/ReplySuggestions.vue
  - frontend/src/components/chat/ParchmentInput.vue
  - frontend/src/components/shared/EmptyState.vue
  - frontend/src/composables/useChatSessions.ts
  - frontend/src/composables/useChatMessages.ts
  - frontend/src/types/chat.ts
  - frontend/src/utils/avatar.ts
  - frontend/src/utils/route.ts

## /characters — Character Library

Entry: `frontend/src/views/CharactersView.vue`

- frontend/src/views/CharactersView.vue
  - frontend/src/components/layout/PageContainer.vue
  - frontend/src/components/discover/DiscoverHeader.vue
  - frontend/src/components/discover/FilterBar.vue
  - frontend/src/components/discover/CategoryPills.vue
  - frontend/src/components/discover/BulkActionBar.vue
  - frontend/src/components/discover/CharacterCard.vue
    - frontend/src/components/discover/CharacterContextMenu.vue
    - frontend/src/utils/avatar.ts
    - frontend/src/utils/characterPreview.ts
  - frontend/src/components/discover/CharacterListRow.vue
    - frontend/src/components/discover/CharacterContextMenu.vue
    - frontend/src/utils/avatar.ts
    - frontend/src/utils/characterPreview.ts
  - frontend/src/components/shared/EmptyState.vue
  - frontend/src/components/shared/ConfirmModal.vue
    - frontend/src/components/shared/Modal.vue
  - frontend/src/components/profiles/ProfilePickerModal.vue
    - frontend/src/components/shared/Modal.vue
  - frontend/src/composables/useCharacters.ts
  - frontend/src/composables/useCreateChat.ts
  - frontend/src/composables/useLibraryFilters.ts
  - frontend/src/composables/useQueryState.ts
  - frontend/src/constants/discoverData.ts
  - frontend/src/types/discover.ts

## /characters/:id — Character Detail

Entry: `frontend/src/views/CharacterDetailView.vue`

- frontend/src/views/CharacterDetailView.vue
  - frontend/src/components/chat/NarrativeText.vue
  - frontend/src/components/discover/CollapsibleField.vue
  - frontend/src/components/profiles/ProfilePickerModal.vue
    - frontend/src/components/shared/Modal.vue
  - frontend/src/composables/useCreateChat.ts
  - frontend/src/api/client.ts
  - frontend/src/utils/avatar.ts
  - frontend/src/utils/date.ts
  - frontend/src/utils/route.ts

## /characters/create and /characters/:id/edit — Character Creator

Entry: `frontend/src/views/CharacterCreateView.vue`

- frontend/src/views/CharacterCreateView.vue
  - frontend/src/components/creator/CharacterTab.vue
    - frontend/src/components/creator/FormField.vue
    - frontend/src/components/creator/Combobox.vue
    - frontend/src/components/creator/TagInput.vue
    - frontend/src/components/creator/AvatarUpload.vue
    - frontend/src/components/creator/AutoTextarea.vue
      - frontend/src/components/shared/Modal.vue
  - frontend/src/components/creator/BehaviorTab.vue
    - frontend/src/components/creator/FormField.vue
    - frontend/src/components/creator/Combobox.vue
    - frontend/src/components/creator/DialoguePairEditor.vue
    - frontend/src/components/creator/AutoTextarea.vue
  - frontend/src/components/creator/WorldTab.vue
    - frontend/src/components/creator/FormField.vue
    - frontend/src/components/creator/LorebookEntryCard.vue
    - frontend/src/components/creator/AutoTextarea.vue
  - frontend/src/components/creator/CharacterPreview.vue
    - frontend/src/components/chat/NarrativeText.vue
    - frontend/src/components/shared/Modal.vue
  - frontend/src/composables/useCharacterForm.ts
  - frontend/src/constants/creatorData.ts
  - frontend/src/types/creator.ts

## /connections — Connections

Entry: `frontend/src/views/ConnectionsView.vue`

- frontend/src/views/ConnectionsView.vue
  - frontend/src/components/connections/ConnectionsTabs.vue
  - frontend/src/components/connections/ProvidersTab.vue
    - frontend/src/components/connections/ProviderForm.vue
    - frontend/src/components/shared/Modal.vue
  - frontend/src/components/connections/ModelsTab.vue
    - frontend/src/components/connections/ModelCreateModal.vue
      - frontend/src/components/connections/ModelForm.vue
      - frontend/src/components/shared/Modal.vue
    - frontend/src/components/shared/DataTable.vue
      - frontend/src/components/shared/AppPagination.vue
  - frontend/src/components/connections/ModelFamiliesTab.vue
    - frontend/src/components/connections/ModelFamilyForm.vue
    - frontend/src/components/shared/Modal.vue
    - frontend/src/components/shared/DataTable.vue
  - frontend/src/composables/useProviders.ts
  - frontend/src/composables/useModels.ts
  - frontend/src/composables/useModelFamilies.ts
  - frontend/src/assets/icons/*.svg

## /loadouts — Loadouts and Personas

Entry: `frontend/src/views/ProfilesView.vue`

- frontend/src/views/ProfilesView.vue
  - frontend/src/components/profiles/ProfilesTabs.vue
  - frontend/src/components/profiles/ProfilesTab.vue
    - frontend/src/components/profiles/ProfileCard.vue
    - frontend/src/components/profiles/ProfileForm.vue
    - frontend/src/components/shared/EmptyState.vue
    - frontend/src/components/shared/Modal.vue
  - frontend/src/components/profiles/PersonaTab.vue
    - frontend/src/components/shared/Modal.vue
  - frontend/src/components/connections/PresetsTab.vue
    - frontend/src/components/connections/ImportPresetModal.vue
    - frontend/src/components/shared/EmptyState.vue
  - frontend/src/components/connections/TemplatesTab.vue
  - frontend/src/components/connections/FragmentsTab.vue
    - frontend/src/components/shared/DataTable.vue
      - frontend/src/components/shared/AppPagination.vue
  - frontend/src/composables/useProfiles.ts
  - frontend/src/composables/usePersonas.ts
  - frontend/src/composables/usePresets.ts
  - frontend/src/composables/usePromptTemplates.ts
  - frontend/src/composables/usePromptFragments.ts

## /memory — Data Bank

Entry: `frontend/src/views/MemoryView.vue`

- frontend/src/views/MemoryView.vue
  - frontend/src/components/layout/PageContainer.vue
  - frontend/src/components/shared/EmptyState.vue
  - frontend/src/composables/useDataBank.ts
    - frontend/src/composables/useListCrud.ts
    - frontend/src/api/client.ts
  - frontend/src/composables/useRag.ts
  - frontend/src/composables/useConfirmAction.ts
  - frontend/src/composables/useToast.ts

## /lorebooks — Lorebooks

Entry: `frontend/src/views/LorebooksView.vue`

- frontend/src/views/LorebooksView.vue
  - frontend/src/components/layout/PageContainer.vue
  - frontend/src/components/lorebooks/LoreEntryCard.vue
  - frontend/src/components/lorebooks/LoreEntryForm.vue
  - frontend/src/components/shared/EmptyState.vue
  - frontend/src/composables/useLorebooks.ts
  - frontend/src/composables/useConfirmAction.ts
  - frontend/src/composables/useToast.ts

## /settings — Settings

Entry: `frontend/src/views/settings/SettingsView.vue`

- frontend/src/views/settings/SettingsView.vue
  - frontend/src/components/settings/SettingsTabs.vue
  - frontend/src/components/settings/InterfaceTab.vue
    - frontend/src/components/settings/ThemeEditor.vue
    - frontend/src/composables/useTheme.ts
    - frontend/src/composables/useCustomTheme.ts
    - frontend/src/composables/useFontSize.ts
    - frontend/src/composables/useChatWidth.ts
    - frontend/src/constants/colorPresets.ts
  - frontend/src/components/settings/LogsTab.vue
    - frontend/src/components/settings/LogDetailModal.vue
      - frontend/src/components/shared/Modal.vue
  - frontend/src/components/settings/AboutTab.vue
    - frontend/src/constants/appInfo.ts

