<?php

declare(strict_types=1);

namespace GlpiPlugin\Categorymanager\Controller;

use Glpi\Controller\AbstractController;
use Glpi\Http\Firewall;
use Glpi\Security\Attribute\SecurityStrategy;
use GlpiPlugin\Categorymanager\Itemtype\VisualizerMenu;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\Routing\Attribute\Route;

/**
 * Invalidation « cache serveur » — no-op en mode plugin GLPI.
 * Remplace ajax/cache_clear.php — URL : /plugins/categorymanager/cache/clear
 */
final class CacheClearController extends AbstractController
{
    #[Route('/cache/clear', name: 'cache_clear', methods: ['POST'])]
    #[SecurityStrategy(Firewall::STRATEGY_AUTHENTICATED)]
    public function __invoke(Request $request): JsonResponse
    {
        VisualizerMenu::checkVisualizerAccess();

        return new JsonResponse(['cleared' => true, 'rows_deleted' => 0]);
    }
}
