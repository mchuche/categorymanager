<?php

declare(strict_types=1);

namespace GlpiPlugin\Categorymanager\Service;

use GlpiPlugin\Categorymanager\I18n\JsCatalog;
use GlpiPlugin\Categorymanager\Itemtype\VisualizerMenu;
use Plugin;
use Session;

/**
 * Prépare les variables Twig et le script d'injection JS pour la page visualiseur.
 * Extrait de l'ancien front/visualizer.php (logique inchangée).
 */
final class VisualizerPageBuilder
{
    /**
     * @return array<string, mixed>
     */
    public static function build(): array
    {
        $pluginRoot   = Plugin::getPhpDir('categorymanager');
        $publicFsPath = $pluginRoot . '/public';
        $indexPath    = $publicFsPath . '/index.html';
        $pluginWeb    = Plugin::getWebDir('categorymanager');
        // Route Symfony NativeApiController — remplace ajax/native.php
        $nativeApi    = $pluginWeb . '/native';
        $csrfToken    = Session::getNewCSRFToken();
        $locale       = Session::getLanguage() ?? 'en_GB';

        $hasVueBuild = is_readable($indexPath);

        $vueStyles = [];
        $vueScripts = [];
        if ($hasVueBuild) {
            $indexContent = (string) file_get_contents($indexPath);
            if (preg_match_all('/<link[^>]+rel="stylesheet"[^>]+href="([^"]+)"[^>]*>/i', $indexContent, $mCss)) {
                foreach ($mCss[1] as $href) {
                    $vueStyles[] = $href;
                }
            }
            if (preg_match_all('/<script[^>]+src="([^"]+)"[^>]*>\\s*<\\/script>/i', $indexContent, $mJs)) {
                foreach ($mJs[1] as $src) {
                    $vueScripts[] = $src;
                }
            }
        }

        /*
         * Flags JSON pour injection dans une balise <script> :
         * sans JSON_HEX_TAG, une séquence "</script>" dans une chaîne traduite fermerait
         * la balise HTML trop tôt.
         */
        $cmJsonFlags = JSON_UNESCAPED_UNICODE
            | JSON_HEX_TAG
            | JSON_HEX_AMP
            | JSON_HEX_APOS
            | JSON_HEX_QUOT
            | (defined('JSON_INVALID_UTF8_SUBSTITUTE') ? JSON_INVALID_UTF8_SUBSTITUTE : 0);

        $jsI18nJson = json_encode(
            JsCatalog::getJsMessages(),
            $cmJsonFlags
        );

        // Globales JS : 5 affectations concaténées (API native, CSRF, web plugin, locale, catalogue i18n).
        $globalsScript = sprintf(
            '<script>%s%s%s%s%s</script>',
            'window.__CM_NATIVE_API__=' . json_encode($nativeApi, JSON_HEX_TAG | JSON_UNESCAPED_SLASHES) . ';',
            'window.__CM_GLPI_CSRF_TOKEN__=' . json_encode($csrfToken, JSON_HEX_TAG | JSON_UNESCAPED_SLASHES) . ';',
            'window.__CM_PLUGIN_WEB__=' . json_encode($pluginWeb, JSON_HEX_TAG | JSON_UNESCAPED_SLASHES) . ';',
            'window.__CM_LOCALE__=' . json_encode($locale, JSON_HEX_TAG | JSON_UNESCAPED_SLASHES) . ';',
            'window.__CM_I18N__=' . ($jsI18nJson !== false ? $jsI18nJson : '{}') . ';'
        );

        return [
            'card_title' => __('ITIL category visualization', 'categorymanager'),
            'card_intro' => __(
                'Explore the category hierarchy and ticket volumes. Data is filtered by your profile and GLPI entities.',
                'categorymanager'
            ),
            'icon'       => VisualizerMenu::getIcon(),
            'has_vue_build' => $hasVueBuild,
            'globals_script' => $globalsScript,
            'vue_styles' => $vueStyles,
            'vue_scripts' => $vueScripts,
            'alert_title' => __('Production files missing', 'categorymanager'),
            'alert_body' => __(
                'Build the interface from the plugin frontend folder, then reload this page.',
                'categorymanager'
            ),
            'alert_command' => __('Run `npm run build` in plugins/categorymanager/frontend', 'categorymanager'),
        ];
    }
}
