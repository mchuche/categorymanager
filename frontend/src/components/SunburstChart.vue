<template>
  <!-- ref sur le conteneur pour mesurer toute la largeur disponible (évite le « petit disque » centré) -->
  <div ref="containerRef" class="sunburst-container">
    <svg ref="svgRef" class="sunburst-svg"></svg>
    <!--
      Pas de Teleport vers body : en plein écran (.sunburst-shell), seul ce sous-arbre est dans la
      couche « top layer » — un tooltip dans body resterait invisible. Ici : position fixed + clientX/Y.
    -->
    <div
      v-if="tooltip.visible"
      class="sunburst-tooltip"
      :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
    >
      <div class="tooltip-content">
        <strong>{{ tooltip.name }}</strong>
        <!--
          directTickets = tickets sur la catégorie seule ;
          childrenTickets = somme des tickets dans l’arbre des enfants ;
          branchTotal = direct + enfants (total de la branche).
        -->
        <div class="tooltip-row">
          Total branche : <strong>{{ tooltip.branchTotal }}</strong>
        </div>
        <div class="tooltip-row">
          Sur cette catégorie : {{ tooltip.directTickets }}
        </div>
        <div class="tooltip-row">
          Dans les sous-catégories : {{ tooltip.childrenTickets }}
        </div>
      </div>
    </div>

    <!--
      Barre sous le graphique : zoom / fil d’Ariane uniquement.
      Le plein écran est géré dans DashboardPage (en-tête), pas ici — évite un doublon sous le visuel.
    -->
    <div class="sunburst-controls">
      <div class="sunburst-controls-actions">
        <button
          v-if="currentPath.length > 0"
          type="button"
          @click="resetZoom"
          class="reset-button"
        >
          ↶ Réinitialiser la vue
        </button>
      </div>
      <div v-if="currentPath.length > 0" class="sunburst-info">
        <span>Chemin : {{ currentPath.join(' > ') }}</span>
      </div>
      <p
        class="sunburst-zoom-hint"
        title="Le zoom géométrique est indépendant du zoom hiérarchique (clic sur un secteur)"
      >
        Ctrl + molette : zoom du graphique · Molette sans Ctrl : défilement de la page
        · glisser sur le fond : déplacer la vue
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as d3 from 'd3'
import { useThemeStore } from '../stores/theme'
import { addDirectTicketLeavesForSunburst } from '../services/treeTransform.js'

/**
 * Props du composant
 * @property {Object} data - Structure arborescente des catégories (format D3.js avec children)
 */
const props = defineProps({
  data: {
    type: Object,
    required: true,
    default: () => ({ id: 'root', name: 'Aucune catégorie', children: [] })
  },
  /**
   * Si true : taille des secteurs proportionnelle aux compteurs (totalTicketCount) dans les données.
   * Si false : pondération uniforme par feuille (structure seule, indépendante du nombre de tickets).
   */
  weightByTickets: {
    type: Boolean,
    default: false
  }
})

/**
 * Données pour d3.partition : en mode « tickets », clone + feuilles internes fictives (`__directSlice`)
 * pour que la somme des angles des enfants reflète le total branche (tickets directs parent inclus).
 * Ces feuilles ne sont pas tracées — seuls les secteurs des vraies catégories sont visibles.
 * En mode « structure », pas de clone (pondération uniforme par feuille réelle).
 */
function cloneDataForSunburstPartition() {
  if (!props.weightByTickets) {
    return props.data
  }
  try {
    const cloned = JSON.parse(JSON.stringify(props.data))
    addDirectTicketLeavesForSunburst(cloned)
    return cloned
  } catch (e) {
    console.warn('Sunburst: impossible de cloner les données pour les tranches « direct »', e)
    return props.data
  }
}

/**
 * Références aux éléments DOM
 */
const svgRef = ref(null)
/** Conteneur du graphique : sert à mesurer la largeur réelle (responsive) */
const containerRef = ref(null)

/**
 * État du composant
 */
const tooltip = ref({
  visible: false,
  x: 0,
  y: 0,
  name: '',
  branchTotal: 0,
  directTickets: 0,
  childrenTickets: 0
})

const currentPath = ref([]) // Chemin actuel dans la hiérarchie (pour le zoom)

/** Store thème : recolorer les éléments D3 (libellés, traits, hub) quand on bascule clair / sombre */
const themeStore = useThemeStore()

/**
 * Lit une variable CSS sur :root (thème clair/sombre défini dans src/styles/theme.css).
 * Utilisé pour les attributs SVG que D3 ne peut pas lier au scoped CSS.
 */
