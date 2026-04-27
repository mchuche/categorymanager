<template>
  <div class="dashboard-container">
    <!-- En-tête : thème + plein écran (session = session GLPI de la page, pas de déconnexion locale) -->
    <header class="dashboard-header">
      <h1>CategorieManager - Visualisation GLPI</h1>
      <div class="dashboard-header-actions">
        <ThemeToggle />
        <!--
          Plein écran : uniquement ici (en-tête). Le graphique Sunburst n’a pas de second bouton
          sous le visuel — évite le doublon « en bas du graphique ».
        -->
        <button
          v-if="showSunburstFullscreenButton"
          type="button"
          class="theme-toolbar-btn"
          :aria-pressed="isSunburstFullscreen"
          :aria-label="isSunburstFullscreen ? 'Quitter le plein écran' : 'Afficher le graphique en plein écran'"
          :title="isSunburstFullscreen ? 'Quitter le plein écran (Échap)' : 'Afficher le graphique en plein écran'"
          @click="toggleSunburstFullscreen"
        >
          <ToolbarIcon :name="isSunburstFullscreen ? 'minimize' : 'maximize'" />
          <span class="sr-only">{{
            isSunburstFullscreen ? 'Quitter le plein écran' : 'Plein écran'
          }}</span>
        </button>
      </div>
    </header>

    <!-- Zone de chargement initial (plein écran) : étapes détaillées dans loadingVerbose -->
    <div v-if="isLoading" class="loading-container">
      <div class="spinner"></div>
      <p class="loading-title">Chargement des catégories</p>
      <p class="loading-detail">{{ loadingVerbose }}</p>
    </div>

    <!-- Message d'erreur -->
    <div v-else-if="errorMessage" class="error-container">
      <p class="error-text">{{ errorMessage }}</p>
      <button @click="loadData" class="retry-button">Réessayer</button>
    </div>

    <!-- Contenu principal : catégories ITIL (pleine largeur) -->
    <div v-else class="content-container">
      <div class="categories-container">
        <div class="categories-card">
          <h2>Catégories ITIL</h2>

          <!--
            Données en cache (localStorage) : date de dernière synchro + bouton actualiser.
            Alerte visuelle si le cache dépasse ~1 mois (CACHE_STALE_AFTER_MS, voir categoriesCache.js).
          -->
          <div
            v-if="categories.length && cacheSnapshotSavedAt"
            class="cache-info-banner"
            :class="{ 'cache-info-banner--stale': cacheIsStale && !isRefreshing }"
          >
            <span class="cache-info-banner__text">
              <template v-if="isRefreshing">Actualisation des données depuis GLPI…</template>
              <template v-else>
                Affichage des données du <strong>{{ cacheDisplayLabel }}</strong>
                <span v-if="dataFromCache" class="cache-info-banner__hint"> (depuis le cache local)</span>
                <span v-if="cacheIsStale" class="cache-info-banner__stale-hint"> — mise à jour recommandée</span>
              </template>
            </span>
            <button
              type="button"
              class="cache-info-banner__btn"
              :disabled="isRefreshing"
              @click="refreshCategoriesFromServer"
            >
              Actualiser
            </button>
            <span v-if="refreshError" class="cache-info-banner__err" role="alert">{{ refreshError }}</span>
          </div>
          
          <!-- Message de chargement des catégories -->
          <div v-if="isLoadingCategories" class="loading-categories">
            <div class="spinner-small"></div>
            <p class="loading-title">Chargement des catégories</p>
            <p class="loading-detail">{{ loadingVerbose }}</p>
          </div>
          
          <!-- Message d'erreur pour les catégories -->
          <div v-else-if="categoriesError" class="error-categories">
            <p class="error-text">{{ categoriesError }}</p>
            <button type="button" class="retry-button" @click="loadCategories({ silent: false })">
              Réessayer
            </button>
          </div>
          
          <!-- Affichage des catégories -->
          <div v-else-if="categories && categories.length > 0" class="categories-list">
            <!-- Une seule barre : compteur + onglets (gain de hauteur) -->
            <div class="categories-toolbar">
              <span class="categories-count" title="Nombre de catégories chargées depuis GLPI">
                <strong>{{ categories.length }}</strong> catégorie(s)
              </span>
              <nav class="view-tabs" aria-label="Type de vue">
                <button
                  @click="viewMode = 'sunburst'"
                  :class="['tab-button', { active: viewMode === 'sunburst' }]"
                  type="button"
                >
                  Sunburst
                </button>
                <button
                  @click="viewMode = 'table'"
                  :class="['tab-button', { active: viewMode === 'table' }]"
                  type="button"
                >
                  Tableau
                </button>
                <button
                  @click="viewMode = 'tree'"
                  :class="['tab-button', { active: viewMode === 'tree' }]"
                  type="button"
                >
                  Arbre
                </button>
                <button
                  @click="viewMode = 'heatmap'"
                  :class="['tab-button', { active: viewMode === 'heatmap' }]"
                  type="button"
                  title="Carte de chaleur : volume par branche sur 12 mois glissants"
                >
                  12 mois
                </button>
                <button
                  @click="viewMode = 'heatmapGroups'"
                  :class="['tab-button', { active: viewMode === 'heatmapGroups' }]"
                  type="button"
                  title="Tickets résolus ou clos par groupe assigné sur 12 mois glissants"
                >
                  Groupes
                </button>
              </nav>
            </div>

            <!-- Recherche : uniquement pour le tableau -->
            <div v-if="viewMode === 'table'" class="categories-controls">
              <input
                v-model="searchQuery"
                type="text"
                placeholder="Rechercher une catégorie..."
                class="search-input"
              />
            </div>

            <!-- Vue Sunburst : ligne compacte puis graphique dans un shell ciblé par l’API Fullscreen (bouton dans l’en-tête) -->
            <div v-if="viewMode === 'sunburst'" class="categories-sunburst-container">
              <div class="sunburst-top-row">
                <div
                  class="sunburst-mode-toggle"
                  role="group"
                  aria-label="Mode d'affichage du sunburst"
                >
                  <span class="sunburst-mode-label">Affichage</span>
                  <button
                    type="button"
                    :class="['sunburst-mode-btn', { 'sunburst-mode-btn--active': !sunburstWeightByTickets }]"
                    @click="sunburstWeightByTickets = false"
                  >
                    Structure
                  </button>
                  <button
                    type="button"
                    :class="['sunburst-mode-btn', { 'sunburst-mode-btn--active': sunburstWeightByTickets }]"
                    @click="sunburstWeightByTickets = true"
                  >
                    Tickets
                  </button>
                </div>
                <p
                  v-if="sunburstWeightByTickets"
                  class="sunburst-hint-inline"
                  title="Secteurs proportionnels au nombre de tickets par branche (total incluant les sous-catégories)."
                >
                  Proportionnel aux tickets par branche.
                </p>
                <p
                  v-else
                  class="sunburst-hint-inline"
                  title="Secteurs selon la hiérarchie uniquement (angles liés aux feuilles), sans pondération par volume de tickets."
                >
                  Vue structure (angles hiérarchiques).
                </p>
              </div>
              <!--
                Période uniquement pour ce Sunburst (découplée du tableau / arbre).
                Cache local sans expiration automatique ; API uniquement si pas de cache ou clic « Rafraîchir ».
              -->
              <div v-if="sunburstWeightByTickets" class="sunburst-period-row">
                <div class="sunburst-period-head">
                  <span id="sunburst-period-label" class="sunburst-period-label">Période (Sunburst uniquement)</span>
                  <button
                    v-if="sunburstPeriodIsFiltered"
                    type="button"
                    class="sunburst-period-refresh-btn"
                    :disabled="sunburstPeriodLoading || isLoadingCategories || isRefreshing"
                    title="Relancer toutes les requêtes de comptage vers GLPI pour cette période"
                    @click="refreshSunburstPeriodCountsFromServer"
                  >
                    Rafraîchir les compteurs
                  </button>
                </div>
                <div
                  class="sunburst-period-chips"
                  role="group"
                  :aria-labelledby="'sunburst-period-label'"
                >
                  <button
                    v-for="(step, i) in SUNBURST_PERIOD_STEPS"
                    :key="step.id"
                    type="button"
                    class="sunburst-period-chip"
                    :class="{ 'sunburst-period-chip--active': sunburstPeriodIndex === i }"
                    :disabled="isLoadingCategories || isRefreshing || sunburstPeriodLoading"
                    :title="step.hint"
                    @click="selectSunburstPeriod(i)"
                  >
                    {{ step.shortLabel }}
                  </button>
                </div>
                <p class="sunburst-period-current" aria-live="polite">
                  <strong>{{ SUNBURST_PERIOD_STEPS[sunburstPeriodIndex]?.shortLabel ?? '—' }}</strong>
                  <span class="sunburst-period-current-hint">
                    — {{ SUNBURST_PERIOD_STEPS[sunburstPeriodIndex]?.hint }}
                  </span>
                </p>
                <p v-if="sunburstPeriodError" class="sunburst-period-err" role="alert">{{ sunburstPeriodError }}</p>
                <p class="sunburst-period-note">
                  Indépendant du <strong>tableau</strong> et de l’<strong>arbre</strong> (toujours historique complet).
                  Les compteurs par période sont mis en cache <strong>sans expiration automatique</strong> ; un nouvel appel
                  GLPI n’a lieu que s’il n’y a pas encore de données locales pour cette période, ou si vous cliquez sur
                  <strong>Rafraîchir les compteurs</strong>.
                  Filtre sur la <strong>date d’ouverture</strong> (GLPI peut utiliser <code>date_creation</code> en secours).
                </p>
              </div>
              <div ref="sunburstShellRef" class="sunburst-shell sunburst-shell--chart">
                <div
                  v-if="sunburstWeightByTickets && sunburstPeriodChartOverlay"
                  class="sunburst-period-overlay"
                  aria-busy="true"
                >
                  <div class="spinner-small"></div>
                  <span>Comptage pour la période…</span>
                </div>
                <SunburstChart
                  :key="`sunburst-${sunburstWeightByTickets ? 'tickets' : 'structure'}-${sunburstPeriodIndex}`"
                  :data="sunburstData"
                  :weight-by-tickets="sunburstWeightByTickets"
                />
              </div>
            </div>

            <!-- Vue tableau : tri au clic sur les en-têtes de colonnes -->
            <div v-else-if="viewMode === 'table'" class="categories-table-container">
              <table class="categories-table">
                <thead>
                  <tr>
                    <th
                      scope="col"
                      :aria-sort="ariaSortFor('id')"
                    >
                      <button
                        type="button"
                        class="th-sort-btn"
                        @click="toggleTableSort('id')"
                      >
                        ID
                        <span class="th-sort-icon" aria-hidden="true">{{ sortIconFor('id') }}</span>
                      </button>
                    </th>
                    <th
                      scope="col"
                      :aria-sort="ariaSortFor('name')"
                    >
                      <button
                        type="button"
                        class="th-sort-btn"
                        @click="toggleTableSort('name')"
                      >
                        Nom
                        <span class="th-sort-icon" aria-hidden="true">{{ sortIconFor('name') }}</span>
                      </button>
                    </th>
                    <th
                      scope="col"
                      :aria-sort="ariaSortFor('parent')"
                    >
                      <button
                        type="button"
                        class="th-sort-btn"
                        @click="toggleTableSort('parent')"
                      >
                        Catégorie parente
                        <span class="th-sort-icon" aria-hidden="true">{{ sortIconFor('parent') }}</span>
                      </button>
                    </th>
                    <th
                      scope="col"
                      :aria-sort="ariaSortFor('level')"
                    >
                      <button
                        type="button"
                        class="th-sort-btn"
                        @click="toggleTableSort('level')"
                      >
                        Niveau
                        <span class="th-sort-icon" aria-hidden="true">{{ sortIconFor('level') }}</span>
                      </button>
                    </th>
                    <th
                      scope="col"
                      :aria-sort="ariaSortFor('tickets')"
                    >
                      <button
                        type="button"
                        class="th-sort-btn"
                        :title="'Tickets ouverts sur cette catégorie uniquement (sans les sous-catégories)'"
                        @click="toggleTableSort('tickets')"
                      >
                        Tickets (direct)
                        <span class="th-sort-icon" aria-hidden="true">{{ sortIconFor('tickets') }}</span>
                      </button>
                    </th>
                    <th
                      scope="col"
                      :aria-sort="ariaSortFor('branch')"
                    >
                      <button
                        type="button"
                        class="th-sort-btn"
                        :title="'Somme : tickets directs + tickets comptés sur toutes les sous-catégories (même logique que le Sunburst « Tickets »)'"
                        @click="toggleTableSort('branch')"
                      >
                        Total branche
                        <span class="th-sort-icon" aria-hidden="true">{{ sortIconFor('branch') }}</span>
                      </button>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr 
                    v-for="category in filteredAndSortedCategories" 
                    :key="category.id"
                    class="category-row"
                  >
                    <td>{{ category.id }}</td>
                    <td class="category-name">{{ category.name || 'Sans nom' }}</td>
                    <td class="parent-cell">{{ parentDisplayLabel(category) }}</td>
                    <td>{{ category.level || '-' }}</td>
                    <td class="ticket-count">{{ category.ticketCount !== undefined ? category.ticketCount : '-' }}</td>
                    <td class="ticket-count">{{ category.totalTicketCount !== undefined ? category.totalTicketCount : '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Vue arbre -->
            <div v-else-if="viewMode === 'tree'" class="categories-tree-container">
              <div class="tree-wrapper">
                <CategoryTreeNode 
                  v-for="rootNode in categoryTree" 
                  :key="rootNode.id"
                  :node="rootNode"
                  :level="0"
                />
              </div>
            </div>

            <!-- Carte de chaleur temporelle (12 mois glissants, agrégation par racines métier) -->
            <div v-else-if="viewMode === 'heatmap'" class="categories-heatmap-container">
              <p class="heatmap-intro">
                Volume de tickets par <strong>branche</strong> (catégorie + sous-arbres) sur les
                <strong>12 derniers mois</strong> (fenêtre glissante jusqu’à aujourd’hui). Utilisez
                <strong>▶ / ▼</strong> pour afficher les sous-catégories sous chaque racine métier. La date utilisée
                est celle d’<strong>ouverture</strong> du ticket (champ détecté dans GLPI :
                <code>date</code> ou <code>date_creation</code>).
              </p>
              <div
                v-if="heatmapMatrix && !heatmapLoading"
                class="heatmap-cache-bar"
              >
                <span v-if="heatmapCacheDisplayLabel" class="heatmap-cache-bar__text">
                  Données du <strong>{{ heatmapCacheDisplayLabel }}</strong>
                  <span v-if="heatmapFromDiskCache" class="heatmap-cache-bar__hint"> (cache local 12 mois)</span>
                </span>
                <button
                  type="button"
                  class="heatmap-cache-bar__btn"
                  :disabled="heatmapLoading"
                  title="Recharger toutes les requêtes (12 mois × catégories)"
                  @click="refreshHeatmapFromServer"
                >
                  Rafraîchir les 12 mois
                </button>
              </div>
              <div
                v-if="heatmapMatrix && !heatmapLoading"
                class="heatmap-sort-bar"
              >
                <label class="heatmap-sort-bar__label" for="heatmap-sort-categories">Trier les lignes</label>
                <select
                  id="heatmap-sort-categories"
                  v-model="heatmapSortMode"
                  class="heatmap-sort-bar__select"
                  aria-describedby="heatmap-sort-hint-cat"
                >
                  <option
                    v-for="opt in HEATMAP_SORT_OPTIONS_CATEGORIES"
                    :key="opt.value"
                    :value="opt.value"
                  >
                    {{ opt.label }}
                  </option>
                </select>
                <span id="heatmap-sort-hint-cat" class="heatmap-sort-bar__hint">
                  Ordre des <strong>racines métier</strong> selon le tri ; sous chaque racine dépliée, ordre
                  d’arbre GLPI. Affichage seul (ne modifie pas GLPI).
                </span>
              </div>
              <div v-if="heatmapLoading" class="heatmap-loading">
                <div class="spinner-small"></div>
                <p class="loading-detail">{{ heatmapStatus }}</p>
              </div>
              <p v-else-if="heatmapError" class="error-text">{{ heatmapError }}</p>
              <!--
                Mode hiérarchique : colonne HTML (arbre repliable) + grille D3 sans libellés à gauche.
                Anciens caches sans tree/monthlyDirectCounts : une seule colonne comme avant.
              -->
              <div
                v-else-if="heatmapMatrix && heatmapMatrixDisplay"
                class="heatmap-body"
                :class="{ 'heatmap-body--with-tree': heatmapCategoriesHierarchical && heatmapMatrixDisplay.heatmapRowsMeta?.length }"
                :style="
                  heatmapCategoriesHierarchical && heatmapMatrixDisplay.heatmapRowsMeta?.length
                    ? { '--heatmap-row-px': heatmapLabelRowHeight + 'px' }
                    : undefined
                "
              >
                <!--
                  Conteneur commun scroll : la colonne libellés et le graphique défilent ensemble
                  (sinon le scroll seul sur l’aside désaligne les noms et les lignes colorées).
                -->
                <div
                  v-if="heatmapCategoriesHierarchical && heatmapMatrixDisplay.heatmapRowsMeta?.length"
                  class="heatmap-paired-scroll"
                  @mouseleave="heatmapHoveredRowIndex = null"
                >
                  <aside
                    class="heatmap-tree-labels heatmap-tree-labels--paired"
                    aria-label="Arbre des catégories et volumes par branche"
                  >
                    <div class="heatmap-tree-labels-toolbar">
                      <button
                        type="button"
                        class="heatmap-tree-collapse-all"
                        :disabled="heatmapExpandedIds.size === 0"
                        title="Masquer toutes les sous-catégories"
                        @click="collapseAllHeatmapExpand"
                      >
                        Replier tout
                      </button>
                    </div>
                    <ul class="heatmap-tree-labels-list" role="list">
                      <li
                        v-for="(row, rowIndex) in heatmapMatrixDisplay.heatmapRowsMeta"
                        :key="`${row.id}-${row.depth}`"
                        class="heatmap-tree-labels-row"
                        :class="{ 'heatmap-tree-labels-row--hl': heatmapHoveredRowIndex === rowIndex }"
                        @mouseenter="heatmapHoveredRowIndex = rowIndex"
                      >
                      <div
                        class="heatmap-tree-labels-line"
                        :style="{ paddingLeft: row.depth * 14 + 6 + 'px' }"
                      >
                        <!-- Bouton seulement si des enfants existent dans l’arbre GLPI -->
                        <button
                          v-if="row.hasChildren"
                          type="button"
                          class="heatmap-tree-toggle"
                          :aria-expanded="heatmapExpandedIds.has(row.id)"
                          :aria-label="
                            (heatmapExpandedIds.has(row.id) ? 'Replier' : 'Déplier') + ' la branche ' + row.name
                          "
                          @click="toggleHeatmapExpand(row.id)"
                        >
                          {{ heatmapExpandedIds.has(row.id) ? '▼' : '▶' }}
                        </button>
                        <span v-else class="heatmap-tree-toggle-spacer" aria-hidden="true" />
                        <span class="heatmap-tree-label-text" :title="row.name">{{ row.name }}</span>
                      </div>
                      </li>
                    </ul>
                  </aside>
                  <div class="heatmap-chart-panel">
                    <TemporalHeatmapChart
                      :key="heatmapChartRenderKey"
                      :matrix="heatmapMatrixDisplay"
                      :selected-month-index="heatmapMonthIndex"
                      :hide-row-labels="true"
                      :highlighted-row-index="
                        heatmapHoveredRowIndex === null ? -1 : heatmapHoveredRowIndex
                      "
                      @update:selected-month-index="heatmapMonthIndex = $event"
                    />
                  </div>
                </div>
                <!-- Ancien cache sans méta hiérarchique : graphique seul avec libellés dans le SVG -->
                <div v-else class="heatmap-chart-panel">
                  <TemporalHeatmapChart
                    :matrix="heatmapMatrixDisplay"
                    :selected-month-index="heatmapMonthIndex"
                    :hide-row-labels="false"
                    @update:selected-month-index="heatmapMonthIndex = $event"
                  />
                </div>
              </div>
            </div>

            <!-- Carte de chaleur : tickets résolus/fermés par groupe assigné (12 mois) -->
            <div v-else-if="viewMode === 'heatmapGroups'" class="categories-heatmap-container">
              <p class="heatmap-intro">
                Nombre de tickets <strong>résolus</strong> ou <strong>clos</strong> (statuts GLPI 5 et 6) par
                <strong>groupe assigné</strong>, sur les <strong>12 derniers mois</strong> (fenêtre glissante). La date
                retenue est la <strong>date de résolution</strong> (<code>solvedate</code>). Seuls les groupes ayant au
                moins un ticket sur la période apparaissent.
              </p>
              <div
                v-if="heatmapGroupsMatrix !== null && !heatmapGroupsLoading"
                class="heatmap-cache-bar"
              >
                <span v-if="heatmapGroupsCacheDisplayLabel" class="heatmap-cache-bar__text">
                  Données du <strong>{{ heatmapGroupsCacheDisplayLabel }}</strong>
                  <span v-if="heatmapGroupsFromDiskCache" class="heatmap-cache-bar__hint"> (cache local groupes)</span>
                </span>
                <button
                  type="button"
                  class="heatmap-cache-bar__btn"
                  :disabled="heatmapGroupsLoading"
                  title="Recharger la liste des groupes et tous les comptages (12 mois × groupes)"
                  @click="refreshHeatmapGroupsFromServer"
                >
                  Rafraîchir groupes
                </button>
              </div>
              <div
                v-if="heatmapGroupsMatrix !== null && !heatmapGroupsLoading && heatmapGroupsMatrix.rowLabels.length > 0"
                class="heatmap-sort-bar"
              >
                <label class="heatmap-sort-bar__label" for="heatmap-sort-groups">Trier les lignes</label>
                <select
                  id="heatmap-sort-groups"
                  v-model="heatmapGroupsSortMode"
                  class="heatmap-sort-bar__select"
                  aria-describedby="heatmap-sort-hint-grp"
                >
                  <option
                    v-for="opt in HEATMAP_SORT_OPTIONS_GROUPS"
                    :key="opt.value"
                    :value="opt.value"
                  >
                    {{ opt.label }}
                  </option>
                </select>
                <span id="heatmap-sort-hint-grp" class="heatmap-sort-bar__hint">
                  Affichage seul ; l’ordre par défaut suit le chargement API (souvent A→Z).
                </span>
              </div>
              <div v-if="heatmapGroupsLoading" class="heatmap-loading">
                <div class="spinner-small"></div>
                <p class="loading-detail">{{ heatmapGroupsStatus }}</p>
              </div>
              <p v-else-if="heatmapGroupsError" class="error-text">{{ heatmapGroupsError }}</p>
              <p
                v-else-if="heatmapGroupsMatrix && heatmapGroupsMatrix.rowLabels.length === 0"
                class="heatmap-empty-msg"
              >
                Aucun ticket résolu ou clos par groupe assigné sur cette fenêtre de 12 mois (vérifiez les droits API ou
                élargissez la période en rechargeant plus tard).
              </p>
              <TemporalHeatmapChart
                v-else-if="heatmapGroupsMatrix && heatmapGroupsMatrix.rowLabels.length > 0"
                :matrix="heatmapGroupsMatrixDisplay"
                :selected-month-index="heatmapGroupsMonthIndex"
                :legend-hint="heatmapGroupsLegendHint"
                slider-input-id="heatmap-groups-month-slider"
                heatmap-aria-label="Carte de chaleur des tickets résolus ou clos par groupe et par mois"
                @update:selected-month-index="heatmapGroupsMonthIndex = $event"
              />
            </div>
            
            <!-- Section debug : données brutes -->
            <details class="debug-section">
              <summary>Données brutes des catégories (debug)</summary>
              <pre>{{ JSON.stringify(categories.slice(0, 5), null, 2) }}</pre>
              <p class="debug-note">Affichage des 5 premières catégories uniquement</p>
            </details>
          </div>
          
          <!-- Message si aucune catégorie -->
          <div v-else class="no-categories">
            <p>Aucune catégorie trouvée</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useAuthStore } from '../stores/auth'
import glpiApi from '../services/glpiApi'
import { transformFlatToTree, computeBranchTicketTotalsByCategoryId } from '../services/treeTransform'
import {
  getLast12MonthRanges,
  buildRootBranchMatrix,
  buildGroupHeatmapMatrix,
  getDateRangeForTicketPeriodPreset,
  cloneTreeForHeatmapCache,
  getHeatmapTreeRootForWalk,
  buildVisibleCategoryHeatmapMatrix,
  heatmapCellHeight
} from '../services/temporalHeatmapData'
import {
  readCategoriesCache,
  writeCategoriesCache,
  clearCategoriesCache,
  CACHE_STALE_AFTER_MS
} from '../services/categoriesCache'
import {
  readHeatmap12Cache,
  writeHeatmap12Cache,
  clearHeatmap12Cache,
  heatmapWindowKey,
  heatmapCategoryIdsKey
} from '../services/heatmap12Cache'
import {
  readHeatmap12GroupsCache,
  writeHeatmap12GroupsCache,
  clearHeatmap12GroupsCache,
  heatmapGroupIdsKey
} from '../services/heatmap12GroupsCache'
import { SUNBURST_PERIOD_STEPS, sunburstPeriodIdFromIndex } from '../services/sunburstPeriodPresets'
import {
  readSunburstPeriodIndex,
  writeSunburstPeriodIndex,
  clearSunburstPeriodIndexStorage
} from '../services/sunburstPeriodStorage'
import {
  readSunburstCountsCache,
  writeSunburstCountsCache,
  clearSunburstCountsCache,
  sunburstCategoryIdsKey
} from '../services/sunburstCountsCache'
import { clearServerHttpCache } from '../services/serverCache'
import { formatApiError } from '../utils/formatApiError'
import CategoryTreeNode from './CategoryTreeNode.vue'
import SunburstChart from './SunburstChart.vue'
import ThemeToggle from './ThemeToggle.vue'
import ToolbarIcon from './ToolbarIcon.vue'
import TemporalHeatmapChart from './TemporalHeatmapChart.vue'
import {
  sortHeatmapMatrix,
  HEATMAP_SORT,
  HEATMAP_SORT_OPTIONS_CATEGORIES,
  HEATMAP_SORT_OPTIONS_GROUPS
} from '../services/heatmapSort'

// État du composant
const isLoading = ref(false)
const errorMessage = ref('')

/**
 * Libellé d’étape affiché pendant le chargement (plein écran ou carte « Réessayer ») :
 * API, hiérarchie, compteurs tickets avec progression.
 */
const loadingVerbose = ref('Initialisation…')

// État pour les catégories ITIL
const categories = ref([])
const isLoadingCategories = ref(false)
const categoriesError = ref('')
const searchQuery = ref('')
/** Colonne de tri du tableau (clic sur en-tête) : id, name, parent, level, tickets, branch */
const tableSortKey = ref('id')
/** Ordre de tri pour le tableau */
const tableSortDir = ref('asc')

/** 'table' | 'tree' | 'sunburst' | 'heatmap' | 'heatmapGroups' */
const viewMode = ref('sunburst')

/** Carte de chaleur temporelle : matrice chargée à la demande (nombreuses requêtes GLPI) */
const heatmapMatrix = ref(null)
const heatmapLoading = ref(false)
const heatmapError = ref('')
const heatmapStatus = ref('')
/** Après rechargement des catégories, il faut regénérer la chaleur */
const heatmapLoadedOnce = ref(false)
/** Mois mis en avant dans le graphique (0 = le plus ancien des 12) */
const heatmapMonthIndex = ref(11)
/** Dernière sauvegarde cache heatmap (ISO) */
const heatmapCacheSavedAt = ref(null)
/** Affichage immédiat issu du localStorage (avant synchro API) */
const heatmapFromDiskCache = ref(false)

/**
 * Nœuds de l’arbre « dépliés » dans la heatmap (ids catégorie).
 * Nouveau Set à chaque toggle pour la réactivité Vue.
 */
const heatmapExpandedIds = ref(new Set())

/** Index de ligne survolée (liste à gauche) → surbrillance sur la grille D3 à droite. */
const heatmapHoveredRowIndex = ref(null)

/** Tri des lignes (affichage uniquement ; la matrice source reste inchangée). */
const heatmapSortMode = ref(HEATMAP_SORT.SOURCE)
const heatmapGroupsSortMode = ref(HEATMAP_SORT.SOURCE)

/**
 * True si la matrice contient l’arbre + comptages mensuels (cache récent ou chargement API).
 * Les anciens caches localStorage sans ces champs restent en mode « racines seules ».
 */
const heatmapCategoriesHierarchical = computed(() => {
  const m = heatmapMatrix.value
  return Boolean(m?.monthlyDirectCounts?.length && m?.tree)
})

/**
 * Matrice affichée : hiérarchique (nœuds visibles selon heatmapExpandedIds) ou legacy.
 * Pour le mode arbre : l’ordre des **racines** suit toujours le mode de tri (volume total, etc.) ;
 * les **sous-nœuds** restent en ordre d’arbre sous le parent déplié — ainsi une racine ne change
 * pas de rang quand on la déplie (avant : retour à l’ordre GLPI brut).
 */
const heatmapMatrixDisplay = computed(() => {
  const raw = heatmapMatrix.value
  if (!raw?.rowLabels?.length) return null

  if (heatmapCategoriesHierarchical.value && categories.value.length) {
    const treeRoot = getHeatmapTreeRootForWalk(raw.tree)
    /** Racines seules, ordre arbre — puis tri pour obtenir l’ordre des ids racines à figer. */
    const rootsOnlyBase = buildVisibleCategoryHeatmapMatrix(
      categories.value,
      raw.monthlyDirectCounts,
      raw.columnLabels,
      treeRoot,
      new Set(),
      null
    )
    const sortedRootsOnly = sortHeatmapMatrix(
      rootsOnlyBase,
      heatmapSortMode.value,
      heatmapMonthIndex.value
    )
    const rootOrder = sortedRootsOnly?.rootIds?.length ? sortedRootsOnly.rootIds : null

    return buildVisibleCategoryHeatmapMatrix(
      categories.value,
      raw.monthlyDirectCounts,
      raw.columnLabels,
      treeRoot,
      heatmapExpandedIds.value,
      rootOrder
    )
  }

  const base = {
    rowLabels: raw.rowLabels,
    columnLabels: raw.columnLabels,
    values: raw.values,
    rootIds: raw.rootIds
  }
  return sortHeatmapMatrix(base, heatmapSortMode.value, heatmapMonthIndex.value)
})

/** Hauteur d’une ligne de libellé (alignée sur la grille D3 via heatmapCellHeight). */
const heatmapLabelRowHeight = computed(() => {
  const m = heatmapMatrixDisplay.value
  if (!m?.rowLabels?.length) return 24
  return heatmapCellHeight(m.rowLabels.length)
})

/** Bascule l’expansion d’une catégorie dans la colonne arbre de la heatmap. */
function toggleHeatmapExpand(id) {
  const s = new Set(heatmapExpandedIds.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  heatmapExpandedIds.value = s
}

/** Replier toutes les branches (retour aux seules racines métier visibles). */
function collapseAllHeatmapExpand() {
  heatmapExpandedIds.value = new Set()
}

/**
 * Clé de rendu pour forcer TemporalHeatmapChart à recréer le SVG quand le nombre de lignes
 * ou l’état d’expansion change (évite un décalage D3 / réactivité profonde).
 */
const heatmapChartRenderKey = computed(() => {
  const m = heatmapMatrixDisplay.value
  const n = m?.rowLabels?.length ?? 0
  const ids = [...heatmapExpandedIds.value].map(String).sort().join(',')
  return `${n}-${ids}`
})

const heatmapGroupsMatrixDisplay = computed(() =>
  sortHeatmapMatrix(
    heatmapGroupsMatrix.value,
    heatmapGroupsSortMode.value,
    heatmapGroupsMonthIndex.value
  )
)

/** Heatmap « groupes assignés » : même logique de cache / rafraîchissement manuel que l’onglet 12 mois catégories. */
const heatmapGroupsMatrix = ref(null)
const heatmapGroupsLoading = ref(false)
const heatmapGroupsError = ref('')
const heatmapGroupsStatus = ref('')
const heatmapGroupsLoadedOnce = ref(false)
const heatmapGroupsMonthIndex = ref(11)
const heatmapGroupsCacheSavedAt = ref(null)
const heatmapGroupsFromDiskCache = ref(false)

/** Texte d’aide sous le graphique D3 (métrique + champs GLPI). */
const heatmapGroupsLegendHint =
  'Intensité = nombre de tickets résolus (5) ou clos (6) pour le mois, selon la date de résolution (solvedate) et le groupe assigné au ticket.'

const heatmapGroupsCacheDisplayLabel = computed(() => {
  if (!heatmapGroupsCacheSavedAt.value) return ''
  try {
    return new Date(heatmapGroupsCacheSavedAt.value).toLocaleString('fr-FR', {
      dateStyle: 'short',
      timeStyle: 'short'
    })
  } catch {
    return ''
  }
})

const heatmapCacheDisplayLabel = computed(() => {
  if (!heatmapCacheSavedAt.value) return ''
  try {
    return new Date(heatmapCacheSavedAt.value).toLocaleString('fr-FR', {
      dateStyle: 'short',
      timeStyle: 'short'
    })
  } catch {
    return ''
  }
})

/** Cache local : affichage immédiat puis rafraîchissement API en arrière-plan */
const dataFromCache = ref(false)
/** Horodatage ISO de la dernière sauvegarde affichée (cache ou réseau) */
const cacheSnapshotSavedAt = ref(null)
const isRefreshing = ref(false)
const refreshError = ref('')

const cacheDisplayLabel = computed(() => {
  if (!cacheSnapshotSavedAt.value) return ''
  try {
    return new Date(cacheSnapshotSavedAt.value).toLocaleString('fr-FR', {
      dateStyle: 'short',
      timeStyle: 'short'
    })
  } catch {
    return ''
  }
})

/** Données plus anciennes qu’environ 1 mois (CACHE_STALE_AFTER_MS) → « mise à jour recommandée » */
const cacheIsStale = computed(() => {
  if (!cacheSnapshotSavedAt.value) return false
  const t = new Date(cacheSnapshotSavedAt.value).getTime()
  return Date.now() - t > CACHE_STALE_AFTER_MS
})

/**
 * Sunburst : false = structure (angles uniformes par feuille), true = surfaces ∝ tickets (total branche).
 */
const sunburstWeightByTickets = ref(false)

/**
 * Sunburst « Tickets » : période **découplée** du tableau / arbre (historique complet).
 * Période choisie par boutons ; préférence d’index en sessionStorage ; compteurs filtrés en localStorage (sans expiration auto).
 */
const sunburstPeriodIndex = ref(0)
/** Comptages filtrés réservés au Sunburst (null = utiliser categories[].ticketCount = historique) */
const sunburstFilteredCounts = ref(null)
/** id de période ('90d', '1y', …) pour lequel sunburstFilteredCounts est valide */
const sunburstFilteredCountsForPeriodId = ref(null)
const sunburstPeriodLoading = ref(false)
const sunburstPeriodError = ref('')
let sunburstFetchGen = 0

/** True si une période autre que « tout » est sélectionnée (affiche le bouton rafraîchir) */
const sunburstPeriodIsFiltered = computed(
  () => sunburstPeriodIdFromIndex(sunburstPeriodIndex.value) !== 'all'
)

/** Voile de chargement si la série affichée ne correspond pas encore aux compteurs filtrés */
const sunburstPeriodChartOverlay = computed(() => {
  if (!sunburstWeightByTickets.value) return false
  const pid = sunburstPeriodIdFromIndex(sunburstPeriodIndex.value)
  if (pid === 'all') return false
  if (sunburstPeriodLoading.value) return true
  return sunburstFilteredCountsForPeriodId.value !== pid
})

/** Enveloppe du graphique pour l’API Fullscreen (bouton dans l’en-tête de page uniquement) */
const sunburstShellRef = ref(null)
const isSunburstFullscreen = ref(false)

/** Affiche « Plein écran » dans le header uniquement sur l’onglet Sunburst avec des données */
const showSunburstFullscreenButton = computed(() => {
  return (
    !isLoading.value &&
    !errorMessage.value &&
    categories.value.length > 0 &&
    viewMode.value === 'sunburst'
  )
})

function isSunburstShellFullscreen() {
  const el = sunburstShellRef.value
  if (!el) return false
  return (
    document.fullscreenElement === el ||
    document.webkitFullscreenElement === el ||
    document.msFullscreenElement === el
  )
}

function syncSunburstFullscreenState() {
  isSunburstFullscreen.value = isSunburstShellFullscreen()
}

function onSunburstFullscreenChange() {
  syncSunburstFullscreenState()
  window.dispatchEvent(new Event('resize'))
}

async function toggleSunburstFullscreen() {
  const el = sunburstShellRef.value
  if (!el) return
  try {
    if (!isSunburstShellFullscreen()) {
      const req =
        el.requestFullscreen ||
        el.webkitRequestFullscreen ||
        el.msRequestFullscreen
      if (req) await req.call(el)
    } else {
      const exit =
        document.exitFullscreen ||
        document.webkitExitFullscreen ||
        document.msExitFullscreen
      if (exit) await exit.call(document)
    }
  } catch (e) {
    console.warn('Plein écran indisponible ou refusé.', e)
  }
  await nextTick()
  syncSunburstFullscreenState()
  window.dispatchEvent(new Event('resize'))
}

/**
 * Charge les catégories ITIL (seule donnée affichée sur le tableau de bord).
 * Si un cache local existe pour cette URL GLPI : affichage immédiat + actualisation silencieuse.
 */
async function loadData() {
  errorMessage.value = ''
  const authStore = useAuthStore()
  const apiUrl = authStore.getApiUrl()
  const cached = readCategoriesCache(apiUrl)

  if (cached?.categories?.length) {
    categories.value = cached.categories.map((c) => ({ ...c }))
    calculateCategoryLevels()
    cacheSnapshotSavedAt.value = cached.savedAt
    dataFromCache.value = true
    isLoading.value = false
    isLoadingCategories.value = false
    categoriesError.value = ''
    loadingVerbose.value = ''

    loadCategories({ silent: true }).catch((err) => {
      console.error('[Dashboard] Rafraîchissement après cache', err)
    })
    return
  }

  isLoading.value = true
  loadingVerbose.value = 'Préparation du chargement (session GLPI, puis liste des catégories)…'

  try {
    await loadCategories({ silent: false })
  } catch (error) {
    console.error('Erreur lors du chargement des données:', error)
    errorMessage.value = 'Erreur lors du chargement des données: ' + (error.message || 'Erreur inconnue')
  } finally {
    isLoading.value = false
    if (!categoriesError.value) {
      loadingVerbose.value = ''
    }
  }
}

/**
 * Actualisation manuelle depuis la bannière (même logique que le chargement silencieux au démarrage).
 */
async function refreshCategoriesFromServer() {
  refreshError.value = ''
  await clearServerHttpCache()
  loadCategories({ silent: true }).catch((err) => {
    console.error('[Dashboard] Actualiser', err)
  })
}

/**
 * Comptages GLPI pour la période Sunburst (période ≠ tout).
 *
 * @param {{ forceNetwork?: boolean }} opts — `true` : ignorer le cache et relancer les requêtes (sur demande).
 */
async function fetchSunburstPeriodCounts(opts = {}) {
  const forceNetwork = opts.forceNetwork === true
  const periodId = sunburstPeriodIdFromIndex(sunburstPeriodIndex.value)
  if (periodId === 'all' || !categories.value.length) {
    sunburstFilteredCounts.value = null
    sunburstFilteredCountsForPeriodId.value = null
    sunburstPeriodLoading.value = false
    sunburstPeriodError.value = ''
    return
  }
  const range = getDateRangeForTicketPeriodPreset(periodId)
  if (!range) {
    sunburstFilteredCounts.value = null
    sunburstFilteredCountsForPeriodId.value = null
    return
  }

  const authStore = useAuthStore()
  const apiUrl = authStore.getApiUrl()
  const categoryIds = categories.value.map((c) => c.id)
  const cKey = sunburstCategoryIdsKey(categoryIds)

  /** Lecture cache disque uniquement si l’utilisateur n’a pas demandé un rafraîchissement explicite */
  if (!forceNetwork) {
    const cached = readSunburstCountsCache(apiUrl, periodId, cKey)
    if (cached?.counts) {
      sunburstFilteredCounts.value = cached.counts
      sunburstFilteredCountsForPeriodId.value = periodId
      sunburstPeriodLoading.value = false
      sunburstPeriodError.value = ''
      return
    }
  }

  const gen = ++sunburstFetchGen
  sunburstPeriodLoading.value = true
  sunburstPeriodError.value = ''
  try {
    const ticketCounts = await glpiApi.getTicketCountsForCategoriesInDateRange(
      categoryIds,
      range.startStr,
      range.endStr,
      {
        concurrency: 8,
        onProgress: () => {}
      }
    )
    if (gen !== sunburstFetchGen) return
    sunburstFilteredCounts.value = ticketCounts
    sunburstFilteredCountsForPeriodId.value = periodId
    writeSunburstCountsCache(apiUrl, periodId, cKey, ticketCounts)
  } catch (e) {
    if (gen !== sunburstFetchGen) return
    console.error('[Dashboard] Sunburst — comptage par période', e)
    sunburstPeriodError.value = e.message || 'Comptage impossible pour cette période.'
    sunburstFilteredCounts.value = null
    sunburstFilteredCountsForPeriodId.value = null
  } finally {
    if (gen === sunburstFetchGen) {
      sunburstPeriodLoading.value = false
    }
  }
}

/**
 * Clic sur un palier de période : mémorise la préférence et charge le cache ou l’API.
 */
function selectSunburstPeriod(index) {
  if (index < 0 || index >= SUNBURST_PERIOD_STEPS.length) return
  sunburstPeriodIndex.value = index
  const authStore = useAuthStore()
  writeSunburstPeriodIndex(authStore.getApiUrl(), index)
  sunburstPeriodError.value = ''
  const pid = sunburstPeriodIdFromIndex(index)
  if (pid === 'all') {
    sunburstFilteredCounts.value = null
    sunburstFilteredCountsForPeriodId.value = null
    sunburstPeriodLoading.value = false
    return
  }
  fetchSunburstPeriodCounts()
}

/** Bouton « Rafraîchir les compteurs » : appelle GLPI même si un cache local existe. */
async function refreshSunburstPeriodCountsFromServer() {
  await clearServerHttpCache()
  await fetchSunburstPeriodCounts({ forceNetwork: true })
}

/**
 * Charge les catégories ITIL depuis l'API GLPI et les compteurs tickets.
 *
 * @param {{ silent?: boolean }} opts — `silent: true` = actualisation en arrière-plan (garde l’affichage courant).
 */
async function loadCategories(opts = {}) {
  const silent = opts.silent === true

  if (!silent) {
    isLoadingCategories.value = true
    categoriesError.value = ''
    categories.value = []
    loadingVerbose.value =
      'Étape 1/3 — Connexion à l’API GLPI et récupération de la liste des catégories ITIL (ITILCategory)…'
  } else {
    isRefreshing.value = true
    refreshError.value = ''
  }

  try {
    console.log('[Dashboard] Récupération des catégories ITIL (getITILCategories)…')
    const categoriesData = await glpiApi.getITILCategories()
    console.log(
      `[Dashboard] ${categoriesData.length} catégorie(s) brute(s) reçue(s) — aperçu ids :`,
      categoriesData.slice(0, 8).map((c) => c.id)
    )

    loadingVerbose.value = `Étape 2/3 — ${categoriesData.length} catégorie(s) reçue(s). Préparation des compteurs de tickets…`

    const categoryIds = categoriesData.map((cat) => cat.id)
    const n = categoryIds.length

    loadingVerbose.value = `Étape 3/3 — Comptage des tickets (historique complet pour tableau / arbre) : préparation des requêtes search/Ticket (0 / ${n})…`
    console.log(`[Dashboard] Lancement du comptage de tickets pour ${n} catégorie(s) (sans filtre date)…`)

    const ticketCounts = await glpiApi.getTicketCountsForCategories(categoryIds, {
      concurrency: 8,
      onProgress(done, total) {
        loadingVerbose.value = `Étape 3/3 — Comptage des tickets : ${done} / ${total} catégorie(s) traitée(s) (requêtes par lots vers GLPI)…`
      }
    })

    loadingVerbose.value =
      'Finalisation — totaux par branche (sous-catégories incluses) et niveaux hiérarchiques…'

    const withDirect = categoriesData.map((cat) => ({
      ...cat,
      ticketCount: ticketCounts[cat.id] ?? 0
    }))
    const branchTotals = computeBranchTicketTotalsByCategoryId(withDirect, ticketCounts)
    categories.value = withDirect.map((cat) => ({
      ...cat,
      totalTicketCount: branchTotals[cat.id] ?? cat.ticketCount ?? 0
    }))
    calculateCategoryLevels()

    heatmapLoadedOnce.value = false
    heatmapMatrix.value = null
    heatmapError.value = ''
    heatmapFromDiskCache.value = false
    heatmapCacheSavedAt.value = null

    const authStore = useAuthStore()
    clearHeatmap12Cache(authStore.getApiUrl())
    clearHeatmap12GroupsCache(authStore.getApiUrl())
    heatmapGroupsLoadedOnce.value = false
    heatmapGroupsMatrix.value = null
    heatmapGroupsError.value = ''
    heatmapGroupsFromDiskCache.value = false
    heatmapGroupsCacheSavedAt.value = null
    const savedAt = writeCategoriesCache(authStore.getApiUrl(), categories.value)
    if (savedAt) {
      cacheSnapshotSavedAt.value = savedAt
    }
    dataFromCache.value = false

    console.log(
      '[Dashboard] Chargement terminé — extrait (5 premières) avec ticketCount / totalTicketCount :',
      categories.value.slice(0, 5).map((c) => ({
        id: c.id,
        name: c.name,
        ticketCount: c.ticketCount,
        totalTicketCount: c.totalTicketCount
      }))
    )
  } catch (error) {
    console.error('Erreur lors de la récupération des catégories:', error)
    if (silent) {
      refreshError.value = 'Actualisation impossible : ' + formatApiError(error)
    } else {
      categoriesError.value =
        'Erreur lors de la récupération des catégories: ' + formatApiError(error)
      loadingVerbose.value = 'Échec du chargement — voir le message d’erreur ci-dessous ou la console (F12).'
    }
  } finally {
    if (!silent) {
      isLoadingCategories.value = false
    }
    isRefreshing.value = false
    if (!categoriesError.value && !silent) {
      loadingVerbose.value = ''
    }
  }
}

/**
 * Calcule le niveau de chaque catégorie dans la hiérarchie
 * Le niveau 0 = catégorie racine (sans parent)
 * Le niveau 1 = enfant direct d'une racine, etc.
 */
function calculateCategoryLevels() {
  // Créer un map pour accéder rapidement aux catégories par ID
  const categoryMap = new Map()
  categories.value.forEach(cat => {
    categoryMap.set(cat.id, cat)
  })
  
  // Fonction récursive pour calculer le niveau
  function getLevel(category) {
    // Si pas de parent, niveau 0 (racine)
    if (!category.itilcategories_id || category.itilcategories_id === 0) {
      return 0
    }
    
    // Trouver le parent
    const parent = categoryMap.get(category.itilcategories_id)
    if (!parent) {
      // Parent non trouvé, considérer comme racine
      return 0
    }
    
    // Si le parent a déjà un niveau calculé, l'utiliser
    if (parent.level !== undefined) {
      return parent.level + 1
    }
    
    // Sinon, calculer récursivement
    return getLevel(parent) + 1
  }
  
  // Calculer le niveau pour chaque catégorie
  categories.value.forEach(cat => {
    cat.level = getLevel(cat)
  })
}

/**
 * Transforme les catégories en structure arborescente pour l'affichage en arbre
 * Utilise le service treeTransform pour créer la hiérarchie
 * Inclut les compteurs de tickets
 */
const categoryTree = computed(() => {
  if (categories.value.length === 0) {
    return []
  }
  
  // Créer un objet avec les compteurs de tickets par catégorie ID
  const ticketCounts = {}
  categories.value.forEach(cat => {
    ticketCounts[cat.id] = cat.ticketCount || 0
  })
  
  // Transformer la liste plate en arbre avec les compteurs de tickets
  const tree = transformFlatToTree(categories.value, ticketCounts)
  
  // Si c'est un nœud racine unique, retourner un tableau avec ce nœud
  // Sinon, retourner les enfants (qui sont les racines)
  if (tree.id === 'root' && tree.children) {
    return tree.children
  } else {
    return [tree]
  }
})

/**
 * Transforme les catégories en structure arborescente pour le graphique Sunburst
 * Utilise le service treeTransform pour créer la hiérarchie complète
 * Le Sunburst nécessite une structure avec un nœud racine unique contenant tous les enfants
 */
const sunburstData = computed(() => {
  if (categories.value.length === 0) {
    return {
      id: 'root',
      name: 'Aucune catégorie',
      ticketCount: 0,
      totalTicketCount: 0,
      children: []
    }
  }

  const ticketCounts = {}
  const pid = sunburstPeriodIdFromIndex(sunburstPeriodIndex.value)
  const filteredReady =
    sunburstWeightByTickets.value &&
    pid !== 'all' &&
    sunburstFilteredCounts.value != null &&
    sunburstFilteredCountsForPeriodId.value === pid

  categories.value.forEach((cat) => {
    if (sunburstWeightByTickets.value && pid !== 'all') {
      ticketCounts[cat.id] = filteredReady ? (sunburstFilteredCounts.value[cat.id] ?? 0) : 0
    } else {
      /** Mode structure ou période « tout » : mêmes totaux que le tableau (historique GLPI) */
      ticketCounts[cat.id] = cat.ticketCount || 0
    }
  })

  return transformFlatToTree(categories.value, ticketCounts)
})

/**
 * Recharge les compteurs filtrés du Sunburst quand la liste des catégories change (actualisation GLPI)
 * ou quand on repasse en mode Tickets avec une période autre que « tout ».
 */
watch(
  () => [sunburstWeightByTickets.value, categories.value.map((c) => c.id).join(',')],
  () => {
    if (!categories.value.length) {
      sunburstFilteredCounts.value = null
      sunburstFilteredCountsForPeriodId.value = null
      return
    }
    if (!sunburstWeightByTickets.value) return
    if (sunburstPeriodIndex.value === 0) {
      sunburstFilteredCounts.value = null
      sunburstFilteredCountsForPeriodId.value = null
      return
    }
    fetchSunburstPeriodCounts()
  }
)

/**
 * Filtre et trie les catégories selon la recherche et le tri (en-têtes du tableau).
 */
const filteredAndSortedCategories = computed(() => {
  let result = [...categories.value]

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(cat => {
      const name = (cat.name || '').toLowerCase()
      const id = String(cat.id || '')
      return name.includes(query) || id.includes(query)
    })
  }

  const dir = tableSortDir.value === 'asc' ? 1 : -1
  const key = tableSortKey.value

  result.sort((a, b) => {
    let cmp = 0
    switch (key) {
      case 'id':
        cmp = (Number(a.id) || 0) - (Number(b.id) || 0)
        break
      case 'name': {
        const nameA = (a.name || '').toLowerCase()
        const nameB = (b.name || '').toLowerCase()
        cmp = nameA.localeCompare(nameB, 'fr', { sensitivity: 'base' })
        break
      }
      case 'parent': {
        const pa = a.itilcategories_id == null || a.itilcategories_id === 0 ? 0 : Number(a.itilcategories_id)
        const pb = b.itilcategories_id == null || b.itilcategories_id === 0 ? 0 : Number(b.itilcategories_id)
        cmp = pa - pb
        break
      }
      case 'level': {
        const la = Number(a.level ?? 0)
        const lb = Number(b.level ?? 0)
        cmp = la - lb
        break
      }
      case 'tickets': {
        const ta = Number(a.ticketCount ?? 0)
        const tb = Number(b.ticketCount ?? 0)
        cmp = ta - tb
        break
      }
      case 'branch': {
        const ta = Number(a.totalTicketCount ?? 0)
        const tb = Number(b.totalTicketCount ?? 0)
        cmp = ta - tb
        break
      }
      default:
        cmp = (Number(a.id) || 0) - (Number(b.id) || 0)
    }
    return dir * cmp
  })

  return result
})

/**
 * Bascule le tri : même colonne → inverse asc/desc ; autre colonne → asc sur cette colonne.
 */
function toggleTableSort(key) {
  if (tableSortKey.value === key) {
    tableSortDir.value = tableSortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    tableSortKey.value = key
    tableSortDir.value = 'asc'
  }
}

/** Attribut aria-sort pour les en-têtes (accessibilité) */
function ariaSortFor(key) {
  if (tableSortKey.value !== key) return 'none'
  return tableSortDir.value === 'asc' ? 'ascending' : 'descending'
}

/** Indicateur visuel de tri actif (▲ / ▼) */
function sortIconFor(key) {
  if (tableSortKey.value !== key) return ''
  return tableSortDir.value === 'asc' ? '▲' : '▼'
}

/**
 * id → nom pour résoudre le libellé du parent (liste chargée).
 */
const categoryNameById = computed(() => {
  const m = {}
  categories.value.forEach((cat) => {
    m[cat.id] = (cat.name && String(cat.name).trim()) ? cat.name : `Catégorie ${cat.id}`
  })
  return m
})

/**
 * Affichage « Nom du parent (id) » ; tiret si racine ; id seul si parent absent du jeu chargé.
 */
function parentDisplayLabel(category) {
  const pid = category.itilcategories_id
  if (pid == null || pid === 0) return '—'
  const name = categoryNameById.value[pid]
  if (name != null) {
    return `${name} (${pid})`
  }
  return `Parent inconnu (${pid})`
}

// Charger les données au montage du composant
onMounted(() => {
  const authStore = useAuthStore()
  const idx = readSunburstPeriodIndex(authStore.getApiUrl())
  if (idx != null && idx >= 0 && idx < SUNBURST_PERIOD_STEPS.length) {
    sunburstPeriodIndex.value = idx
  }
  loadData()
  document.addEventListener('fullscreenchange', onSunburstFullscreenChange)
  document.addEventListener('webkitfullscreenchange', onSunburstFullscreenChange)
  document.addEventListener('MSFullscreenChange', onSunburstFullscreenChange)
})

onUnmounted(() => {
  document.removeEventListener('fullscreenchange', onSunburstFullscreenChange)
  document.removeEventListener('webkitfullscreenchange', onSunburstFullscreenChange)
  document.removeEventListener('MSFullscreenChange', onSunburstFullscreenChange)
  try {
    const el = sunburstShellRef.value
    if (el && isSunburstShellFullscreen()) {
      const exit = document.exitFullscreen || document.webkitExitFullscreen || document.msExitFullscreen
      if (exit) exit.call(document).catch(() => {})
    }
  } catch (_) {
    /* ignore */
  }
})

/**
 * Récupère les comptages directs par catégorie pour chaque mois (requêtes GLPI en série par mois).
 */
async function fetchHeatmapMonthlyCounts(monthRanges, categoryIds, { verboseProgress = false } = {}) {
  const monthlyDirectCounts = []
  for (let i = 0; i < monthRanges.length; i++) {
    const mr = monthRanges[i]
    if (verboseProgress) {
      heatmapStatus.value = `Chaleur temporelle : mois ${i + 1}/12 (${mr.label})…`
    }
    const counts = await glpiApi.getTicketCountsForCategoriesInDateRange(
      categoryIds,
      mr.startStr,
      mr.endStr,
      {
        concurrency: 6,
        onProgress(done, total) {
          if (verboseProgress) {
            heatmapStatus.value = `Mois ${i + 1}/12 (${mr.label}) — ${done}/${total} catégories`
          }
        }
      }
    )
    monthlyDirectCounts.push(counts)
  }
  return monthlyDirectCounts
}

/**
 * Met à jour la matrice, le cache local et les métadonnées affichées.
 */
function applyHeatmapMatrixFromCounts(monthRanges, monthlyDirectCounts, apiUrl, categoryIdsKey, windowKey) {
  const lastCounts = monthlyDirectCounts[monthlyDirectCounts.length - 1] || {}
  const tree = transformFlatToTree(categories.value, lastCounts)
  const legacy = buildRootBranchMatrix(
    categories.value,
    monthRanges,
    monthlyDirectCounts,
    tree
  )
  /** Arbre minimal + comptages directs par mois : permet lignes repliables + rétrocompat cache. */
  heatmapMatrix.value = {
    ...legacy,
    monthlyDirectCounts,
    tree: cloneTreeForHeatmapCache(tree)
  }
  heatmapLoadedOnce.value = true
  heatmapMonthIndex.value = Math.min(11, Math.max(0, monthRanges.length - 1))
  const savedAt = writeHeatmap12Cache(apiUrl, heatmapMatrix.value, categoryIdsKey, windowKey)
  if (savedAt) {
    heatmapCacheSavedAt.value = savedAt
  }
  heatmapFromDiskCache.value = false
}

/** Bouton « Rafraîchir les 12 mois » : ignore le cache et relance toutes les requêtes. */
async function refreshHeatmapFromServer() {
  await clearServerHttpCache()
  await loadHeatmapData({ forceRefresh: true })
}

/**
 * Carte de chaleur : 12 mois × N catégories — cache localStorage + API.
 * Chargement paresseux à l’ouverture de l’onglet « 12 mois ».
 *
 * Si le cache disque est valide, on affiche sans appeler l’API : aucun rafraîchissement
 * automatique (idle / arrière-plan) — seul le bouton « Rafraîchir les 12 mois » force GLPI.
 *
 * @param {{ forceRefresh?: boolean }} opts — forcer le réseau (pas de lecture cache).
 */
async function loadHeatmapData(opts = {}) {
  const forceRefresh = opts.forceRefresh === true
  if (!categories.value.length) return

  if (!forceRefresh && heatmapLoadedOnce.value && heatmapMatrix.value) {
    return
  }

  const authStore = useAuthStore()
  const apiUrl = authStore.getApiUrl()
  const monthRanges = getLast12MonthRanges()
  const categoryIds = categories.value.map((c) => c.id)
  const categoryIdsKey = heatmapCategoryIdsKey(categoryIds)
  const windowKey = heatmapWindowKey(monthRanges)

  if (!forceRefresh) {
    const cached = readHeatmap12Cache(apiUrl, categoryIdsKey, windowKey)
    if (cached?.matrix) {
      heatmapMatrix.value = cached.matrix
      heatmapLoadedOnce.value = true
      const nCols = cached.matrix.columnLabels?.length ?? 12
      heatmapMonthIndex.value = Math.min(nCols - 1, Math.max(0, 11))
      heatmapCacheSavedAt.value = cached.savedAt
      heatmapFromDiskCache.value = true
      heatmapError.value = ''
      return
    }
  }

  heatmapLoading.value = true
  heatmapError.value = ''
  heatmapStatus.value = 'Préparation des plages mensuelles…'

  try {
    const monthlyDirectCounts = await fetchHeatmapMonthlyCounts(monthRanges, categoryIds, {
      verboseProgress: true
    })
    applyHeatmapMatrixFromCounts(monthRanges, monthlyDirectCounts, apiUrl, categoryIdsKey, windowKey)
  } catch (e) {
    console.error('[Dashboard] Chaleur temporelle', e)
    heatmapError.value =
      e.message || 'Impossible de charger la chaleur temporelle (vérifiez les droits API / le champ date Ticket).'
  } finally {
    heatmapLoading.value = false
    heatmapStatus.value = ''
  }
}

/**
 * Comptages par groupe pour chaque mois (résolu + clos, solvedate dans la plage).
 */
async function fetchHeatmapGroupsMonthlyCounts(monthRanges, groupIds, { verboseProgress = false } = {}) {
  const monthly = []
  for (let i = 0; i < monthRanges.length; i++) {
    const mr = monthRanges[i]
    if (verboseProgress) {
      heatmapGroupsStatus.value = `Groupes : mois ${i + 1}/12 (${mr.label})…`
    }
    const counts = await glpiApi.getTicketSolvedOrClosedCountsForGroupsInDateRange(
      groupIds,
      mr.startStr,
      mr.endStr,
      {
        concurrency: 6,
        onProgress(done, total) {
          if (verboseProgress) {
            heatmapGroupsStatus.value = `Mois ${i + 1}/12 (${mr.label}) — ${done}/${total} groupes`
          }
        }
      }
    )
    monthly.push(counts)
  }
  return monthly
}

/**
 * Met à jour la matrice groupes, le cache local et les métadonnées affichées.
 */
function applyHeatmapGroupsMatrix(monthRanges, monthlyCounts, groupsList, apiUrl, groupIdsKey, windowKey) {
  heatmapGroupsMatrix.value = buildGroupHeatmapMatrix(monthRanges, monthlyCounts, groupsList)
  heatmapGroupsLoadedOnce.value = true
  heatmapGroupsMonthIndex.value = Math.min(11, Math.max(0, monthRanges.length - 1))
  const savedAt = writeHeatmap12GroupsCache(apiUrl, heatmapGroupsMatrix.value, groupIdsKey, windowKey)
  if (savedAt) {
    heatmapGroupsCacheSavedAt.value = savedAt
  }
  heatmapGroupsFromDiskCache.value = false
  heatmapGroupsError.value = ''
}

/** Bouton « Rafraîchir groupes » : ignore le cache et relance toutes les requêtes. */
async function refreshHeatmapGroupsFromServer() {
  await clearServerHttpCache()
  await loadGroupHeatmapData({ forceRefresh: true })
}

/**
 * Heatmap groupes assignés : 12 mois × groupes actifs — cache localStorage + API.
 * Chargement paresseux à l’ouverture de l’onglet « Groupes ». Pas de rafraîchissement automatique.
 *
 * @param {{ forceRefresh?: boolean }} opts
 */
async function loadGroupHeatmapData(opts = {}) {
  const forceRefresh = opts.forceRefresh === true
  if (!categories.value.length) return

  if (!forceRefresh && heatmapGroupsLoadedOnce.value && heatmapGroupsMatrix.value !== null) {
    return
  }

  heatmapGroupsLoading.value = true
  heatmapGroupsError.value = ''
  heatmapGroupsStatus.value = 'Chargement des groupes GLPI…'

  try {
    const authStore = useAuthStore()
    const apiUrl = authStore.getApiUrl()
    const monthRanges = getLast12MonthRanges()
    const windowKey = heatmapWindowKey(monthRanges)

    const groups = await glpiApi.getGroups()
    if (!groups.length) {
      heatmapGroupsMatrix.value = buildGroupHeatmapMatrix(monthRanges, [], [])
      heatmapGroupsLoadedOnce.value = true
      heatmapGroupsCacheSavedAt.value = null
      heatmapGroupsFromDiskCache.value = false
      heatmapGroupsError.value =
        'Aucun groupe GLPI trouvé — vérifiez les droits API ou le profil utilisateur.'
      return
    }

    const ids = groups.map((g) => g.id)
    const gKey = heatmapGroupIdsKey(ids)

    if (!forceRefresh) {
      const cached = readHeatmap12GroupsCache(apiUrl, gKey, windowKey)
      if (cached?.matrix) {
        heatmapGroupsMatrix.value = cached.matrix
        heatmapGroupsLoadedOnce.value = true
        const nCols = cached.matrix.columnLabels?.length ?? 12
        heatmapGroupsMonthIndex.value = Math.min(nCols - 1, Math.max(0, 11))
        heatmapGroupsCacheSavedAt.value = cached.savedAt
        heatmapGroupsFromDiskCache.value = true
        heatmapGroupsError.value = ''
        return
      }
    }

    heatmapGroupsStatus.value = 'Préparation des plages mensuelles…'
    const monthly = await fetchHeatmapGroupsMonthlyCounts(monthRanges, ids, {
      verboseProgress: true
    })
    applyHeatmapGroupsMatrix(monthRanges, monthly, groups, apiUrl, gKey, windowKey)
  } catch (e) {
    console.error('[Dashboard] Heatmap groupes', e)
    heatmapGroupsError.value =
      e.message || 'Impossible de charger la heatmap par groupes (vérifiez les droits API / les champs Ticket).'
  } finally {
    heatmapGroupsLoading.value = false
    heatmapGroupsStatus.value = ''
  }
}

/** Nouvelle matrice (API ou cache) : on replie l’arbre pour éviter des ids obsolètes. */
watch(heatmapMatrix, () => {
  heatmapExpandedIds.value = new Set()
  heatmapHoveredRowIndex.value = null
})

watch(viewMode, (mode) => {
  if (mode !== 'sunburst') {
    const fs = document.fullscreenElement
    if (fs && fs.classList && fs.classList.contains('sunburst-shell')) {
      const exit = document.exitFullscreen || document.webkitExitFullscreen || document.msExitFullscreen
      exit?.call(document).catch(() => {})
    }
    syncSunburstFullscreenState()
  }
  if (mode === 'heatmap') {
    loadHeatmapData()
  }
  if (mode === 'heatmapGroups') {
    loadGroupHeatmapData()
  }
})
</script>

<style scoped>
.dashboard-container {
  min-height: 100vh;
  width: 100%;
  max-width: 100%;
  background-color: var(--app-bg);
  box-sizing: border-box;
  transition: background-color 0.2s ease;
}

.dashboard-header {
  background: var(--app-header-bg);
  padding: 16px 24px;
  box-shadow: 0 2px 4px var(--app-header-shadow);
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  box-sizing: border-box;
  transition: background 0.2s ease, box-shadow 0.2s ease;
}

.dashboard-header h1 {
  font-size: 1.5rem;
  color: var(--app-text);
  margin: 0;
}

.dashboard-header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  gap: 12px;
}

