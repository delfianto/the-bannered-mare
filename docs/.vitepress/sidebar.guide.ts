import type { DefaultTheme } from 'vitepress'

export const guideSidebar: DefaultTheme.SidebarItem[] = [
  { text: 'Introduction', link: '/guide/' },
  { text: 'Quick Start', link: '/guide/quick-start' },
  {
    text: 'Setup',
    items: [
      { text: 'Backend', link: '/guide/setup-backend' },
      { text: 'Frontend', link: '/guide/setup-frontend' },
    ],
  },
]
