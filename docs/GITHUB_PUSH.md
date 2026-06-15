# Pousser le dépôt sur GitHub

## Erreur : `Permission to mchuche/... denied to mchuche49`

GitHub identifie le pousseur grâce au **jeton (PAT)**, pas seulement au nom d’utilisateur saisi. Si le message indique **`mchuche49`**, c’est que le **token a été généré sur le compte `mchuche49`** (ou un ancien token de ce compte est encore en cache). Tant que vous collez ce token, l’erreur restera.

**Correctif :**

1. Ouvrez GitHub en étant connecté **en `mchuche`** (déconnectez-vous de `mchuche49` si besoin, ou fenêtre privée).
2. Créez un **nouveau** Personal Access Token (classic) : **Settings → Developer settings → Personal access tokens → Generate new token**, cochez **`repo`**.
3. Sur le serveur, videz le cache d’identifiants Git puis poussez à nouveau :

   ```bash
   git credential-cache exit 2>/dev/null
   printf "protocol=https\nhost=github.com\n" | git credential reject
   cd /chemin/vers/categorymanager
   git remote set-url origin "https://mchuche@github.com/mchuche/categorymanager.git"
   git push -u origin main
   ```

4. Quand Git demande le mot de passe : collez **uniquement** le **nouveau** token du compte **`mchuche`**.

L’URL avec `mchuche@` devant `github.com` force l’utilisateur affiché côté Git ; le compte effectif sur GitHub reste celui lié au **PAT**.

## Première configuration HTTPS (URL recommandée)

1. Même procédure de token, compte **`mchuche`**.
2. `git push` : **username** `mchuche`, **password** = le **token** (jamais le mot de passe du site).

## Alternative : SSH

```bash
git remote set-url origin git@github.com:mchuche/categorymanager.git
ssh-add -l   # vérifier qu'une clé est chargée pour ce compte
git push -u origin main
```

La clé publique doit être ajoutée sur le compte **mchuche** : **Settings → SSH and GPG keys**.
