PRD : CategorieManager - Visualiseur de Catégories GLPI (Sunburst)
📄 Vision du Produit
Offrir une vue d'ensemble interactive et hiérarchique des catégories GLPI pour identifier rapidement les volumes de tickets et la répartition des demandes via l'API HL de GLPI 11.

🏗️ Architecture Technique (Frontend Only)
L'application sera développée en tant qu'Application Single Page (SPA) communiquant directement avec l'API GLPI.

• Framework : Vue.js 3 (Composition API).

• Librairie de Visualisation : D3.js ou Sunburst-chart.

• Gestion d'état : Pinia (pour stocker le token de session et les données catégories).

• Appels API : Axios ou Fetch native.

🛠️ Spécifications Fonctionnelles
1. Page de Configuration / Connexion

• Formulaire pour saisir l'URL de GLPI, l'App-Token et l'User-Token.

• Stockage sécurisé (SessionStorage) pour la durée de la navigation.

2. Dashboard Sunburst

• Récupération récursive ou globale des `ITILCategory`.

• Algorithme de transformation de la liste plate en structure `children[]`.

• Interactivité :

  • Zoom au clic.

  • Tooltip au survol avec métriques.

  • Export de la vue actuelle en PNG/SVG.

🔄 Flux de Données
1. L'utilisateur se connecte.

2. Vue.js appelle `GET /itilcategory` via l'API HL.

3. Le composant Vue transforme les données en arbre JSON.

4. D3.js rend le graphique Sunburst.

📅 Roadmap MVP
• Init projet Vue 3 + Vite.

• Service de transformation de données (Flat to Tree).

• Affichage du premier niveau de catégories.

• Ajout du drill-down interactif.
