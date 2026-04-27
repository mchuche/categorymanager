#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Génère locales/fr_FR.po et locales/en_GB.po pour le domaine gettext « categorymanager »,
puis compile les .mo (msgfmt doit être disponible).

Usage : depuis la racine du plugin :
  python3 scripts/build_locales.py
"""

from __future__ import annotations

import os
import subprocess
import sys

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCALES = os.path.join(PLUGIN_ROOT, "locales")

# Chaînes PHP / Twig hors i18n_js (msgid anglais → français).
EXTRA_FR: dict[str, str] = {
    # « Category visualizer » / pluriel : voir PLURAL_FR (gettext _n + __ partagent le msgid singulier).
    "ITIL category visualization": "Visualisation des catégories ITIL",
    "Explore the category hierarchy and ticket volumes. Data is filtered by your profile and GLPI entities.": (
        "Explorez la hiérarchie des catégories et les volumes de tickets. Les données sont filtrées selon votre profil et vos entités GLPI."
    ),
    "Production files missing": "Fichiers de production absents",
    "Build the interface from the plugin frontend folder, then reload this page.": (
        "Compilez l’interface depuis le dossier frontend du plugin, puis rechargez cette page."
    ),
    "Run `npm run build` in plugins/categorymanager/frontend": (
        "Exécutez « npm run build » dans plugins/categorymanager/frontend"
    ),
    "Access to the ITIL category visualizer": "Accès au visualiseur des catégories ITIL",
    "CategoryManager": "CategoryManager",
    "Access": "Accès",
    "This plugin requires GLPI >= 11.0.": "Ce plugin nécessite GLPI ≥ 11.0.",
    "CategoryManager access denied (profile or insufficient ticket read): %s": (
        "Accès CategoryManager refusé (profil ou droits de lecture des tickets insuffisants) : %s"
    ),
    "Session expired — log in to GLPI again and reload the visualizer.": (
        "Session expirée — reconnectez-vous à GLPI puis rechargez le visualiseur."
    ),
    "JSON encoding failed (categories): %s": "Échec de l’encodage JSON (catégories) : %s",
    "JSON encoding failed (groups): %s": "Échec de l’encodage JSON (groupes) : %s",
    "POST method expected.": "Méthode POST attendue.",
    "Invalid or expired CSRF token — reload the visualizer page.": (
        "Jeton CSRF invalide ou expiré — rechargez la page du visualiseur."
    ),
    'Invalid "ids" parameter.': 'Paramètre « ids » invalide.',
    "JSON encoding failed (ticket_counts): %s": "Échec de l’encodage JSON (ticket_counts) : %s",
    "Invalid ids / start / end parameters.": "Paramètres ids / start / end invalides.",
    "JSON encoding failed (ticket_counts_range): %s": (
        "Échec de l’encodage JSON (ticket_counts_range) : %s"
    ),
    "Invalid group_ids / start / end parameters.": "Paramètres group_ids / start / end invalides.",
    "JSON encoding failed (group_counts_range): %s": (
        "Échec de l’encodage JSON (group_counts_range) : %s"
    ),
    "Unknown action.": "Action inconnue.",
    "Server error: %s": "Erreur serveur : %s",
}

# Pluriel _n (visualizer.class.php)
PLURAL_FR = (
    "Category visualizer",
    "Category visualizers",
    ["Visualiseur de catégories", "Visualiseurs de catégories"],
)

# Dictionnaire msgid → msgstr pour PluginCategorymanagerI18n::getJsMessages().
# À tenir à jour lors de chaque nouvelle clé dans inc/i18n_js.class.php (sinon gettext
# retombe sur l’anglais pour cette chaîne tant que le .po n’est pas régénéré manuellement).
JS_FR: dict[str, str] = {
    "Initializing…": "Initialisation…",
    "CategoryManager — GLPI visualization": "CategoryManager — visualisation GLPI",
    "ITIL categories": "Catégories ITIL",
    "Loading categories": "Chargement des catégories",
    "Retry": "Réessayer",
    "Switch to light mode": "Passer en mode clair",
    "Switch to dark mode": "Passer en mode sombre",
    "Full screen chart": "Graphique plein écran",
    "Exit full screen": "Quitter le plein écran",
    "Exit full screen (Esc)": "Quitter le plein écran (Échap)",
    "Full screen": "Plein écran",
    "Sunburst": "Sunburst",
    "Table": "Tableau",
    "Tree": "Arbre",
    "12 months": "12 mois",
    "Groups": "Groupes",
    "Heatmap: volume per branch over 12 rolling months": (
        "Carte de chaleur : volume par branche sur 12 mois glissants"
    ),
    "Tickets solved or closed per assigned group over 12 rolling months": (
        "Tickets résolus ou fermés par groupe assigné sur 12 mois glissants"
    ),
    "Refreshing data from GLPI…": "Actualisation des données depuis GLPI…",
    "Showing data from %s": "Données affichées depuis %s",
    "(from local cache)": "(cache local)",
    " — update recommended": " — mise à jour recommandée",
    "Refresh": "Actualiser",
    "Search for a category…": "Rechercher une catégorie…",
    "View type": "Type de vue",
    "ID": "ID",
    "Name": "Nom",
    "Parent category": "Catégorie parente",
    "Level": "Niveau",
    "Tickets (direct)": "Tickets (directs)",
    "Branch total": "Total branche",
    "Open tickets on this category only (excluding subcategories)": (
        "Tickets ouverts sur cette catégorie uniquement (hors sous-catégories)"
    ),
    'Sum: direct tickets + tickets on all subcategories (same logic as Sunburst “Tickets”)': (
        "Somme : tickets directs + tickets sur toutes les sous-catégories (même logique que Sunburst « Tickets »)"
    ),
    "categories": "catégories",
    "Number of categories loaded from GLPI": "Nombre de catégories chargées depuis GLPI",
    "Sunburst display mode": "Mode d’affichage Sunburst",
    "Display": "Affichage",
    "Structure": "Structure",
    "Tickets": "Tickets",
    "Proportional to tickets per branch.": "Proportionnel au nombre de tickets par branche.",
    "Structure view (hierarchical angles).": "Vue structure (angles hiérarchiques).",
    "Period (Sunburst only)": "Période (Sunburst uniquement)",
    "Refresh counts": "Rafraîchir les compteurs",
    "Re-run all GLPI count requests for this period": (
        "Relancer toutes les requêtes GLPI de comptage pour cette période"
    ),
    "Counting for period…": "Comptage pour la période…",
    "Category %s": "Catégorie %s",
    "No name": "Sans nom",
    "Unknown parent (%s)": "Parent inconnu (%s)",
    "No category": "Aucune catégorie",
    "No categories found": "Aucune catégorie trouvée",
    "Raw category data (debug)": "Données brutes des catégories (débogage)",
    "Showing the first 5 categories only": "Affichage des 5 premières catégories uniquement",
    "Ticket volume per branch (category + sub-trees) over the last 12 rolling months (window up to today). Use ▶ / ▼ to show subcategories under each business root. The date used is the ticket opening date (GLPI field detected: date or date_creation).": (
        "Volume de tickets par branche (catégorie + sous-arbres) sur les 12 derniers mois glissants (fenêtre jusqu’à aujourd’hui). Utilisez ▶ / ▼ pour afficher les sous-catégories sous chaque racine métier. La date utilisée est la date d’ouverture du ticket (champ GLPI détecté : date ou date_creation)."
    ),
    "Data from %s": "Données du %s",
    "(local 12-month cache)": "(cache local 12 mois)",
    "Refresh 12 months": "Rafraîchir les 12 mois",
    "Reload all requests (12 months × categories)": (
        "Recharger toutes les requêtes (12 mois × catégories)"
    ),
    "Sort rows": "Trier les lignes",
    "Order of business roots follows the sort; under each expanded root, GLPI tree order. Display only (does not change GLPI).": (
        "L’ordre des racines métier suit le tri ; sous chaque racine dépliée, ordre de l’arbre GLPI. Affichage uniquement (ne modifie pas GLPI)."
    ),
    "Category tree and volumes per branch": "Arbre des catégories et volumes par branche",
    "Collapse all": "Tout replier",
    "Hide all subcategories": "Masquer toutes les sous-catégories",
    "Expand branch: %s": "Déplier la branche : %s",
    "Collapse branch: %s": "Replier la branche : %s",
    "Number of tickets solved or closed (GLPI statuses 5 and 6) per assigned group over the last 12 rolling months (sliding window). Resolution date (solvedate). Only groups with at least one ticket in the period appear.": (
        "Nombre de tickets résolus ou fermés (statuts GLPI 5 et 6) par groupe assigné sur les 12 derniers mois glissants (fenêtre coulissante). Date de résolution (solvedate). Seuls les groupes ayant au moins un ticket sur la période apparaissent."
    ),
    "(local groups cache)": "(cache local groupes)",
    "Refresh groups": "Rafraîchir les groupes",
    "Reload group list and all counts (12 months × groups)": (
        "Recharger la liste des groupes et tous les comptages (12 mois × groupes)"
    ),
    "Display only; default order follows API load (often A→Z).": (
        "Affichage uniquement ; l’ordre par défaut suit le chargement API (souvent A→Z)."
    ),
    "No solved or closed tickets by assigned group in this 12-month window (check API rights or try again later).": (
        "Aucun ticket résolu ou fermé par groupe assigné sur cette fenêtre de 12 mois (vérifiez les droits API ou réessayez plus tard)."
    ),
    "Intensity = count of solved (5) or closed (6) tickets for the month, by resolution date (solvedate) and assigned group.": (
        "Intensité = nombre de tickets résolus (5) ou fermés (6) pour le mois, selon la date de résolution (solvedate) et le groupe assigné."
    ),
    "Heatmap of solved or closed tickets by group and month": (
        "Carte de chaleur des tickets résolus ou fermés par groupe et par mois"
    ),
    "All": "Tout",
    "Full history (same as table)": "Historique complet (identique au tableau)",
    "90d": "90 j",
    "Rolling 90-day window": "Fenêtre glissante de 90 jours",
    "6 mo": "6 mois",
    "Rolling 6-month window": "Fenêtre glissante de 6 mois",
    "1 yr": "1 an",
    "Rolling 1-year window": "Fenêtre glissante d’un an",
    "2 yr": "2 ans",
    "Rolling 2-year window": "Fenêtre glissante de deux ans",
    "3 yr": "3 ans",
    "Rolling 3-year window": "Fenêtre glissante de trois ans",
    "Independent of the table and tree (always full history). Period counters are cached with no automatic expiry; GLPI is called only when there is no local data for that period, or when you click Refresh counts. Filter on opening date (GLPI may fall back to date_creation).": (
        "Indépendant du tableau et de l’arbre (toujours historique complet). Les compteurs par période sont mis en cache sans expiration automatique ; GLPI n’est appelé que s’il n’y a pas encore de données locales pour cette période, ou si vous cliquez sur « Rafraîchir les compteurs ». Filtre sur la date d’ouverture (GLPI peut utiliser date_creation en secours)."
    ),
    "Tree order (business roots)": "Ordre de l’arbre (racines métier)",
    "Total volume over 12 months (↓)": "Volume total sur 12 mois (↓)",
    "Displayed month volume (↓)": "Volume du mois affiché (↓)",
    "Name (A→Z)": "Nom (A→Z)",
    "Load order (default)": "Ordre de chargement (par défaut)",
    "Sectors proportional to ticket count per branch (total including subcategories).": (
        "Secteurs proportionnels au nombre de tickets par branche (total incluant les sous-catégories)."
    ),
    "Sectors by hierarchy only (angles tied to leaves), without weighting by ticket volume.": (
        "Secteurs selon la hiérarchie uniquement (angles liés aux feuilles), sans pondération par volume de tickets."
    ),
    "Preparing load (GLPI session, then category list)…": (
        "Préparation du chargement (session GLPI, puis liste des catégories)…"
    ),
    "Step 1/3 — Connecting to GLPI API and retrieving ITIL categories…": (
        "Étape 1/3 — Connexion à l’API GLPI et récupération de la liste des catégories ITIL…"
    ),
    "Step 2/3 — %s categories received. Preparing ticket counts…": (
        "Étape 2/3 — %s catégories reçues. Préparation des compteurs de tickets…"
    ),
    "Step 3/3 — Counting tickets (full history for table/tree): preparing search/Ticket requests (0 / %s)…": (
        "Étape 3/3 — Comptage des tickets (historique complet pour tableau / arbre) : préparation des requêtes search/Ticket (0 / %s)…"
    ),
    "Step 3/3 — Counting tickets: %s / %s categories processed (batched requests to GLPI)…": (
        "Étape 3/3 — Comptage des tickets : %s / %s catégories traitées (requêtes par lots vers GLPI)…"
    ),
    "Finalizing — branch totals (including subcategories) and hierarchy levels…": (
        "Finalisation — totaux par branche (sous-catégories incluses) et niveaux hiérarchiques…"
    ),
    "Error loading data: %s": "Erreur lors du chargement des données : %s",
    "Unknown error": "Erreur inconnue",
    "Refresh failed: %s": "Actualisation impossible : %s",
    "Error retrieving categories: %s": "Erreur lors de la récupération des catégories : %s",
    "Load failed — see error message below or console (F12).": (
        "Échec du chargement — voir le message d’erreur ci-dessous ou la console (F12)."
    ),
    "Unable to count for this period.": "Comptage impossible pour cette période.",
    "Temporal heatmap: month %s/12 (%s)…": "Carte temporelle : mois %s/12 (%s)…",
    "Month %s/12 (%s) — %s/%s categories": "Mois %s/12 (%s) — %s/%s catégories",
    "Preparing monthly ranges…": "Préparation des plages mensuelles…",
    "Unable to load temporal heatmap (check API rights / Ticket date field).": (
        "Impossible de charger la carte temporelle (vérifiez les droits API / le champ date Ticket)."
    ),
    "Groups: month %s/12 (%s)…": "Groupes : mois %s/12 (%s)…",
    "Month %s/12 (%s) — %s/%s groups": "Mois %s/12 (%s) — %s/%s groupes",
    "Loading GLPI groups…": "Chargement des groupes GLPI…",
    "No GLPI groups found — check API rights or user profile.": (
        "Aucun groupe GLPI trouvé — vérifiez les droits API ou le profil utilisateur."
    ),
    "Unable to load group heatmap (check API rights / Ticket fields).": (
        "Impossible de charger la heatmap par groupes (vérifiez les droits API / les champs Ticket)."
    ),
}


def escape_po_string(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def write_po(path: str, lang: str, plural_forms: str, entries: dict[str, str]) -> None:
    lines = [
        'msgid ""',
        'msgstr ""',
        '"Project-Id-Version: CategoryManager\\n"',
        '"Report-Msgid-Bugs-To: \\n"',
        '"POT-Creation-Date: 2026-04-27 12:00+0000\\n"',
        '"PO-Revision-Date: 2026-04-27 12:00+0000\\n"',
        '"Last-Translator: \\n"',
        '"Language-Team: \\n"',
        f'"Language: {lang}\\n"',
        '"MIME-Version: 1.0\\n"',
        '"Content-Type: text/plain; charset=UTF-8\\n"',
        '"Content-Transfer-Encoding: 8bit\\n"',
        f'"Plural-Forms: {plural_forms}\\n"',
        "",
    ]

    # Pluriel _n (une entrée gettext avec msgid_plural).
    sid, pid, forms = PLURAL_FR
    lines.append('msgid "%s"' % escape_po_string(sid))
    lines.append('msgid_plural "%s"' % escape_po_string(pid))
    if lang == "fr_FR":
        lines.append('msgstr[0] "%s"' % escape_po_string(forms[0]))
        lines.append('msgstr[1] "%s"' % escape_po_string(forms[1]))
    else:
        lines.append('msgstr[0] "%s"' % escape_po_string(sid))
        lines.append('msgstr[1] "%s"' % escape_po_string(pid))
    lines.append("")

    for msgid in sorted(entries.keys(), key=lambda x: (x.lower(), x)):
        msgstr = entries[msgid]
        lines.append('msgid "%s"' % escape_po_string(msgid))
        lines.append('msgstr "%s"' % escape_po_string(msgstr))
        lines.append("")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> int:
    merged: dict[str, str] = {}
    merged.update(JS_FR)
    merged.update(EXTRA_FR)

    # fr_FR : traductions françaises
    fr_po = os.path.join(LOCALES, "fr_FR.po")
    write_po(fr_po, "fr_FR", "nplurals=2; plural=(n > 1);", merged)

    # en_GB : msgstr identique au msgid (catalogue pour cohérence GLPI)
    en_entries = {k: k for k in merged}
    en_po = os.path.join(LOCALES, "en_GB.po")
    write_po(en_po, "en_GB", "nplurals=2; plural=(n != 1);", en_entries)

    for stem in ("fr_FR", "en_GB"):
        po = os.path.join(LOCALES, f"{stem}.po")
        mo = os.path.join(LOCALES, f"{stem}.mo")
        subprocess.run(["msgfmt", "-o", mo, po], check=True)
        print("Written", po, "→", mo)

    return 0


if __name__ == "__main__":
    sys.exit(main())
