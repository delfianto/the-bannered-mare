import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import { useRoute } from 'vitepress'
import { nextTick, onMounted, watch } from 'vue'
import Figure from './Figure.vue'
import { wireLightbox } from './lightbox'
import './custom.css'

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    // Global so markdown can author `<Figure>…</Figure>` without imports.
    app.component('Figure', Figure)
  },
  setup() {
    // VitePress is an SPA: wire the diagram lightbox on first mount and after
    // every navigation, once the new page's DOM has been rendered.
    const route = useRoute()
    onMounted(() => {
      wireLightbox()
      watch(
        () => route.path,
        () => nextTick(wireLightbox)
      )
    })
  },
} satisfies Theme
