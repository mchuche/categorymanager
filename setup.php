<?php
/**
 * -------------------------------------------------------------------------
 * CategoryManager — plugin GLPI 11 (architecture moderne : PSR-4 + contrôleurs)
 * -------------------------------------------------------------------------
 * Point d'entrée enregistré par le noyau GLPI au chargement.
 * Les routes HTTP sont déclarées dans src/Controller/ (préfixe /plugins/categorymanager/).
 * -------------------------------------------------------------------------
 */

if (!defined('GLPI_ROOT')) {
    die("Sorry. You can't access this file directly");
}

include_once __DIR__ . '/hook.php';

use GlpiPlugin\Categorymanager\Itemtype\VisualizerMenu;
use GlpiPlugin\Categorymanager\Profile\ProfileTab;

/** Version affichée dans Configuration > Plugins */
define('PLUGIN_CATEGORYMANAGER_VERSION', '0.2.0');

/**
 * Initialisation : autoload Composer, hooks, classes namespaced.
 */
function plugin_init_categorymanager(): void
{
    global $PLUGIN_HOOKS;

    // Autoload PSR-4 (GlpiPlugin\Categorymanager\) — requis pour contrôleurs et services
    $autoload = __DIR__ . '/vendor/autoload.php';
    if (is_readable($autoload)) {
        require_once $autoload;
    }

    $PLUGIN_HOOKS['csrf_compliant']['categorymanager'] = true;

    // Entrée dans le menu « Outils » (clé interne GLPI : tools)
    $PLUGIN_HOOKS['menu_toadd']['categorymanager'] = [
        'tools' => VisualizerMenu::class,
    ];

    Plugin::registerClass(VisualizerMenu::class);

    // Onglet « CategoryManager » sur Configuration > Profils : matrice du droit plugin_categorymanager
    Plugin::registerClass(ProfileTab::class, [
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
        'homepage'     => 'https://github.com/mchuche/categorymanager',
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
        echo __('This plugin requires GLPI >= 11.0.', 'categorymanager');

        return false;
    }

    if (!is_readable(__DIR__ . '/vendor/autoload.php')) {
        echo __(
            'Composer autoload missing — run `composer install` in the plugin directory (plugins/categorymanager).',
            'categorymanager'
        );

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
