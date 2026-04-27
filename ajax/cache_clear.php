<?php

/**
 * -------------------------------------------------------------------------
 * Invalidation « cache serveur » — no-op en mode plugin GLPI
 * -------------------------------------------------------------------------
 * Le front appelle ce script après les boutons « actualiser ». L’ancien
 * backend FastAPI vidait un cache SQLite ; ici il n’y a pas d’équivalent,
 * on renvoie simplement un JSON succès pour que l’UI reste cohérente.
 * -------------------------------------------------------------------------
 */

include '../../../inc/includes.php';

Html::header_nocache();

PluginCategorymanagerVisualizer::checkVisualizerAccess();

header('Content-Type: application/json; charset=UTF-8');
echo json_encode(['cleared' => true, 'rows_deleted' => 0], JSON_UNESCAPED_UNICODE);
