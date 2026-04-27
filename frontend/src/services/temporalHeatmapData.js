/**
 * Données pour la carte de chaleur temporelle (12 mois glissants).
 * Les plages sont en heure locale du navigateur ; GLPI reçoit des chaînes « YYYY-MM-DD HH:mm:ss ».
 */

import { computeBranchTicketTotalsByCategoryId } from './treeTransform'

/**
 * Hauteur de cellule (alignée avec TemporalHeatmapChart) pour synchroniser libellés / grille.
 * @param {number} nRows
 */
export function heatmapCellHeight(nRows) {
  return Math.min(32, Math.max(22, 520 / Math.max(1, nRows)))
}

function pad2(n) {
  return String(n).padStart(2, '0')
}

/**
 * Horodatage local au format attendu par les critères search/Ticket (morethan / lessthan).
 * @param {Date} d
 */
export function formatDateTimeLocal(d) {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(
    d.getMinutes()
  )}:${pad2(d.getSeconds())}`
}

/**
 * Fenêtre glissante pour le Sunburst « Tickets » (date d’ouverture / champ détecté GLPI, comme la heatmap).
 * @param {'all'|'90d'|'6m'|'1y'|'2y'|'3y'} preset
 * @returns {{ startStr: string, endStr: string } | null} null = tout l’historique (pas de filtre date)
 */
export function getDateRangeForTicketPeriodPreset(preset) {
  if (preset === 'all' || preset == null || preset === '') {
    return null
  }
  const now = new Date()
  const start = new Date(now)
  if (preset === '90d') {
    start.setDate(start.getDate() - 90)
  } else if (preset === '6m') {
    start.setMonth(start.getMonth() - 6)
  } else if (preset === '1y') {
    start.setFullYear(start.getFullYear() - 1)
  } else if (preset === '2y') {
    start.setFullYear(start.getFullYear() - 2)
  } else if (preset === '3y') {
    start.setFullYear(start.getFullYear() - 3)
  } else {
    return null
  }
  /** fin exclusive : +1 min pour inclure les tickets « maintenant » dans les bornes GLPI */
  const endExclusive = new Date(now.getTime() + 60 * 1000)
  return {
    startStr: formatDateTimeLocal(start),
    endStr: formatDateTimeLocal(endExclusive)
  }
}

/**
 * Retourne les 12 mois complets précédant « maintenant » : du plus ancien au plus récent.
 * Chaque entrée : libellé court, bornes [start, end[ pour filtre API.
 *
 * @returns {Array<{ label: string, startStr: string, endStr: string, year: number, month: number }>}
 */
export function getLast12MonthRanges() {
  const now = new Date()
  const ranges = []

  for (let delta = 11; delta >= 0; delta--) {
    const end = new Date(now.getFullYear(), now.getMonth() - delta + 1, 1, 0, 0, 0)
    const start = new Date(now.getFullYear(), now.getMonth() - delta, 1, 0, 0, 0)
    const label = start.toLocaleDateString('fr-FR', { month: 'short', year: '2-digit' })
    ranges.push({
      label,
      startStr: formatDateTimeLocal(start),
      endStr: formatDateTimeLocal(end),
      year: start.getFullYear(),
      month: start.getMonth() + 1
    })
  }

  return ranges
}

/**
 * À partir de l’arbre des catégories, retourne les identifiants des racines métier
 * (enfants directs du nœud virtuel « root », ou la racine unique).
 *
 * @param {Object} tree — sortie de transformFlatToTree
 * @returns {Array<{ id: number|string, name: string }>}
 */
export function getRootBranchesForHeatmap(tree) {
  if (!tree) return []
  if (tree.id === 'root' && Array.isArray(tree.children) && tree.children.length > 0) {
    return tree.children.map((c) => ({
      id: c.id,
      name: c.name || `Catégorie ${c.id}`
    }))
  }
  return [{ id: tree.id, name: tree.name || `Catégorie ${tree.id}` }]
}

/**
 * Construit la matrice racines × mois : chaque cellule = total tickets de la branche (catégorie + sous-arbres)
 * pour le mois donné (comptages directs par catégorie agrégés ensuite comme le Sunburst « Tickets »).
 *
 * @param {Array} flatCategories — liste plate GLPI
 * @param {Array<{ label: string }>} monthRanges — même longueur et ordre que monthlyDirectCounts
 * @param {Array<Record<number, number>>} monthlyDirectCounts — un objet par mois
 */
export function buildRootBranchMatrix(flatCategories, monthRanges, monthlyDirectCounts, tree) {
  const roots = getRootBranchesForHeatmap(tree)
  const rowLabels = roots.map((r) => r.name)
  const rootIds = roots.map((r) => r.id)
  const columnLabels = monthRanges.map((m) => m.label)

  const values = rootIds.map(() => monthlyDirectCounts.map(() => 0))

  monthlyDirectCounts.forEach((directMap, monthIdx) => {
    const branchTotals = computeBranchTicketTotalsByCategoryId(flatCategories, directMap)
    rootIds.forEach((rid, rowIdx) => {
      const t = branchTotals[rid]
      values[rowIdx][monthIdx] = Number.isFinite(t) && t >= 0 ? t : 0
    })
  })

  return {
    rowLabels,
    columnLabels,
    values,
    rootIds
  }
}

/**
 * Matrice groupes × mois : uniquement les groupes ayant au moins un ticket résolu/fermé
 * sur la fenêtre (somme des 12 mois > 0). Lignes triées par nom (locale fr).
 *
 * @param {Array<{ label: string }>} monthRanges
 * @param {Array<Record<number, number>>} monthlyCountsByGroupId — un objet par mois (id groupe → effectif)
 * @param {Array<{ id: number, name: string }>} groupsList — tous les groupes GLPI considérés pour les requêtes
 * @returns {{ rowLabels: string[], columnLabels: string[], values: number[][], groupIds: number[] }}
 */
export function buildGroupHeatmapMatrix(monthRanges, monthlyCountsByGroupId, groupsList) {
  const columnLabels = monthRanges.map((m) => m.label)
  const idToName = new Map(
    groupsList.map((g) => [Number(g.id), (g.name || `Groupe ${g.id}`).trim() || `Groupe ${g.id}`])
  )
  const allIds = groupsList.map((g) => Number(g.id)).filter((id) => Number.isFinite(id) && id > 0)

  const totals = new Map()
  allIds.forEach((id) => totals.set(id, 0))

  monthlyCountsByGroupId.forEach((monthMap) => {
    allIds.forEach((id) => {
      const v = monthMap[id] ?? monthMap[String(id)] ?? 0
      const n = Number(v)
      totals.set(id, (totals.get(id) || 0) + (Number.isFinite(n) && n > 0 ? n : 0))
    })
  })

  const activeIds = allIds.filter((id) => (totals.get(id) || 0) > 0)
  activeIds.sort((a, b) => {
    const na = idToName.get(a) || ''
    const nb = idToName.get(b) || ''
    return na.localeCompare(nb, 'fr', { sensitivity: 'base' })
  })

  const values = activeIds.map((gid) =>
    monthlyCountsByGroupId.map((monthMap) => {
      const v = monthMap[gid] ?? monthMap[String(gid)] ?? 0
      const n = Number(v)
      return Number.isFinite(n) && n >= 0 ? n : 0
    })
  )

  return {
    rowLabels: activeIds.map((id) => idToName.get(id) || `Groupe ${id}`),
    columnLabels,
    values,
    groupIds: activeIds
  }
}

// ---------------------------------------------------------------------------
// Heatmap hiérarchique (catégories) : lignes repliables sous l’arbre GLPI
// ---------------------------------------------------------------------------

/**
 * Arbre minimal sérialisable pour le cache (id, name, children).
 * @param {object} tree — sortie de transformFlatToTree
 * @returns {object|null}
 */
export function cloneTreeForHeatmapCache(tree) {
  if (!tree) return null
  function walk(node) {
    if (!node || node.__directSlice) return null
    if (node.id === 'root') {
      return {
        id: 'root',
        name: node.name || '',
        children: (node.children || []).map(walk).filter(Boolean)
      }
    }
    const children = (node.children || []).map(walk).filter(Boolean)
    return {
      id: node.id,
      name: node.name || `Catégorie ${node.id}`,
      children
    }
  }
  return walk(tree)
}

/**
 * Racine unique pour le parcours : nœud virtuel `root` ou enveloppe d’une racine unique.
 * @param {object} treeJson — objet issu du cache ou du live
 */
export function getHeatmapTreeRootForWalk(treeJson) {
  if (!treeJson) return null
  if (treeJson.id === 'root' && Array.isArray(treeJson.children)) return treeJson
  return { id: 'root', name: '', children: [treeJson] }
}

/**
 * Lignes visibles en profondeur d’abord : racines toujours ; enfants si parent dans `expandedIds`.
 *
 * @param {object} treeRoot — retour de getHeatmapTreeRootForWalk
 * @param {Set<number|string>|Iterable<number|string>} expandedIds
 * @param {Array<number|string>|null} rootOrder — ordre des racines métier (ids). Si fourni (ex. issu
 *   du tri « volume total »), on conserve cet ordre au dépliage pour éviter qu’une racine « saute »
 *   en revenant à l’ordre brut de l’arbre GLPI. Les ids manquants sont ajoutés à la fin (ordre arbre).
 * @returns {Array<{ id: number|string, name: string, depth: number, hasChildren: boolean }>}
 */
export function getVisibleHeatmapRows(treeRoot, expandedIds, rootOrder = null) {
  const rows = []
  const exp = expandedIds instanceof Set ? expandedIds : new Set(expandedIds || [])

  function walk(node, depth) {
    if (!node) return
    if (node.id === 'root') {
      const ch = node.children || []
      const usable = ch.filter((c) => c && !c.__directSlice)
      const byId = new Map(usable.map((n) => [n.id, n]))

      let ordered = usable
      if (Array.isArray(rootOrder) && rootOrder.length > 0) {
        const seen = new Set()
        const out = []
        for (const rid of rootOrder) {
          if (byId.has(rid)) {
            out.push(byId.get(rid))
            seen.add(rid)
          }
        }
        for (const c of usable) {
          if (!seen.has(c.id)) out.push(c)
        }
        ordered = out
      }

      ordered.forEach((c) => walk(c, 0))
      return
    }
    if (node.__directSlice) return

    const hasCh = Array.isArray(node.children) && node.children.length > 0
    rows.push({
      id: node.id,
      name: node.name || `Catégorie ${node.id}`,
      depth,
      hasChildren: hasCh
    })
    if (hasCh && exp.has(node.id)) {
      node.children.forEach((c) => walk(c, depth + 1))
    }
  }

  walk(treeRoot, 0)
  return rows
}

/**
 * Matrice affichée : une ligne par nœud visible, cellule = total branche (comme avant pour une racine).
 *
 * @param {Array} flatCategories
 * @param {Array<Record<number, number>>} monthlyDirectCounts
 * @param {string[]} columnLabels
 * @param {object} treeRoot
 * @param {Set<number|string>} expandedIds
 * @param {Array<number|string>|null} rootOrder — voir {@link getVisibleHeatmapRows}
 */
export function buildVisibleCategoryHeatmapMatrix(
  flatCategories,
  monthlyDirectCounts,
  columnLabels,
  treeRoot,
  expandedIds,
  rootOrder = null
) {
  const rows = getVisibleHeatmapRows(treeRoot, expandedIds, rootOrder)
  const nM = monthlyDirectCounts.length
  const values = rows.map(() => new Array(nM).fill(0))

  for (let m = 0; m < nM; m++) {
    const direct = monthlyDirectCounts[m] || {}
    const branchTotals = computeBranchTicketTotalsByCategoryId(flatCategories, direct)
    rows.forEach((row, ri) => {
      const t = branchTotals[row.id]
      values[ri][m] = Number.isFinite(t) && t >= 0 ? t : 0
    })
  }

  return {
    rowLabels: rows.map((r) => r.name),
    columnLabels,
    values,
    rootIds: rows.map((r) => r.id),
    heatmapRowsMeta: rows
  }
}
