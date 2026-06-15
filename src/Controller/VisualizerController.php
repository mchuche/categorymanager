<?php

declare(strict_types=1);

namespace GlpiPlugin\Categorymanager\Controller;

use Glpi\Application\View\TemplateRenderer;
use Glpi\Controller\AbstractController;
use Glpi\Http\Firewall;
use Glpi\Security\Attribute\SecurityStrategy;
use GlpiPlugin\Categorymanager\Itemtype\VisualizerMenu;
use GlpiPlugin\Categorymanager\Service\VisualizerPageBuilder;
use Html;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

/**
 * Page principale du visualiseur (Twig + bundle Vue).
 * Remplace front/visualizer.php — URL : /plugins/categorymanager/visualizer
 */
final class VisualizerController extends AbstractController
{
    #[Route('/visualizer', name: 'visualizer', methods: ['GET'])]
    #[SecurityStrategy(Firewall::STRATEGY_CENTRAL_ACCESS)]
    public function __invoke(Request $request): Response
    {
        // Même contrôle d'accès que l'ancienne page front (droit plugin_categorymanager ou repli ticket)
        VisualizerMenu::checkVisualizerAccess();

        ob_start();
        Html::header(
            __('Category visualizer', 'categorymanager'),
            $request->getRequestUri(),
            'tools',
            'plugincategorymanagervisualizer'
        );

        TemplateRenderer::getInstance()->display(
            '@categorymanager/visualizer_page.html.twig',
            VisualizerPageBuilder::build()
        );

        Html::footer();

        return new Response(ob_get_clean() ?: '');
    }
}
