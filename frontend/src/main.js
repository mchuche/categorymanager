import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import './styles/theme.css'
import { initThemeBeforeApp, useThemeStore } from './stores/theme.js'

// Thème avant le premier rendu : évite un flash du mode clair si l’utilisateur préfère le sombre
initThemeBeforeApp()

// Création de l'application Vue avec Pinia pour la gestion d'état
const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
// Aligner le store Pinia avec le document (libellé correct du bouton thème au premier rendu)
useThemeStore().init()
app.mount('#app')
