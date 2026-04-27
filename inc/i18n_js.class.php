<?php

/**
 * -------------------------------------------------------------------------
 * Chaînes UI pour le bundle JavaScript (injectées dans window.__CM_I18N__)
 * -------------------------------------------------------------------------
 * Chaque valeur passe par gettext (domaine categorymanager) : les mêmes msgid
 * que dans locales/*.po pour en_GB / fr_FR.
 * -------------------------------------------------------------------------
 */

if (!defined('GLPI_ROOT')) {
    die("Sorry. You can't access this file directly");
}

final class PluginCategorymanagerI18n
{
    /**
     * Libellés pour le front Vue (clés stables côté JS).
     *
     * @return array<string, string>
     */
    public static function getJsMessages(): array
    {
        return [
            'loading_init' => __('Initializing…', 'categorymanager'),
            'dashboard_title' => __('CategoryManager — GLPI visualization', 'categorymanager'),
            'categories_heading' => __('ITIL categories', 'categorymanager'),
            'loading_categories' => __('Loading categories', 'categorymanager'),
            'retry' => __('Retry', 'categorymanager'),
            'theme_light' => __('Switch to light mode', 'categorymanager'),
            'theme_dark' => __('Switch to dark mode', 'categorymanager'),
            'fullscreen_enter' => __('Full screen chart', 'categorymanager'),
            'fullscreen_exit' => __('Exit full screen', 'categorymanager'),
            'fullscreen_exit_esc' => __('Exit full screen (Esc)', 'categorymanager'),
            'fullscreen_sr' => __('Full screen', 'categorymanager'),
            'tab_sunburst' => __('Sunburst', 'categorymanager'),
            'tab_table' => __('Table', 'categorymanager'),
            'tab_tree' => __('Tree', 'categorymanager'),
            'tab_heatmap12' => __('12 months', 'categorymanager'),
            'tab_groups' => __('Groups', 'categorymanager'),
            'tab_heatmap12_title' => __('Heatmap: volume per branch over 12 rolling months', 'categorymanager'),
            'tab_groups_title' => __('Tickets solved or closed per assigned group over 12 rolling months', 'categorymanager'),
            'cache_refreshing' => __('Refreshing data from GLPI…', 'categorymanager'),
            'cache_showing_from' => __('Showing data from %s', 'categorymanager'),
            'cache_local_hint' => __('(from local cache)', 'categorymanager'),
            'cache_stale_hint' => __(' — update recommended', 'categorymanager'),
            'refresh' => __('Refresh', 'categorymanager'),
            'search_placeholder' => __('Search for a category…', 'categorymanager'),
            'view_mode_label' => __('View type', 'categorymanager'),
            'col_id' => __('ID', 'categorymanager'),
            'col_name' => __('Name', 'categorymanager'),
            'col_parent' => __('Parent category', 'categorymanager'),
            'col_level' => __('Level', 'categorymanager'),
            'col_tickets_direct' => __('Tickets (direct)', 'categorymanager'),
            'col_branch_total' => __('Branch total', 'categorymanager'),
            'col_tickets_direct_hint' => __('Open tickets on this category only (excluding subcategories)', 'categorymanager'),
            'col_branch_hint' => __('Sum: direct tickets + tickets on all subcategories (same logic as Sunburst “Tickets”)', 'categorymanager'),
            'categories_loaded_count' => __('categories', 'categorymanager'),
            'categories_count_title' => __('Number of categories loaded from GLPI', 'categorymanager'),
            'sunburst_display_aria' => __('Sunburst display mode', 'categorymanager'),
            'display_mode' => __('Display', 'categorymanager'),
            'mode_structure' => __('Structure', 'categorymanager'),
            'mode_tickets' => __('Tickets', 'categorymanager'),
            'hint_proportional_tickets' => __('Proportional to tickets per branch.', 'categorymanager'),
            'hint_structure_angles' => __('Structure view (hierarchical angles).', 'categorymanager'),
            'period_heading' => __('Period (Sunburst only)', 'categorymanager'),
            'refresh_counts' => __('Refresh counts', 'categorymanager'),
            'refresh_counts_title' => __('Re-run all GLPI count requests for this period', 'categorymanager'),
            'counting_period' => __('Counting for period…', 'categorymanager'),
            'category_with_id' => __('Category %s', 'categorymanager'),
            'unsorted_name' => __('No name', 'categorymanager'),
            'parent_unknown' => __('Unknown parent (%s)', 'categorymanager'),
            'root_empty' => __('No category', 'categorymanager'),
            'no_categories_found' => __('No categories found', 'categorymanager'),
            'debug_raw_title' => __('Raw category data (debug)', 'categorymanager'),
            'debug_note' => __('Showing the first 5 categories only', 'categorymanager'),
            'heatmap_intro' => __('Ticket volume per branch (category + sub-trees) over the last 12 rolling months (window up to today). Use ▶ / ▼ to show subcategories under each business root. The date used is the ticket opening date (GLPI field detected: date or date_creation).', 'categorymanager'),
            'heatmap_data_from' => __('Data from %s', 'categorymanager'),
            'heatmap_cache_hint' => __('(local 12-month cache)', 'categorymanager'),
            'heatmap_refresh_12' => __('Refresh 12 months', 'categorymanager'),
            'heatmap_refresh_12_title' => __('Reload all requests (12 months × categories)', 'categorymanager'),
            'sort_rows' => __('Sort rows', 'categorymanager'),
            'heatmap_sort_hint_cat' => __('Order of business roots follows the sort; under each expanded root, GLPI tree order. Display only (does not change GLPI).', 'categorymanager'),
            'heatmap_tree_aria' => __('Category tree and volumes per branch', 'categorymanager'),
            'collapse_all' => __('Collapse all', 'categorymanager'),
            'collapse_all_title' => __('Hide all subcategories', 'categorymanager'),
            'expand_branch' => __('Expand branch: %s', 'categorymanager'),
            'collapse_branch' => __('Collapse branch: %s', 'categorymanager'),
            'heatmap_intro_groups' => __('Number of tickets solved or closed (GLPI statuses 5 and 6) per assigned group over the last 12 rolling months (sliding window). Resolution date (solvedate). Only groups with at least one ticket in the period appear.', 'categorymanager'),
            'heatmap_groups_cache_hint' => __('(local groups cache)', 'categorymanager'),
            'heatmap_refresh_groups' => __('Refresh groups', 'categorymanager'),
            'heatmap_refresh_groups_title' => __('Reload group list and all counts (12 months × groups)', 'categorymanager'),
            'heatmap_sort_hint_grp' => __('Display only; default order follows API load (often A→Z).', 'categorymanager'),
            'heatmap_empty_groups' => __('No solved or closed tickets by assigned group in this 12-month window (check API rights or try again later).', 'categorymanager'),
            'heatmap_legend_groups' => __('Intensity = count of solved (5) or closed (6) tickets for the month, by resolution date (solvedate) and assigned group.', 'categorymanager'),
            'heatmap_chart_aria_groups' => __('Heatmap of solved or closed tickets by group and month', 'categorymanager'),
            'period_all_short' => __('All', 'categorymanager'),
            'period_all_hint' => __('Full history (same as table)', 'categorymanager'),
            'period_90d_short' => __('90d', 'categorymanager'),
            'period_90d_hint' => __('Rolling 90-day window', 'categorymanager'),
            'period_6m_short' => __('6 mo', 'categorymanager'),
            'period_6m_hint' => __('Rolling 6-month window', 'categorymanager'),
            'period_1y_short' => __('1 yr', 'categorymanager'),
            'period_1y_hint' => __('Rolling 1-year window', 'categorymanager'),
            'period_2y_short' => __('2 yr', 'categorymanager'),
            'period_2y_hint' => __('Rolling 2-year window', 'categorymanager'),
            'period_3y_short' => __('3 yr', 'categorymanager'),
            'period_3y_hint' => __('Rolling 3-year window', 'categorymanager'),
            'sunburst_period_note' => __('Independent of the table and tree (always full history). Period counters are cached with no automatic expiry; GLPI is called only when there is no local data for that period, or when you click Refresh counts. Filter on opening date (GLPI may fall back to date_creation).', 'categorymanager'),
            'heatmap_sort_source_cat' => __('Tree order (business roots)', 'categorymanager'),
            'heatmap_sort_total_desc' => __('Total volume over 12 months (↓)', 'categorymanager'),
            'heatmap_sort_month_desc' => __('Displayed month volume (↓)', 'categorymanager'),
            'heatmap_sort_alpha' => __('Name (A→Z)', 'categorymanager'),
            'heatmap_sort_source_grp' => __('Load order (default)', 'categorymanager'),

            /** Infobulles Sunburst (complément aux libellés courts ci-dessus). */
            'hint_proportional_tickets_title' => __(
                'Sectors proportional to ticket count per branch (total including subcategories).',
                'categorymanager'
            ),
            'hint_structure_angles_title' => __(
                'Sectors by hierarchy only (angles tied to leaves), without weighting by ticket volume.',
                'categorymanager'
            ),

            /** Étapes de chargement détaillées (liste catégories + compteurs). */
            'loading_prep' => __('Preparing load (GLPI session, then category list)…', 'categorymanager'),
            'loading_step1' => __(
                'Step 1/3 — Connecting to GLPI API and retrieving ITIL categories…',
                'categorymanager'
            ),
            'loading_step2' => __('Step 2/3 — %s categories received. Preparing ticket counts…', 'categorymanager'),
            'loading_step3_prep' => __(
                'Step 3/3 — Counting tickets (full history for table/tree): preparing search/Ticket requests (0 / %s)…',
                'categorymanager'
            ),
            'loading_step3_progress' => __(
                'Step 3/3 — Counting tickets: %s / %s categories processed (batched requests to GLPI)…',
                'categorymanager'
            ),
            'loading_finalize' => __(
                'Finalizing — branch totals (including subcategories) and hierarchy levels…',
                'categorymanager'
            ),

            /** Erreurs Vue (chargement / rafraîchissement). */
            'error_load_data' => __('Error loading data: %s', 'categorymanager'),
            'error_unknown' => __('Unknown error', 'categorymanager'),
            'error_refresh_failed' => __('Refresh failed: %s', 'categorymanager'),
            'error_categories_retrieval' => __('Error retrieving categories: %s', 'categorymanager'),
            'error_load_failed_verbose' => __(
                'Load failed — see error message below or console (F12).',
                'categorymanager'
            ),
            'sunburst_count_failed' => __('Unable to count for this period.', 'categorymanager'),

            /** Progression heatmap 12 mois (catégories / groupes). */
            'heatmap_status_month_loading' => __('Temporal heatmap: month %s/12 (%s)…', 'categorymanager'),
            'heatmap_status_month_progress' => __('Month %s/12 (%s) — %s/%s categories', 'categorymanager'),
            'heatmap_prep_ranges' => __('Preparing monthly ranges…', 'categorymanager'),
            'heatmap_load_failed' => __(
                'Unable to load temporal heatmap (check API rights / Ticket date field).',
                'categorymanager'
            ),
            'heatmap_groups_month_loading' => __('Groups: month %s/12 (%s)…', 'categorymanager'),
            'heatmap_groups_month_progress' => __('Month %s/12 (%s) — %s/%s groups', 'categorymanager'),
            'heatmap_groups_loading_list' => __('Loading GLPI groups…', 'categorymanager'),
            'heatmap_groups_none' => __('No GLPI groups found — check API rights or user profile.', 'categorymanager'),
            'heatmap_groups_load_failed' => __(
                'Unable to load group heatmap (check API rights / Ticket fields).',
                'categorymanager'
            ),
        ];
    }
}