function getCssVar(name, fallback) {
  if (typeof document === 'undefined') return fallback
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

/**
 * Met à jour couleurs de contour des arcs, libellés et hub selon le thème actif.
 */
function applySunburstThemeColors() {
  if (!g) return
  const arcStroke = getCssVar('--sunburst-arc-stroke', '#ffffff')
  const labelFill = getCssVar('--sunburst-label-fill', '#333333')
  const labelStroke = getCssVar('--sunburst-label-stroke', 'rgba(255, 255, 255, 0.94)')
  g.selectAll('path').attr('stroke', arcStroke)
  g.selectAll('text.sunburst-arc-label').attr('fill', labelFill).attr('stroke', labelStroke)
  const hubFill = getCssVar('--sunburst-hub-fill', '#ffffff')
  const hubStroke = getCssVar('--sunburst-hub-stroke', '#4caf50')
  const hubIcon = getCssVar('--sunburst-hub-icon', '#2e7d32')
  g.selectAll('g.sunburst-hub circle').attr('fill', hubFill).attr('stroke', hubStroke)
  g.selectAll('g.sunburst-hub text').attr('fill', hubIcon)
}

watch(
  () => themeStore.isDark,
  () => {
    nextTick(() => {
      applySunburstThemeColors()
      window.dispatchEvent(new Event('resize'))
    })
  }
)

/**
 * Pile des sous-arbres « focus » : à chaque drill-down on empile `d.data` ; la racine affichée est
 * toujours `zoomStack[zoomStack.length - 1]` (ou `props.data` si la pile est vide). Permet de
 * remonter d’un niveau (cercle central) sans recalculer les parents depuis d’anciens nœuds D3.
 */
let zoomStack = []

/**
 * Variables pour D3.js
 */
let svg = null
/** Groupe intermédiaire : reçoit la transformation d3.zoom (échelle + translation) */
let zoomLayer = null
let zoomBehavior = null
/** Référence pour retirer l’écouteur molette sans Ctrl (défilement page, sans zoom graphique) */
let wheelPageScrollHandler = null
let g = null // Groupe du tracé centré (translate vers le centre du SVG)
let width = 800
let height = 800
let radius = Math.min(width, height) / 2 - 10
let currentRoot = null // Nœud racine actuel (change lors du zoom)
let partition = null // Fonction de partition D3.js
let arc = null // Fonction d'arc D3.js
let colorScale = null // Échelle de couleurs

/** Debounce pour ResizeObserver / resize (évite des centaines de redraw) */
let resizeDebounceId = null

/**
 * Échelle k du zoom géométrique d3.zoom sur le SVG (facteur uniforme).
 * Sert à élargir le budget tangentiel des libellés : plus on zoome, plus on peut afficher de caractères.
 */
let geometricZoomK = 1
/** requestAnimationFrame : évite de recalculer les libellés à chaque événement molette */
let zoomLabelsRafId = null

/** Retarde la disparition du tooltip pour éviter les trous entre secteurs (stroke) */
let tooltipHideTimerId = null

function clearTooltipHideTimer() {
  if (tooltipHideTimerId !== null) {
    clearTimeout(tooltipHideTimerId)
    tooltipHideTimerId = null
  }
}

/** Position viewport pour position:fixed (ne pas utiliser pageX/pageY avec le scroll) */
function tooltipPositionFromEvent(event) {
  return {
    x: event.clientX + 14,
    y: event.clientY + 14
  }
}

/**
 * Dimensions du carré de dessin : largeur = celle du conteneur, hauteur = largeur
 * (sinon min(largeur, hauteur) limite par la hauteur et laisse du blanc sur les côtés)
 */
function getDrawSize() {
  const el = containerRef.value
  if (!el) {
    return { width: 800, height: 800 }
  }
  const w = el.clientWidth || el.getBoundingClientRect().width
  const size = Math.max(320, Math.floor(w))
  return { width: size, height: size }
}

/**
 * Poids pour d3.hierarchy().sum(fn) : fn est appelée pour **chaque** nœud, et la valeur
 * stockée est fn(datum) + Σ enfants. Si fn renvoie autre chose que 0 sur un nœud **interne**
 * (ex. totalTicketCount), on double-compte : la somme des enfants ne remplit plus l’angle du
 * parent → « trou » dans le disque (souvent un gros secteur vide). Les poids doivent donc
 * être portés uniquement par les **feuilles** (pas d’enfants dans les données).
 */
function leafValueForPartition(datum) {
  if (datum.children && datum.children.length > 0) {
    return 0
  }
  if (!props.weightByTickets) {
    return 1
  }
  const value = Number(datum.totalTicketCount)
  if (Number.isFinite(value) && value > 0) {
    return value
  }
  return 1
}

/**
 * Fallback si Canvas indisponible (SSR) : largeur moyenne par caractère (sans-serif).
 * L’estimation `longueur × 0.4 × fs` surestime souvent les chaînes courtes en chiffres / minuscules
 * et sous-estime les libellés longs → troncatures « Ord… » alors que l’arc est large.
 */
const LABEL_CHAR_WIDTH_FACTOR = 0.4
/**
 * Taille minimale des libellés sur les arcs (px). En dessous, le texte devient difficile à lire ;
 * on accepte de ne pas afficher de label sur les secteurs trop étroits plutôt que de descendre sous ce plancher.
 */
/** Plancher / plafond en px : un peu plus haut qu’avant pour une lecture plus confortable sur l’arc */
const LABEL_FONT_MIN = 6.5
const LABEL_FONT_MAX = 14

/** Contexte Canvas réutilisé pour measureText (aligné sur le rendu SVG texte par défaut) */
let labelMeasureCtx = null

function getLabelMeasureContext() {
  if (typeof document === 'undefined') return null
  if (!labelMeasureCtx) {
    const c = document.createElement('canvas')
    labelMeasureCtx = c.getContext('2d')
  }
  return labelMeasureCtx
}

/**
 * Largeur affichée du libellé à la taille donnée — préférable à une moyenne par caractère
 * pour « Ecran (1268) » vs « Ordinateur portable (5868) » (chiffres vs lettres).
 */
function measureLabelWidth(str, fontSize) {
  const ctx = getLabelMeasureContext()
  if (!ctx) {
    return (str || '').length * fontSize * LABEL_CHAR_WIDTH_FACTOR
  }
  /* Même graisse que les libellés SVG (voir .sunburst-arc-label) pour une mesure cohérente */
  ctx.font = `600 ${fontSize}px sans-serif`
  return ctx.measureText(str || '').width
}

function truncateSunburstLabel(full, maxChars) {
  if (!full || maxChars < 1) return ''
  if (full.length <= maxChars) return full
  if (maxChars <= 1) return '…'
  return full.slice(0, maxChars - 1) + '…'
}

/**
 * Plus grand nombre de caractères « logiques » (avant …) pour lequel la chaîne tronquée tient dans budget.
 */
function maxTruncationCharsFitting(full, fontSize, budget) {
  if (!full) return 0
  if (measureLabelWidth(full, fontSize) <= budget) {
    return full.length
  }
  let lo = 1
  let hi = full.length
  let best = 1
  while (lo <= hi) {
    const mid = Math.floor((lo + hi) / 2)
    const piece = truncateSunburstLabel(full, mid)
    if (measureLabelWidth(piece, fontSize) <= budget) {
      best = mid
      lo = mid + 1
    } else {
      hi = mid - 1
    }
  }
  return best
}

/**
 * Libellé sur l’arc : vue structure = tickets directs sur la catégorie ;
 * vue tickets = total de branche (catégorie + toutes les sous-catégories), cohérent avec la surface du secteur.
 */
function fullArcLabelText(d) {
  const name = d.data.name || ''
  if (props.weightByTickets) {
    const total = Number(d.data.totalTicketCount)
    const branchTotal = Number.isFinite(total) && total >= 0 ? total : 0
    return `${name} (${branchTotal})`
  }
  const tc = Number(d.data.ticketCount)
  const direct = Number.isFinite(tc) && tc >= 0 ? tc : 0
  return `${name} (${direct})`
}

/**
 * Découpe « Nom (123) » en deux lignes pour mieux utiliser l’épaisseur du ring (vue structure).
 */
function splitNameAndTicketLine(full) {
  const re = / \((\d+)\)$/
  const m = full.match(re)
  if (!m) return null
  const name = full.slice(0, -m[0].length).trim()
  return [name, `(${m[1]})`]
}

/**
 * Rayon du libellé : milieu de l’anneau (y0 + y1) / 2 — centre radial de la cellule en « donut ».
 * L’angle est le médian (x0 + x1) / 2 dans sunburstLabelTransform ; le budget d’arc utilise le même r.
 */
function sunburstLabelRadius(d) {
  return (d.y0 + d.y1) / 2
}

/**
 * Un libellé par secteur : priorité au texte entier en réduisant la police, puis 2 lignes, puis troncature.
 * L’espace « vide » perçu est souvent radial alors que la contrainte réelle est la longueur d’arc :
 * on compense en diminuant font-size et en empilant nom / compteur.
 */
function computeLabelRow(d) {
  const full = fullArcLabelText(d)
  const dx = d.x1 - d.x0
  const dy = d.y1 - d.y0
  const rLabel = sunburstLabelRadius(d)
  const arcLen = dx * rLabel
  /**
   * À l’écran, un zoom k agrandit l’arc en pixels : on autorise un budget texte proportionnel
   * pour afficher plus de caractères sans changer la géométrie des secteurs (plafond pour limiter les chevauchements).
   */
  const budgetZoomMultiplier = Math.min(4, Math.max(1, geometricZoomK))
  /** Petite marge pour antialiasing / arrondis de mesure Canvas vs SVG */
  const budget = arcLen * 0.99 * budgetZoomMultiplier

  if (arcLen < 1.2 || dy < 4 || dx <= 0.0005) {
    return null
  }

  /**
   * Hauteur max du glyphe : liée à l’épaisseur radiale du ring (texte tangent à l’arc).
   * 0.72 au lieu de 0.6 : un peu plus de marge verticale sans déborder visuellement sur l’anneau.
   */
  const maxFontByRing = dy * 0.72

  // 1) Une ligne : police réduite jusqu’au minimum pour faire tenir tout le texte sur l’arc
  for (let fs = LABEL_FONT_MAX; fs >= LABEL_FONT_MIN; fs -= 0.25) {
    const raw = Math.round(fs * 10) / 10
    const fontSize = Math.min(raw, maxFontByRing)
    if (fontSize < LABEL_FONT_MIN) continue
    if (measureLabelWidth(full, fontSize) <= budget) {
      return { node: d, layout: { fontSize, text: full, lines: null } }
    }
  }

  // 2) Deux lignes : nom + (nombre) — structure (direct) ou tickets (total branche)
  //    Plafonds un peu assouplis : l’ancien dy*0.4 + 2.35×h forcait une micro-police sur certains anneaux
  //    alors qu’une ligne tenait en largeur (ex. « Ecran » vs « Périphériques » sur le même ring).
  const pair = splitNameAndTicketLine(full)
  if (pair) {
    const [nameLine, numLine] = pair
    const twoLineFontCap = dy * 0.55
    /** Bloc des deux tspans : ~1em + 1.08em (voir applySunburstLabelContent) + petite marge */
    const lineBlockMax = dy * 0.98
    for (let fs = LABEL_FONT_MAX; fs >= LABEL_FONT_MIN; fs -= 0.25) {
      const raw = Math.round(fs * 10) / 10
      const fontSize = Math.min(raw, maxFontByRing, twoLineFontCap)
      if (fontSize < LABEL_FONT_MIN) continue
      if (fontSize * 2.1 > lineBlockMax) continue
      if (
        measureLabelWidth(nameLine, fontSize) <= budget &&
        measureLabelWidth(numLine, fontSize) <= budget
      ) {
        return { node: d, layout: { fontSize, lines: [nameLine, numLine], text: null } }
      }
    }
  }

  // 3) Troncature : ne pas fixer la plus grande police puis couper — ça donne « Ord… » avec de la
  //    place restante. On teste plusieurs tailles et on privilégie le plus de caractères visibles,
  //    puis la plus grande police à égalité.
  let best = null
  for (let fs = LABEL_FONT_MAX; fs >= LABEL_FONT_MIN; fs -= 0.25) {
    const raw = Math.round(fs * 10) / 10
    const fontSize = Math.min(raw, maxFontByRing)
    if (fontSize < LABEL_FONT_MIN) continue
    const maxChars = maxTruncationCharsFitting(full, fontSize, budget)
    const text = truncateSunburstLabel(full, maxChars)
    if (!text) continue
    if (
      !best ||
      maxChars > best.maxChars ||
      (maxChars === best.maxChars && fontSize > best.fontSize)
    ) {
      best = { fontSize, text, maxChars }
    }
  }
  if (!best) return null
  return { node: d, layout: { fontSize: best.fontSize, text: best.text, lines: null } }
}

function buildSunburstLabelRows(nodes) {
  return nodes.map(computeLabelRow).filter(Boolean)
}

/**
 * Clé unique pour le join D3 (paths + libellés). Seul `d.data.id` provoque des collisions
 * (ids dupliqués / manquants / typés différemment) : le mauvais secteur est alors mis à jour,
 * les paths peuvent disparaître alors que les <text> restent visibles.
 */
function sunburstNodeKey(d) {
  return d
    .ancestors()
    .map(n => n.data.id ?? '∅')
    .join('>')
}

/**
 * Place le libellé au centre angulaire de la cellule (angle médian), à sunburstLabelRadius (milieu radial).
 * Tangente à l’arc pour la lecture ; retournement 180° quand le médian ≥ π pour garder le texte lisible.
 */
function sunburstLabelTransform(d) {
  const mid = (d.x0 + d.x1) / 2
  const r = sunburstLabelRadius(d)
  const midDeg = mid * 180 / Math.PI
  const flip = mid >= Math.PI ? 180 : 0
  return `rotate(${midDeg - 90}) translate(${r},0) rotate(${flip})`
}

/**
 * La partition D3 réserve la première bande radiale au nœud racine (depth 0).
 * On ne dessine pas la racine → bande vide au centre ; on recale les y puis on borne pour éviter
 * innerRadius ≥ outerRadius ou NaN (arc invisible).
 */
function removeUnpaintedRootBand(root) {
  if (!root || root.depth !== 0) return
  const band = root.y1 - root.y0
  if (band <= 1e-6) return
  if (band >= radius - 1e-6) return
  const denom = radius - band
  if (denom <= 1e-6) return
  const scale = radius / denom
  root.each(d => {
    if (d.depth === 0) return
    d.y0 = (d.y0 - band) * scale
    d.y1 = (d.y1 - band) * scale
  })
  root.each(d => {
    if (d.depth === 0) return
    d.y0 = Math.max(0, Math.min(radius, d.y0))
    d.y1 = Math.max(0, Math.min(radius, d.y1))
    if (d.y1 <= d.y0) {
      d.y1 = d.y0 + 1e-3
    }
  })
}

function applySunburstLabelContent(textSelection, row) {
  const { layout } = row
  textSelection.selectAll('tspan').remove()
  if (layout.lines && layout.lines.length) {
    layout.lines.forEach((line, i) => {
      textSelection
        .append('tspan')
        .attr('x', 0)
        .attr('dy', i === 0 ? '0' : '1.08em')
        .text(line)
    })
  } else {
    textSelection.text(layout.text || '')
  }
}

/**
 * Delta molette pour d3.zoom : la valeur par défaut de D3 multiplie par 10 si event.ctrlKey
 * (gestes type pincement / zoom OS). Comme notre zoom graphique utilise toujours Ctrl+molette,
 * ce facteur rendait chaque cran trop fort — on reprend la même formule que D3 sans ce ×10.
 * Optionnel : coefficient < 1 pour un zoom encore plus progressif.
 */
const SUNBURST_ZOOM_WHEEL_SENSITIVITY = 0.85

function sunburstWheelDelta(event) {
  const base =
    -event.deltaY * (event.deltaMode === 1 ? 0.05 : event.deltaMode ? 1 : 0.002)
  return base * SUNBURST_ZOOM_WHEEL_SENSITIVITY
}

/**
 * Configure d3.zoom sur le SVG : Ctrl + molette = zoom, glisser sur le fond = pan (pas sur les secteurs).
 * Molette sans Ctrl : défilement de la page (voir attachWheelPageScrollWithoutCtrl).
 */
function setupZoomInteraction() {
  if (!svg || !zoomLayer) return

  zoomBehavior = d3
    .zoom()
    .scaleExtent([0.2, 10])
    .wheelDelta(sunburstWheelDelta)
    .on('zoom', (event) => {
      zoomLayer.attr('transform', event.transform)
      geometricZoomK = event.transform.k
      scheduleSunburstLabelsAfterZoom()
    })
    .filter((event) => {
      // Molette sans Ctrl : pas de zoom D3 — le défilement page est géré en capture ailleurs
      if (event.type === 'wheel') {
        if (!event.ctrlKey) {
          return false
        }
        event.preventDefault()
        return true
      }
      if (event.type === 'dblclick') {
        return false
      }
      if (event.type === 'mousedown' && event.button === 0) {
        const tag = event.target?.tagName?.toLowerCase()
        if (tag === 'path' || tag === 'text' || tag === 'circle' || tag === 'tspan') {
          return false
        }
      }
      return true
    })

  svg.call(zoomBehavior)
  svg.call(zoomBehavior.transform, d3.zoomIdentity)

  attachWheelPageScrollWithoutCtrl()
}

/**
 * Molette sans Ctrl au-dessus du SVG : évite le scroll implicite sur le SVG et fait défiler
 * la fenêtre (scrollBy). Ctrl + molette est laissé à d3.zoom (zoom graphique, pas la page).
 * Écouteur en capture + passive: false pour que preventDefault fonctionne.
 */
function attachWheelPageScrollWithoutCtrl() {
  detachWheelPageScrollWithoutCtrl()
  const el = svgRef.value
  if (!el) return

  wheelPageScrollHandler = (event) => {
    if (event.ctrlKey) return
    event.preventDefault()
    event.stopPropagation()
    window.scrollBy({ top: event.deltaY, behavior: 'auto' })
  }
  el.addEventListener('wheel', wheelPageScrollHandler, { capture: true, passive: false })
}

function detachWheelPageScrollWithoutCtrl() {
  const el = svgRef.value
  if (!el || !wheelPageScrollHandler) return
  el.removeEventListener('wheel', wheelPageScrollHandler, { capture: true })
  wheelPageScrollHandler = null
}

/**
 * Remet le zoom géométrique à l’identité (sans toucher au drill-down hiérarchique).
 * Instantané pour coller au re-dessin lors de « Réinitialiser la vue ».
 */
function resetGeometricZoom() {
  geometricZoomK = 1
  if (svg && zoomBehavior) {
    svg.call(zoomBehavior.transform, d3.zoomIdentity)
  }
}

/**
 * Recalcule les libellés après un changement de zoom (throttle 1 frame).
 */
function scheduleSunburstLabelsAfterZoom() {
  if (zoomLabelsRafId != null) {
    cancelAnimationFrame(zoomLabelsRafId)
  }
  zoomLabelsRafId = requestAnimationFrame(() => {
    zoomLabelsRafId = null
    updateSunburstLabels(false)
    applySunburstThemeColors()
  })
}

/**
 * Initialise le graphique Sunburst
 * Cette fonction configure D3.js et dessine le graphique initial
 */
function initSunburst() {
  // Vérifier que le SVG et les données sont disponibles
  if (!svgRef.value) {
    console.warn('Sunburst: SVG ref non disponible')
    return
  }
  
  // Vérifier que les données sont valides
  if (!props.data) {
    console.warn('Sunburst: Aucune donnée disponible')
    return
  }
  
  // Vérifier que les données ont une structure valide (avec children)
  if (!props.data.children || !Array.isArray(props.data.children) || props.data.children.length === 0) {
    console.warn('Sunburst: Aucune catégorie disponible dans les données', props.data)
    return
  }

  // Nouvelle construction depuis la racine : plus de zoom partiel
  zoomStack = []
  currentPath.value = []
  geometricZoomK = 1

  // Nettoyer le SVG existant
  d3.select(svgRef.value).selectAll('*').remove()

  // Dimensions = carré basé sur la largeur du conteneur (remplit l’espace horizontal)
  const dim = getDrawSize()
  width = dim.width
  height = dim.height
  radius = Math.min(width, height) / 2 - 10

  // Créer le SVG (tailles explicites en pixels)
  svg = d3.select(svgRef.value)
    .attr('width', width)
    .attr('height', height)
    .attr('viewBox', `0 0 ${width} ${height}`)
    .style('max-width', '100%')
    .style('height', 'auto')
    .style('touch-action', 'none')

  /*
   * Zoom géométrique (d3.zoom) : zoomLayer reçoit translate/scale ; g reste centré sur l’origine
   * du disque pour la partition — même logique qu’avant, avec une couche de vue au-dessus.
   */
  zoomLayer = svg.append('g').attr('class', 'sunburst-zoom-layer')
  g = zoomLayer
    .append('g')
    .attr('class', 'sunburst-plot')
    .attr('transform', `translate(${width / 2},${height / 2})`)

  setupZoomInteraction()

  // Configurer la fonction de partition (hiérarchie circulaire)
  // La partition divise l'espace en secteurs pour chaque nœud
  partition = d3.partition()
    .size([2 * Math.PI, radius]) // Angle (2π = 360°) et rayon

  // Configurer la fonction d'arc (dessine les secteurs)
  // Chaque secteur représente une catégorie dans la hiérarchie
  arc = d3.arc()
    .startAngle(d => d.x0) // Angle de début
    .endAngle(d => d.x1)   // Angle de fin
    .innerRadius(d => d.y0) // Rayon intérieur (profondeur dans la hiérarchie)
    .outerRadius(d => d.y1) // Rayon extérieur

  // Créer une échelle de couleurs
  // Utilise une palette de couleurs pour différencier les catégories
  // Palette personnalisée avec 20 couleurs distinctes pour couvrir toutes les catégories
  const colorPalette = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
    '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
    '#c49c94', '#f7b6d3', '#c7c7c7', '#dbdb8d', '#9edae5',
    '#393b79', '#5254a3', '#6b6ecf', '#9c9ede', '#637939',
    '#8ca252', '#b5cf6b', '#cedb9c', '#8c6d31', '#bd9e39',
    '#e7ba52', '#e7cb94', '#843c39', '#ad494a', '#d6616b',
    '#e7969c', '#7b4173', '#a55194', '#ce6dbd', '#de9ed6'
  ]
  colorScale = d3.scaleOrdinal()
    .domain([]) // Sera rempli dynamiquement
    .range(colorPalette) // Palette de couleurs personnalisée

  // Nœud racine : pondération selon weightByTickets (structure seule vs volumes tickets)
  currentRoot = d3.hierarchy(cloneDataForSunburstPartition())
    .sum(leafValueForPartition)
    .sort((a, b) => (b.value || 0) - (a.value || 0))

  partition(currentRoot)
  removeUnpaintedRootBand(currentRoot)

  drawSunburst()
}

