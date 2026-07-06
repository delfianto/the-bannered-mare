import { defineConfig } from 'vitepress'
import { architectureSidebar } from './sidebar.architecture'
import { guideSidebar } from './sidebar.guide'

export default defineConfig({
  title: 'The Bannered Mare',
  description:
    'Documentation for The Bannered Mare — an AI-powered platform for local roleplay sessions.',
  base: '/the-bannered-mare/',
  srcExclude: ['superpowers/**'],
  themeConfig: {
    search: { provider: 'local' },
    nav: [
      { text: 'Guide', link: '/guide/' },
      { text: 'Architecture', link: '/architecture/' },
    ],
    sidebar: {
      '/guide/': guideSidebar,
      '/architecture/': architectureSidebar,
    },
    socialLinks: [
      { icon: 'github', link: 'https://github.com/delfianto/the-bannered-mare' },
    ],
  },
})
