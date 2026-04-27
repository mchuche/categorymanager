<?php
/**
 * -------------------------------------------------------------------------
 * Classe d’ancrage menu — visualiseur de catégories (CategoryManager)
 * -------------------------------------------------------------------------
 * CommonGLPI fournit l’intégration au menu latéral. On force l’URL vers
 * front/visualizer.php pour éviter l’ambiguïté du routeur GLPI 11 avec
 * un fichier front/menu.php homonyme d’une classe (cf. stockmanager).
 * -------------------------------------------------------------------------
 */

if (!defined('GLPI_ROOT')) {
    die("Sorry. You can't access this file directly");
}

/**
 * Point d’entrée utilisateur : page embarquant l’application Vue buildée.
 */
class PluginCategorymanagerVisualizer extends CommonGLPI
{
    /**
     * Droit technique stocké dans glpi_profilerights (colonne name).
     * Réglé par profil : Configuration > Profils > [profil] > onglet CategoryManager.
     * @see PluginCategorymanagerProfile::getAllRights()
     */
    public static $rightname = 'plugin_categorymanager';

    /**
     * Libellé du type (menu, en-têtes).
     */
    public static function getTypeName($nb = 0)
    {
        return _n('Visualiseur catégories', 'Visualiseur catégories', $nb, 'categorymanager');
    }

    /**
     * Icône Tabler (GLPI 11) pour le menu latéral.
     */
    public static function getIcon(): string
    {
        return 'ti ti-chart-donut-2';
    }

    /**
     * URL réelle de la page (évite la collision contrôleur générique / Search).
     */
    public static function getSearchURL($full = true)
    {
        global $CFG_GLPI;

        $root = $full ? ($CFG_GLPI['root_doc'] ?? '') : '';

        return $root . '/plugins/categorymanager/front/visualizer.php';
    }

    /**
     * Indique si l’utilisateur courant peut ouvrir le visualiseur (menu + page + ajax).
     *
     * Règles :
     * - Si la session contient une valeur pour `plugin_categorymanager` (ligne en base) : on applique
     *   strictement la lecture sur ce droit (c’est le réglage de l’onglet Profil > CategoryManager).
     * - Si la clé est absente (install partielle, cache profil ancien) : repli sur la lecture « ticket »,
     *   comme avant la 0.1.1, pour ne pas masquer le menu à tort.
     */
    public static function hasVisualizerAccess(): bool
    {
        $profile = $_SESSION['glpiactiveprofile'] ?? [];

        if (array_key_exists(static::$rightname, $profile)) {
            return ((int) $profile[static::$rightname] & READ) === READ;
        }

        return Session::haveRight('ticket', READ);
    }

    /**
     * Vérifie l’accès au visualiseur avec les mêmes règles que {@see hasVisualizerAccess()}
     * et lève l’exception GLPI attendue si refus (comme {@see Session::checkRight}).
     */
    public static function checkVisualizerAccess(): void
    {
        if (self::hasVisualizerAccess()) {
            return;
        }

        if (!array_key_exists(static::$rightname, $_SESSION['glpiactiveprofile'] ?? [])) {
            Session::checkRight('ticket', READ);

            return;
        }

        Session::checkRight(static::$rightname, READ);
    }

    /**
     * Contrôle d’affichage du menu latéral : aligné sur {@see hasVisualizerAccess()}.
     */
    public static function canView(): bool
    {
        return self::hasVisualizerAccess();
    }
}
