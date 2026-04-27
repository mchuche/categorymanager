/**
 * Tri des lignes des cartes de chaleur (catégories racines ou groupes × mois).
 * La matrice source n’est pas modifiée : on retourne une copie avec lignes réordonnées.
 */

/** @typedef {'source'|'total_desc'|'month_desc'|'alpha_asc'} HeatmapSortMode */

export const HEATMAP_SORT = {
  SOURCE: 'source',
  TOTAL_DESC: 'total_desc',
  MONTH_DESC: 'month_desc',
  ALPHA_ASC: 'alpha_asc'
}

/** Options affichées pour l’onglet heatmap « racines métier » */
export const HEATMAP_SORT_OPTIONS_CATEGORIES = [
  { value: HEATMAP_SORT.SOURCE, label: 'Ordre arbre (racines métier)' },
  { value: HEATMAP_SORT.TOTAL_DESC, label: 'Volume total sur 12 mois (↓)' },
  { value: HEATMAP_SORT.MONTH_DESC, label: 'Volume du mois affiché (↓)' },
  { value: HEATMAP_SORT.ALPHA_ASC, label: 'Nom (A → Z)' }
]

/** Options affichées pour l’onglet heatmap « groupes » */
export const HEATMAP_SORT_OPTIONS_GROUPS = [
  { value: HEATMAP_SORT.SOURCE, label: 'Ordre chargement (défaut)' },
  { value: HEATMAP_SORT.TOTAL_DESC, label: 'Volume total sur 12 mois (↓)' },
  { value: HEATMAP_SORT.MONTH_DESC, label: 'Volume du mois affiché (↓)' },
  { value: HEATMAP_SORT.ALPHA_ASC, label: 'Nom (A → Z)' }
]

/**
 * Somme des cellules d’une ligne.
 * @param {number[][]} values
 * @param {number} rowIdx
 */
function rowTotal(values, rowIdx) {
  const row = values[rowIdx]
  if (!row || !row.length) return 0
  return row.reduce((acc, v) => acc + (Number.isFinite(Number(v)) ? Number(v) : 0), 0)
}

/**
 * Compare deux libellés de ligne (tie-break).
 * @param {string} a
 * @param {string} b
 */
function labelCompare(a, b) {
  return String(a).localeCompare(String(b), 'fr', { sensitivity: 'base' })
}

/**
 * Réordonne les lignes d’une matrice heatmap selon le mode.
 *
 * @param {{ rowLabels: string[], columnLabels: string[], values: number[][], rootIds?: unknown[], groupIds?: number[], heatmapRowsMeta?: unknown[] } | null} matrix
 * @param {HeatmapSortMode} mode
 * @param {number} selectedMonthIndex — index colonne pour MONTH_DESC (curseur mois)
 * @returns {typeof matrix}
 */
export function sortHeatmapMatrix(matrix, mode, selectedMonthIndex) {
  if (!matrix || !matrix.rowLabels?.length || !matrix.values?.length) {
    return matrix
  }

  if (mode === HEATMAP_SORT.SOURCE) {
    return matrix
  }

  const nRows = matrix.rowLabels.length
  const nCols = matrix.columnLabels?.length ?? 0
  const mi = Math.min(Math.max(0, Math.floor(Number(selectedMonthIndex) || 0)), Math.max(0, nCols - 1))

  const indices = Array.from({ length: nRows }, (_, i) => i)
  const vals = matrix.values

  if (mode === HEATMAP_SORT.TOTAL_DESC) {
    indices.sort((a, b) => {
      const ta = rowTotal(vals, a)
      const tb = rowTotal(vals, b)
      if (tb !== ta) return tb - ta
      return labelCompare(matrix.rowLabels[a], matrix.rowLabels[b])
    })
  } else if (mode === HEATMAP_SORT.MONTH_DESC) {
    indices.sort((a, b) => {
      const va = Number(vals[a]?.[mi]) || 0
      const vb = Number(vals[b]?.[mi]) || 0
      if (vb !== va) return vb - va
      return labelCompare(matrix.rowLabels[a], matrix.rowLabels[b])
    })
  } else if (mode === HEATMAP_SORT.ALPHA_ASC) {
    indices.sort((a, b) => labelCompare(matrix.rowLabels[a], matrix.rowLabels[b]))
  } else {
    return matrix
  }

  const rowLabels = indices.map((i) => matrix.rowLabels[i])
  const values = indices.map((i) => [...matrix.values[i]])

  const out = {
    ...matrix,
    rowLabels,
    values
  }

  if (Array.isArray(matrix.rootIds) && matrix.rootIds.length === nRows) {
    out.rootIds = indices.map((i) => matrix.rootIds[i])
  }
  if (Array.isArray(matrix.groupIds) && matrix.groupIds.length === nRows) {
    out.groupIds = indices.map((i) => matrix.groupIds[i])
  }
  if (Array.isArray(matrix.heatmapRowsMeta) && matrix.heatmapRowsMeta.length === nRows) {
    out.heatmapRowsMeta = indices.map((i) => matrix.heatmapRowsMeta[i])
  }

  return out
}
