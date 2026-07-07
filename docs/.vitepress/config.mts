import { defineConfig } from 'vitepress'
import { apiSidebar } from './sidebar.api'
import { architectureSidebar } from './sidebar.architecture'
import { guideSidebar } from './sidebar.guide'
import { providersSidebar } from './sidebar.providers'
import { sillytavernSidebar } from './sidebar.sillytavern'

export default defineConfig({
  title: 'The Bannered Mare',
  description:
    'Technical reference for The Bannered Mare — a self-hostable, AI-powered platform for local roleplay sessions.',
  base: '/the-bannered-mare/',
  srcExclude: ['superpowers/**'],
  markdown: {
    // Escape Vue interpolation syntax ({{ }}) inside inline code spans so that
    // ST macro literals like `{{pipe}}` are not processed as Vue template
    // expressions by the compiler.
    config(md) {
      const defaultCodeInline = md.renderer.rules.code_inline!
      md.renderer.rules.code_inline = function (...args) {
        const html = defaultCodeInline(...args)
        return html.replace(/\{\{/g, '&#123;&#123;').replace(/\}\}/g, '&#125;&#125;')
      }
    },
  },
  themeConfig: {
    search: { provider: 'local' },
    nav: [
      { text: 'Getting Started', link: '/guide/' },
      { text: 'Architecture', link: '/architecture/' },
      { text: 'API Reference', link: '/api/' },
      { text: 'LLM Providers', link: '/providers/' },
      { text: 'SillyTavern Study', link: '/sillytavern/' },
    ],
    sidebar: {
      '/guide/': guideSidebar,
      '/architecture/': architectureSidebar,
      '/api/': apiSidebar,
      '/providers/': providersSidebar,
      '/sillytavern/': sillytavernSidebar,
    },
    socialLinks: [
      { icon: 'github', link: 'https://github.com/delfianto/the-bannered-mare' },
    ],
  },
})
