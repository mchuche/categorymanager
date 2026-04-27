# Pousser le dépôt sur GitHub

## Si vous voyez « Permission denied » / compte incorrect (ex. `mchuche49` au lieu de `mchuche`)

Les identifiants HTTPS précédents ont été invalidés sur cette machine (`git credential reject`). Au prochain `git push`, Git vous redemandera un mot de passe : utilisez un **Personal Access Token (classic)** du compte **`mchuche`**, pas le mot de passe du site.

1. GitHub → **Settings → Developer settings → Personal access tokens → Tokens (classic)** → **Generate new token**, cochez au minimum **`repo`**.
2. Dans le dépôt :

   ```bash
   cd /chemin/vers/categorymanager
   git push -u origin main
   ```

3. **Username** : `mchuche`  
4. **Password** : collez le **token** (pas votre mot de passe GitHub).

## Alternative : SSH

```bash
git remote set-url origin git@github.com:mchuche/categorymanager.git
ssh-add -l   # vérifier qu'une clé est chargée pour ce compte
git push -u origin main
```

La clé publique doit être ajoutée sur le compte **mchuche** : **Settings → SSH and GPG keys**.