.loading-title {
  font-weight: 600;
  font-size: 1.15rem;
  color: var(--app-text);
  margin: 0;
}

.loading-detail {
  font-size: 0.95rem;
  color: var(--app-text-muted);
  max-width: min(520px, 92vw);
  text-align: center;
  line-height: 1.45;
  margin: 0;
}

.spinner {
  border: 4px solid var(--app-spinner-track);
  border-top: 4px solid var(--app-primary);
  border-radius: 50%;
  width: 50px;
  height: 50px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  gap: 20px;
}

.error-text {
  color: var(--app-danger);
  font-size: 1.1rem;
}

.retry-button {
  background: var(--app-primary);
  color: #ffffff;
  border: none;
  padding: 12px 24px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
}

.retry-button:hover {
  background: var(--app-primary-hover);
}

.content-container {
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  padding: 16px 24px 32px;
  display: flex;
  flex-direction: column;
}

.debug-section {
  margin-top: 24px;
  padding: 16px;
  background-color: var(--app-debug-bg);
  border-radius: 6px;
}

.debug-section summary {
  cursor: pointer;
  font-weight: 600;
  color: var(--app-text-muted);
  margin-bottom: 8px;
}

.debug-section pre {
  background: var(--app-debug-pre-bg);
  color: var(--app-text);
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 0.85rem;
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid var(--app-border);
}