/** Nœuds avec secteur visible (exclut racine + tranches « direct » fictives). */
function getSunburstRenderableNodes() {
  if (!currentRoot) return []
  return currentRoot.descendants().filter(d => d.depth && !d.data.__directSlice)
}

/**
 * Met à jour uniquement les libellés (troncature recalculée selon geometricZoomK).
 * @param {boolean} animate — transition 750 ms (premier dessin) ou mise à jour immédiate (zoom).
 */
function updateSunburstLabels(animate) {
  if (!g || !currentRoot) return

  const nodes = getSunburstRenderableNodes()
  const labelRows = buildSunburstLabelRows(nodes)
  const labels = g.selectAll('text.sunburst-arc-label').data(labelRows, row => sunburstNodeKey(row.node))

  const labelsEnter = labels
    .enter()
    .append('text')
    .attr('class', 'sunburst-arc-label')
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'middle')
    .attr('fill', () => getCssVar('--sunburst-label-fill', '#333333'))
    /* Halo lisible sur fond coloré : contour dessiné avant le remplissage (paint-order en CSS) */
    .attr('stroke', () => getCssVar('--sunburst-label-stroke', 'rgba(255, 255, 255, 0.94)'))
    .attr('font-weight', '600')
    .attr('pointer-events', 'none')

  const merged = labelsEnter.merge(labels)
  merged.each(function (row) {
    applySunburstLabelContent(d3.select(this), row)
  })
  merged.attr('stroke-width', row => {
    const fs = row.layout.fontSize
    const w = Math.min(2.75, Math.max(0.55, fs * 0.14 + 0.35))
    return `${w}px`
  })
  merged.attr('stroke', () => getCssVar('--sunburst-label-stroke', 'rgba(255, 255, 255, 0.94)'))

  if (animate) {
    merged
      .transition()
      .duration(750)
      .attr('font-size', row => `${row.layout.fontSize}px`)
      .attr('opacity', 1)
      .attr('transform', row => sunburstLabelTransform(row.node))
  } else {
    merged
      .attr('font-size', row => `${row.layout.fontSize}px`)
      .attr('opacity', 1)
      .attr('transform', row => sunburstLabelTransform(row.node))
  }

  const exitSel = labels.exit()
  if (animate) {
    exitSel.transition().duration(750).attr('opacity', 0).remove()
  } else {
    exitSel.attr('opacity', 0).remove()
  }
}

