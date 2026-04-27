<template>
  <!--
    Carte de chaleur : racines métier × 12 mois. Slider + lecture automatique pour parcourir le temps.
    Les couleurs suivent l’intensité (échelle séquentielle D3).
  -->
  <div class="heatmap-wrap">
    <div class="heatmap-toolbar">
      <label class="heatmap-slider-label" :for="sliderInputId">
        Mois affiché (surbrillance) :
        <span class="heatmap-slider-value">{{ currentMonthLabel }}</span>
      </label>
      <input
        :id="sliderInputId"
        v-model.number="localMonthIndex"
        type="range"
        class="heatmap-range"
        min="0"
        :max="maxMonthSlider"
        step="1"
        :aria-valuetext="currentMonthLabel"
      />
      <button
        type="button"
        class="heatmap-play-btn"
        :aria-pressed="playing"
        :title="playing ? 'Pause' : 'Lecture automatique'"
        @click="togglePlay"
      >
        {{ playing ? '⏸ Pause' : '▶ Lecture' }}
      </button>
    </div>
    <div ref="chartRootRef" class="heatmap-chart-root" />
    <p class="heatmap-legend-hint">
      {{ legendText }}
    </p>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as d3 from 'd3'
import { heatmapCellHeight } from '../services/temporalHeatmapData'

/**
 * @typedef {{ rowLabels: string[], columnLabels: string[], values: number[][] }} HeatmapMatrix
 */
const props = defineProps({
  /** Matrice racines × mois (valeurs ≥ 0) */
  matrix: {
    type: Object,
    default: null
  },
  /** Index du mois mis en avant (0 = premier des 12) */
  selectedMonthIndex: {
    type: Number,
    default: 11
  },
  /** Texte sous le graphique (métrique + période). Si vide, libellé par défaut (vue catégories). */
  legendHint: {
    type: String,
    default: ''
  },
  /** id HTML unique si plusieurs heatmaps dans l’app (accessibilité label/for). */
  sliderInputId: {
    type: String,
    default: 'heatmap-month-slider'
  },
  /** aria-label du SVG pour lecteurs d’écran */
  heatmapAriaLabel: {
    type: String,
    default: 'Carte de chaleur des tickets par ligne et par mois'
  },
  /**
   * Si true : pas de libellés de lignes dans le SVG (colonne HTML séparée, ex. arbre repliable).
   * Les marges gauches sont réduites pour laisser place au panneau externe.
   */
  hideRowLabels: {
    type: Boolean,
    default: false
  },
  /**
   * Ligne mise en surbrillance (0-based), ex. survol de la liste HTML à gauche.
   * -1 = aucune. Dessine un voile sur la rangée pour lier libellé ↔ cellules.
   */
  highlightedRowIndex: {
    type: Number,
    default: -1
  }
})

const legendText = computed(() => {
  if (props.legendHint && String(props.legendHint).trim()) {
    return props.legendHint.trim()
  }
  return 'Intensité = volume de tickets sur la branche (catégorie + sous-catégories) pour le mois (date d’ouverture du ticket, selon GLPI).'
})

const emit = defineEmits(['update:selectedMonthIndex'])

const chartRootRef = ref(null)
const localMonthIndex = ref(props.selectedMonthIndex)
let playTimerId = null
const playing = ref(false)

const nCols = computed(() => props.matrix?.columnLabels?.length ?? 0)

const currentMonthLabel = computed(() => {
  const m = props.matrix
  if (!m || !m.columnLabels || localMonthIndex.value < 0) return '—'
  return m.columnLabels[localMonthIndex.value] ?? '—'
})

watch(
  () => props.selectedMonthIndex,
  (v) => {
    if (typeof v === 'number' && v >= 0) localMonthIndex.value = v
  }
)

watch(localMonthIndex, (v) => {
  emit('update:selectedMonthIndex', v)
  drawHeatmap()
})

watch(
  () => props.matrix,
  () => {
    nextTick(() => drawHeatmap())
  },
  { deep: true }
)

/**
 * Redessin explicite : dimensions, mode libellés, ligne survolée (liste HTML à gauche).
 */
watch(
  () => [
    props.matrix?.rowLabels?.length,
    props.matrix?.values?.length,
    props.hideRowLabels,
    props.highlightedRowIndex
  ],
  () => nextTick(() => drawHeatmap())
)

const maxMonthSlider = computed(() => Math.max(0, (props.matrix?.columnLabels?.length ?? 1) - 1))

let resizeObserver = null

onMounted(() => {
  drawHeatmap()
  resizeObserver = new ResizeObserver(() => drawHeatmap())
  if (chartRootRef.value) {
    resizeObserver.observe(chartRootRef.value)
  }
})

