import type { DefaultTheme } from 'vitepress'

export const architectureSidebar: DefaultTheme.SidebarItem[] = [
  { text: 'Overview', link: '/architecture/' },
  {
    text: 'Backend',
    collapsed: false,
    items: [
      { text: 'Project Structure', link: '/architecture/backend/project-structure' },
      { text: 'Data Model', link: '/architecture/backend/data-model' },
      { text: 'Persistence Layer', link: '/architecture/backend/persistence' },
      { text: 'LLM Integration', link: '/architecture/backend/llm-integration' },
      { text: 'Prompt System', link: '/architecture/backend/prompt-system' },
      { text: 'Characters & Personas', link: '/architecture/backend/characters-and-personas' },
    ],
  },
  {
    text: 'Frontend',
    collapsed: false,
    items: [
      { text: 'Project Structure', link: '/architecture/frontend/project-structure' },
      { text: 'Design System', link: '/architecture/frontend/design-system' },
      { text: 'Main Screens', link: '/architecture/frontend/main-screens' },
      { text: 'Core Components', link: '/architecture/frontend/core-components' },
      { text: 'LLM Harness', link: '/architecture/frontend/llm-harness' },
      { text: 'Mock Harness', link: '/architecture/frontend/mock-harness' },
      { text: 'Backend Connection', link: '/architecture/frontend/backend-connection' },
      { text: 'State & Localization', link: '/architecture/frontend/state-and-localization' },
    ],
  },
]
