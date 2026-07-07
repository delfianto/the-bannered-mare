import type { DefaultTheme } from 'vitepress'

// Getting Started is a single flowing document; the sidebar links to its
// in-page sections so a long page stays navigable.
export const guideSidebar: DefaultTheme.SidebarItem[] = [
  {
    text: 'Getting Started',
    items: [
      { text: "What you'll need", link: '/guide/#what-you-ll-need' },
      { text: 'Standing up the backend', link: '/guide/#standing-up-the-backend' },
      { text: 'Standing up the frontend', link: '/guide/#standing-up-the-frontend' },
      { text: 'Running both halves', link: '/guide/#running-both-halves' },
      { text: 'Keeping the API contract in sync', link: '/guide/#keeping-the-api-contract-in-sync' },
      { text: 'Where to go next', link: '/guide/#where-to-go-next' },
    ],
  },
]
