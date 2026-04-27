<?php

/**
 * -------------------------------------------------------------------------
 * Données CategoryManager — accès natif GLPI (sans apirest.php ni jetons)
 * -------------------------------------------------------------------------
 * Toutes les requêtes s’exécutent dans la session web courante : entités,
 * profils et droits sont ceux de l’utilisateur connecté (comme un écran
 * GLPI classique). Le front Vue consomme le JSON produit par ajax/native.php.
 *
 * Comptages tickets : agrégations SQL directes (GROUP BY), et non plus le
 * moteur SearchEngine par catégorie — évite les timeouts / mémoire quand il
 * y a des centaines de catégories (chaque appel SearchEngine est lourd).
 * -------------------------------------------------------------------------
 */

if (!defined('GLPI_ROOT')) {
    die("Sorry. You can't access this file directly");
}

/**
 * Chargement et agrégations pour le visualiseur (catégories, tickets, groupes).
 */
final class PluginCategorymanagerNative
{
    /**
     * Taille max des listes d’ids dans une seule clause `IN (...)` pour les agrégations tickets.
     * Au-delà, MySQL peut être très lent sur grosses tables et le proxy nginx renvoie 504.
     */
    private const TICKET_COUNT_IN_CHUNK = 80;

    /**
     * Restriction SQL de base sur `glpi_tickets` : non supprimé + entités visibles (session active).
     *
     * @return array<string, mixed>
     */
    private static function ticketSqlBaseWhere(): array
    {
        return [
            'glpi_tickets.is_deleted' => 0,
        ] + getEntitiesRestrictCriteria('glpi_tickets');
    }

    /**
     * Liste des catégories ITIL visibles pour l’utilisateur (entités, profil).
     *
     * @return list<array<string, mixed>> format proche de l’API REST pour le front existant
     */
    public static function getItilCategories(): array
    {
        global $DB;

        $table = ITILCategory::getTable();
        // « auto » : aligné sur la récursivité métier des catégories ITIL (sous-entités).
        $iterator = $DB->request([
            'FROM'   => $table,
            'WHERE'  => getEntitiesRestrictCriteria($table, '', '', 'auto'),
            'ORDER'  => [$table . '.completename ASC'],
            'LIMIT'  => 2000,
        ]);

        $out = [];
        foreach ($iterator as $row) {
            $id = (int) $row['id'];
            $parent = (int) ($row['itilcategories_id'] ?? 0);
            $out[] = [
                'id'                => $id,
                'name'              => (string) ($row['name'] ?? ''),
                'completename'      => (string) ($row['completename'] ?? ''),
                'itilcategories_id' => $parent > 0 ? $parent : 0,
                'level'             => (int) ($row['level'] ?? 0),
                'entities_id'       => (int) ($row['entities_id'] ?? 0),
                'comment'           => (string) ($row['comment'] ?? ''),
            ];
        }

        return $out;
    }

    /**
     * Comptage de tickets par catégorie ITIL (catégorie exacte sur le ticket).
     * Requêtes agrégées découpées par lots d’ids (`IN` limité) pour limiter le temps SQL et les 504 nginx.
     *
     * @param list<int> $ids
     * @return array<int, int> id catégorie => nombre
     */
    public static function getTicketCountsByCategory(array $ids): array
    {
        global $DB;

        $allIds = array_values(array_unique(array_map('intval', $ids)));
        $counts = [];
        foreach ($allIds as $id) {
            $counts[$id] = 0;
        }

        $positiveIds = array_values(array_filter($allIds, static fn (int $v): bool => $v > 0));
        if ($positiveIds === []) {
            return $counts;
        }

        $chunk = self::TICKET_COUNT_IN_CHUNK;
        $n = count($positiveIds);
        for ($off = 0; $off < $n; $off += $chunk) {
            $slice = array_slice($positiveIds, $off, $chunk);
            $where = self::ticketSqlBaseWhere() + [
                'glpi_tickets.itilcategories_id' => $slice,
            ];

            // Convention GLPI {@see DBmysqlIterator::handleFields} : clé de table => nom de champ.
            $iterator = $DB->request([
                'SELECT' => [
                    'glpi_tickets'     => 'itilcategories_id',
                    'COUNT DISTINCT'   => ['glpi_tickets.id AS nb'],
                ],
                'FROM'     => 'glpi_tickets',
                'WHERE'    => $where,
                'GROUPBY'  => 'glpi_tickets.itilcategories_id',
            ]);

            foreach ($iterator as $row) {
                $cid = (int) ($row['itilcategories_id'] ?? 0);
                if (array_key_exists($cid, $counts)) {
                    $counts[$cid] = (int) ($row['nb'] ?? 0);
                }
            }
        }

        return $counts;
    }

