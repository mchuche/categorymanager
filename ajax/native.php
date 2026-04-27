<?php



/**

 * -------------------------------------------------------------------------

 * API JSON « native » CategoryManager (session GLPI, sans jetons REST)

 * -------------------------------------------------------------------------

 * Paramètre GET action :

 * - categories          → liste catégories ITIL

 * - groups              → groupes assignables

 * - ticket_counts       → POST JSON { "ids": [1,2,…], "_glpi_csrf_token": "…" }

 * - ticket_counts_range → POST JSON { "ids", "start", "end", "_glpi_csrf_token" }

 * - group_counts_range  → POST JSON { "group_ids", "start", "end", "_glpi_csrf_token" }

 * -------------------------------------------------------------------------

 *

 * Tout le travail utile est dans un seul try : si une erreur survient avant (ex. chargement

 * de la classe du plugin), Symfony renverrait le JSON générique « Une erreur est survenue »

 * sans champ `ok` / `error` attendu par le front.

 */



include '../../../inc/includes.php';



/** @var int Flags JSON communs (UTF-8 + remplacement caractères invalides en base). */

$jsonFlags = JSON_UNESCAPED_UNICODE | (defined('JSON_INVALID_UTF8_SUBSTITUTE') ? JSON_INVALID_UTF8_SUBSTITUTE : 0);



$jsonError = static function (int $code, string $message) use ($jsonFlags): void {

    http_response_code($code);

    echo json_encode(['ok' => false, 'error' => $message], $jsonFlags);

};



try {

    // GLPI 11 : la fonction globale `header_nocache()` n’existe plus — équivalent sur {@see Html}.
    Html::header_nocache();



    header('Content-Type: application/json; charset=UTF-8');



    // Les comptages agrégés restent légers ; on garde une marge pour grosses bases.

    @set_time_limit(300);



    include_once Plugin::getPhpDir('categorymanager') . '/inc/native.class.php';



    /**

     * Droit minimal : même matrice que la page visualiseur (plugin_categorymanager, lecture).

     * Réponses JSON explicites pour ne pas laisser Symfony renvoyer seulement « Une erreur est survenue ».

     */

    try {

        PluginCategorymanagerVisualizer::checkVisualizerAccess();

    } catch (\Glpi\Exception\Http\AccessDeniedHttpException $e) {

        $jsonError(403, 'Accès CategoryManager refusé (profil ou lecture ticket insuffisante) : ' . $e->getMessage());

        return;

    } catch (\Glpi\Exception\SessionExpiredException $e) {

        $jsonError(401, 'Session expirée — reconnectez-vous à GLPI puis rechargez le visualiseur.');

        return;

    }



    $action = $_GET['action'] ?? $_POST['action'] ?? '';



    switch ($action) {

        case 'categories':

            $payload = json_encode(

                ['ok' => true, 'categories' => PluginCategorymanagerNative::getItilCategories()],

                $jsonFlags

            );

            if ($payload === false) {

                $jsonError(500, 'Encodage JSON impossible (catégories) : ' . json_last_error_msg());

                return;

            }

            echo $payload;

            return;



        case 'groups':

            $payload = json_encode(

                ['ok' => true, 'groups' => PluginCategorymanagerNative::getAssignableGroups()],

                $jsonFlags

            );

            if ($payload === false) {

                $jsonError(500, 'Encodage JSON impossible (groupes) : ' . json_last_error_msg());

                return;

            }

            echo $payload;

            return;



        case 'ticket_counts':

        case 'ticket_counts_range':

        case 'group_counts_range':

            if (strtoupper($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {

                $jsonError(405, 'Méthode POST attendue.');

                return;

            }

            $raw = file_get_contents('php://input');

            $input = is_string($raw) ? (json_decode($raw, true) ?: []) : [];

            if (!Session::validateCSRF($input, true)) {

                $jsonError(403, 'Jeton CSRF invalide ou expiré — rechargez la page du visualiseur.');

                return;

            }



            if ($action === 'ticket_counts') {

                $ids = $input['ids'] ?? [];

                if (!is_array($ids)) {

                    $jsonError(400, 'Paramètre « ids » invalide.');

                    return;

                }

                $map = PluginCategorymanagerNative::getTicketCountsByCategory($ids);

                $payload = json_encode(['ok' => true, 'counts' => $map], $jsonFlags);

                if ($payload === false) {

                    $jsonError(500, 'Encodage JSON impossible (ticket_counts) : ' . json_last_error_msg());

                    return;

                }

                echo $payload;

                return;

            }



            if ($action === 'ticket_counts_range') {

                $ids = $input['ids'] ?? [];

                $start = trim((string) ($input['start'] ?? ''));

                $end = trim((string) ($input['end'] ?? ''));

                if (!is_array($ids) || $start === '' || $end === '') {

                    $jsonError(400, 'Paramètres ids / start / end invalides.');

                    return;

                }

                $map = PluginCategorymanagerNative::getTicketCountsByCategoryInDateRange($ids, $start, $end);

                $payload = json_encode(['ok' => true, 'counts' => $map], $jsonFlags);

                if ($payload === false) {

                    $jsonError(500, 'Encodage JSON impossible (ticket_counts_range) : ' . json_last_error_msg());

                    return;

                }

                echo $payload;

                return;

            }



            // group_counts_range

            $gids = $input['group_ids'] ?? [];

            $start = trim((string) ($input['start'] ?? ''));

            $end = trim((string) ($input['end'] ?? ''));

            if (!is_array($gids) || $start === '' || $end === '') {

                $jsonError(400, 'Paramètres group_ids / start / end invalides.');

                return;

            }

            $map = PluginCategorymanagerNative::getTicketSolvedOrClosedCountsForGroupsInDateRange(

                $gids,

                $start,

                $end

            );

            $payload = json_encode(['ok' => true, 'counts' => $map], $jsonFlags);

            if ($payload === false) {

                $jsonError(500, 'Encodage JSON impossible (group_counts_range) : ' . json_last_error_msg());

                return;

            }

            echo $payload;

            return;



        default:

            $jsonError(400, 'Action inconnue.');

            return;

    }

} catch (\Throwable $e) {

    try {

        Toolbox::logInFile(

            'php-errors',

            'categorymanager native.php: ' . $e->getMessage() . "\n" . $e->getTraceAsString()

        );

    } catch (\Throwable $ignored) {

        // Ne pas masquer l’erreur métier si l’écriture du log échoue (droits disque, etc.).

    }

    $jsonError(500, 'Erreur serveur : ' . $e->getMessage());

}


