<template>
  <!--
    Icônes SVG harmonisées (trait 2px, bouts ronds) pour la barre d’actions (thème, plein écran).
    Couleur = currentColor pour hériter du bouton parent.
  -->
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    class="toolbar-icon"
    aria-hidden="true"
    focusable="false"
  >
    <!-- Lune : passer en mode sombre -->
    <g v-if="name === 'moon'">
      <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
    </g>
    <!-- Soleil : passer en mode clair -->
    <g v-else-if="name === 'sun'">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
    </g>
    <!-- Entrée plein écran -->
    <g v-else-if="name === 'maximize'">
      <polyline points="15 3 21 3 21 9" />
      <polyline points="9 21 3 21 3 15" />
      <line x1="21" y1="3" x2="14" y2="10" />
      <line x1="3" y1="21" x2="10" y2="14" />
    </g>
    <!-- Sortie plein écran -->
    <g v-else-if="name === 'minimize'">
      <polyline points="4 14 10 14 10 20" />
      <polyline points="20 10 14 10 14 4" />
      <line x1="14" y1="10" x2="21" y2="3" />
      <line x1="3" y1="21" x2="10" y2="14" />
    </g>
  </svg>
</template>

<script setup>
/**
 * @typedef {'moon'|'sun'|'maximize'|'minimize'} ToolbarIconName
 */

defineProps({
  /** Identifiant du glyphe à afficher */
  name: {
    type: String,
    required: true,
    validator: (v) => ['moon', 'sun', 'maximize', 'minimize'].includes(v)
  }
})
</script>

<style scoped>
.toolbar-icon {
  display: block;
  width: 22px;
  height: 22px;
  flex-shrink: 0;
}
</style>