/* Section catégories : pleine largeur de la zone sous l’en-tête */
.categories-container {
  width: 100%;
  max-width: 100%;
  display: flex;
  justify-content: stretch;
  align-items: flex-start;
}

.categories-card {
  background: var(--app-surface);
  border-radius: 12px;
  padding: 16px 20px 20px;
  box-shadow: 0 4px 6px var(--app-card-shadow);
  width: 100%;
  max-width: none;
  box-sizing: border-box;
  transition: background 0.2s ease, box-shadow 0.2s ease;
}

.categories-card h2 {
  margin: 0 0 10px 0;
  color: var(--app-text);
  font-size: 1.5rem;
  border-bottom: 2px solid var(--app-primary);
  padding-bottom: 8px;
}

/* Compteur + onglets sur une ligne (moins de hauteur vertical) */
.categories-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px 16px;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--app-border-soft);
}

.categories-count {
  font-size: 0.95rem;
  color: var(--app-text);
  white-space: nowrap;
}

.categories-toolbar .view-tabs {
  margin-bottom: 0;
  border-bottom: none;
  flex: 1;
  justify-content: flex-end;
  min-width: min(100%, 420px);
}

.loading-categories,
.error-categories,
.no-categories {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  gap: 16px;
}

.spinner-small {
  border: 3px solid var(--app-spinner-track);
  border-top: 3px solid var(--app-primary);
  border-radius: 50%;
  width: 30px;
  height: 30px;
  animation: spin 1s linear infinite;
}

