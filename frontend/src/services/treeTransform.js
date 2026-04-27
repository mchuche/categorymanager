/**
 * Service de transformation de données
 * Convertit une liste plate de catégories en structure arborescente (tree)
 * pour la visualisation Sunburst avec D3.js
 */

/**
 * Transforme une liste plate de catégories en structure arborescente
 * @param {Array} flatCategories - Liste plate des catégories depuis l'API GLPI
 * @param {Object} ticketCounts - Objet avec les compteurs de tickets par catégorie ID
 * @returns {Object} Structure arborescente avec propriété 'children' pour D3.js
 */
export function transformFlatToTree(flatCategories, ticketCounts = {}) {
  // Créer un Map pour accéder rapidement aux catégories par ID
  const categoryMap = new Map()
  
  // Étape 1 : Créer un objet pour chaque catégorie avec sa structure de base
  flatCategories.forEach(category => {
    const categoryId = category.id
    // Toujours un nombre : sinon l’addition récursive peut concaténer des chaînes ("5"+"10"="510")
    // et d3.partition reçoit des valeurs invalides → cercle incomplet sur le sunburst « tickets ».
    const rawCount = ticketCounts[categoryId]
    const ticketCount = Number(rawCount)
    const safeTicketCount = Number.isFinite(ticketCount) && ticketCount >= 0 ? ticketCount : 0

    categoryMap.set(categoryId, {
      id: categoryId,
      name: category.name || `Catégorie ${categoryId}`,
      // Compteur de tickets pour cette catégorie uniquement (sans les sous-catégories)
      ticketCount: safeTicketCount,
      // Compteur total (catégorie + sous-catégories) sera calculé après
      totalTicketCount: ticketCount,
      // Référence au parent pour la construction de l'arbre
      parentId: category.itilcategories_id || null,
      // Tableau des enfants (sera rempli à l'étape 2)
      children: []
    })
  })

  // Étape 2 : Construire la hiérarchie en reliant les enfants aux parents
  const rootNodes = []
  
  categoryMap.forEach((category, categoryId) => {
    const parentId = category.parentId

    if (parentId && categoryMap.has(parentId)) {
      // Cette catégorie a un parent, l'ajouter comme enfant du parent
      const parent = categoryMap.get(parentId)
      parent.children.push(category)
    } else {
      // Cette catégorie n'a pas de parent (ou le parent n'existe pas), c'est une racine
      rootNodes.push(category)
    }
  })

  // Étape 3 : Calculer les compteurs totaux récursivement (catégorie + toutes les sous-catégories)
  function calculateTotalCounts(node) {
    let total = Number(node.ticketCount)
    if (!Number.isFinite(total) || total < 0) total = 0

    if (node.children && node.children.length > 0) {
      node.children.forEach(child => {
        calculateTotalCounts(child)
        const c = Number(child.totalTicketCount)
        total += Number.isFinite(c) && c >= 0 ? c : 0
      })
    }

    node.totalTicketCount = total
  }

  // Calculer les totaux pour tous les nœuds racine
  rootNodes.forEach(root => {
    calculateTotalCounts(root)
  })

  // Étape 4 : Créer la structure racine pour D3.js Sunburst
  // D3.js Sunburst attend un objet racine avec des enfants
  if (rootNodes.length === 1) {
    // Si une seule racine, la retourner directement
    return rootNodes[0]
  } else if (rootNodes.length > 1) {
    // Si plusieurs racines, créer un nœud racine virtuel
    return {
      id: 'root',
      name: 'Toutes les catégories',
      ticketCount: 0,
      totalTicketCount: rootNodes.reduce(
        (sum, node) => sum + (Number(node.totalTicketCount) || 0),
        0
      ),
      children: rootNodes
    }
  } else {
    // Aucune catégorie trouvée
    return {
      id: 'root',
      name: 'Aucune catégorie',
      ticketCount: 0,
      totalTicketCount: 0,
      children: []
    }
  }
}

/**
 * Aplatit une structure arborescente en liste pour faciliter certaines opérations
 * @param {Object} treeNode - Nœud de l'arbre
 * @returns {Array} Liste plate de tous les nœuds
 */
export function flattenTree(treeNode) {
  const result = [treeNode]
  
  if (treeNode.children && treeNode.children.length > 0) {
    treeNode.children.forEach(child => {
      result.push(...flattenTree(child))
    })
  }
  
  return result
}

/**
 * Sunburst « tickets » : pour chaque nœud qui a à la fois des enfants ET des tickets directs sur la
 * catégorie GLPI (sans les sous-catégories), on ajoute une feuille synthétique. Sinon la partition
 * ne répartit l’angle qu’entre les sous-arbres — les tickets « restés » sur le parent n’étaient pas
 * comptés dans l’angle. Ces nœuds (`__directSlice`) ne sont pas dessinés : ils réservent seulement
 * l’angle (espaces vides entre les vraies catégories).
 *
 * @param {Object} root — Racine retournée par transformFlatToTree (non clonée : sera mutée)
 */
export function addDirectTicketLeavesForSunburst(root) {
  if (!root) return

  function walk(node) {
    if (!node.children || node.children.length === 0) return
    node.children.forEach(walk)

    const direct = Number(node.ticketCount)
    if (!Number.isFinite(direct) || direct <= 0) return

    const synthetic = {
      id: `__direct__${node.id}`,
      name: 'Hors sous-catégories',
      ticketCount: direct,
      totalTicketCount: direct,
      children: [],
      __directSlice: true
    }
    node.children = [...node.children, synthetic]
  }

  walk(root)
}

/**
 * Pour chaque catégorie, total de tickets sur la branche (cette catégorie + toutes les sous-catégories).
 * Même agrégation que pour le Sunburst « tickets » (`totalTicketCount` sur l’arbre).
 *
 * @param {Array} flatCategories - Liste plate (avec au moins id, itilcategories_id)
 * @param {Object} ticketCounts - { [categoryId]: nombre de tickets directs }
 * @returns {Record<number|string, number>} total par id de catégorie
 */
export function computeBranchTicketTotalsByCategoryId(flatCategories, ticketCounts = {}) {
  const tree = transformFlatToTree(flatCategories, ticketCounts)
  const nodes = flattenTree(tree)
  const out = {}
  for (const node of nodes) {
    if (node.id != null && node.id !== 'root') {
      const t = Number(node.totalTicketCount)
      out[node.id] = Number.isFinite(t) && t >= 0 ? t : 0
    }
  }
  return out
}