/**
 * Dessine le graphique Sunburst
 * Crée les arcs (secteurs) pour chaque catégorie et ajoute les interactions
 */
function drawSunburst() {
  if (!g || !currentRoot) return

  const nodes = getSunburstRenderableNodes()

  // Créer les arcs (secteurs) pour chaque nœud
  const path = g.selectAll('path')
    .data(nodes, sunburstNodeKey)

  // Entrée : créer les nouveaux arcs
  const pathEnter = path.enter()
    .append('path')
    .attr('fill', d => {
      // Couleur = ancêtre de profondeur 1 (ne pas réutiliser la variable d du datum)
      let n = d
      while (n.depth > 1) n = n.parent
      return colorScale(n.data.id) || '#888'
    })
    .attr('fill-opacity', 0.8)
    .attr('stroke', () => getCssVar('--sunburst-arc-stroke', '#ffffff'))
    .attr('stroke-width', 1)
    .attr('cursor', 'pointer')

  const mergedPaths = pathEnter.merge(path)
    .on('mouseover', handleMouseOver)
    .on('mousemove', handleTooltipPointerMove)
    .on('mouseout', handleMouseOut)
    .on('click', handleClick)

  /*
   * IMPORTANT : ne jamais appeler arc.innerRadius() / .outerRadius() sur le générateur global
   * `arc` pour la sortie (exit). En JS l’argument de .attr() est évalué tout de suite, ce qui
   * mutait `arc` avant même la transition du merge → secteurs plats / chemins vides (page blanche
   * avec seuls les libellés).
   */
  mergedPaths
    .transition()
    .duration(750)
    .attr('d', d => {
      if (d.x0 === d.x1 || d.y0 === d.y1) {
        console.warn('Sunburst: Arc invalide détecté', {
          x0: d.x0,
          x1: d.x1,
          y0: d.y0,
          y1: d.y1,
          value: d.value,
          data: d.data
        })
        return ''
      }
      const p = arc(d)
      return p == null ? '' : p
    })

  path.exit()
    .transition()
    .duration(750)
    .attr('d', node =>
      d3
        .arc()
        .innerRadius(node.y0)
        .outerRadius(node.y0)
        .startAngle(node.x0)
        .endAngle(node.x1)(node)
    )
    .remove()

  // Libellés : police adaptative + troncature (budget élargi quand geometricZoomK > 1)
  updateSunburstLabels(true)

  // Cercle central : remonter d’un cran (au-dessus des arcs pour capter le clic)
  drawSunburstHub()
  applySunburstThemeColors()
}

