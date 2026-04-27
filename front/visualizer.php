<?php
/**
 * -------------------------------------------------------------------------
 * Page front — CategoryManager (corps de page avec l’app Vue)
 * -------------------------------------------------------------------------
 * Après `npm run build` dans frontend/, les assets sont servis
 * depuis plugins/categorymanager/public/ (voir vite.config.js).
 * Les données viennent de ajax/native.php (session GLPI, pas d’API REST navigateur).
 * Tant que le build n’existe pas, un message invite à lancer le build.
 * -------------------------------------------------------------------------
 */

require_once __DIR__ . '/../../../inc/includes.php';

// Droit : matrice Profils (plugin_categorymanager) ou repli ticket si clé absente — voir PluginCategorymanagerVisualizer::checkVisualizerAccess()
PluginCategorymanagerVisualizer::checkVisualizerAccess();

Html::header(
    __('Visualiseur de catégories', 'categorymanager'),
    $_SERVER['PHP_SELF'],
    'tools',
    'plugincategorymanagervisualizer'
);

$pluginRoot   = Plugin::getPhpDir('categorymanager');
// Répertoire servi par le serveur web : .../plugins/categorymanager/public/
$publicFsPath = $pluginRoot . '/public';
$indexPath    = $publicFsPath . '/index.html';
$webBase      = Plugin::getWebDir('categorymanager') . '/public';

if (!is_readable($indexPath)) {
    // Pas encore de build Vite : message explicite (étape pipeline CI / local)
    echo "<div class='alert alert-info'>";
    echo "<p><strong>CategoryManager</strong> : les fichiers de production ne sont pas présents.</p>";
    echo "<p>Exécutez <code>npm run build</code> dans <code>plugins/categorymanager/frontend</code>, ";
    echo "puis rechargez cette page.</p>";
    echo "</div>";
    Html::footer();
    return;
}

/**
 * Mode « PHP natif » : le JS appelle ajax/native.php (session GLPI, moteur de recherche).
 * __CM_GLPI_CSRF_TOKEN__ : jeton pour les POST JSON (Session::validateCSRF avec préservation).
 */
$pluginWeb = Plugin::getWebDir('categorymanager');
$nativeApi  = $pluginWeb . '/ajax/native.php';
$csrfToken  = Session::getNewCSRFToken();

echo '<script>';
echo 'window.__CM_NATIVE_API__=' . json_encode($nativeApi, JSON_HEX_TAG | JSON_UNESCAPED_SLASHES) . ';';
echo 'window.__CM_GLPI_CSRF_TOKEN__=' . json_encode($csrfToken, JSON_HEX_TAG | JSON_UNESCAPED_SLASHES) . ';';
echo 'window.__CM_PLUGIN_WEB__=' . json_encode($pluginWeb, JSON_HEX_TAG | JSON_UNESCAPED_SLASHES) . ';';
echo "</script>\n";

/**
 * Le build Vite génère index.html avec &lt;link&gt; (CSS) et &lt;script&gt; (JS module)
 * en chemins absolus sous /plugins/categorymanager/public/...
 * Ordre : feuilles de style d’abord, puis scripts (évite flash sans styles).
 */
$indexContent = (string) file_get_contents($indexPath);
if (preg_match_all('/<link[^>]+rel="stylesheet"[^>]+href="([^"]+)"[^>]*>/i', $indexContent, $mCss)) {
    foreach ($mCss[1] as $href) {
        echo '<link rel="stylesheet" href="' . htmlspecialchars($href) . '">' . "\n";
    }
}
if (preg_match_all('/<script[^>]+src="([^"]+)"[^>]*>\\s*<\\/script>/i', $indexContent, $mJs)) {
    foreach ($mJs[1] as $src) {
        echo '<script type="module" src="' . htmlspecialchars($src) . '"></script>' . "\n";
    }
}

echo '<div id="app" class="container-fluid" style="min-height:50vh"></div>' . "\n";

Html::footer();
