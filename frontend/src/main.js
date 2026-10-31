import { createApp } from 'vue'
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import App from './App.vue'

const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'jarvisDark',
    themes: {
      jarvisDark: {
        dark: true,
        colors: {
          background: '#0b1119',
          surface: '#111e29',
          primary: '#008f8f',
          secondary: '#8ca4ae'
        }
      }
    }
  }
})

createApp(App).use(vuetify).mount('#app')
