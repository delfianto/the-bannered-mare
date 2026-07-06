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

export const sillytavernSidebar: DefaultTheme.SidebarItem[] = [
  { text: 'Overview', link: '/sillytavern/' },
  {
    text: 'Analysis',
    collapsed: false,
    items: topics.map(([slug, label]) => ({ text: label, link: `/sillytavern/analysis/${slug}` })),
  },
  {
    text: 'Comparison',
    collapsed: false,
    items: topics.map(([slug, label]) => ({ text: label, link: `/sillytavern/comparison/${slug}` })),
  },
]
