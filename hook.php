<?php
/**
 * -------------------------------------------------------------------------
 * CategoryManager — hooks d'installation / désinstallation (GLPI 11)
 * -------------------------------------------------------------------------
 * Droits profils : nom technique `plugin_categorymanager` (lecture = accès
 * visualiseur + ajax/native.php).
 *
 * Installation :
 * - Création d’une ligne par profil si absente ; **lecture accordée par défaut**
 *   (l’admin retire l’accès via Configuration > Profils > CategoryManager).
 * - Mise à jour depuis &lt; 0.1.2 : pour les lignes déjà présentes à 0 avec
 *   lecture ticket, passage à READ (corrige le menu invisible après 0.1.1).
 * -------------------------------------------------------------------------
 */

if (!defined('GLPI_ROOT')) {
    die("Sorry. You can't access this file directly");
}

/**
 * Lit la version enregistrée du plugin avant mise à jour du fichier setup.
 */
function plugin_categorymanager_get_db_version(): string
{
    global $DB;

    $it = $DB->request([
        'SELECT' => ['version'],
        'FROM'   => Plugin::getTable(),
        'WHERE'  => ['directory' => 'categorymanager'],
        'LIMIT'  => 1,
    ]);
    foreach ($it as $row) {
        return (string) ($row['version'] ?? '0');
    }

    return '0';
}

/**
 * Crée la ligne glpi_profilerights manquante pour chaque profil (lecture par défaut).
 *
 * Idempotent pour les insertions : si la ligne existe déjà, on ne la modifie pas ici.
 *
 * @return bool true si succès
 */
function plugin_categorymanager_install(): bool
{
    global $DB;

    // Version stockée en base **avant** que GLPI n’aligne le numéro sur setup.php (fin du cycle install)
    $dbVersionBefore = plugin_categorymanager_get_db_version();

    // Vide le cache des noms de droits possibles (liste dérivée de glpi_profilerights)
    ProfileRight::cleanAllPossibleRights();

    foreach ($DB->request(['SELECT' => ['id'], 'FROM' => Profile::getTable()]) as $row) {
        $profiles_id = (int) $row['id'];

        // Déjà présent : on ne change pas les droits dans cette boucle (évite d’écraser le choix admin)
        if (countElementsInTable(ProfileRight::getTable(), [
            'profiles_id' => $profiles_id,
            'name'        => 'plugin_categorymanager',
        ]) > 0) {
            continue;
        }

        // Lecture par défaut : le menu réapparaît ; retirer l’accès se fait dans l’onglet Profil
        $initialRights = READ;

        $DB->insert(ProfileRight::getTable(), [
            'profiles_id' => $profiles_id,
            'name'        => 'plugin_categorymanager',
            'rights'      => $initialRights,
        ]);
    }

    // Correctif 0.1.2 : profils déjà migrés en 0.1.1 avec droit plugin à 0 mais lecture ticket
    if (version_compare($dbVersionBefore, '0.1.2', '<')) {
        foreach ($DB->request(['SELECT' => ['id'], 'FROM' => Profile::getTable()]) as $row) {
            $profiles_id = (int) $row['id'];
            $rights       = ProfileRight::getProfileRights($profiles_id, ['plugin_categorymanager', 'ticket']);
            $pluginVal    = (int) ($rights['plugin_categorymanager'] ?? 0);
            $ticketVal    = (int) ($rights['ticket'] ?? 0);
            if ($pluginVal === 0 && ($ticketVal & READ) === READ) {
                $DB->update(
                    ProfileRight::getTable(),
                    ['rights' => READ],
                    [
                        'profiles_id' => $profiles_id,
                        'name'        => 'plugin_categorymanager',
                    ]
                );
            }
        }
    }

    ProfileRight::cleanAllPossibleRights();

    return true;
}

/**
 * Désinstallation : supprime les entrées du droit plugin (plus utilisé).
 *
 * @return bool true si succès
 */
function plugin_categorymanager_uninstall(): bool
{
    if (!ProfileRight::deleteProfileRights(['plugin_categorymanager'])) {
        return false;
    }
    ProfileRight::cleanAllPossibleRights();

    return true;
}