.categories-controls {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.search-input {
  flex: 1;
  min-width: 200px;
  padding: 10px 14px;
  border: 1px solid var(--app-border);
  border-radius: 6px;
  font-size: 1rem;
  background: var(--app-input-bg);
  color: var(--app-text);
}

.search-input:focus {
  outline: none;
  border-color: var(--app-primary);
  box-shadow: 0 0 0 3px var(--app-input-focus-ring);
}

/* En-têtes de tableau cliquables pour le tri */
.th-sort-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 6px;
  padding: 12px;
  margin: 0;
  border: none;
  background: transparent;
  color: inherit;
  font: inherit;
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  text-align: left;
  border-radius: 0;
}

.th-sort-btn:hover {
  background: var(--app-th-sort-hover);
}

.th-sort-btn:focus-visible {
  outline: 2px solid var(--app-th-sort-focus);
  outline-offset: -2px;
}

.th-sort-icon {
  font-size: 0.75em;
  opacity: 0.95;
  flex-shrink: 0;
  min-width: 1em;
}

.categories-table-container {
  overflow-x: auto;
  max-height: 600px;
  overflow-y: auto;
  border: 1px solid var(--app-border);
  border-radius: 6px;
}

.categories-table {
  width: 100%;
  border-collapse: collapse;
  background: var(--app-surface);
}

