/**
 * Tri des lignes des cartes de chaleur (catégories racines ou groupes × mois).
 */

/** @typedef {'source'|'total_desc'|'month_desc'|'alpha_asc'} HeatmapSortMode */

export const HEATMAP_SORT = {
  SOURCE: 'source',
  TOTAL_DESC: 'total_desc',
  MONTH_DESC: 'month_desc',
  ALPHA_ASC: 'alpha_asc'
}

/**
 * @param {(k: string) => string} t — ex. cmT depuis i18n.js
 * @returns {Array<{ value: string, label: string }>}
 */
export function getHeatmapSortOptionsCategories(t) {
  return [
    { value: HEATMAP_SORT.SOURCE, label: t('heatmap_sort_source_cat') },
    { value: HEATMAP_SORT.TOTAL_DESC, label: t('heatmap_sort_total_desc') },
    { value: HEATMAP_SORT.MONTH_DESC, label: t('heatmap_sort_month_desc') },
    { value: HEATMAP_SORT.ALPHA_ASC, label: t('heatmap_sort_alpha') }
  ]
}

/**
 * @param {(k: string) => string} t
 * @returns {Array<{ value: string, label: string }>}
 */
export function getHeatmapSortOptionsGroups(t) {
  return [
    { value: HEATMAP_SORT.SOURCE, label: t('heatmap_sort_source_grp') },
    { value: HEATMAP_SORT.TOTAL_DESC, label: t('heatmap_sort_total_desc') },
    { value: HEATMAP_SORT.MONTH_DESC, label: t('heatmap_sort_month_desc') },
    { value: HEATMAP_SORT.ALPHA_ASC, label: t('heatmap_sort_alpha') }
  ]
}

function rowTotal(values, rowIdx) {
  const row = values[rowIdx]
  if (!row || !row.length) return 0
  return row.reduce((acc, v) => acc + (Number.isFinite(Number(v)) ? Number(v) : 0), 0)
}

function labelCompare(a, b, locale) {
  const loc = locale || (typeof navigator !== 'undefined' ? navigator.language : 'en')
  return String(a).localeCompare(String(b), loc, { sensitivity: 'base' })
}

/**
 * @param {{ rowLabels: string[], columnLabels: string[], values: number[][], rootIds?: unknown[], groupIds?: number[], heatmapRowsMeta?: unknown[] } | null} matrix
 * @param {HeatmapSortMode} mode
 * @param {number} selectedMonthIndex
 * @param {string} [locale]
 */
export function sortHeatmapMatrix(matrix, mode, selectedMonthIndex, locale = undefined) {
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
      return labelCompare(matrix.rowLabels[a], matrix.rowLabels[b], locale)
    })
  } else if (mode === HEATMAP_SORT.MONTH_DESC) {
    indices.sort((a, b) => {
      const va = vals[a]?.[mi]
      const vb = vals[b]?.[mi]
      const na = Number.isFinite(Number(va)) ? Number(va) : 0
      const nb = Number.isFinite(Number(vb)) ? Number(vb) : 0
      if (nb !== na) return nb - na
      return labelCompare(matrix.rowLabels[a], matrix.rowLabels[b], locale)
    })
  } else if (mode === HEATMAP_SORT.ALPHA_ASC) {
    indices.sort((a, b) =>
      labelCompare(matrix.rowLabels[a], matrix.rowLabels[b], locale)
    )
  }

  const newRowLabels = indices.map((i) => matrix.rowLabels[i])
  const newValues = indices.map((i) => vals[i])
  const meta = matrix.heatmapRowsMeta
  const newMeta = meta ? indices.map((i) => meta[i]) : undefined

  const out = {
    ...matrix,
    rowLabels: newRowLabels,
    values: newValues
  }
  if (newMeta) {
    out.heatmapRowsMeta = newMeta
  }
  return out
}