    /**
     * Comptages par catégorie avec filtre sur la date d’ouverture du ticket [start, end[.
     * Une requête agrégée pour toutes les catégories demandées.
     *
     * @param list<int> $ids
     * @return array<int, int>
     */
    public static function getTicketCountsByCategoryInDateRange(array $ids, string $startStr, string $endStr): array
    {
        global $DB;

        $allIds = array_values(array_unique(array_map('intval', $ids)));
        $counts = [];
        foreach ($allIds as $id) {
            $counts[$id] = 0;
        }

        $positiveIds = array_values(array_filter($allIds, static fn (int $v): bool => $v > 0));
        if ($positiveIds === [] || trim($startStr) === '' || trim($endStr) === '') {
            return $counts;
        }

        $chunk = self::TICKET_COUNT_IN_CHUNK;
        $n = count($positiveIds);
        for ($off = 0; $off < $n; $off += $chunk) {
            $slice = array_slice($positiveIds, $off, $chunk);
            $where = self::ticketSqlBaseWhere() + [
                'glpi_tickets.itilcategories_id' => $slice,
            ];
            $where[] = [
                'AND' => [
                    ['glpi_tickets.date' => ['>=', $startStr]],
                    ['glpi_tickets.date' => ['<', $endStr]],
                ],
            ];

            $iterator = $DB->request([
                'SELECT' => [
                    'glpi_tickets'     => 'itilcategories_id',
                    'COUNT DISTINCT'   => ['glpi_tickets.id AS nb'],
                ],
                'FROM'     => 'glpi_tickets',
                'WHERE'    => $where,
                'GROUPBY'  => 'glpi_tickets.itilcategories_id',
            ]);

            foreach ($iterator as $row) {
                $cid = (int) ($row['itilcategories_id'] ?? 0);
                if (array_key_exists($cid, $counts)) {
                    $counts[$cid] = (int) ($row['nb'] ?? 0);
                }
            }
        }

        return $counts;
    }

    /**
     * Tickets résolus (5) ou clos (6) : solvedate dans [start, end[, groupe assigné (liaison groupe/ticket).
     * Une requête agrégée par groupe au lieu de 2 × SearchEngine × nombre de groupes.
     *
     * @param list<int> $groupIds
     * @return array<int, int> id groupe => total (5 + 6)
     */
    public static function getTicketSolvedOrClosedCountsForGroupsInDateRange(
        array $groupIds,
        string $startStr,
        string $endStr
    ): array {
        global $DB;

        $allGids = array_values(array_unique(array_map('intval', $groupIds)));
        $counts = [];
        foreach ($allGids as $gid) {
            $counts[$gid] = 0;
        }

        $positiveGids = array_values(array_filter($allGids, static fn (int $v): bool => $v > 0));
        if ($positiveGids === [] || trim($startStr) === '' || trim($endStr) === '') {
            return $counts;
        }

        $gt = \Group_Ticket::getTable();

        $chunk = self::TICKET_COUNT_IN_CHUNK;
        $n = count($positiveGids);
        for ($off = 0; $off < $n; $off += $chunk) {
            $slice = array_slice($positiveGids, $off, $chunk);
            $where = [
                $gt . '.type'   => (int) \CommonITILActor::ASSIGN,
                $gt . '.groups_id' => $slice,
                'glpi_tickets.is_deleted' => 0,
                'glpi_tickets.status'     => [5, 6],
            ];
            $where = $where + getEntitiesRestrictCriteria('glpi_tickets');
            $where[] = [
                'AND' => [
                    ['glpi_tickets.solvedate' => ['>=', $startStr]],
                    ['glpi_tickets.solvedate' => ['<', $endStr]],
                ],
            ];

            $iterator = $DB->request([
                'SELECT' => [
                    $gt              => 'groups_id',
                    'COUNT DISTINCT' => ['glpi_tickets.id AS nb'],
                ],
                'FROM'       => $gt,
                'INNER JOIN' => [
                    'glpi_tickets' => [
                        'ON' => [
                            $gt            => 'tickets_id',
                            'glpi_tickets' => 'id',
                        ],
                    ],
                ],
                'WHERE'   => $where,
                'GROUPBY' => [$gt . '.groups_id'],
            ]);

            foreach ($iterator as $row) {
                $gid = (int) ($row['groups_id'] ?? 0);
                if (array_key_exists($gid, $counts)) {
                    $counts[$gid] = (int) ($row['nb'] ?? 0);
                }
            }
        }

        return $counts;
    }

    /**
     * Groupes assignables (techniciens) visibles pour l’utilisateur.
     *
     * @return list<array{id: int, name: string}>
     */
    public static function getAssignableGroups(): array
    {
        global $DB;

        $gtable = Group::getTable();
        $where = array_merge(
            [
                'is_assign' => 1,
            ],
            getEntitiesRestrictCriteria($gtable, '', '', 'auto')
        );

        $iterator = $DB->request([
            'FROM'   => $gtable,
            'WHERE'  => $where,
            'ORDER'  => [$gtable . '.completename ASC'],
            'LIMIT'  => 8000,
        ]);

        $out = [];
        foreach ($iterator as $row) {
            $id = (int) $row['id'];
            if ($id <= 0) {
                continue;
            }
            $name = trim((string) ($row['completename'] ?? $row['name'] ?? ''));
            if ($name === '') {
                $name = 'Groupe ' . $id;
            }
            $out[] = ['id' => $id, 'name' => $name];
        }

        return $out;
    }
}
