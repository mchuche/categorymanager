"""
Service GLPI pour StockManager v1.0

Ce module gère toutes les interactions avec l'API REST High-Level de GLPI 11,
notamment :
- Authentification OAuth2 (Authorization Code Flow)
- Gestion des tokens (access_token, refresh_token)
- Recherche de matériels par numéro de série ou numéro d'inventaire
- Mise à jour des statuts et des informations matériel
- Purge des données techniques

Auteur: DSI
Version: 1.0
"""

import os
import logging
import asyncio
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from datetime import datetime, timedelta
from urllib.parse import urlencode, quote
from pathlib import Path
import json

import httpx
from pydantic import BaseModel, Field
from dotenv import load_dotenv

if TYPE_CHECKING:
    from models.profile import GLPIProfileConfig

# Chargement des variables d'environnement depuis le fichier .env
# Essaie plusieurs emplacements possibles pour le fichier .env
env_paths = [
    Path(__file__).parent.parent / ".env",  # backend/.env
    Path.cwd() / ".env",                     # Répertoire courant/.env
    Path(__file__).parent / ".env",          # backend/services/.env (peu probable)
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
        break
else:
    # Si aucun .env n'est trouvé, charge quand même depuis le répertoire courant
    # (utile si les variables sont définies dans l'environnement système)
    load_dotenv(override=False)

# Configuration du logger pour ce module
logger = logging.getLogger(__name__)


# ============================================================================
# Modèles de données Pydantic pour la validation
# ============================================================================

class GLPIOAuthTokens(BaseModel):
    """
    Modèle représentant les tokens OAuth2 retournés par GLPI.
    
    Attributes:
        access_token: Token d'accès pour les requêtes API
        refresh_token: Token pour renouveler l'access_token
        expires_in: Durée de vie du token en secondes
        token_type: Type de token (généralement "Bearer")
        expires_at: Date/heure d'expiration calculée
    """
    access_token: str = Field(..., description="Token d'accès OAuth2")
    refresh_token: Optional[str] = Field(None, description="Token de rafraîchissement")
    expires_in: int = Field(..., description="Durée de vie en secondes")
    token_type: str = Field(default="Bearer", description="Type de token")
    expires_at: Optional[datetime] = Field(None, description="Date d'expiration calculée")
    
    def __init__(self, **data):
        """Calcule automatiquement la date d'expiration lors de la création"""
        super().__init__(**data)
        if not self.expires_at and self.expires_in:
            # Calcule la date d'expiration à partir de maintenant + expires_in
            self.expires_at = datetime.utcnow() + timedelta(seconds=self.expires_in)


class GLPIUserInfo(BaseModel):
    """
    Modèle représentant les informations utilisateur retournées par GLPI.
    
    Attributes:
        id: Identifiant unique de l'utilisateur dans GLPI
        name: Nom d'utilisateur
        realname: Nom réel de l'utilisateur
        firstname: Prénom de l'utilisateur
        email: Adresse email
        profiles_id: ID du profil GLPI de l'utilisateur
        entities_id: ID de l'entité courante dans GLPI
        entities: Liste des IDs d'entités accessibles
    """
    id: int
    name: str
    realname: Optional[str] = None
    firstname: Optional[str] = None
    email: Optional[str] = None
    # Informations de profil et d'entité
    profiles_id: Optional[int] = None
    entities_id: Optional[int] = None
    entities: Optional[list] = None


# ============================================================================
# Service GLPI Principal
# ============================================================================

class GLPIService:
    """
    Service pour interagir avec l'API REST High-Level de GLPI 11.
    
    Ce service gère l'authentification OAuth2 et toutes les opérations
    CRUD sur les matériels dans GLPI.
    
    Usage:
        service = GLPIService()
        # Générer l'URL d'autorisation pour rediriger l'utilisateur
        auth_url = await service.get_authorization_url()
        # Échanger le code d'autorisation contre un token
        tokens = await service.exchange_authorization_code(code)
        # Utiliser le service avec le token
        service.set_tokens(tokens)
        # Rechercher un matériel
        item = await service.search_item_by_serial_or_inventory("SN123456")
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        scopes: Optional[str] = None
    ):
        """
        Initialise le service GLPI avec les paramètres OAuth2.
        
        Les paramètres peuvent être fournis directement ou seront lus depuis
        les variables d'environnement si non fournis.
        
        Args:
            base_url: URL de base de GLPI (ex: https://glpi.example.com)
            client_id: Client ID de l'application OAuth2 GLPI
            client_secret: Client Secret de l'application OAuth2 GLPI
            redirect_uri: URL de redirection après authentification
            scopes: Scopes OAuth2 demandés (séparés par des espaces)
        """
        # Lecture des variables d'environnement si non fournies
        self.base_url = base_url or os.getenv("GLPI_BASE_URL", "").rstrip("/")
        self.client_id = client_id or os.getenv("GLPI_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("GLPI_CLIENT_SECRET", "")
        self.redirect_uri = redirect_uri or os.getenv("GLPI_REDIRECT_URI", "")
        self.scopes = scopes or os.getenv("GLPI_OAUTH_SCOPES", "api user")
        
        # Validation des paramètres requis
        missing_params = []
        if not self.base_url:
            missing_params.append("GLPI_BASE_URL")
        if not self.client_id:
            missing_params.append("GLPI_CLIENT_ID")
        if not self.client_secret:
            missing_params.append("GLPI_CLIENT_SECRET")
        if not self.redirect_uri:
            missing_params.append("GLPI_REDIRECT_URI")
        
        if missing_params:
            env_file_path = Path(__file__).parent.parent / ".env"
            raise ValueError(
                f"Les paramètres OAuth2 GLPI suivants sont manquants: {', '.join(missing_params)}\n"
                f"Vérifiez que le fichier .env existe à l'emplacement: {env_file_path}\n"
                f"Vous pouvez copier env.example.txt vers .env et remplir les valeurs."
            )
        
        # Construction des URLs d'API
        # Note: urljoin remplace le chemin au lieu de l'ajouter, donc on construit manuellement
        # Format attendu: https://glpi.example.com/api.php/authorize
        base_url_clean = self.base_url.rstrip("/")
        self.api_base = f"{base_url_clean}/api.php"
        self.authorize_url = f"{base_url_clean}/api.php/authorize"
        self.token_url = f"{base_url_clean}/api.php/token"
        
        # Stockage des tokens actuels
        self._tokens: Optional[GLPIOAuthTokens] = None
        
        # Client HTTP asynchrone (sera créé à la demande)
        self._client: Optional[httpx.AsyncClient] = None
        
        # Configuration SSL : vérification des certificats
        # Par défaut True, peut être désactivé via GLPI_VERIFY_SSL=false pour les certificats auto-signés
        ssl_verify_env = os.getenv("GLPI_VERIFY_SSL", "true").lower()
        self.verify_ssl = ssl_verify_env not in ("false", "0", "no", "off")
        
        if not self.verify_ssl:
            logger.warning(
                "⚠️  La vérification SSL est DÉSACTIVÉE. "
                "À utiliser uniquement en développement avec des certificats auto-signés."
            )
        
        logger.info(f"Service GLPI initialisé avec l'URL de base: {self.base_url}")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """
        Obtient ou crée un client HTTP asynchrone.
        
        Le client est réutilisé pour améliorer les performances.
        
        Returns:
            Client HTTP asynchrone configuré
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),  # Timeout de 30 secondes
                follow_redirects=True,
                verify=self.verify_ssl  # Vérification SSL (False pour certificats auto-signés)
            )
        return self._client
    
    async def close(self):
        """
        Ferme le client HTTP proprement.
        
        À appeler lors de la destruction de l'instance pour libérer les ressources.
        """
        if self._client is not None:
            await self._client.aclose()
            self._client = None
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Génère l'URL d'autorisation OAuth2 pour rediriger l'utilisateur.
        
        Cette URL doit être utilisée pour rediriger l'utilisateur vers GLPI
        afin qu'il s'authentifie. Après authentification, GLPI redirigera
        vers redirect_uri avec un code d'autorisation.
        
        Args:
            state: Chaîne aléatoire pour prévenir les attaques CSRF (optionnel)
                  Si non fourni, un state peut être généré côté client
        
        Returns:
            URL complète d'autorisation OAuth2
        
        Example:
            >>> service = GLPIService()
            >>> auth_url = service.get_authorization_url(state="random_string_123")
            >>> # Rediriger l'utilisateur vers auth_url
        """
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scopes,
        }
        
        # Ajout du state pour la sécurité CSRF si fourni
        if state:
            params["state"] = state
        
        # Construction de l'URL avec les paramètres
        auth_url = f"{self.authorize_url}?{urlencode(params)}"
        
        logger.debug(f"URL d'autorisation générée: {auth_url.split('?')[0]}...")
        return auth_url
    
    async def exchange_authorization_code(
        self,
        code: str,
        state: Optional[str] = None
    ) -> GLPIOAuthTokens:
        """
        Échange le code d'autorisation contre un access token et un refresh token.
        
        Cette méthode est appelée après que l'utilisateur s'est authentifié
        sur GLPI et que le code d'autorisation a été récupéré depuis l'URL
        de redirection.
        
        Args:
            code: Code d'autorisation retourné par GLPI dans l'URL de redirection
            state: État fourni lors de la génération de l'URL (vérification CSRF)
        
        Returns:
            Objet GLPIOAuthTokens contenant les tokens OAuth2
        
        Raises:
            httpx.HTTPStatusError: Si l'échange du code échoue (code invalide, etc.)
            ValueError: Si la réponse de GLPI est invalide
        
        Example:
            >>> # Après redirection depuis GLPI avec code=abc123
            >>> tokens = await service.exchange_authorization_code("abc123")
            >>> service.set_tokens(tokens)
        """
        client = await self._get_client()
        
        # Préparation des données pour la requête POST
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
        }
        
        logger.info("Échange du code d'autorisation contre un token OAuth2...")
        
        try:
            # Tentative 1: Authentification via Basic Auth (RFC 6749 Section 2.3.1)
            # Certaines implémentations OAuth2 préfèrent cette méthode
            import base64
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {encoded_credentials}"
            }
            
            # Préparation des données sans client_id et client_secret dans le body
            # quand on utilise Basic Auth
            data_without_creds = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
            }
            
            # Envoi de la requête POST vers l'endpoint token de GLPI avec Basic Auth
            logger.debug(f"Tentative avec Basic Auth vers: {self.token_url}")
            response = await client.post(
                self.token_url,
                data=data_without_creds,
                headers=headers
            )
            
            # Vérification que la requête a réussi
            response.raise_for_status()
            
            # Parse de la réponse JSON
            token_data = response.json()
            
            # Validation et création de l'objet GLPIOAuthTokens
            tokens = GLPIOAuthTokens(**token_data)
            
            # Stockage automatique des tokens
            self._tokens = tokens
            
            logger.info(
                f"Token OAuth2 obtenu avec succès. Expire dans {tokens.expires_in}s "
                f"(à {tokens.expires_at})"
            )
            
            return tokens
            
        except httpx.HTTPStatusError as e:
            # Si Basic Auth échoue avec invalid_client, on essaie avec les credentials dans le body
            if e.response.status_code == 401 or (e.response.status_code == 400 and "invalid_client" in e.response.text):
                logger.warning(
                    f"Basic Auth échoué ({e.response.status_code}), tentative avec credentials dans le body..."
                )
                
                # Tentative 2: Authentification via body (méthode standard)
                headers_body = {
                    "Content-Type": "application/x-www-form-urlencoded"
                }
                
                response = await client.post(
                    self.token_url,
                    data=data,  # Avec client_id et client_secret dans le body
                    headers=headers_body
                )
                response.raise_for_status()
            else:
                logger.error(
                    f"Échec de l'échange du code d'autorisation: {e.response.status_code} - "
                    f"{e.response.text}"
                )
                raise
        except Exception as e:
            logger.error(f"Erreur lors de l'échange du code d'autorisation: {str(e)}")
            raise ValueError(f"Impossible d'échanger le code d'autorisation: {str(e)}")
    
    async def refresh_access_token(self) -> GLPIOAuthTokens:
        """
        Renouvelle l'access token en utilisant le refresh token.
        
        Cette méthode doit être appelée lorsque l'access token est expiré
        ou proche de l'expiration pour obtenir un nouveau token sans
        redemander à l'utilisateur de s'authentifier.
        
        Returns:
            Nouvel objet GLPIOAuthTokens avec les tokens actualisés
        
        Raises:
            ValueError: Si aucun refresh token n'est disponible
            httpx.HTTPStatusError: Si le refresh token est invalide ou expiré
        
        Example:
            >>> if service.is_token_expired():
            ...     tokens = await service.refresh_access_token()
            ...     service.set_tokens(tokens)
        """
        if not self._tokens or not self._tokens.refresh_token:
            raise ValueError(
                "Aucun refresh token disponible. Une nouvelle authentification "
                "est requise."
            )
        
        client = await self._get_client()
        
        # Préparation des données pour la requête POST
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self._tokens.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        
        logger.info("Renouvellement de l'access token via refresh token...")
        
        try:
            # Envoi de la requête POST vers l'endpoint token de GLPI
            response = await client.post(
                self.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            # Vérification que la requête a réussi
            response.raise_for_status()
            
            # Parse de la réponse JSON
            token_data = response.json()
            
            # Validation et création du nouvel objet GLPIOAuthTokens
            new_tokens = GLPIOAuthTokens(**token_data)
            
            # Mise à jour des tokens stockés
            self._tokens = new_tokens
            
            logger.info(
                f"Token OAuth2 renouvelé avec succès. Nouvelle expiration dans "
                f"{new_tokens.expires_in}s"
            )
            
            return new_tokens
            
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Échec du renouvellement du token: {e.response.status_code} - "
                f"{e.response.text}"
            )
            # Si le refresh token est invalide, on le supprime
            self._tokens = None
            raise
        except Exception as e:
            logger.error(f"Erreur lors du renouvellement du token: {str(e)}")
            raise ValueError(f"Impossible de renouveler le token: {str(e)}")
    
    def set_tokens(self, tokens: GLPIOAuthTokens):
        """
        Définit les tokens OAuth2 à utiliser pour les requêtes API.
        
        Args:
            tokens: Objet GLPIOAuthTokens contenant les tokens
        """
        self._tokens = tokens
        logger.debug("Tokens OAuth2 définis dans le service")
    
    def is_token_expired(self, margin_seconds: int = 60) -> bool:
        """
        Vérifie si le token d'accès actuel est expiré ou proche de l'expiration.
        
        Args:
            margin_seconds: Marge de sécurité en secondes avant l'expiration
                          (défaut: 60 secondes pour éviter les expirations pendant
                          l'exécution d'une requête)
        
        Returns:
            True si le token est expiré ou proche de l'expiration, False sinon
        """
        if not self._tokens or not self._tokens.expires_at:
            return True
        
        # Vérifie si le token expire dans moins de margin_seconds secondes
        expiration_time = self._tokens.expires_at - timedelta(seconds=margin_seconds)
        return datetime.utcnow() >= expiration_time
    
    async def _ensure_valid_token(self):
        """
        S'assure qu'un token valide est disponible pour les requêtes API.
        
        Si le token est expiré, tente de le renouveler automatiquement.
        Si le renouvellement échoue, lève une exception.
        
        Raises:
            ValueError: Si aucun token n'est disponible et qu'aucun renouvellement
                       n'est possible
        """
        if not self._tokens:
            raise ValueError(
                "Aucun token OAuth2 disponible. Authentification requise."
            )
        
        if self.is_token_expired():
            logger.info("Token expiré, tentative de renouvellement...")
            try:
                await self.refresh_access_token()
            except Exception as e:
                logger.error(f"Impossible de renouveler le token: {str(e)}")
                raise ValueError(
                    "Token expiré et impossible de le renouveler. "
                    "Une nouvelle authentification est requise."
                )
    
    async def _get_user_data_raw(self) -> Dict[str, Any]:
        """
        Récupère les données brutes de l'utilisateur depuis GLPI.
        
        Cette méthode privée retourne le dictionnaire brut retourné par l'API GLPI,
        permettant d'accéder à des champs supplémentaires comme default_profile.name
        et default_entity.name qui ne sont pas dans GLPIUserInfo.
        
        Returns:
            Dictionnaire brut des données utilisateur depuis l'API GLPI
        """
        await self._ensure_valid_token()
        
        client = await self._get_client()
        
        headers = {
            "Authorization": f"{self._tokens.token_type} {self._tokens.access_token}",
        }
        
        endpoints_to_try = [
            f"{self.api_base}/Administration/User/Me",
            f"{self.api_base}/Administration/User/Me/",
        ]
        
        response = None
        last_error = None
        
        for endpoint_url in endpoints_to_try:
            try:
                try:
                    response = await client.get(endpoint_url, headers=headers)
                    response.raise_for_status()
                    break
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 400 and ("JSON" in str(e.response.text) or "invalide" in str(e.response.text).lower()):
                        headers_with_content = headers.copy()
                        headers_with_content["Content-Type"] = "application/json"
                        response = await client.post(
                            endpoint_url, 
                            headers=headers_with_content,
                            json={}
                        )
                        response.raise_for_status()
                        break
                    else:
                        raise
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 404:
                    continue
                else:
                    raise
        
        if response is None:
            raise last_error or ValueError("Aucun endpoint valide trouvé")
        
        return response.json()
    
    async def get_user_info(self) -> GLPIUserInfo:
        """
        Récupère les informations de l'utilisateur authentifié depuis GLPI.
        
        Cette méthode utilise l'endpoint /Administration/User/Me/ de l'API REST
        High-Level de GLPI avec le token OAuth2.
        
        L'endpoint utilisé est : /api.php/Administration/User/Me/
        
        Returns:
            Objet GLPIUserInfo contenant les informations de l'utilisateur
        
        Raises:
            ValueError: Si aucun token n'est disponible
            httpx.HTTPStatusError: Si la requête échoue
        
        Example:
            >>> user_info = await service.get_user_info()
            >>> print(f"Utilisateur: {user_info.name} ({user_info.email})")
        """
        logger.debug("Récupération des informations utilisateur depuis GLPI...")
        
        try:
            # Utiliser la méthode privée pour récupérer les données brutes
            user_data = await self._get_user_data_raw()
            
            # Log pour voir toutes les clés disponibles dans la réponse GLPI
            logger.info(f"=== Données brutes retournées par GLPI ===")
            logger.info(f"Clés disponibles: {list(user_data.keys())}")
            # Afficher un extrait des données (limité pour ne pas surcharger les logs)
            data_preview = {k: v for k, v in list(user_data.items())[:15]}
            logger.info(f"Extrait des données (15 premiers champs): {json.dumps(data_preview, indent=2, default=str)}")
            # Log spécifique pour default_profile et default_entity
            logger.info(f"default_profile: {user_data.get('default_profile')}")
            logger.info(f"default_entity: {user_data.get('default_entity')}")
            
            # Extraction des informations utilisateur depuis la réponse
            # GLPI utilise "username" au lieu de "name", et "default_profile"/"default_entity" au lieu de "profiles_id"/"entities_id"
            
            # Extraction du profil : GLPI retourne "default_profile" qui peut être un objet ou un ID
            profiles_id = None
            default_profile = user_data.get("default_profile")
            if default_profile:
                if isinstance(default_profile, dict):
                    profiles_id = default_profile.get("id") or default_profile.get("profiles_id")
                elif isinstance(default_profile, (int, str)):
                    profiles_id = int(default_profile)
            # Fallback: chercher profiles_id directement (pour compatibilité)
            if not profiles_id:
                profiles_id = user_data.get("profiles_id")
            # Fallback: chercher dans une liste "profiles"
            if not profiles_id and "profiles" in user_data:
                profiles_list = user_data.get("profiles", [])
                if isinstance(profiles_list, list) and len(profiles_list) > 0:
                    if isinstance(profiles_list[0], dict):
                        profiles_id = profiles_list[0].get("id") or profiles_list[0].get("profiles_id")
                    elif isinstance(profiles_list[0], (int, str)):
                        profiles_id = int(profiles_list[0])
            
            # Extraction de l'entité : GLPI retourne "default_entity" qui peut être un objet ou un ID
            entities_id = None
            default_entity = user_data.get("default_entity")
            if default_entity:
                if isinstance(default_entity, dict):
                    entities_id = default_entity.get("id") or default_entity.get("entities_id")
                elif isinstance(default_entity, (int, str)):
                    entities_id = int(default_entity)
            # Fallback: chercher entities_id directement (pour compatibilité)
            if entities_id is None:
                entities_id = user_data.get("entities_id")
            # Fallback: chercher dans une liste "entities"
            if entities_id is None and "entities" in user_data:
                entities_list = user_data.get("entities", [])
                if isinstance(entities_list, list) and len(entities_list) > 0:
                    if isinstance(entities_list[0], dict):
                        entities_id = entities_list[0].get("id") or entities_list[0].get("entities_id")
                    elif isinstance(entities_list[0], (int, str)):
                        entities_id = int(entities_list[0])
            
            # Extraction de l'email : GLPI retourne "emails" comme une liste d'objets
            email = None
            emails = user_data.get("emails", [])
            if isinstance(emails, list) and len(emails) > 0:
                # Prendre l'email par défaut ou le premier disponible
                default_email = next((e.get("email") for e in emails if e.get("is_default")), None)
                email = default_email or (emails[0].get("email") if isinstance(emails[0], dict) else None)
            # Fallback: chercher email directement
            if not email:
                email = user_data.get("email")
            
            user_info = GLPIUserInfo(
                id=user_data.get("id", 0),
                name=user_data.get("username") or user_data.get("name", ""),  # GLPI utilise "username"
                realname=user_data.get("realname"),
                firstname=user_data.get("firstname"),
                email=email,
                # Extraction du profil et de l'entité si disponibles
                profiles_id=profiles_id,
                entities_id=entities_id,
                entities=user_data.get("entities", []),
            )
            
            logger.info(f"Informations utilisateur récupérées: {user_info.name} (ID: {user_info.id})")
            logger.info(f"Profil ID extrait: {user_info.profiles_id}")
            logger.info(f"Entité ID extraite: {user_info.entities_id}")
            logger.info(f"Liste des entités: {user_info.entities}")
            return user_info
            
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Échec de la récupération des informations utilisateur: "
                f"{e.response.status_code} - {e.response.text}"
            )
            raise
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des informations utilisateur: {str(e)}")
            raise ValueError(f"Impossible de récupérer les informations utilisateur: {str(e)}")
    
    async def get_profile_name(self, profile_id: int) -> Optional[str]:
        """
        Récupère le nom d'un profil GLPI depuis son ID.
        
        Cette méthode interroge l'endpoint /Administration/Profile/{id} pour obtenir
        le nom d'un profil à partir de son identifiant.
        
        Args:
            profile_id: ID du profil à récupérer
        
        Returns:
            Nom du profil ou None si non trouvé ou en cas d'erreur
        
        Example:
            >>> profile_name = await service.get_profile_name(4)
            >>> print(f"Profil: {profile_name}")
        """
        if not profile_id:
            return None
        
        await self._ensure_valid_token()
        client = await self._get_client()
        
        headers = {
            "Authorization": f"{self._tokens.token_type} {self._tokens.access_token}",
        }
        
        try:
            # Utilisation de l'endpoint /Administration/Profile/{id}
            endpoint_url = f"{self.api_base}/Administration/Profile/{profile_id}"
            logger.debug(f"Récupération du nom du profil {profile_id} depuis {endpoint_url}")
            
            response = await client.get(endpoint_url, headers=headers)
            response.raise_for_status()
            
            profile_data = response.json()
            profile_name = profile_data.get("name")
            logger.debug(f"Nom du profil {profile_id} récupéré: {profile_name}")
            return profile_name
        except httpx.HTTPStatusError as e:
            logger.warning(f"Impossible de récupérer le nom du profil {profile_id}: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.warning(f"Erreur lors de la récupération du nom du profil {profile_id}: {str(e)}")
            return None
    
    async def get_entity_name(self, entity_id: int) -> Optional[str]:
        """
        Récupère le nom d'une entité GLPI depuis son ID.
        
        Cette méthode interroge l'endpoint /Entity/{id} pour obtenir le nom d'une
        entité à partir de son identifiant. L'entité 0 est généralement la racine.
        
        Args:
            entity_id: ID de l'entité à récupérer (0 = Root entity)
        
        Returns:
            Nom de l'entité ou "Root entity" pour l'ID 0, ou None si non trouvé
        
        Example:
            >>> entity_name = await service.get_entity_name(2)
            >>> print(f"Entité: {entity_name}")
        """
        # L'entité 0 est généralement la racine dans GLPI
        if entity_id == 0:
            return "Root entity"
        
        if not entity_id:
            return None
        
        await self._ensure_valid_token()
        client = await self._get_client()
        
        headers = {
            "Authorization": f"{self._tokens.token_type} {self._tokens.access_token}",
        }
        
        try:
            # Utilisation de l'endpoint /Entity/{id}
            endpoint_url = f"{self.api_base}/Entity/{entity_id}"
            logger.debug(f"Récupération du nom de l'entité {entity_id} depuis {endpoint_url}")
            
            response = await client.get(endpoint_url, headers=headers)
            response.raise_for_status()
            
            entity_data = response.json()
            entity_name = entity_data.get("name")
            logger.debug(f"Nom de l'entité {entity_id} récupéré: {entity_name}")
            return entity_name
        except httpx.HTTPStatusError as e:
            logger.warning(f"Impossible de récupérer le nom de l'entité {entity_id}: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.warning(f"Erreur lors de la récupération du nom de l'entité {entity_id}: {str(e)}")
            return None
    
    # ========================================================================
    # Méthodes pour la gestion des matériels
    # ========================================================================
    
    async def search_item_by_serial_or_inventory(
        self,
        serial_or_inventory: str
    ) -> Optional[Dict[str, Any]]:
        """
        Recherche un matériel par numéro de série ou numéro d'inventaire.
        
        Cette méthode utilise l'endpoint global `/Assets/Global` de GLPI avec un filtre
        pour rechercher dans tous les types d'items (Computer, Monitor, Printer, etc.)
        un matériel correspondant au numéro de série ou au numéro d'inventaire fourni.
        
        Format du filtre utilisé : `serial==VALEUR` ou `otherserial==VALEUR`
        Endpoint : `/api.php/Assets/Global?filter=...`
        
        Args:
            serial_or_inventory: Numéro de série ou numéro d'inventaire à rechercher
        
        Returns:
            Dictionnaire contenant les informations du matériel trouvé, ou None si non trouvé
            Format: {
                "id": 123,
                "itemtype": "Computer",
                "serial": "SN123456",
                "inventory_number": "INV-001",
                "brand": "Dell",
                "model": "OptiPlex",
                "status": "En stock",
                "status_id": 1,
                "entity_id": 2,
                "location_id": 5,
                ...
            }
        
        Raises:
            ValueError: Si aucun token n'est disponible
            httpx.HTTPStatusError: Si la requête échoue
        """
        await self._ensure_valid_token()
        
        client = await self._get_client()
        
        # Headers avec le token OAuth2
        # Pour les requêtes GET, on n'a pas besoin de Content-Type: application/json
        headers = {
            "Authorization": f"{self._tokens.token_type} {self._tokens.access_token}"
        }
        
        logger.info(f"Recherche d'un matériel avec: '{serial_or_inventory}'")
        logger.info(f"Headers utilisés: {headers}")
        
        try:
            all_results = []
            
            # Tentative 1: Recherche par numéro de série
            # Utilisation du champ 'serial' selon la documentation GLPI
            try:
                # Format du filtre: serial==VALEUR (URL encodé)
                serial_filter = f"serial=={serial_or_inventory}"
                serial_filter_encoded = quote(serial_filter)
                endpoint = f"{self.api_base}/Assets/Global?filter={serial_filter_encoded}"
                
                logger.info(f"=" * 80)
                logger.info(f"Recherche par numéro de série avec champ 'serial'")
                logger.info(f"URL complète: {endpoint}")
                logger.info(f"Filtre brut: {serial_filter}")
                logger.info(f"Filtre encodé: {serial_filter_encoded}")
                logger.info(f"Headers: Authorization={headers.get('Authorization', 'N/A')[:50]}...")
                logger.info(f"=" * 80)
                
                response = await client.get(endpoint, headers=headers)
                response.raise_for_status()
                
                search_data = response.json()
                logger.info(f"Structure de la réponse API (première recherche): {json.dumps(search_data, indent=2)[:1000]}")
                logger.debug(f"Réponse brute complète de l'API: {search_data}")
                
                # Extraction des résultats
                results = []
                
                if isinstance(search_data, (dict, list)):
                    if isinstance(search_data, dict):
                        # Différentes structures possibles de réponse
                        results = search_data.get("data", [])
                        if not results:
                            results = search_data.get("items", [])
                        if not results:
                            results = search_data.get("results", [])
                        if not results and isinstance(search_data.get("0"), dict):
                            # Structure avec clés numériques
                            results = [v for k, v in search_data.items() if k.isdigit() and isinstance(v, dict)]
                        if not isinstance(results, list):
                            results = []
                    else:
                        # La réponse est directement une liste
                        results = search_data if isinstance(search_data, list) else []
                    
                    # Extraction et normalisation de l'itemtype depuis chaque résultat
                    # L'itemtype est dans le champ '_itemtype' avec underscore selon GLPI
                    for result in results:
                        if isinstance(result, dict):
                            # Extraire _itemtype et le copier vers itemtype pour faciliter l'accès
                            itemtype_value = result.get("_itemtype") or result.get("itemtype")
                            if itemtype_value:
                                result["itemtype"] = itemtype_value
                
                if results:
                    logger.info(f"Trouvé {len(results)} résultat(s) par numéro de série")
                    all_results.extend(results)
                else:
                    logger.debug(f"Aucun résultat avec le champ 'serial'")
            
            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"Erreur lors de la recherche par numéro de série: "
                    f"{e.response.status_code} - {e.response.text[:200]}"
                )
            except Exception as e:
                logger.warning(f"Exception lors de la recherche par numéro de série: {str(e)}")
            
            # Tentative 2: Recherche par numéro d'inventaire (si pas de résultats ou en complément)
            # Utilisation du champ 'otherserial' selon la documentation GLPI
            try:
                # Format du filtre: otherserial==VALEUR (URL encodé)
                inventory_filter = f"otherserial=={serial_or_inventory}"
                inventory_filter_encoded = quote(inventory_filter)
                endpoint = f"{self.api_base}/Assets/Global?filter={inventory_filter_encoded}"
                
                logger.info(f"=" * 80)
                logger.info(f"Recherche par numéro d'inventaire avec champ 'otherserial'")
                logger.info(f"URL complète: {endpoint}")
                logger.info(f"Filtre brut: {inventory_filter}")
                logger.info(f"Filtre encodé: {inventory_filter_encoded}")
                logger.info(f"Headers: Authorization={headers.get('Authorization', 'N/A')[:50]}...")
                logger.info(f"=" * 80)
                
                response = await client.get(endpoint, headers=headers)
                response.raise_for_status()
                
                search_data = response.json()
                logger.debug(f"Réponse brute de l'API (inventaire): {search_data}")
                
                # Extraction des résultats
                results = []
                
                if isinstance(search_data, (dict, list)):
                    if isinstance(search_data, dict):
                        results = search_data.get("data", [])
                        if not results:
                            results = search_data.get("items", [])
                        if not results:
                            results = search_data.get("results", [])
                        if not results and isinstance(search_data.get("0"), dict):
                            results = [v for k, v in search_data.items() if k.isdigit() and isinstance(v, dict)]
                        if not isinstance(results, list):
                            results = []
                    else:
                        # La réponse est directement une liste
                        results = search_data if isinstance(search_data, list) else []
                    
                    # Extraction et normalisation de l'itemtype depuis chaque résultat
                    # L'itemtype est dans le champ '_itemtype' avec underscore selon GLPI
                    for result in results:
                        if isinstance(result, dict):
                            # Extraire _itemtype et le copier vers itemtype pour faciliter l'accès
                            itemtype_value = result.get("_itemtype") or result.get("itemtype")
                            if itemtype_value:
                                result["itemtype"] = itemtype_value
                    
                    if results:
                        logger.info(f"Trouvé {len(results)} résultat(s) par numéro d'inventaire")
                        # Ajouter uniquement les résultats qui ne sont pas déjà dans all_results
                        existing_ids = {r.get("id") for r in all_results if isinstance(r, dict) and r.get("id")}
                        for result in results:
                            if isinstance(result, dict) and result.get("id") not in existing_ids:
                                all_results.append(result)
                else:
                    logger.debug(f"Aucun résultat avec le champ 'otherserial'")
            
            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"Erreur lors de la recherche par numéro d'inventaire: "
                    f"{e.response.status_code} - {e.response.text[:200]}"
                )
            except Exception as e:
                logger.warning(f"Exception lors de la recherche par numéro d'inventaire: {str(e)}")
            
            logger.info(f"Total de {len(all_results)} résultat(s) trouvé(s) après toutes les recherches")
            
            # Si des résultats ont été trouvés, retourner le premier
            if all_results:
                # Recherche d'une correspondance exacte
                exact_match = None
                for result in all_results:
                    if not isinstance(result, dict):
                        continue
                    
                    # Extraction du numéro de série (peut être dans différents champs selon GLPI)
                    serial = (
                        result.get("serialnumber") or 
                        result.get("serial") or 
                        result.get("serial_number") or 
                        result.get("serialnumber") or
                        ""
                    )
                    # Extraction du numéro d'inventaire
                    inventory = (
                        result.get("otherserial") or 
                        result.get("inventory_number") or 
                        result.get("inventorynumber") or
                        ""
                    )
                    
                    # Comparaison insensible à la casse pour une correspondance exacte
                    if (serial and serial.upper() == serial_or_inventory.upper()) or \
                       (inventory and inventory.upper() == serial_or_inventory.upper()):
                        exact_match = result
                        break
                
                final_result = exact_match if exact_match else all_results[0]
                
                # Extraction de l'itemtype depuis différentes sources possibles
                # L'itemtype devrait déjà être copié depuis '_itemtype' dans le code précédent
                # Mais on vérifie quand même au cas où
                itemtype = (
                    final_result.get("itemtype") or
                    final_result.get("_itemtype") or
                    final_result.get("item_type") or
                    final_result.get("type") or
                    None
                )
                
                # Si l'itemtype n'est pas encore présent, on le récupère depuis _itemtype
                if not itemtype and final_result.get("_itemtype"):
                    itemtype = final_result["_itemtype"]
                    final_result["itemtype"] = itemtype
                
                # Si l'itemtype n'est toujours pas trouvé, on log pour debug
                if not itemtype and final_result.get("id"):
                    logger.debug(f"Itemtype non trouvé pour l'item ID={final_result.get('id')}")
                
                logger.info(
                    f"Matériel trouvé: ID={final_result.get('id')}, "
                    f"Type={itemtype or 'N/A'}, "
                    f"Serial={final_result.get('serialnumber', final_result.get('serial', 'N/A'))}"
                )
                
                return final_result
            else:
                logger.info(f"Aucun matériel trouvé avec: {serial_or_inventory}")
                return None
                
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Échec de la recherche: {e.response.status_code} - {e.response.text}"
            )
            raise
        except Exception as e:
            logger.error(f"Erreur lors de la recherche: {str(e)}")
            raise ValueError(f"Impossible de rechercher le matériel: {str(e)}")
    
    # ========================================================================
    # Méthodes pour la gestion des licences et mises à jour
    # ========================================================================
    
    async def check_licenses(self, item_id: int, itemtype: str) -> bool:
        """
        Vérifie si des licences logicielles sont rattachées au matériel.
        
        Cette méthode recherche les licences associées à un item GLPI.
        Si des licences sont trouvées, retourne True (blocage de sécurité).
        
        Args:
            item_id: ID de l'item GLPI
            itemtype: Type d'item (Computer, Monitor, etc.)
        
        Returns:
            True si des licences sont présentes (blocage), False sinon
        
        Raises:
            ValueError: Si aucun token n'est disponible
            httpx.HTTPStatusError: Si la requête échoue
        """
        await self._ensure_valid_token()
        
        client = await self._get_client()
        headers = {
            "Authorization": f"{self._tokens.token_type} {self._tokens.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            # Recherche des licences via l'endpoint SoftwareLicense
            # Format: /api.php/Assets/{itemtype}/{item_id}/SoftwareLicense
            endpoint = f"{self.api_base}/Assets/{itemtype}/{item_id}/SoftwareLicense"
            
            logger.debug(f"Vérification des licences pour {itemtype}/{item_id} via {endpoint}")
            
            response = await client.get(endpoint, headers=headers)
            response.raise_for_status()
            
            licenses_data = response.json()
            
            # La réponse peut être une liste ou un objet avec une liste
            licenses = []
            if isinstance(licenses_data, list):
                licenses = licenses_data
            elif isinstance(licenses_data, dict):
                # Essayer différentes clés possibles
                licenses = licenses_data.get("data", licenses_data.get("items", licenses_data.get("results", [])))
                if not isinstance(licenses, list):
                    licenses = []
            
            has_licenses = len(licenses) > 0
            
            if has_licenses:
                logger.warning(f"⚠️  {len(licenses)} licence(s) trouvée(s) pour {itemtype}/{item_id} - Blocage de sécurité")
            else:
                logger.info(f"✓ Aucune licence trouvée pour {itemtype}/{item_id}")
            
            return has_licenses
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Pas de licences (endpoint non trouvé ou aucune licence)
                logger.debug(f"Aucune licence trouvée pour {itemtype}/{item_id} (404)")
                return False
            else:
                logger.error(f"Erreur lors de la vérification des licences: {e.response.status_code} - {e.response.text}")
                raise
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des licences: {str(e)}")
            raise ValueError(f"Impossible de vérifier les licences: {str(e)}")
    
    async def update_item_glpi(
        self,
        item_id: int,
        itemtype: str,
        profile_config: "GLPIProfileConfig",
        item_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Met à jour un item GLPI selon la configuration du profil métier.
        
        Met à jour uniquement les champs spécifiés (non null) :
        - Statut (target_status_id)
        - Entité (target_entity_id)
        - Lieu (target_location_id)
        - is_deleted (soft delete)
        
        IMPORTANT: Cette méthode gère le versioning de la High-Level API GLPI 11.
        Elle récupère automatiquement la version actuelle de l'item et l'inclut
        dans la mise à jour pour éviter les conflits de verrouillage.
        
        Args:
            item_id: ID de l'item GLPI à mettre à jour
            itemtype: Type d'item (Computer, Monitor, etc.)
            profile_config: Configuration GLPI du profil (GLPIProfileConfig)
            item_data: Données de l'item déjà récupérées (optionnel, pour éviter un GET supplémentaire)
        
        Returns:
            True si la mise à jour a réussi, False sinon
        
        Raises:
            ValueError: Si aucun token n'est disponible
            httpx.HTTPStatusError: Si la requête échoue
        """
        await self._ensure_valid_token()
        
        client = await self._get_client()
        headers = {
            "Authorization": f"{self._tokens.token_type} {self._tokens.access_token}",
            "Content-Type": "application/json"
        }
        
        # Construire le payload avec uniquement les champs non null
        # Note: L'API High-Level de GLPI peut accepter les relations sous forme d'objets {"id": ...}
        # ou d'entiers directs selon la version. On essaiera d'abord avec les objets.
        update_data = {}
        
        if profile_config.target_status_id is not None:
            # Essayer avec un objet {"id": ...} d'abord
            # Si ça ne fonctionne pas, on pourra essayer avec un entier direct
            update_data["status"] = {"id": profile_config.target_status_id}
            logger.debug(f"Mise à jour statut: {profile_config.target_status_id} (format: status={{id: ...}})")
        
        if profile_config.target_entity_id is not None:
            update_data["entity"] = {"id": profile_config.target_entity_id}
            logger.debug(f"Mise à jour entité: {profile_config.target_entity_id} (format: entity={{id: ...}})")
        
        if profile_config.target_location_id is not None:
            update_data["location"] = {"id": profile_config.target_location_id}
            logger.debug(f"Mise à jour lieu: {profile_config.target_location_id} (format: location={{id: ...}})")
        
        # is_deleted est toujours défini (bool), donc on l'inclut toujours
        update_data["is_deleted"] = profile_config.is_deleted
        logger.debug(f"Mise à jour is_deleted: {profile_config.is_deleted}")
        
        if not update_data:
            logger.warning(f"Aucune mise à jour à effectuer pour {itemtype}/{item_id} (tous les champs sont null)")
            return True
        
        endpoint = f"{self.api_base}/Assets/{itemtype}/{item_id}"
        
        # ========================================================================
        # ÉTAPE 1: Récupérer la version actuelle de l'item (pour éviter les verrous)
        # ========================================================================
        # La High-Level API de GLPI 11 utilise un système de versioning.
        # Chaque item a un champ _version qui doit être inclus dans les mises à jour
        # pour éviter les conflits de mise à jour concurrente.
        current_version = None
        max_retries = 3  # Nombre maximum de tentatives en cas de conflit de version
        
        # Si item_data est fourni, essayer d'extraire la version depuis ces données
        if item_data and isinstance(item_data, dict):
            current_version = (
                item_data.get("_version") or 
                item_data.get("version") or 
                item_data.get("__version__")
            )
            if current_version:
                logger.info(f"✓ Version récupérée depuis item_data fourni: {current_version}")
        
        # Si on n'a pas la version, essayer de la récupérer via un GET
        # Mais utiliser Assets/Global avec un filtre car l'endpoint direct peut échouer
        if current_version is None:
            for attempt in range(max_retries):
                try:
                    # Essayer d'abord avec Assets/Global et un filtre sur l'ID
                    logger.info(f"🔄 Récupération de la version via Assets/Global (tentative {attempt + 1}/{max_retries})")
                    filter_endpoint = f"{self.api_base}/Assets/Global?filter=id=={item_id}"
                    logger.info(f"   Endpoint GET: {filter_endpoint}")
                    try:
                        get_response = await client.get(filter_endpoint, headers=headers)
                        get_response.raise_for_status()
                        logger.info(f"✓ GET réussi: status {get_response.status_code}")
                    except Exception as get_error:
                        logger.warning(f"⚠️  Erreur lors du GET via Assets/Global: {str(get_error)}")
                        # Si ça échoue, on continue sans version (l'API peut ne pas l'exiger)
                        logger.warning(f"   Continuation sans version - l'API peut accepter la mise à jour sans _version")
                        break
                    
                    # Extraire la version de la réponse
                    get_data = get_response.json()
                
                    # Logger la réponse complète pour debug
                    logger.debug(f"Réponse GET complète (premiers 2000 caractères): {json.dumps(get_data, indent=2)[:2000]}")
                    
                    # Normaliser la réponse (peut être un dict ou une liste)
                    normalized_data = None
                    if isinstance(get_data, list) and len(get_data) > 0:
                        # Chercher l'item avec le bon ID
                        for item in get_data:
                            if isinstance(item, dict) and item.get("id") == item_id:
                                normalized_data = item
                                break
                        if not normalized_data and len(get_data) > 0:
                            normalized_data = get_data[0]
                        logger.debug(f"Réponse normalisée (premier élément de la liste)")
                    elif isinstance(get_data, dict):
                        if "data" in get_data:
                            data_list = get_data["data"]
                            if isinstance(data_list, list) and len(data_list) > 0:
                                for item in data_list:
                                    if isinstance(item, dict) and item.get("id") == item_id:
                                        normalized_data = item
                                        break
                                if not normalized_data:
                                    normalized_data = data_list[0]
                            else:
                                normalized_data = get_data["data"]
                        else:
                            normalized_data = get_data
                        logger.debug(f"Réponse normalisée (champ 'data' ou dict direct)")
                    
                    # Logger tous les champs disponibles pour debug
                    if isinstance(normalized_data, dict):
                        logger.info(f"Champs disponibles dans la réponse GET: {list(normalized_data.keys())}")
                        
                        # Extraire le champ _version (peut être _version, version, ou dans un objet meta)
                        current_version = (
                            normalized_data.get("_version") or 
                            normalized_data.get("version") or 
                            normalized_data.get("__version__") or
                            (normalized_data.get("meta", {}).get("_version") if isinstance(normalized_data.get("meta"), dict) else None) or
                            (normalized_data.get("meta", {}).get("version") if isinstance(normalized_data.get("meta"), dict) else None)
                        )
                        
                        # Si on ne trouve pas _version, essayer de chercher dans tous les champs qui contiennent "version"
                        if current_version is None:
                            for key, value in normalized_data.items():
                                if "version" in key.lower() and value is not None:
                                    logger.debug(f"Champ contenant 'version' trouvé: {key} = {value}")
                                    current_version = value
                                    break
                    
                    if current_version:
                        logger.info(f"✓ Version actuelle récupérée: {current_version} (type: {type(current_version).__name__})")
                        break  # On a trouvé la version, on sort de la boucle
                    else:
                        logger.warning(f"⚠️  Version non trouvée dans la réponse (tentative {attempt + 1}/{max_retries})")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(0.2)
                            continue
                
                except Exception as get_error:
                    logger.warning(f"⚠️  Erreur lors de la récupération de la version (tentative {attempt + 1}/{max_retries}): {str(get_error)}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.2)
                        continue
                    break
        
        # Inclure la version dans le payload si on l'a trouvée
        if current_version is None:
            logger.warning(f"⚠️  Champ _version non trouvé pour {itemtype}/{item_id}.")
            logger.warning(f"   Tentative de mise à jour sans version - l'API peut rejeter ou accepter selon la configuration.")
        else:
            # Inclure la version dans le payload de mise à jour
            # S'assurer que c'est un entier ou une chaîne selon ce que l'API attend
            update_data["_version"] = int(current_version) if isinstance(current_version, (int, str)) and str(current_version).isdigit() else current_version
            logger.info(f"✓ Version incluse dans le payload: {update_data['_version']}")
        
        # ========================================================================
        # ÉTAPE 2: Effectuer la mise à jour avec la version
        # ========================================================================
        for attempt in range(max_retries):
            try:
                logger.info(f"Mise à jour {itemtype}/{item_id} avec: {update_data}")
                logger.info(f"Endpoint: {endpoint}")
                logger.info(f"Payload complet (JSON): {json.dumps(update_data, indent=2)}")
                
                # Vérifier que _version est présent si nécessaire
                if "_version" not in update_data:
                    logger.warning(f"⚠️  ATTENTION: Le champ _version n'est PAS présent dans le payload.")
                    logger.warning(f"   L'API GLPI peut rejeter cette requête avec une erreur 400.")
                    logger.warning(f"   Payload actuel: {json.dumps(update_data, indent=2)}")
                
                # Utiliser PATCH pour la mise à jour partielle
                response = await client.patch(endpoint, headers=headers, json=update_data)
                
                # Logger la réponse pour debug
                logger.debug(f"Réponse status: {response.status_code}")
                try:
                    response_data = response.json()
                    logger.debug(f"Réponse body: {json.dumps(response_data, indent=2)}")
                except:
                    logger.debug(f"Réponse text: {response.text}")
                
                # Gérer les erreurs spécifiques
                if response.status_code == 400:
                    # Erreur 400: format invalide - peut-être que le format des relations est incorrect
                    error_text = response.text
                    logger.error(f"❌ Erreur 400 (Bad Request) pour {itemtype}/{item_id}")
                    logger.error(f"   Erreur: {error_text[:500]}")
                    logger.error(f"   Payload envoyé: {json.dumps(update_data, indent=2)}")
                    
                    # Si c'est la première tentative et qu'on n'a pas de _version, essayer avec un format différent
                    if attempt == 0 and "_version" not in update_data:
                        logger.warning(f"⚠️  Tentative avec format alternatif (entiers directs au lieu d'objets)")
                        # Réessayer avec des entiers directs au lieu d'objets
                        update_data_alt = {}
                        if profile_config.target_status_id is not None:
                            update_data_alt["states_id"] = profile_config.target_status_id
                        if profile_config.target_entity_id is not None:
                            update_data_alt["entities_id"] = profile_config.target_entity_id
                        if profile_config.target_location_id is not None:
                            update_data_alt["locations_id"] = profile_config.target_location_id
                        update_data_alt["is_deleted"] = profile_config.is_deleted
                        if current_version is not None:
                            update_data_alt["_version"] = current_version
                        
                        logger.info(f"   Nouvelle tentative avec format alternatif: {json.dumps(update_data_alt, indent=2)}")
                        response_alt = await client.patch(endpoint, headers=headers, json=update_data_alt)
                        if response_alt.status_code == 200:
                            logger.info(f"✓ Mise à jour réussie avec le format alternatif!")
                            response = response_alt
                        else:
                            logger.error(f"❌ Le format alternatif a aussi échoué: {response_alt.status_code}")
                            response = response_alt
                    
                    response.raise_for_status()
                
                if response.status_code == 409:
                    error_text = response.text
                    logger.warning(f"⚠️  Conflit de version (409) pour {itemtype}/{item_id} (tentative {attempt + 1}/{max_retries})")
                    logger.warning(f"   Erreur: {error_text[:500]}")
                    
                    if attempt < max_retries - 1:
                        # Réessayer en récupérant la nouvelle version
                        logger.info(f"   Nouvelle tentative dans 0.5 secondes...")
                        await asyncio.sleep(0.5)  # Attendre un peu avant de réessayer
                        current_version = None  # Forcer la récupération d'une nouvelle version
                        continue  # Réessayer la boucle
                    else:
                        # Toutes les tentatives ont échoué
                        logger.error(f"❌ Échec de la mise à jour après {max_retries} tentatives (conflit de version)")
                        response.raise_for_status()  # Lève l'exception
                
                # Si on arrive ici, la mise à jour a réussi
                response.raise_for_status()
                
                # Vérifier que la mise à jour a bien été appliquée en récupérant l'item
                try:
                    verify_response = await client.get(endpoint, headers=headers)
                    if verify_response.status_code == 200:
                        updated_item = verify_response.json()
                        # Normaliser la réponse (peut être un dict ou une liste)
                        if isinstance(updated_item, list) and len(updated_item) > 0:
                            updated_item = updated_item[0]
                        elif isinstance(updated_item, dict) and "data" in updated_item:
                            updated_item = updated_item["data"]
                        
                        # Vérifier le statut si on l'a mis à jour
                        if profile_config.target_status_id is not None:
                            current_status = updated_item.get("states_id") or updated_item.get("status") or updated_item.get("state")
                            if current_status:
                                # Peut être un entier ou un objet avec id
                                status_id = current_status if isinstance(current_status, int) else current_status.get("id") if isinstance(current_status, dict) else None
                                if status_id == profile_config.target_status_id:
                                    logger.info(f"✓ Statut vérifié: {status_id} (attendu: {profile_config.target_status_id})")
                                else:
                                    logger.warning(f"⚠️  Statut après mise à jour: {status_id} (attendu: {profile_config.target_status_id})")
                            else:
                                logger.warning(f"⚠️  Impossible de vérifier le statut après mise à jour")
                except Exception as verify_error:
                    logger.warning(f"Impossible de vérifier la mise à jour: {str(verify_error)}")
                
                logger.info(f"✓ {itemtype}/{item_id} mis à jour avec succès (version: {current_version})")
                
                # ⚠️ TEMPORAIRE : Déverrouiller les champs verrouillés par GLPI
                # Cette solution de contournement accède directement à la base de données GLPI
                # pour supprimer les verrous créés automatiquement lors de la mise à jour.
                # À supprimer dès qu'une solution API sera disponible.
                try:
                    from services.glpisql_service import glpisql_service
                    
                    # Déterminer les champs qui ont été mis à jour
                    updated_fields = []
                    if profile_config.target_status_id is not None:
                        updated_fields.append("states_id")
                    if profile_config.target_entity_id is not None:
                        updated_fields.append("entities_id")
                    if profile_config.target_location_id is not None:
                        updated_fields.append("locations_id")
                    
                    if updated_fields and glpisql_service.enabled:
                        logger.info(f"🔓 Déverrouillage temporaire des champs: {updated_fields}")
                        unlock_success, unlock_error, unlock_count = await glpisql_service.unlock_item_fields_after_update(
                            item_id, itemtype, updated_fields
                        )
                        if unlock_success:
                            if unlock_count > 0:
                                logger.info(f"✓ {unlock_count} verrou(x) supprimé(s) pour {itemtype}/{item_id}")
                            else:
                                logger.debug(f"ℹ Aucun verrou trouvé pour {itemtype}/{item_id} (normal si pas de verrou)")
                        else:
                            logger.warning(f"⚠️  Impossible de déverrouiller les champs: {unlock_error}")
                            logger.warning(f"   Les verrous peuvent toujours être présents dans GLPI")
                    elif updated_fields and not glpisql_service.enabled:
                        logger.warning("⚠️  Service GLPI SQL désactivé - Les verrous ne seront pas supprimés")
                        logger.warning("   Activez le service avec GLPI_DB_ENABLED=true dans le .env pour supprimer les verrous automatiquement")
                except ImportError:
                    # Le service n'est pas disponible, on continue sans déverrouillage
                    logger.debug("Service GLPI SQL non disponible - Déverrouillage ignoré")
                except Exception as unlock_error:
                    # Ne pas faire échouer la mise à jour si le déverrouillage échoue
                    logger.warning(f"⚠️  Erreur lors du déverrouillage (non bloquant): {str(unlock_error)}")
                
                return True
                
            except httpx.HTTPStatusError as e:
                # Si c'est un conflit de version (409), on réessaye si possible
                if e.response.status_code == 409 and attempt < max_retries - 1:
                    logger.warning(f"⚠️  Conflit de version (409) pour {itemtype}/{item_id} (tentative {attempt + 1}/{max_retries})")
                    logger.warning(f"   Erreur: {e.response.text[:500]}")
                    logger.info(f"   Nouvelle tentative dans 0.5 secondes...")
                    await asyncio.sleep(0.5)
                    current_version = None  # Forcer la récupération d'une nouvelle version
                    continue  # Réessayer la boucle
                
                # Autre erreur HTTP ou toutes les tentatives ont échoué
                logger.error(f"Erreur lors de la mise à jour {itemtype}/{item_id}: {e.response.status_code}")
                logger.error(f"Réponse erreur: {e.response.text}")
                logger.error(f"Payload envoyé: {json.dumps(update_data, indent=2)}")
                raise
            except Exception as e:
                logger.error(f"Erreur lors de la mise à jour {itemtype}/{item_id}: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise ValueError(f"Impossible de mettre à jour l'item: {str(e)}")
        
        # Si on arrive ici, toutes les tentatives ont échoué
        logger.error(f"❌ Échec de la mise à jour après {max_retries} tentatives")
        raise ValueError(f"Impossible de mettre à jour l'item après {max_retries} tentatives")
    
    async def purge_technical_data(self, item_id: int, itemtype: str) -> bool:
        """
        Purge les données techniques d'un item GLPI.
        
        Supprime :
        - Les logiciels installés (glpi_items_softwareversions)
        - Les disques (glpi_items_disks)
        - L'OS (glpi_items_operatingsystems)
        - Les ports réseau (glpi_networkports)
        - Les verrous glpi-agent (glpi_plugin_fusioninventory_locks)
        
        Args:
            item_id: ID de l'item GLPI
            itemtype: Type d'item (Computer, Monitor, etc.)
        
        Returns:
            True si la purge a réussi, False sinon
        
        Raises:
            ValueError: Si aucun token n'est disponible
        """
        await self._ensure_valid_token()
        
        client = await self._get_client()
        headers = {
            "Authorization": f"{self._tokens.token_type} {self._tokens.access_token}",
            "Content-Type": "application/json"
        }
        
        success_count = 0
        error_count = 0
        
        # Liste des endpoints à purger
        # Note: Les endpoints exacts peuvent varier selon la version de GLPI
        purge_endpoints = []
        
        # Pour les ordinateurs, on purge les données techniques
        if itemtype == "Computer":
            purge_endpoints = [
                ("Items/SoftwareVersion", "logiciels"),
                ("Items/Disk", "disques"),
                ("Items/OperatingSystem", "OS"),
                ("NetworkPort", "ports réseau"),
            ]
        
        logger.info(f"Purge des données techniques pour {itemtype}/{item_id}")
        
        for endpoint_suffix, description in purge_endpoints:
            try:
                # Format: /api.php/Assets/{itemtype}/{item_id}/{endpoint}
                endpoint = f"{self.api_base}/Assets/{itemtype}/{item_id}/{endpoint_suffix}"
                
                logger.debug(f"Suppression des {description} via {endpoint}")
                
                # Récupérer d'abord la liste des éléments à supprimer
                response = await client.get(endpoint, headers=headers)
                
                if response.status_code == 404:
                    # Aucun élément à supprimer
                    logger.debug(f"Aucun {description} trouvé pour {itemtype}/{item_id}")
                    continue
                
                response.raise_for_status()
                items_to_delete = response.json()
                
                # Normaliser la réponse (peut être une liste ou un objet)
                if isinstance(items_to_delete, dict):
                    items_to_delete = items_to_delete.get("data", items_to_delete.get("items", []))
                
                if not isinstance(items_to_delete, list):
                    items_to_delete = []
                
                # Supprimer chaque élément
                for item in items_to_delete:
                    item_delete_id = item.get("id") or item.get("items_id")
                    if item_delete_id:
                        delete_endpoint = f"{endpoint}/{item_delete_id}"
                        try:
                            delete_response = await client.delete(delete_endpoint, headers=headers)
                            if delete_response.status_code in (200, 204):
                                success_count += 1
                                logger.debug(f"✓ {description} ID {item_delete_id} supprimé")
                            else:
                                error_count += 1
                                logger.warning(f"Échec suppression {description} ID {item_delete_id}: {delete_response.status_code}")
                        except httpx.HTTPStatusError as e:
                            if e.response.status_code == 404:
                                # Déjà supprimé, on ignore
                                logger.debug(f"{description} ID {item_delete_id} déjà supprimé")
                            else:
                                error_count += 1
                                logger.warning(f"Erreur suppression {description} ID {item_delete_id}: {e.response.status_code}")
                
                logger.info(f"Purge des {description} terminée: {success_count} supprimés, {error_count} erreurs")
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    # Endpoint non disponible pour ce type d'item, on continue
                    logger.debug(f"Endpoint {endpoint_suffix} non disponible pour {itemtype}")
                    continue
                else:
                    logger.warning(f"Erreur lors de la purge des {description}: {e.response.status_code} - {e.response.text}")
                    error_count += 1
            except Exception as e:
                logger.warning(f"Erreur lors de la purge des {description}: {str(e)}")
                error_count += 1
        
        # Purge des verrous glpi-agent (spécifique)
        try:
            # Endpoint pour les verrous FusionInventory
            # Note: Cet endpoint peut varier selon la configuration GLPI
            locks_endpoint = f"{self.api_base}/PluginFusioninventoryLock"
            
            # Rechercher les verrous pour cet item
            # Format de filtre: items_id=={item_id} AND itemtype=={itemtype}
            filter_query = f"items_id=={item_id} AND itemtype=={itemtype}"
            filter_encoded = quote(filter_query)
            
            response = await client.get(f"{locks_endpoint}?filter={filter_encoded}", headers=headers)
            
            if response.status_code == 200:
                locks_data = response.json()
                locks = locks_data if isinstance(locks_data, list) else locks_data.get("data", [])
                
                for lock in locks:
                    lock_id = lock.get("id")
                    if lock_id:
                        try:
                            delete_response = await client.delete(f"{locks_endpoint}/{lock_id}", headers=headers)
                            if delete_response.status_code in (200, 204):
                                logger.info(f"✓ Verrou glpi-agent ID {lock_id} supprimé")
                                success_count += 1
                        except httpx.HTTPStatusError as e:
                            if e.response.status_code != 404:
                                logger.warning(f"Erreur suppression verrou {lock_id}: {e.response.status_code}")
                                error_count += 1
        except Exception as e:
            # Les verrous sont optionnels, on ne bloque pas si ça échoue
            logger.debug(f"Impossible de purger les verrous glpi-agent: {str(e)}")
        
        logger.info(f"Purge terminée pour {itemtype}/{item_id}: {success_count} éléments supprimés, {error_count} erreurs")
        
        # On considère que c'est un succès si au moins une suppression a réussi ou si aucune erreur critique
        return error_count == 0 or success_count > 0


# ============================================================================
# Instance globale du service GLPI
# ============================================================================
glpi_service = GLPIService()

