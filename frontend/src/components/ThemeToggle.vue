<template>
  <!--
    Bascule clair / sombre : icône seule (soleil / lune), libellé pour l’accessibilité.
    Style global .theme-toolbar-btn (theme.css) pour alignement avec plein écran.
  -->
  <button
    type="button"
    class="theme-toolbar-btn"
    :aria-pressed="themeStore.isDark"
    :aria-label="themeStore.isDark ? t('theme_light') : t('theme_dark')"
    :title="themeStore.isDark ? t('theme_light') : t('theme_dark')"
    @click="themeStore.toggle()"
  >
    <ToolbarIcon :name="themeStore.isDark ? 'sun' : 'moon'" />
    <span class="sr-only">{{ themeStore.isDark ? t('theme_light') : t('theme_dark') }}</span>
  </button>
</template>

<script setup>
import { useThemeStore } from '../stores/theme'
import { cmT as t } from '../i18n'
import ToolbarIcon from './ToolbarIcon.vue'

const themeStore = useThemeStore()
</script>
