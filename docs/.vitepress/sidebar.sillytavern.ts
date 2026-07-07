import type { DefaultTheme } from 'vitepress'

const topics: [slug: string, label: string][] = [
  ['code-structure', 'Code Structure'],
  ['prompting', 'Prompting'],
  ['providers', 'Providers'],
  ['streaming', 'Streaming'],
  ['character-cards', 'Character Cards'],
  ['world-lore', 'World / Lore'],
  ['chat-system', 'Chat System'],
  ['rag', 'RAG'],
  ['slash-commands', 'Slash Commands'],
  ['tool-calling', 'Tool Calling'],
  ['extensions', 'Extensions'],
  ['tags-stats-data', 'Tags / Stats / Data'],
  ['presets', 'Presets'],
]

// The per-topic Comparison pages are the study's entry points. Each links into a
// deep SillyTavern Analysis page (kept as a reference archive, reachable via those
// links but intentionally not listed in the nav).
export const sillytavernSidebar: DefaultTheme.SidebarItem[] = [
  { text: 'Overview', link: '/sillytavern/' },
  {
    text: 'Topics',
    collapsed: false,
    items: topics.map(([slug, label]) => ({
      text: label,
      link: `/sillytavern/comparison/${slug}`,
    })),
  },
]
