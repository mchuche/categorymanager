<?php

declare(strict_types=1);

namespace GlpiPlugin\Categorymanager\Controller;

use Glpi\Controller\AbstractController;
use Glpi\Exception\Http\AccessDeniedHttpException;
use Glpi\Exception\SessionExpiredException;
use Glpi\Http\Firewall;
use Glpi\Security\Attribute\SecurityStrategy;
use GlpiPlugin\Categorymanager\Itemtype\VisualizerMenu;
use GlpiPlugin\Categorymanager\Service\NativeDataService;
use Session;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;
use Toolbox;

/**
 * API JSON « native » CategoryManager (session GLPI, sans jetons REST).
 * Remplace ajax/native.php — URL : /plugins/categorymanager/native?action=…
 */
final class NativeApiController extends AbstractController
{
    #[Route('/native', name: 'native_api', methods: ['GET', 'POST'])]
    #[SecurityStrategy(Firewall::STRATEGY_AUTHENTICATED)]
    public function __invoke(Request $request): Response
    {
        @set_time_limit(300);

        try {
            try {
                VisualizerMenu::checkVisualizerAccess();
            } catch (AccessDeniedHttpException $e) {
                return $this->jsonError(
                    403,
                    sprintf(
                        __('CategoryManager access denied (profile or insufficient ticket read): %s', 'categorymanager'),
                        $e->getMessage()
                    )
                );
            } catch (SessionExpiredException $e) {
                return $this->jsonError(
                    401,
                    __('Session expired — log in to GLPI again and reload the visualizer.', 'categorymanager')
                );
            }

            $action = $request->query->get('action', $request->request->get('action', ''));

            return match ($action) {
                'categories' => $this->handleCategories(),
                'groups' => $this->handleGroups(),
                'ticket_counts',
                'ticket_counts_range',
                'group_counts_range' => $this->handleCounts($request, (string) $action),
                default => $this->jsonError(400, __('Unknown action.', 'categorymanager')),
            };
        } catch (\Throwable $e) {
            try {
                Toolbox::logInFile(
                    'php-errors',
                    'categorymanager native API: ' . $e->getMessage() . "\n" . $e->getTraceAsString()
                );
            } catch (\Throwable $ignored) {
            }

            return $this->jsonError(
                500,
                sprintf(__('Server error: %s', 'categorymanager'), $e->getMessage())
            );
        }
    }

    private function handleCategories(): JsonResponse
    {
        return new JsonResponse([
            'ok' => true,
            'categories' => NativeDataService::getItilCategories(),
        ]);
    }

    private function handleGroups(): JsonResponse
    {
        return new JsonResponse([
            'ok' => true,
            'groups' => NativeDataService::getAssignableGroups(),
        ]);
    }

    private function handleCounts(Request $request, string $action): JsonResponse
    {
        if (!$request->isMethod('POST')) {
            return $this->jsonError(405, __('POST method expected.', 'categorymanager'));
        }

        $input = json_decode($request->getContent(), true) ?: [];

        if (!Session::validateCSRF($input, true)) {
            return $this->jsonError(
                403,
                __('Invalid or expired CSRF token — reload the visualizer page.', 'categorymanager')
            );
        }

        if ($action === 'ticket_counts') {
            $ids = $input['ids'] ?? [];
            if (!is_array($ids)) {
                return $this->jsonError(400, __('Invalid "ids" parameter.', 'categorymanager'));
            }
            $map = NativeDataService::getTicketCountsByCategory($ids);

            return $this->encodeCounts('ticket_counts', $map);
        }

        if ($action === 'ticket_counts_range') {
            $ids = $input['ids'] ?? [];
            $start = trim((string) ($input['start'] ?? ''));
            $end = trim((string) ($input['end'] ?? ''));
            if (!is_array($ids) || $start === '' || $end === '') {
                return $this->jsonError(400, __('Invalid ids / start / end parameters.', 'categorymanager'));
            }
            $map = NativeDataService::getTicketCountsByCategoryInDateRange($ids, $start, $end);

            return $this->encodeCounts('ticket_counts_range', $map);
        }

        $gids = $input['group_ids'] ?? [];
        $start = trim((string) ($input['start'] ?? ''));
        $end = trim((string) ($input['end'] ?? ''));
        if (!is_array($gids) || $start === '' || $end === '') {
            return $this->jsonError(400, __('Invalid group_ids / start / end parameters.', 'categorymanager'));
        }
        $map = NativeDataService::getTicketSolvedOrClosedCountsForGroupsInDateRange($gids, $start, $end);

        return $this->encodeCounts('group_counts_range', $map);
    }

    /**
     * @param array<int, int> $map
     */
    private function encodeCounts(string $context, array $map): JsonResponse
    {
        return new JsonResponse(['ok' => true, 'counts' => $map]);
    }


    /** Flags JSON communs (UTF-8 + remplacement caractères invalides). */
    private static function jsonFlags(): int
    {
        return JSON_UNESCAPED_UNICODE
            | (defined('JSON_INVALID_UTF8_SUBSTITUTE') ? JSON_INVALID_UTF8_SUBSTITUTE : 0);
    }

    private function jsonError(int $code, string $message): JsonResponse
    {
        return new JsonResponse(['ok' => false, 'error' => $message], $code);
    }
}