onUnmounted(() => {
  if (playTimerId != null) clearInterval(playTimerId)
  resizeObserver?.disconnect()
})

function togglePlay() {
  if (playing.value) {
    playing.value = false
    if (playTimerId != null) {
      clearInterval(playTimerId)
      playTimerId = null
    }
    return
  }
  playing.value = true
  playTimerId = window.setInterval(() => {
    const max = Math.max(0, nCols.value - 1)
    if (max <= 0) return
    localMonthIndex.value = localMonthIndex.value >= max ? 0 : localMonthIndex.value + 1
  }, 900)
}

function drawHeatmap() {
  const el = chartRootRef.value
  const data = props.matrix
  if (!el) return
  if (!data || !data.values?.length || !data.columnLabels?.length) {
    el.innerHTML = ''
    return
  }

  const rowLabels = data.rowLabels
  const colLabels = data.columnLabels
  const values = data.values
  const nColsLocal = colLabels.length
  // Toujours aligner le dessin sur le minimum (évite crash si données désynchronisées).
  const nRows = Math.min(rowLabels.length, values?.length ?? 0)
  if (nRows === 0) {
    el.innerHTML = ''
    return
  }
  if (rowLabels.length !== values.length) {
    console.warn('[TemporalHeatmapChart] rowLabels et values de longueurs différentes', {
      rowLabels: rowLabels.length,
      values: values.length
    })
  }

  const flatVals = values.flat ? values.flat() : [].concat(...values)
  const maxVal = d3.max(flatVals, (d) => d) || 1
  const colorScale = d3.scaleSequential(d3.interpolateYlOrRd).domain([0, maxVal])

  const primaryStroke =
    getComputedStyle(document.documentElement).getPropertyValue('--app-primary').trim() || '#667eea'
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark'
  const cellStrokeMuted = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)'

  const width = el.clientWidth || 800
  // Marge gauche large si les libellés sont dans le SVG ; sinon grille seule (alignée avec heatmapCellHeight).
  /** Marge basse : libellés mois + légende (hanging baseline pour les mois → pas de chevauchement grille). */
  const margin = {
    top: 8,
    right: 16,
    bottom: 62,
    left: props.hideRowLabels ? 12 : 160
  }
  const innerW = Math.max(200, width - margin.left - margin.right)
  const cellW = innerW / nColsLocal
  const cellH = heatmapCellHeight(nRows)
  const innerH = cellH * nRows
  const height = margin.top + innerH + margin.bottom

  el.innerHTML = ''

  const svg = d3
    .select(el)
    .append('svg')
    .attr('width', width)
    .attr('height', height)
    .attr('role', 'img')
    .attr('aria-label', props.heatmapAriaLabel)

  const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`)

  const highlightCol = Math.min(Math.max(0, localMonthIndex.value), nColsLocal - 1)

  const guideStroke = isDark ? 'rgba(255,255,255,0.16)' : 'rgba(0,0,0,0.1)'

  /**
   * Filets horizontaux entre les rangées (mode libellés externes) : guide l’œil sans masquer les couleurs.
   */
  if (props.hideRowLabels) {
    const guides = g.append('g').attr('class', 'heatmap-row-guides').attr('pointer-events', 'none')
    for (let r = 0; r <= nRows; r++) {
      guides
        .append('line')
        .attr('x1', 0)
        .attr('x2', innerW)
        .attr('y1', r * cellH)
        .attr('y2', r * cellH)
        .attr('stroke', guideStroke)
        .attr('stroke-width', r === 0 || r === nRows ? 1.1 : 0.85)
    }
  }

  for (let r = 0; r < nRows; r++) {
    for (let c = 0; c < nColsLocal; c++) {
      const v = values[r][c] ?? 0
      const x = c * cellW
      const y = r * cellH
      const cell = g
        .append('rect')
        .attr('x', x)
        .attr('y', y)
        .attr('width', cellW - 1)
        .attr('height', cellH - 1)
        .attr('rx', 2)
        .attr('fill', colorScale(v))
        .attr('stroke', c === highlightCol ? primaryStroke : cellStrokeMuted)
        .attr('stroke-width', c === highlightCol ? 2.5 : 0.5)

      cell.append('title').text(`${rowLabels[r]} — ${colLabels[c]} : ${v} ticket(s)`)
    }
  }

  /**
   * Surbrillance de la rangée (synchronisée avec le survol de la liste catégories à gauche).
   */
  if (
    props.hideRowLabels &&
    props.highlightedRowIndex >= 0 &&
    props.highlightedRowIndex < nRows
  ) {
    const hr = props.highlightedRowIndex
    g.append('g')
      .attr('class', 'heatmap-row-highlight')
      .attr('pointer-events', 'none')
      .append('rect')
      .attr('x', 0)
      .attr('y', hr * cellH)
      .attr('width', innerW)
      .attr('height', cellH)
      .attr('fill', primaryStroke)
      .attr('fill-opacity', isDark ? 0.22 : 0.18)
      .attr('stroke', primaryStroke)
      .attr('stroke-opacity', 0.55)
      .attr('stroke-width', 1)
  }

  /**
   * Libellés mois (sous la grille, sans empiéter sur la dernière rangée).
   * Par défaut, y = ligne de base : la moitié des glypès est au-dessus → chevauchement des cellules.
   * dominant-baseline=hanging : y est le haut du texte, placé juste sous la grille.
   */
  const monthLabelTop = innerH + 6
  g.append('g')
    .attr('class', 'heatmap-month-labels')
    .attr('transform', `translate(0, ${monthLabelTop})`)
    .selectAll('text')
    .data(colLabels)
    .enter()
    .append('text')
    .attr('x', (_, i) => i * cellW + cellW / 2)
    .attr('y', 0)
    .attr('dominant-baseline', 'hanging')
    .attr('text-anchor', 'middle')
    .attr('font-size', '10px')
    .attr('fill', 'currentColor')
    .attr('class', (_, i) => (i === highlightCol ? 'heatmap-col-active' : ''))
    .text((d) => d)

  /**
   * Libellés lignes (à gauche) — désactivés si le parent fournit une colonne HTML (hideRowLabels).
   */
  if (!props.hideRowLabels) {
    const rowG = g.append('g').attr('transform', `translate(-8, 0)`)
    rowLabels.forEach((label, i) => {
      const short = label.length > 36 ? `${label.slice(0, 34)}…` : label
      const te = rowG
        .append('text')
        .attr('x', 0)
        .attr('y', i * cellH + cellH / 2)
        .attr('dy', '0.35em')
        .attr('text-anchor', 'end')
        .attr('font-size', '11px')
        .attr('fill', 'currentColor')
        .text(short)
      te.append('title').text(label)
    })
  }

  /**
   * Barre de légende dégradé (sous le graphique)
   */
  const legendW = Math.min(280, innerW)
  const legendH = 10
  const lx = 0
  /** Sous les libellés mois (~11px en hanging + petit interstice) */
  const ly = monthLabelTop + 16

  const defs = svg.append('defs')
  const gradId = `heatmap-grad-${Math.random().toString(36).slice(2)}`
  const grad = defs
    .append('linearGradient')
    .attr('id', gradId)
    .attr('x1', '0%')
    .attr('x2', '100%')

  const steps = 10
  for (let i = 0; i <= steps; i++) {
    const t = i / steps
    grad.append('stop').attr('offset', `${t * 100}%`).attr('stop-color', colorScale(t * maxVal))
  }

  g.append('rect')
    .attr('x', lx)
    .attr('y', ly)
    .attr('width', legendW)
    .attr('height', legendH)
    .attr('fill', `url(#${gradId})`)
    .attr('rx', 2)

  g.append('text')
    .attr('x', 0)
    .attr('y', ly + legendH + 14)
    .attr('font-size', '10px')
    .attr('fill', 'currentColor')
    .text(`0 — ${maxVal} ticket(s) (max sur la période)`)
}
</script>

<style scoped>
.heatmap-wrap {
  width: 100%;
  min-height: 200px;
  color: var(--app-text, #333);
}

.heatmap-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px 16px;
  margin-bottom: 12px;
}

.heatmap-slider-label {
  font-size: 0.9rem;
  color: var(--app-text-muted);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.heatmap-slider-value {
  font-weight: 600;
  color: var(--app-text);
}

.heatmap-range {
  flex: 1;
  min-width: 160px;
  max-width: 360px;
  accent-color: var(--app-primary, #667eea);
}

.heatmap-play-btn {
  padding: 8px 14px;
  border: 1px solid var(--app-border);
  border-radius: 8px;
  background: var(--app-surface);
  color: var(--app-text);
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 600;
}

.heatmap-play-btn:hover {
  background: var(--app-mode-btn-hover-bg);
}

.heatmap-chart-root {
  width: 100%;
  overflow-x: auto;
}

.heatmap-legend-hint {
  margin-top: 12px;
  font-size: 0.8rem;
  color: var(--app-text-muted);
  line-height: 1.4;
}

:deep(.heatmap-col-active) {
  font-weight: 700;
  fill: var(--app-primary);
}
</style>