.categories-table thead {
  background-color: var(--app-primary);
  color: #ffffff;
  position: sticky;
  top: 0;
  z-index: 10;
}

.categories-table th {
  padding: 0;
  text-align: left;
  font-weight: 600;
  font-size: 0.9rem;
  vertical-align: middle;
}

.categories-table tbody tr {
  border-bottom: 1px solid var(--app-border-soft);
  transition: background-color 0.2s;
}

.categories-table tbody tr:hover {
  background-color: var(--app-table-row-hover);
}

.categories-table td {
  padding: 12px;
  font-size: 0.95rem;
  color: var(--app-text);
}

.category-name {
  font-weight: 500;
  color: var(--app-table-text);
}

.parent-cell {
  word-break: break-word;
  max-width: 280px;
}

.debug-note {
  margin-top: 8px;
  font-size: 0.85rem;
  color: var(--app-text-muted);
  font-style: italic;
}

.ticket-count {
  font-weight: 500;
  color: var(--app-success);
  text-align: center;
}

/* Onglets (séparés si hors toolbar — ex. usage futur) */
.view-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  border-bottom: 2px solid var(--app-border-soft);
}

/* Sunburst : zone compacte + shell cible du mode plein écran (bouton dans l’en-tête) */
.categories-sunburst-container {
  width: 100%;
  min-height: 360px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
  background: var(--app-sunburst-zone-bg);
  border-radius: 8px;
  box-sizing: border-box;
  transition: background 0.2s ease;
}