/**
 * Hub central (petit disque) : visible uniquement en vue zoomée ; clic = même effet qu’un
 * « retour arrière » d’un niveau dans la hiérarchie (dépile `zoomStack`).
 */
function drawSunburstHub() {
  if (!g || !currentRoot) return

  g.selectAll('g.sunburst-hub').remove()

  if (zoomStack.length === 0) return

  // Rayon : proportionnel au graphique, plafonné pour rester lisible sur petits écrans
  const hubR = Math.min(28, radius * 0.1)

  /**
   * Libellé du « parent » cible après clic : soit la catégorie précédente dans la pile,
   * soit la racine virtuelle (vue globale) quand il ne reste qu’un seul niveau de zoom.
   */
  const parentLabel =
    zoomStack.length >= 2
      ? zoomStack[zoomStack.length - 2].name || 'Niveau parent'
      : props.data.name || 'Vue globale'

  const hub = g.append('g').attr('class', 'sunburst-hub')

  hub
    .append('circle')
    .attr('r', hubR)
    .attr('fill', () => getCssVar('--sunburst-hub-fill', '#ffffff'))
    .attr('stroke', () => getCssVar('--sunburst-hub-stroke', '#4caf50'))
    .attr('stroke-width', 2)
    .attr('cursor', 'pointer')
    .on('click', event => {
      event.stopPropagation()
      zoomOutOneLevel()
    })
    .on('mouseover', function onHubOver() {
      d3.select(this).attr('fill', getCssVar('--sunburst-hub-fill-hover', '#e8f5e9'))
    })
    .on('mouseout', function onHubOut() {
      d3.select(this).attr('fill', getCssVar('--sunburst-hub-fill', '#ffffff'))
    })

  hub
    .append('title')
    .text(`Remonter d'un niveau — vers : ${parentLabel}`)

  hub
    .append('text')
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'central')
    .attr('font-size', Math.min(18, hubR * 0.85))
    .attr('fill', () => getCssVar('--sunburst-hub-icon', '#2e7d32'))
    .attr('pointer-events', 'none')
    .text('↑')
}

