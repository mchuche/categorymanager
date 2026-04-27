<?php

/**
 * -------------------------------------------------------------------------
 * Onglet « Profils » — droit d’accès au visualiseur CategoryManager
 * -------------------------------------------------------------------------
 * Enregistré via {@see Plugin::registerClass} avec `addtabon` => `Profile`.
 * L’administrateur coche quels profils peuvent ouvrir la page (lecture seule).
 * Le nom technique du droit en base est `plugin_categorymanager` (colonne
 * `glpi_profilerights.name`), aligné sur {@see PluginCategorymanagerVisualizer::$rightname}.
 * -------------------------------------------------------------------------
 */

if (!defined('GLPI_ROOT')) {
    die("Sorry. You can't access this file directly");
}

/**
 * Matrice de droits sur la fiche Profil (Configuration > Profils > [profil] > CategoryManager).
 */
class PluginCategorymanagerProfile extends Profile
{
    /** Droit requis pour modifier les profils (pas le droit du plugin). */
    public static $rightname = 'profile';

    /**
     * Déclaration des lignes affichées dans la matrice GLPI (une ligne = un droit stocké en base).
     *
     * @return list<array{itemtype: class-string, label: string, field: string, rights: array<int, string>}>
     */
    public static function getAllRights(): array
    {
        return [
            [
                'itemtype' => 'PluginCategorymanagerVisualizer',
                'label'    => __('Accès au visualiseur de catégories ITIL', 'categorymanager'),
                'field'    => 'plugin_categorymanager',
                'rights'   => [
                    READ => __('Lecture'),
                ],
            ],
        ];
    }

    /**
     * Titre de l’onglet sur la fiche Profil.
     */
    public function getTabNameForItem(CommonGLPI $item, $withtemplate = 0)
    {
        if ($item->getType() === Profile::class) {
            return __('CategoryManager', 'categorymanager');
        }

        return '';
    }

    /**
     * Contenu de l’onglet : matrice lecture pour le droit `plugin_categorymanager`.
     */
    public static function displayTabContentForItem(CommonGLPI $item, $tabnum = 1, $withtemplate = 0)
    {
        if ($item->getType() === Profile::class) {
            $profile = new self();
            $profile->showFormCategorymanager((int) $item->getID());
        }

        return true;
    }

    /**
     * Affiche la matrice de droits (sauvegarde via le formulaire standard du profil GLPI).
     *
     * @param int $profiles_id identifiant du profil en cours d’édition
     */
    public function showFormCategorymanager(int $profiles_id): void
    {
        echo "<div class='firstbloc'>";

        // Étape 1 : seuls les comptes qui gèrent les profils peuvent modifier la matrice (pas les utilisateurs « helpdesk » sans droit profile)
        $canedit = Session::haveRightsOr(self::$rightname, [CREATE, UPDATE, PURGE]);
        $profile = new Profile();

        // Étape 2 : même formulaire POST que le reste de la fiche Profil (traitement standard GLPI sur « update »)
        if ($canedit) {
            echo "<form method='post' action='" . htmlspecialchars($profile->getFormURL(), ENT_QUOTES, 'UTF-8') . "'>";
        }

        // Étape 3 : charger le profil ciblé pour que displayRightsChoiceMatrix lise les valeurs courantes dans glpi_profilerights
        $profile->getFromDB($profiles_id);
        $profile->displayRightsChoiceMatrix(
            self::getAllRights(),
            [
                'canedit'       => $canedit,
                'default_class' => 'tab_bg_2',
                'title'         => __('Accès', 'categorymanager'),
            ]
        );

        if ($canedit) {
            echo "<div class='center'>";
            echo Html::hidden('id', ['value' => $profiles_id]);
            echo Html::submit(_sx('button', 'Save'), ['name' => 'update', 'class' => 'btn btn-primary']);
            echo "</div>\n";
            Html::closeForm();
        }

        echo '</div>';
    }
}