.sunburst-top-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px 12px;
}

.sunburst-hint-inline {
  margin: 0;
  font-size: 0.8rem;
  color: var(--app-sunburst-hint);
  line-height: 1.35;
  max-width: min(100%, 420px);
}

.sunburst-shell {
  flex: 1 1 auto;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.sunburst-shell:fullscreen {
  background: var(--app-sunburst-fullscreen-bg);
  padding: 12px 16px 20px;
  box-sizing: border-box;
  overflow: auto;
}

.sunburst-shell:-webkit-full-screen {
  background: var(--app-sunburst-fullscreen-bg);
  padding: 12px 16px 20px;
  box-sizing: border-box;
}

.categories-sunburst-container :deep(.sunburst-container) {
  width: 100%;
  min-width: 0;
  flex: 1 1 auto;
}

.sunburst-mode-toggle {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.sunburst-mode-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--app-text-muted);
  margin-right: 2px;
}

.sunburst-mode-btn {
  padding: 6px 12px;
  border: 1px solid var(--app-mode-btn-border);
  background: var(--app-mode-btn-bg);
  color: var(--app-mode-btn-text);
  font-size: 0.88rem;
  font-weight: 500;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s, color 0.2s, border-color 0.2s;
}

.sunburst-mode-btn:hover {
  background: var(--app-mode-btn-hover-bg);
  border-color: var(--app-mode-btn-hover-border);
}

