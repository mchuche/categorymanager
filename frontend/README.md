# CategorieManager — Visualiseur de catégories GLPI

Application **Vue.js 3** pour visualiser de manière interactive les catégories ITIL de GLPI (Sunburst, métriques, etc.).

**Lecture rapide :** ce dépôt sert à **deux usages** qui ne doivent pas être confondus :

| | **Mode A — Développement local** | **Mode B — Plugin dans GLPI (production typique)** |
|---|----------------------------------|-----------------------------------------------------|
| **But** | Coder l’interface sans forcément passer par une page GLPI à chaque requête | Utilisateurs finaux dans GLPI après build des assets |
| **Données** | Backend **FastAPI** qui appelle `apirest.php` avec jetons **côté serveur Python** | Fichier PHP **`ajax/native.php`** : **session GLPI**, droits et entités comme un écran natif |
| **Jetons REST (App / User)** | Configurés dans `server/.env`, jamais dans le navigateur | **Aucun** côté client ; pas besoin d’activer la consommation REST pour les utilisateurs du visualiseur |
| **Prérequis serveur app** | Node.js + Python + instance GLPI avec API REST pour le proxy | **Seulement** GLPI 11+ et le plugin ; **pas** de processus Python ni d’API REST obligatoire pour ce chemin |
| **Commandes typiques** | `npm run server` + `npm run dev` | `npm run build` puis activer le plugin dans GLPI |

Les sections ci-dessous détaillent **Mode A** puis **Mode B** dans cet ordre logique (dév → livraison).

---

## Fonctionnalités (interface commune)

Quel que soit le mode, l’interface offre notamment :

- **Visualisation Sunburst** et hiérarchie des catégories ITIL
- **Métriques** : nombre de tickets par catégorie, plages de dates, heatmaps / groupes (selon l’écran)

**Côté technique, le « backend » diffère :**

- **Mode A** : FastAPI fait office de **proxy** vers l’API REST GLPI, avec cache HTTP persistant (SQLite) côté serveur de dev ; boutons « Actualiser » / « Rafraîchir » pour invalider ce cache.
- **Mode B** : le navigateur parle uniquement à **`plugins/categorymanager/ajax/native.php`** ; PHP interroge la base comme GLPI (agrégations SQL, restrictions d’entités). **Pas** de FastAPI ni de SQLite sur ce chemin.

---

## Prérequis — développement local (Mode A)

- **Node.js** **16.14+** (build Vite 4) ou **18+** recommandé, et `npm`
- **Python 3.10+** avec `pip` (backend FastAPI)
- Une instance GLPI avec l’**API REST bas niveau** (`apirest.php`) activée pour les tests du proxy
- **App-Token** et **User-Token** renseignés dans `server/.env` (secrets **uniquement** côté machine de dev, jamais committés)

---

## Prérequis — déploiement plugin GLPI (Mode B)

- **GLPI** version compatible plugin (voir `setup.php` du plugin : plage `glpi` min/max)
- **Node.js + npm** sur la machine qui **produit le build** (CI ou poste développeur) — le serveur GLPI n’a pas besoin de Node en production si vous y **copiez** déjà le dossier `public/` généré
- **Pas** de Python ni de fichier `.env` FastAPI sur le serveur GLPI pour faire fonctionner le visualiseur intégré : tout passe par PHP et la session utilisateur

---

## Variables d’environnement — Mode A (développement uniquement)

Ces fichiers restent **hors dépôt** (voir `.gitignore`). Créez-les localement à la main.

### Fichier `.env` à la racine du projet Vue (`frontend/`)

Utilisé par **Vite** (`import.meta.env`). Ce n’est **pas** un secret : même URL d’instance que le backend pour la cohérence des clés de cache navigateur.

```bash
# Exemple — adapter l’URL à votre instance GLPI
VITE_GLPI_PUBLIC_BASE_URL=https://votre-glpi.example.com
```

*(Optionnel)* vous pouvez aussi y dupliquer les variables du backend FastAPI si vous ne souhaitez pas tenir `server/.env` séparément ; dans ce cas les mêmes noms que ci-dessous (`GLPI_BASE_URL`, etc.) sont lus selon la logique du serveur Python.

### Fichier `server/.env` (FastAPI — proxy vers `apirest.php`)

```bash
# URL publique de l’instance GLPI (sans slash final)
GLPI_BASE_URL=https://votre-glpi.example.com

# Jetons API bas niveau (Configuration GLPI > API ; profil utilisateur)
GLPI_APP_TOKEN=
GLPI_USER_TOKEN=

# Optionnel — TLS : false si certificat auto-signé / CA interne non reconnue par Python (redémarrer uvicorn après changement)
# GLPI_TLS_VERIFY=false

# Optionnel — origines CORS si le front appelle directement le port 8000 (virgule)
# CORS_ORIGINS=http://127.0.0.1:5174,http://localhost:5174
```

