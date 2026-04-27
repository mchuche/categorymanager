import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'url'
import { resolve, dirname } from 'path'

// Répertoire du fichier de config (évite les chemins relatifs ambigus)
const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// Sortie du build : racine du plugin GLPI (public/ servi sous /plugins/categorymanager/public/)
// frontend/ est à la racine du plugin → un seul niveau au-dessus pour atteindre public/
const pluginPublicDir = resolve(__dirname, '../public')

export default defineConfig({
  plugins: [vue()],

  // Préfixe des URLs des assets en production (doit correspondre à l’URL Apache/GLPI)
  base: '/plugins/categorymanager/public/',

  build: {
    outDir: pluginPublicDir,
    emptyOutDir: true,
  },

  preview: {
    port: 4174,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },

  server: {
    port: 5174,
    open: true,
    // Dev : proxy vers le backend FastAPI (jetons GLPI côté serveur)
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
