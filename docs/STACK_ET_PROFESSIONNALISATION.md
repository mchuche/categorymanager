# Stack technique et pistes de professionnalisation — CategorieManager

Document de référence : technologies actuellement utilisées dans le dépôt, puis recommandations **priorisées** pour renforcer la qualité, la maintenabilité et le niveau « produit » de l’application.

---

## 1. Technologies utilisées (état du projet)

### Langage et exécution

| Élément | Détail |
|--------|--------|
| **JavaScript (ES modules)** | Pas de TypeScript dans le code applicatif ; `package.json` avec `"type": "module"`. |
| **Node.js** | **16.14+** suffit avec Vite 4 (build plugin) ; **18+** reste le standard recommandé pour l’écosystème npm / futures montées de version Vite. |

### Front-end — cœur de l’UI

| Techno | Rôle |
|--------|------|
| **Vue 3** | Framework UI (Composition API, composants `.vue`). |
| **Pinia** | État global (ex. authentification, thème). |
| **Vite 4** | Build dev/prod, HMR, bundling Rollup sous le capot (aligné Node 16 côté build plugin). |
| **@vitejs/plugin-vue** | Compilation des SFC Vue. |

### Données et API

| Techno | Rôle |
|--------|------|
| **Axios** | Requêtes HTTP : en **dev**, proxy Vite → FastAPI → `apirest.php` ; en **plugin GLPI**, `ajax/native.php` (session PHP, agrégations SQL / droits entités — pas de jetons REST navigateur). |
| **Proxy Vite (dev)** | Contournement CORS en développement ; cible configurable dans `vite.config.js`. |

### Visualisation

| Techno | Rôle |
|--------|------|
| **D3.js v7** | Graphiques (Sunburst, hiérarchies, échelles, etc.). |

### Persistance navigateur

| Mécanisme | Usage dans le projet |
|-----------|----------------------|
| **`localStorage`** | Caches métier (catégories, heatmaps, Sunburst), thème — centralisé dans `src/services/browserLocalCache.js`. |
| **`sessionStorage`** | Session d’auth, brouillon formulaire connexion, index période Sunburst — via les variantes `*Session*` du même module. |

### Hébergement des assets

| Élément | Détail |
|--------|--------|
| **Build statique intégré au plugin GLPI** | `frontend/vite.config.js` définit `build.outDir` vers `plugins/categorymanager/public/` et `base: '/plugins/categorymanager/public/'` — c’est la cible du **Mode B** (voir `frontend/README.md`, section déploiement plugin). |
| **Build hors plugin** | Un déploiement « standalone » peut reprendre les mêmes fichiers statiques ; ce n’est pas le flux principal documenté pour GLPI. |

### Documentation produit / API

| Fichier | Contenu |
|---------|---------|
| `docs/PRD  CategorieManager - Visualiseur.md` | Exigences fonctionnelles |
| `docs/GLPI11 High-Level REST API.json` | Référence API (réutilisable pour tests ou mocks) |

---

## 2. Ce qui manque aujourd’hui (constat « pro »)

Ces éléments ne sont **pas** présents dans le dépôt au moment de la rédaction ; les ajouter améliore nettement le niveau professionnel :

- **Linter / formateur** (ESLint, Prettier) — pas de config racine dédiée au projet.
- **Tests automatisés** (unitaires / composants) — pas de Vitest / Cypress / Playwright dans `package.json`.
- **Typage statique** — pas de TypeScript ni de contrôle strict JSDoc via `tsc --checkJs`.
- **CI/CD** — pas de pipeline visible (GitHub Actions, GitLab CI, etc.) pour `lint` + `build` (+ tests).
- **Variables d’environnement** — la cible du proxy Vite est en dur dans le fichier de config (à externaliser pour les différents environnements).

---

## 3. Recommandations (par ordre de jugement)

Les priorités ci-dessous sont **indicatives** : adapter à votre contrainte (temps, équipe, hébergement).

### Priorité haute — retour sur investissement rapide

1. **ESLint + Prettier (+ plugin Vue)**  
   - Uniformise le style, détecte les bugs classiques (variables inutilisées, hooks mal utilisés).  
   - Intégration naturelle avec l’IDE (Cursor / VS Code).

2. **Script `npm run lint` et `npm run format`**  
   - Exécutés avant commit (husky + lint-staged, optionnel) ou au minimum en CI.

3. **CI minimale**  
   - À chaque push / PR : `npm ci`, `npm run build`, et si vous ajoutez le lint : `npm run lint`.  
   - Évite les régressions de build sur une autre machine.

4. **Variables locales `.env` + lecture des URLs via `import.meta.env`**  
   - Pour la **cible du proxy** et toute URL de dev, éviter les URLs d’instance dans le dépôt.  
   - Documenter les noms de variables dans le README (sans commiter de `.env` ni de secrets).

### Priorité moyenne — qualité et évolutivité

5. **Vitest + Vue Test Utils**  
   - Commencer par les **stores Pinia** et les **services purs** (`glpiApi`, caches, `treeTransform`).  
   - Les composants lourds (Dashboard) peuvent venir ensuite.

6. **TypeScript progressif**  
   - Soit migration `.ts` + `<script setup lang="ts">`,  
   - soit **`allowJs` + JSDoc** avec `checkJs` pour typer sans tout réécrire d’un coup.

7. **Découpage des routes (Vue Router) + lazy loading**  
   - Si l’app grossit : `Login` vs `Dashboard` en chunks séparés réduit le JS initial.

8. **Gestion d’erreurs utilisateur**  
   - Toasts / bannières cohérentes pour les échecs API, timeouts, 401/403.  
   - Éviter uniquement `console.warn` pour l’utilisateur final.

### Priorité plus basse ou contextuelle

9. **Analyse du bundle** (`rollup-plugin-visualizer` ou `vite build --report`)  
   - Identifier si D3 est entièrement importé alors qu’un import ciblé suffirait.

10. **Accessibilité (a11y)**  
    - Contraste, focus clavier, labels de formulaires (souvent déjà partiellement là — audit ciblé).

11. **E2E (Playwright / Cypress)**  
    - Utile si vous avez des parcours critiques (connexion mockée, dashboard).

12. **Journalisation structurée côté client**  
    - En interne uniquement : niveaux de log, corrélation avec version de build (`import.meta.env`).

---

## 4. Synthèse « feuille de route » possible

| Phase | Actions typiques |
|-------|-------------------|
| **Court terme** | ESLint + Prettier, CI build (+ lint), `.env` pour le proxy |
| **Moyen terme** | Vitest sur services/stores, amélioration UX erreurs API |
| **Long terme** | TypeScript ou checkJs strict, routes lazy, E2E si besoin métier |

---

## 5. Références dans ce dépôt

- **Modes dev (FastAPI) vs plugin GLPI (`native.php`)** : tableau et déploiement dans `frontend/README.md`.
- Architecture générale : `frontend/README.md`  
- PRD : `docs/PRD  CategorieManager - Visualiseur.md`  
- Point d’entrée app : `frontend/src/main.js`  
- Persistance navigateur unifiée : `frontend/src/services/browserLocalCache.js`

---

*Document généré pour faciliter la montée en maturité du produit ; à faire évoluer avec les choix d’équipe (hébergeur, politique de sécurité, charte graphique).*