---

## Installation — Mode A (front + backend FastAPI)

### Front (racine du projet Vue)

```bash
npm install
# Créez .env à la racine du projet Vue — voir section « Variables d'environnement » ci-dessus.
```

### Backend FastAPI (`server/`)

```bash
cd server
python -m venv .venv
# Linux / macOS :
source .venv/bin/activate
# Windows :
# .venv\Scripts\activate
pip install -r requirements.txt
# Créez server/.env — voir section « Variables d'environnement » ci-dessus (GLPI_BASE_URL, jetons).
```

---

## Développement local (Mode A — deux terminaux)

1. **API** (port 8000) : à la racine du projet front, `npm run server` (ou `cd server && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`).
2. **Front** (port 5174) : `npm run dev` — le proxy Vite envoie `/api` vers `http://127.0.0.1:8000` (voir `vite.config.js`).

Ouvrir l’application fournie par Vite : pas d’écran de connexion dans le navigateur ; les jetons GLPI restent **uniquement** dans l’environnement du serveur FastAPI.

---

## Build et déploiement

### Plugin GLPI (Mode B — chemin principal en production)

1. À la racine du projet Vue : **`npm run build`**.
2. **Vite** écrit directement dans le répertoire **`public/` du plugin GLPI**, à côté du PHP :  
   `…/plugins/categorymanager/public/`  
   (voir `vite.config.js` : `outDir` pointe vers ce dossier, `base: '/plugins/categorymanager/public/'`).
3. Dans GLPI : activer / mettre à jour le plugin **CategoryManager**. L’entrée de menu est sous **Outils → Visualiseur catégories** (libellé selon version GLPI).

**Résumé :** une fois le build déployé avec le plugin, les utilisateurs n’utilisent **pas** FastAPI ni les jetons REST dans le navigateur ; le script `front/visualizer.php` injecte `window.__CM_NATIVE_API__` et le JS appelle `ajax/native.php`.

### Déploiement « statique + FastAPI » (Mode A étendu — optionnel)

Si vous hébergez l’application **en dehors** de GLPI tout en gardant le proxy FastAPI (scénario moins courant que le plugin), il faut prévoir vous-même le **reverse proxy**, le service Python et les fichiers statiques issus du build. Ce n’est **pas** le flux documenté pour l’intégration standard dans GLPI.

---

## Plugin GLPI — droits et comportement

**Données :** tout transite par **`ajax/native.php`** — session GLPI, **aucun** jeton App/User ni appel à `apirest.php` depuis le navigateur.

**Accès par profil :** **Configuration → Profils** → [profil] → onglet **CategoryManager** → case **Lecture** (`plugin_categorymanager`). Depuis la version **0.1.2**, la lecture est **accordée par défaut** aux nouvelles entrées de droits ; vous pouvez la retirer pour masquer le menu. Après mise à jour du plugin depuis la **0.1.1**, exécutez **Mettre à jour** dans la liste des plugins pour réaligner les droits. Si la ligne de droit du plugin n’existe pas encore en session, le code peut retomber sur la lecture **ticket** (comportement historique).

---

## Architecture (vue d’ensemble)

| Couche | Détail |
|--------|--------|
| **Front** | **Vue.js 3** (Composition API), **Pinia**, **D3.js**, **Axios** — commun aux deux modes |
| **Mode A** | **FastAPI** + **httpx** + cache SQLite (`server/data/http_cache.sqlite3`) derrière le proxy Vite |
| **Mode B** | **PHP GLPI** (`PluginCategorymanagerNative`, etc.) — pas de stack Python |

---

## Structure utile du dépôt

```
plugins/categorymanager/
  templates/           # Twig — enveloppe GLPI (cartes) autour du montage Vue en Mode B
  frontend/            # Projet Vue + server/ FastAPI (Mode A uniquement pour Python)
    server/app/        # FastAPI — proxy REST + cache
    src/services/      # glpiApi.js : détection native (__CM_NATIVE_API__) vs /api/glpi/…
  ajax/native.php      # API JSON Mode B (session GLPI)
  public/              # Sortie du `npm run build` (Vite → outDir)
  front/visualizer.php # Header/footer GLPI + Twig + globales JS + bundle Vue
  docs/                # PRD, stack, références API (hors code applicatif)
```

---

## Documentation complémentaire

- PRD : `../docs/PRD  CategorieManager - Visualiseur.md`
- Stack et professionnalisation : `../docs/STACK_ET_PROFESSIONNALISATION.md`
