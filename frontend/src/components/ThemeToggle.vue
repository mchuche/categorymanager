<template>
  <!--
    Bascule clair / sombre : icône seule (soleil / lune), libellé pour l’accessibilité.
    Style global .theme-toolbar-btn (theme.css) pour alignement avec plein écran.
  -->
  <button
    type="button"
    class="theme-toolbar-btn"
    :aria-pressed="themeStore.isDark"
    :aria-label="themeStore.isDark ? 'Passer en mode clair' : 'Passer en mode sombre'"
    :title="themeStore.isDark ? 'Passer en mode clair' : 'Passer en mode sombre'"
    @click="themeStore.toggle()"
  >
    <ToolbarIcon :name="themeStore.isDark ? 'sun' : 'moon'" />
    <span class="sr-only">{{ themeStore.isDark ? 'Passer en mode clair' : 'Passer en mode sombre' }}</span>
  </button>
</template>

<script setup>
import { useThemeStore } from '../stores/theme'
import ToolbarIcon from './ToolbarIcon.vue'

const themeStore = useThemeStore()
</script>