.sunburst-mode-btn--active {
  background: var(--app-primary);
  border-color: var(--app-primary-muted);
  color: #ffffff;
}

.sunburst-mode-btn--active:hover {
  background: var(--app-primary-hover);
  border-color: var(--app-primary-muted);
  color: #ffffff;
}

.sunburst-period-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px 10px;
  margin: 0 0 4px 0;
  border-radius: 6px;
  border: 1px solid var(--app-border-soft);
  background: var(--app-mode-btn-hover-bg);
}

.sunburst-period-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px 12px;
  margin-bottom: 4px;
}

.sunburst-period-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--app-text-muted);
}

.sunburst-period-refresh-btn {
  padding: 5px 11px;
  font-size: 0.78rem;
  font-weight: 600;
  border-radius: 6px;
  border: 1px solid var(--app-primary);
  background: transparent;
  color: var(--app-primary);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  white-space: nowrap;
}

.sunburst-period-refresh-btn:hover:not(:disabled) {
  background: var(--app-primary);
  color: #fff;
}

.sunburst-period-refresh-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.sunburst-period-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.sunburst-period-chip {
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--app-mode-btn-border);
  background: var(--app-bg);
  color: var(--app-text);
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}

.sunburst-period-chip:hover:not(:disabled) {
  border-color: var(--app-primary);
  color: var(--app-primary);
}

