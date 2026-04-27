<?php
/**
 * -------------------------------------------------------------------------
 * API JSON « native » CategoryManager (session GLPI, sans jetons REST)
 * -------------------------------------------------------------------------
 * Paramètre GET action : categories, groups, ticket_counts, ticket_counts_range,
 * group_counts_range (voir README).
 * -------------------------------------------------------------------------
 */

include '../../../inc/includes.php';

/** @var int Flags JSON communs (UTF-8 + remplacement caractères invalides en base). */
$jsonFlags = JSON_UNESCAPED_UNICODE | (defined('JSON_INVALID_UTF8_SUBSTITUTE') ? JSON_INVALID_UTF8_SUBSTITUTE : 0);

$jsonError = static function (int $code, string $message) use ($jsonFlags): void {
    http_response_code($code);
    echo json_encode(['ok' => false, 'error' => $message], $jsonFlags);
};

try {
    Html::header_nocache();
    header('Content-Type: application/json; charset=UTF-8');
    @set_time_limit(300);

    include_once Plugin::getPhpDir('categorymanager') . '/inc/native.class.php';

    try {
        PluginCategorymanagerVisualizer::checkVisualizerAccess();
    } catch (\Glpi\Exception\Http\AccessDeniedHttpException $e) {
        $jsonError(
            403,
            sprintf(
                __('CategoryManager access denied (profile or insufficient ticket read): %s', 'categorymanager'),
                $e->getMessage()
            )
        );
        return;
    } catch (\Glpi\Exception\SessionExpiredException $e) {
        $jsonError(
            401,
            __('Session expired — log in to GLPI again and reload the visualizer.', 'categorymanager')
        );
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
                $jsonError(
                    500,
                    sprintf(
                        __('JSON encoding failed (categories): %s', 'categorymanager'),
                        json_last_error_msg()
                    )
                );
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
                $jsonError(
                    500,
                    sprintf(
                        __('JSON encoding failed (groups): %s', 'categorymanager'),
                        json_last_error_msg()
                    )
                );
                return;
            }
            echo $payload;
            return;

        case 'ticket_counts':
        case 'ticket_counts_range':
        case 'group_counts_range':
            if (strtoupper($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
                $jsonError(405, __('POST method expected.', 'categorymanager'));
                return;
            }

            $raw = file_get_contents('php://input');
            $input = is_string($raw) ? (json_decode($raw, true) ?: []) : [];

            if (!Session::validateCSRF($input, true)) {
                $jsonError(
                    403,
                    __('Invalid or expired CSRF token — reload the visualizer page.', 'categorymanager')
                );
                return;
            }

            if ($action === 'ticket_counts') {
                $ids = $input['ids'] ?? [];
                if (!is_array($ids)) {
                    $jsonError(400, __('Invalid "ids" parameter.', 'categorymanager'));
                    return;
                }
                $map = PluginCategorymanagerNative::getTicketCountsByCategory($ids);
                $payload = json_encode(['ok' => true, 'counts' => $map], $jsonFlags);
                if ($payload === false) {
                    $jsonError(
                        500,
                        sprintf(
                            __('JSON encoding failed (ticket_counts): %s', 'categorymanager'),
                            json_last_error_msg()
                        )
                    );
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
                    $jsonError(400, __('Invalid ids / start / end parameters.', 'categorymanager'));
                    return;
                }
                $map = PluginCategorymanagerNative::getTicketCountsByCategoryInDateRange($ids, $start, $end);
                $payload = json_encode(['ok' => true, 'counts' => $map], $jsonFlags);
                if ($payload === false) {
                    $jsonError(
                        500,
                        sprintf(
                            __('JSON encoding failed (ticket_counts_range): %s', 'categorymanager'),
                            json_last_error_msg()
                        )
                    );
                    return;
                }
                echo $payload;
                return;
            }

            $gids = $input['group_ids'] ?? [];
            $start = trim((string) ($input['start'] ?? ''));
            $end = trim((string) ($input['end'] ?? ''));
            if (!is_array($gids) || $start === '' || $end === '') {
                $jsonError(400, __('Invalid group_ids / start / end parameters.', 'categorymanager'));
                return;
            }
            $map = PluginCategorymanagerNative::getTicketSolvedOrClosedCountsForGroupsInDateRange($gids, $start, $end);
            $payload = json_encode(['ok' => true, 'counts' => $map], $jsonFlags);
            if ($payload === false) {
                $jsonError(
                    500,
                    sprintf(
                        __('JSON encoding failed (group_counts_range): %s', 'categorymanager'),
                        json_last_error_msg()
                    )
                );
                return;
            }
            echo $payload;
            return;

        default:
            $jsonError(400, __('Unknown action.', 'categorymanager'));
            return;
    }
} catch (\Throwable $e) {
    try {
        Toolbox::logInFile(
            'php-errors',
            'categorymanager native.php: ' . $e->getMessage() . "\n" . $e->getTraceAsString()
        );
    } catch (\Throwable $ignored) {
    }
    $jsonError(
        500,
        sprintf(__('Server error: %s', 'categorymanager'), $e->getMessage())
    );
}
