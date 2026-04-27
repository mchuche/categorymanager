<template>
  <div class="tree-node" :style="{ paddingLeft: level * 20 + 'px' }">
    <!-- Ligne de la catégorie -->
    <div class="tree-node-line" :class="{ 'is-root': level === 0 }">
      <!-- Indicateur visuel de la hiérarchie -->
      <span class="tree-indicator">
        <span v-if="hasChildren" class="tree-toggle" @click="toggleExpanded">
          {{ isExpanded ? '▼' : '▶' }}
        </span>
        <span v-else class="tree-leaf">•</span>
      </span>
      
      <!-- Nom de la catégorie -->
      <span class="tree-node-name" :class="{ 'tree-root': level === 0 }">
        <strong v-if="level === 0">{{ node.name || `Catégorie ${node.id}` }}</strong>
        <span v-else>{{ node.name || `Catégorie ${node.id}` }}</span>
        <span class="tree-node-id">(ID: {{ node.id }})</span>
        <span v-if="node.ticketCount !== undefined" class="tree-node-tickets">
          • {{ node.ticketCount }} ticket(s)
        </span>
      </span>
    </div>
    
    <!-- Enfants (affichés si la catégorie est expandée) -->
    <div v-if="hasChildren && isExpanded" class="tree-children">
      <CategoryTreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :level="level + 1"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

/**
 * Composant récursif pour afficher un nœud de l'arbre des catégories
 * Affiche la catégorie et ses enfants de manière hiérarchique
 */
const props = defineProps({
  node: {
    type: Object,
    required: true
  },
  level: {
    type: Number,
    default: 0
  }
})

// Extraire les props pour les utiliser dans le template
// Dans Vue 3 avec <script setup>, les props sont automatiquement disponibles
// mais on peut aussi les extraire explicitement
const { node, level } = props

// État pour gérer l'expansion/réduction des nœuds
const isExpanded = ref(level < 2) // Par défaut, expander les 2 premiers niveaux

// Vérifier si ce nœud a des enfants
const hasChildren = computed(() => {
  return node.children && node.children.length > 0
})

/**
 * Bascule l'état d'expansion du nœud
 */
function toggleExpanded() {
  isExpanded.value = !isExpanded.value
}
</script>

<style scoped>
.tree-node {
  margin: 4px 0;
  user-select: none;
}

.tree-node-line {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.tree-node-line:hover {
  background-color: var(--app-tree-hover);
}

.tree-node-line.is-root {
  font-weight: 600;
  background-color: var(--app-tree-root-bg);
  border-left: 3px solid var(--app-primary);
  padding-left: 12px;
}

.tree-indicator {
  display: inline-block;
  width: 20px;
  text-align: center;
  color: var(--app-text-soft);
  font-size: 0.85rem;
}

.tree-toggle {
  cursor: pointer;
  color: var(--app-primary);
  font-weight: bold;
  transition: transform 0.2s;
}

.tree-toggle:hover {
  color: var(--app-primary-hover);
}

.tree-leaf {
  color: var(--app-tree-leaf-dot);
}

.tree-node-name {
  flex: 1;
  color: var(--app-text);
}

.tree-node-name.tree-root {
  color: var(--app-primary);
}

.tree-node-id {
  color: var(--app-text-soft);
  font-size: 0.85rem;
  margin-left: 8px;
  font-weight: normal;
}

.tree-node-tickets {
  color: var(--app-success);
  font-size: 0.85rem;
  margin-left: 8px;
  font-weight: 500;
}

.tree-children {
  margin-left: 0;
  border-left: 1px dashed var(--app-border);
  margin-left: 10px;
  padding-left: 10px;
}
</style>
