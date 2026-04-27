<?php
/**
 * -------------------------------------------------------------------------
 * CategoryManager — plugin GLPI 11
 * -------------------------------------------------------------------------
 * Visualiseur de catégories ITIL (Sunburst, etc.) — point d’entrée enregistré
 * par le noyau GLPI au chargement.
 * -------------------------------------------------------------------------
 */

if (!defined('GLPI_ROOT')) {
    die("Sorry. You can't access this file directly");
}

include_once __DIR__ . '/hook.php';

/** Version affichée dans Configuration > Plugins */
define('PLUGIN_CATEGORYMANAGER_VERSION', '0.1.2');

/**
 * Initialisation : hooks, classes, menu.
 */
function plugin_init_categorymanager(): void
{
    global $PLUGIN_HOOKS;

    $PLUGIN_HOOKS['csrf_compliant']['categorymanager'] = true;

    // Chiffrement des jetons dans glpi_configs (clé sodium GLPI)
    // Entrée dans le menu « Outils » (clé interne GLPI : tools) — cf. stockmanager
    $PLUGIN_HOOKS['menu_toadd']['categorymanager'] = [
        'tools' => 'PluginCategorymanagerVisualizer',
    ];

    Plugin::registerClass('PluginCategorymanagerVisualizer');

    // Onglet « CategoryManager » sur Configuration > Profils : matrice du droit plugin_categorymanager
    Plugin::registerClass('PluginCategorymanagerProfile', [
        'addtabon' => Profile::class,
    ]);
}

/**
 * Métadonnées du plugin (nom, version, prérequis).
 *
 * @return array<string, mixed>
 */
function plugin_version_categorymanager(): array
{
    return [
        'name'         => 'CategoryManager',
        'version'      => PLUGIN_CATEGORYMANAGER_VERSION,
        'author'       => 'CategoryManager',
        'license'      => 'GPLv3+',
        'homepage'     => '',
        'requirements' => [
            'glpi' => [
                'min' => '11.0',
                'max' => '12.0',
            ],
            'php'  => [
                'min' => '8.2.0',
            ],
        ],
    ];
}

/**
 * Vérifications avant installation / activation.
 */
function plugin_categorymanager_check_prerequisites(): bool
{
    if (version_compare(GLPI_VERSION, '11.0', '<')) {
        echo 'Ce plugin nécessite GLPI >= 11.0.';
        return false;
    }
    return true;
}

/**
 * Indique si le plugin est correctement configuré après installation.
 */
function plugin_categorymanager_check_config(bool $verbose = false): bool
{
    return true;
}