/**
 * Remonte d’un niveau dans la hiérarchie (inverse du drill-down sur un arc).
 */
function zoomOutOneLevel() {
  if (zoomStack.length === 0) return
  if (!props.data || !props.data.children || !Array.isArray(props.data.children)) {
    return
  }

  zoomStack.pop()
  syncPathFromStack()

  const rootData =
    zoomStack.length === 0 ? cloneDataForSunburstPartition() : zoomStack[zoomStack.length - 1]

  currentRoot = d3.hierarchy(rootData)
    .sum(leafValueForPartition)
    .sort((a, b) => (b.value || 0) - (a.value || 0))

  partition(currentRoot)
  removeUnpaintedRootBand(currentRoot)
  drawSunburst()
}

/**
 * Aligne le fil d’Ariane textuel sur la pile de zoom (noms des catégories focus).
 */
function syncPathFromStack() {
  currentPath.value = zoomStack.map(
    x => x.name || `Catégorie ${x.id}`
  )
}

/**
 * Gère le survol de la souris sur un arc
 * Affiche un tooltip avec les informations de la catégorie
 */
/**
 * Infobulle : total de branche = tickets directs + tickets dans l’arbre des enfants.
 */
function ticketTooltipPayload(d) {
  const direct = Number(d.data.ticketCount)
  const directN = Number.isFinite(direct) && direct >= 0 ? direct : 0
  let total = Number(d.data.totalTicketCount)
  if (!Number.isFinite(total) || total < 0) {
    total = d.value != null ? Number(d.value) : directN
  }
  if (!Number.isFinite(total) || total < 0) total = directN
  const childrenN = Math.max(0, total - directN)
  return {
    name: d.data.name,
    branchTotal: total,
    directTickets: directN,
    childrenTickets: childrenN
  }
}

