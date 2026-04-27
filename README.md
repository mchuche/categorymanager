# CategoryManager — plugin GLPI

Visualiseur des **catégories ITIL** (Sunburst, métriques, comptages tickets) dans l’interface GLPI. La version publiée dans **Configuration → Plugins** est définie dans [`setup.php`](setup.php) (`PLUGIN_CATEGORYMANAGER_VERSION`).

## Prérequis

- **GLPI** 11.x (bornes min/max : [`plugin_version_categorymanager()`](setup.php) dans `setup.php`).
- **PHP** ≥ 8.2 (idem `requirements` dans `setup.php`).

## Installation côté GLPI

1. Déposer le dossier du plugin sous `plugins/categorymanager/` (comme tout plugin GLPI).
2. Vérifier que les **fichiers du build** sont présents dans [`public/`](public/) (`index.html`, dossier `assets/`). Sans eux, la page du visualiseur affiche un message invitant à lancer le build.
3. Dans GLPI : **Configuration → Plugins** → installer / activer **CategoryManager**.
4. Menu utilisateur : **Outils → Visualiseur catégories** (libellé selon la langue).
5. **Droits** : **Configuration → Profils** → onglet **CategoryManager** → **Lecture** (`plugin_categorymanager`). Détails dans [`frontend/README.md`](frontend/README.md) (section plugin GLPI).

## Reconstruire l’interface (assets Vue)

Les sources de l’interface sont dans [`frontend/`](frontend/). Pour régénérer `public/` :

```bash
cd frontend
npm ci    # ou npm install
npm run build
```

Le build Vite écrit directement dans `plugins/categorymanager/public/` (voir [`frontend/vite.config.js`](frontend/vite.config.js)).

**Sur le serveur GLPI**, Node.js n’est nécessaire que si vous compilez **sur cette machine**. Sinon, compilez ailleurs (CI, poste dev) et déployez le dossier `public/` avec le plugin.

## Documentation détaillée

| Document | Contenu |
|----------|---------|
| [`frontend/README.md`](frontend/README.md) | Deux modes (dev avec FastAPI vs plugin GLPI `ajax/native.php`), variables d’environnement, architecture |
| [`docs/STACK_ET_PROFESSIONNALISATION.md`](docs/STACK_ET_PROFESSIONNALISATION.md) | Stack technique, pistes de qualité (lint, tests, CI) |
| [`docs/PRD  CategorieManager - Visualiseur.md`](<docs/PRD  CategorieManager - Visualiseur.md>) | Exigences fonctionnelles (PRD) |

## Arborescence utile (aperçu)

```
categorymanager/
├── setup.php, hook.php      # Point d’entrée GLPI, installation / droits
├── inc/                     # Classes PHP (visualiseur, profil, données natives)
├── front/visualizer.php     # Page qui charge l’app et injecte l’API native
├── ajax/native.php          # JSON en session GLPI (pas de jetons REST navigateur)
├── public/                  # Build de production (généré par npm run build)
├── frontend/                # Sources Vue + serveur FastAPI de développement
└── docs/                    # PRD, stack, références API
```

## Licence

GPLv3+ (voir métadonnées du plugin dans `setup.php`).
