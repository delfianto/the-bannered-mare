import { defineConfig } from 'vitepress'

// Sidebar modules are registered by later tasks:
//   import { guideSidebar } from './sidebar.guide'
//   import { architectureSidebar } from './sidebar.architecture'
//   import { providersSidebar } from './sidebar.providers'
//   import { sillytavernSidebar } from './sidebar.sillytavern'

export default defineConfig({
  title: 'The Bannered Mare',
  description:
    'Documentation for The Bannered Mare — an AI-powered platform for local roleplay sessions.',
  base: '/the-bannered-mare/',
  srcExclude: ['superpowers/**'],
  themeConfig: {
    search: { provider: 'local' },
    nav: [{ text: 'Guide', link: '/guide/' }],
    sidebar: {},
    socialLinks: [
      { icon: 'github', link: 'https://github.com/delfianto/the-bannered-mare' },
    ],
  },
})