function handleMouseOver(event, d) {
  clearTooltipHideTimer()
  const pos = tooltipPositionFromEvent(event)
  const t = ticketTooltipPayload(d)
  tooltip.value = {
    visible: true,
    x: pos.x,
    y: pos.y,
    name: t.name,
    branchTotal: t.branchTotal,
    directTickets: t.directTickets,
    childrenTickets: t.childrenTickets
  }

  d3.select(event.currentTarget)
    .attr('fill-opacity', 1)
    .attr('stroke-width', 2)
}

/** Suit le pointeur tant que le tooltip est affiché (évite un infobulle « figée » au premier pixel) */
function handleTooltipPointerMove(event) {
  if (!tooltip.value.visible) return
  const pos = tooltipPositionFromEvent(event)
  tooltip.value = { ...tooltip.value, x: pos.x, y: pos.y }
}

/**
 * Sortie du secteur : masquage retardé pour laisser le temps de passer au secteur voisin
 * ou sur le trait blanc sans faire clignoter l’infobulle.
 */
function handleMouseOut(event) {
  d3.select(event.currentTarget)
    .attr('fill-opacity', 0.8)
    .attr('stroke-width', 1)

  clearTooltipHideTimer()
  tooltipHideTimerId = window.setTimeout(() => {
    tooltipHideTimerId = null
    tooltip.value.visible = false
  }, 120)
}

/**
 * Gère le clic sur un arc
 * Effectue un zoom sur la catégorie cliquée (drill-down)
 */
function handleClick(event, d) {
  if (!d.children || d.children.length === 0) {
    return
  }
  event.stopPropagation()

  // Historique de zoom : un niveau par clic (permet la remontée via le cercle central)
  zoomStack.push(d.data)
  syncPathFromStack()

  /*
   * Ne pas faire currentRoot = d : les nœuds gardent leur depth d’origine (ex. 2, 3…).
   * d3.partition() place les y selon depth ; avec une « fausse » racine depth > 0, les arcs
   * sortent du disque ou deviennent invalides → secteurs vides, seuls les <text> restent.
   */
  currentRoot = d3.hierarchy(d.data)
    .sum(leafValueForPartition)
    .sort((a, b) => (b.value || 0) - (a.value || 0))

  partition(currentRoot)
  removeUnpaintedRootBand(currentRoot)
  drawSunburst()
}

/**
 * Réinitialise le zoom
 * Retourne à la vue complète de toutes les catégories
 */