.sunburst-period-chip:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.sunburst-period-chip--active {
  background: var(--app-primary);
  border-color: var(--app-primary-muted);
  color: #fff;
}

.sunburst-period-chip--active:hover:not(:disabled) {
  background: var(--app-primary-hover);
  border-color: var(--app-primary-muted);
  color: #fff;
}

.sunburst-period-current {
  margin: 6px 0 0 0;
  font-size: 0.82rem;
  color: var(--app-text);
  line-height: 1.35;
}

.sunburst-period-current-hint {
  font-weight: 400;
  color: var(--app-text-soft);
}

.sunburst-period-err {
  margin: 0;
  font-size: 0.82rem;
  color: var(--app-danger);
}

.sunburst-shell--chart {
  position: relative;
}

.sunburst-period-overlay {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: var(--app-mode-btn-hover-bg);
  font-size: 0.9rem;
  color: var(--app-text-muted);
  border-radius: 6px;
}

.sunburst-period-note {
  margin: 0;
  font-size: 0.78rem;
  color: var(--app-sunburst-hint);
  line-height: 1.4;
}

.sunburst-period-note code {
  font-size: 0.85em;
}

.tab-button {
  padding: 10px 20px;
  border: none;
  background: transparent;
  color: var(--app-tab-inactive);
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: all 0.2s;
}

.tab-button:hover {
  color: var(--app-primary);
}

.tab-button.active {
  color: var(--app-primary);
  border-bottom-color: var(--app-primary);
}

/* Styles pour la vue arbre */
.categories-tree-container {
  background: var(--app-tree-bg);
  border: 1px solid var(--app-border);
  border-radius: 6px;
  padding: 20px;
  max-height: 600px;
  overflow-y: auto;
}

.tree-wrapper {
  font-family: 'Courier New', monospace;
  font-size: 0.95rem;
}

/* Vue chaleur temporelle */
.categories-heatmap-container {
  width: 100%;
  padding: 8px 10px;
  background: var(--app-sunburst-zone-bg);
  border-radius: 8px;
  box-sizing: border-box;
}

.heatmap-intro {
  font-size: 0.85rem;
  color: var(--app-text-muted);
  line-height: 1.45;
  margin: 0 0 16px 0;
  max-width: 920px;
}

.heatmap-intro code {
  font-size: 0.85em;
  padding: 2px 6px;
  background: var(--app-mode-btn-hover-bg);
  border-radius: 4px;
  color: var(--app-text);
}

.heatmap-loading {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px;
}

.heatmap-cache-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  margin: 0 0 12px 0;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--app-border);
  background: var(--app-mode-btn-hover-bg);
  font-size: 0.88rem;
  color: var(--app-text-muted);
}

.heatmap-cache-bar__text {
  flex: 1;
  min-width: 200px;
  line-height: 1.4;
}

.heatmap-cache-bar__hint {
  font-weight: 500;
  color: var(--app-text-soft);
}

.heatmap-cache-bar__btn {
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid var(--app-primary);
  background: transparent;
  color: var(--app-primary);
  font-weight: 600;
  font-size: 0.85rem;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}

.heatmap-cache-bar__btn:hover:not(:disabled) {
  background: var(--app-primary);
  color: #fff;
}

.heatmap-cache-bar__btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

/* Tri des lignes (affichage uniquement) */
.heatmap-sort-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  margin: 0 0 12px 0;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--app-border);
  background: var(--app-bg);
  font-size: 0.88rem;
}

.heatmap-sort-bar__label {
  font-weight: 600;
  color: var(--app-text);
}

.heatmap-sort-bar__select {
  min-width: 220px;
  max-width: 100%;
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid var(--app-border);
  background: var(--app-mode-btn-hover-bg);
  color: var(--app-text);
  font-size: 0.88rem;
  cursor: pointer;
}

.heatmap-sort-bar__hint {
  flex: 1;
  min-width: 180px;
  font-size: 0.8rem;
  color: var(--app-text-soft);
  line-height: 1.35;
}

/* Colonne arbre + carte D3 (onglet 12 mois catégories) */
.heatmap-body {
  width: 100%;
  box-sizing: border-box;
}

/**
 * Scroll partagé : la grille SVG et la liste des noms ont la même hauteur totale et défilent
 * ensemble (évite tout décalage si l’utilisateur scrollait uniquement la colonne de gauche).
 */
.heatmap-paired-scroll {
  display: flex;
  align-items: flex-start;
  /* Espace minimal pour que liste et grille forment un visuel continu */
  gap: 4px;
  width: 100%;
  max-height: min(85vh, 960px);
  overflow-x: hidden;
  overflow-y: auto;
  box-sizing: border-box;
}

.heatmap-body--with-tree .heatmap-chart-panel {
  flex: 1;
  min-width: 0;
}

.heatmap-tree-labels {
  flex: 0 0 min(280px, 38vw);
  max-width: 320px;
  padding: 6px 8px 8px 4px;
  border-radius: 8px;
  border: 1px solid var(--app-border);
  background: var(--app-bg);
  font-size: 0.82rem;
  line-height: 1.2;
}

/** Colonne collée à la grille : filet vertical pour prolonger la lecture des lignes */
.heatmap-tree-labels--paired {
  border-right: 2px solid var(--app-border);
  padding-right: 10px;
}

/* Même hauteur minimale que .heatmap-toolbar du composant enfant (curseur mois + lecture). */
.heatmap-body--with-tree .heatmap-tree-labels-toolbar {
  display: flex;
  align-items: center;
  min-height: 56px;
  margin-bottom: 12px;
  padding-bottom: 0;
  border-bottom: 1px solid var(--app-border);
}

.heatmap-body--with-tree .heatmap-chart-panel :deep(.heatmap-toolbar) {
  min-height: 56px;
  margin-bottom: 12px;
  box-sizing: border-box;
}

.heatmap-tree-collapse-all {
  padding: 4px 10px;
  border-radius: 6px;
  border: 1px solid var(--app-border);
  background: var(--app-mode-btn-hover-bg);
  color: var(--app-text);
  font-size: 0.8rem;
  cursor: pointer;
}

.heatmap-tree-collapse-all:hover:not(:disabled) {
  border-color: var(--app-primary);
  color: var(--app-primary);
}

.heatmap-tree-collapse-all:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.heatmap-tree-labels-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

/**
 * Hauteur fixe = cellule D3 (variable CSS --heatmap-row-px définie sur .heatmap-body).
 * minHeight laissait le navigateur agrandir les lignes → décalage cumulé avec la grille.
 */
.heatmap-tree-labels-row {
  display: flex;
  align-items: stretch;
  box-sizing: border-box;
  margin: 0;
  padding: 0;
  height: var(--heatmap-row-px, 24px);
  min-height: var(--heatmap-row-px, 24px);
  max-height: var(--heatmap-row-px, 24px);
  overflow: hidden;
  /* Bandes alternées : même logique que les filets horizontaux du SVG (lignes paires) */
  border-bottom: 1px solid var(--heatmap-row-line, var(--app-border));
}

.heatmap-tree-labels-row:nth-child(even) {
  background: var(--heatmap-label-zebra, color-mix(in srgb, var(--app-text) 7%, transparent));
}

/** Survol : lien explicite avec la surbrillance sur la grille (prop highlightedRowIndex) */
.heatmap-tree-labels-row--hl {
  background: color-mix(in srgb, var(--app-primary) 24%, transparent) !important;
  box-shadow: inset 3px 0 0 0 var(--app-primary);
}

.heatmap-tree-labels-line {
  display: flex;
  align-items: center;
  gap: 4px;
  width: 100%;
  min-height: 0;
  flex: 1;
}

.heatmap-tree-toggle {
  flex: 0 0 22px;
  width: 22px;
  height: 22px;
  padding: 0;
  margin: 0;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--app-primary);
  font-size: 0.7rem;
  line-height: 1;
  cursor: pointer;
}

.heatmap-tree-toggle:hover {
  background: var(--app-mode-btn-hover-bg);
}

.heatmap-tree-toggle-spacer {
  flex: 0 0 22px;
  width: 22px;
  display: inline-block;
}

.heatmap-tree-label-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--app-text);
}

.heatmap-chart-panel {
  width: 100%;
}

/* Aucune ligne à afficher (groupes sans volume sur 12 mois) */
.heatmap-empty-msg {
  margin: 12px 0 0 0;
  padding: 14px 16px;
  border-radius: 8px;
  border: 1px dashed var(--app-border);
  color: var(--app-text-soft);
  font-size: 0.95rem;
  line-height: 1.45;
}

/* Bannière cache / fraîcheur des données */
.cache-info-banner {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 14px;
  margin: 0 0 14px 0;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid var(--app-border);
  background: var(--app-mode-btn-hover-bg);
  font-size: 0.88rem;
  color: var(--app-text-muted);
}

.cache-info-banner--stale {
  border-color: rgba(255, 152, 0, 0.55);
  background: rgba(255, 152, 0, 0.08);
}

.cache-info-banner__text {
  flex: 1;
  min-width: 200px;
  line-height: 1.4;
}

.cache-info-banner__hint {
  font-weight: 500;
  color: var(--app-text-soft);
}

.cache-info-banner__stale-hint {
  color: var(--app-warning-fg);
  font-weight: 600;
}

.cache-info-banner__btn {
  padding: 6px 14px;
  border-radius: 6px;
  border: 1px solid var(--app-primary);
  background: var(--app-primary);
  color: #fff;
  font-weight: 600;
  font-size: 0.85rem;
  cursor: pointer;
  transition: background 0.2s, opacity 0.2s;
}

.cache-info-banner__btn:hover:not(:disabled) {
  background: var(--app-primary-hover);
}

.cache-info-banner__btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.cache-info-banner__err {
  flex-basis: 100%;
  font-size: 0.85rem;
  color: var(--app-danger);
}
</style>