function resetZoom() {
  // Vérifier que les données sont valides
  if (!props.data || !props.data.children || !Array.isArray(props.data.children) || props.data.children.length === 0) {
    console.warn('Sunburst: Impossible de réinitialiser, données invalides')
    return
  }

  currentRoot = d3.hierarchy(cloneDataForSunburstPartition())
    .sum(leafValueForPartition)
    .sort((a, b) => (b.value || 0) - (a.value || 0))

  partition(currentRoot)
  removeUnpaintedRootBand(currentRoot)

  zoomStack = []
  currentPath.value = []

  resetGeometricZoom()
  // Redessiner le graphique
  drawSunburst()
}

/**
 * Redimensionne le SVG et recalcule la partition **sans** détruire le DOM ni réinitialiser
 * le zoom — sinon ResizeObserver (hauteur du tableau de catégories, etc.) relançait
 * initSunburst() et donnait l’impression d’un « rechargement » + perte du focus.
 */
function resizeSunburst() {
  if (!svgRef.value || !g || !currentRoot) return

  const dim = getDrawSize()
  width = dim.width
  height = dim.height
  radius = Math.min(width, height) / 2 - 10

  d3.select(svgRef.value)
    .attr('width', width)
    .attr('height', height)
    .attr('viewBox', `0 0 ${width} ${height}`)

  g.attr('transform', `translate(${width / 2},${height / 2})`)

  partition.size([2 * Math.PI, radius])
  partition(currentRoot)
  removeUnpaintedRootBand(currentRoot)
  if (svg) {
    geometricZoomK = d3.zoomTransform(svg.node()).k
  }
  drawSunburst()
}

/**
 * Redimensionnement fenêtre / conteneur : conserver currentRoot (vue zoomée ou non).
 */
function handleResize() {
  if (!svgRef.value) return
  if (resizeDebounceId !== null) {
    clearTimeout(resizeDebounceId)
  }
  resizeDebounceId = window.setTimeout(() => {
    resizeDebounceId = null
    nextTick(() => {
      if (g && currentRoot) {
        resizeSunburst()
      } else {
        initSunburst()
      }
    })
  }, 120)
}

/** ResizeObserver : redimensionne le graphique quand la carte / la fenêtre change de largeur */
let resizeObserver = null

onMounted(() => {
  nextTick(() => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        initSunburst()
      })
    })
  })

  window.addEventListener('resize', handleResize)

  nextTick(() => {
    if (containerRef.value && typeof ResizeObserver !== 'undefined') {
      resizeObserver = new ResizeObserver(() => handleResize())
      resizeObserver.observe(containerRef.value)
    }
  })
})

onUnmounted(() => {
  if (zoomLabelsRafId != null) {
    cancelAnimationFrame(zoomLabelsRafId)
    zoomLabelsRafId = null
  }
  clearTooltipHideTimer()
  detachWheelPageScrollWithoutCtrl()
  const el = containerRef.value
  if (resizeObserver) {
    if (el) resizeObserver.unobserve(el)
    resizeObserver.disconnect()
    resizeObserver = null
  }
  window.removeEventListener('resize', handleResize)
  if (resizeDebounceId !== null) {
    clearTimeout(resizeDebounceId)
  }
})

/**
 * Surveiller les changements de données
 * Réinitialiser le graphique quand les données changent
 */
watch(
  () => [props.data, props.weightByTickets],
  ([newData]) => {
    zoomStack = []
    currentPath.value = []
    if (newData && newData.children && Array.isArray(newData.children) && newData.children.length > 0) {
      nextTick(() => initSunburst())
    } else if (svgRef.value) {
      d3.select(svgRef.value).selectAll('*').remove()
    }
  },
  { deep: true }
)
</script>

<style scoped>
/* Conteneur principal du graphique Sunburst */
.sunburst-container {
  width: 100%;
  height: 100%;
  min-height: 600px;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: flex-start;
}

/* SVG : dimensions fixées par D3 (carré = largeur du conteneur) ; pas de min-height pour éviter le décalage */
.sunburst-svg {
  display: block;
  width: 100%;
  max-width: 100%;
  height: auto;
  vertical-align: top;
}

/* Libellés sur les arcs : contour puis remplissage, jointures arrondies (lisibilité sur secteurs colorés) */
.sunburst-svg :deep(text.sunburst-arc-label) {
  paint-order: stroke fill;
  stroke-linejoin: round;
}

/* Tooltip au survol */
.sunburst-tooltip {
  position: fixed;
  left: 0;
  top: 0;
  margin: 0;
  background: rgba(0, 0, 0, 0.85);
  color: white;
  padding: 10px 15px;
  border-radius: 5px;
  pointer-events: none;
  z-index: 20000;
  font-size: 14px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  max-width: min(360px, calc(100vw - 24px));
}

.tooltip-content {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.tooltip-content strong {
  font-size: 16px;
  margin-bottom: 5px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.3);
  padding-bottom: 5px;
}

.sunburst-tooltip .tooltip-row {
  margin-top: 4px;
  font-size: 13px;
  line-height: 1.35;
}

/* Contrôles du graphique */
.sunburst-controls {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.sunburst-controls-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  align-items: center;
}

.reset-button {
  padding: 8px 16px;
  background: var(--sunburst-reset-bg);
  color: #ffffff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.3s;
}

.reset-button:hover {
  background: var(--sunburst-reset-hover);
}

.sunburst-info {
  font-size: 12px;
  color: var(--sunburst-info-text);
  text-align: center;
  max-width: 600px;
  word-break: break-word;
}

.sunburst-zoom-hint {
  margin: 10px 0 0 0;
  font-size: 11px;
  color: var(--sunburst-info-text);
  text-align: center;
  line-height: 1.35;
  max-width: 640px;
}
</style>
