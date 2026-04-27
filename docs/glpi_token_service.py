"""
Service de gestion des tokens GLPI OAuth2 dans la base de données

Ce module gère le stockage des tokens OAuth2 GLPI des utilisateurs authentifiés
dans une base de données SQLite locale, avec expiration automatique et chiffrement.
"""

import logging
import json
from typing import Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError

from services.glpi_service import GLPIOAuthTokens, GLPIUserInfo
from services.db_session_service import db_session_service
from services.encryption_service import encryption_service
from services.session_models import GLPIUserTokens

logger = logging.getLogger(__name__)


class GLPITokenService:
    """
    Service pour gérer le stockage des tokens OAuth2 GLPI des utilisateurs.
    
    Les tokens sont stockés dans une base de données SQLite locale,
    avec chiffrement et expiration automatique.
    """
    
    def store_tokens(
        self,
        user_id: int,
        tokens: GLPIOAuthTokens,
        user_info: Optional[GLPIUserInfo] = None
    ) -> bool:
        """
        Stocke les tokens OAuth2 GLPI d'un utilisateur.
        
        Les tokens sont chiffrés avant stockage dans la base de données.
        
        Args:
            user_id: ID de l'utilisateur GLPI
            tokens: Objet GLPIOAuthTokens contenant les tokens
            user_info: Informations utilisateur à mettre en cache (optionnel)
        
        Returns:
            True si stockage réussi, False sinon
        """
        try:
            session = db_session_service.get_session()
            
            # Chiffrer les tokens
            access_token_encrypted = encryption_service.encrypt(tokens.access_token)
            refresh_token_encrypted = (
                encryption_service.encrypt(tokens.refresh_token)
                if tokens.refresh_token
                else None
            )
            
            # Préparer le cache des infos utilisateur (JSON)
            user_info_cache = None
            if user_info:
                user_info_cache = json.dumps({
                    'id': user_info.id,
                    'name': user_info.name,
                    'realname': user_info.realname,
                    'firstname': user_info.firstname,
                    'email': user_info.email,
                    'profiles_id': user_info.profiles_id,
                    'entities_id': user_info.entities_id,
                })
            
            # Vérifier si des tokens existent déjà pour cet utilisateur
            existing_tokens = session.query(GLPIUserTokens).filter(GLPIUserTokens.user_id == user_id).first()
            
            if existing_tokens:
                # Mettre à jour les tokens existants
                existing_tokens.access_token_encrypted = access_token_encrypted
                existing_tokens.refresh_token_encrypted = refresh_token_encrypted
                existing_tokens.expires_at = tokens.expires_at or (datetime.utcnow() + timedelta(seconds=tokens.expires_in))
                existing_tokens.user_info_cache = user_info_cache
                existing_tokens.last_refresh = datetime.utcnow()
                existing_tokens.updated_at = datetime.utcnow()
            else:
                # Créer de nouveaux tokens
                new_tokens = GLPIUserTokens(
                    user_id=user_id,
                    access_token_encrypted=access_token_encrypted,
                    refresh_token_encrypted=refresh_token_encrypted,
                    expires_at=tokens.expires_at or (datetime.utcnow() + timedelta(seconds=tokens.expires_in)),
                    user_info_cache=user_info_cache,
                    last_refresh=datetime.utcnow()
                )
                session.add(new_tokens)
            
            session.commit()
            session.close()
            
            logger.info(f"Tokens GLPI stockés pour l'utilisateur ID={user_id}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors du stockage des tokens GLPI: {str(e)}")
            if 'session' in locals():
                session.rollback()
                session.close()
            return False
    
    def get_tokens(self, user_id: int) -> Optional[Tuple[GLPIOAuthTokens, Optional[GLPIUserInfo]]]:
        """
        Récupère les tokens OAuth2 GLPI d'un utilisateur s'ils sont valides.
        
        Args:
            user_id: ID de l'utilisateur
        
        Returns:
            Tuple (tokens, user_info) si valides, None sinon
        """
        try:
            session = db_session_service.get_session()
            
            # Rechercher les tokens
            glpi_tokens_db = session.query(GLPIUserTokens).filter(GLPIUserTokens.user_id == user_id).first()
            
            if not glpi_tokens_db:
                logger.debug(f"Aucun token GLPI stocké pour l'utilisateur ID={user_id}")
                session.close()
                return None
            
            # Vérifier l'expiration (avec une marge de 60 secondes)
            # Utiliser datetime.utcnow() pour cohérence avec expires_at qui est en UTC
            if datetime.utcnow() > glpi_tokens_db.expires_at - timedelta(seconds=60):
                logger.info(f"Tokens GLPI expirés pour l'utilisateur ID={user_id}")
                session.close()
                return None
            
            # Déchiffrer les tokens
            access_token = encryption_service.decrypt(glpi_tokens_db.access_token_encrypted)
            refresh_token = (
                encryption_service.decrypt(glpi_tokens_db.refresh_token_encrypted)
                if glpi_tokens_db.refresh_token_encrypted
                else None
            )
            
            # Recréer l'objet GLPIOAuthTokens
            tokens = GLPIOAuthTokens(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=int((glpi_tokens_db.expires_at - datetime.utcnow()).total_seconds()),
                expires_at=glpi_tokens_db.expires_at
            )
            
            # Décoder les infos utilisateur si disponibles
            user_info = None
            if glpi_tokens_db.user_info_cache:
                try:
                    user_info_dict = json.loads(glpi_tokens_db.user_info_cache)
                    user_info = GLPIUserInfo(**user_info_dict)
                except Exception as e:
                    logger.warning(f"Erreur lors du décodage des infos utilisateur: {str(e)}")
            
            session.close()
            logger.debug(f"Tokens GLPI récupérés pour l'utilisateur ID={user_id}")
            return (tokens, user_info)
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des tokens GLPI: {str(e)}")
            if 'session' in locals():
                session.close()
            return None
    
    def remove_tokens(self, user_id: int) -> bool:
        """
        Supprime les tokens GLPI d'un utilisateur.
        
        Args:
            user_id: ID de l'utilisateur
        
        Returns:
            True si suppression réussie, False sinon
        """
        try:
            session = db_session_service.get_session()
            
            glpi_tokens_db = session.query(GLPIUserTokens).filter(GLPIUserTokens.user_id == user_id).first()
            
            if glpi_tokens_db:
                session.delete(glpi_tokens_db)
                session.commit()
                logger.info(f"Tokens GLPI supprimés pour l'utilisateur ID={user_id}")
                session.close()
                return True
            else:
                session.close()
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de la suppression des tokens GLPI: {str(e)}")
            if 'session' in locals():
                session.rollback()
                session.close()
            return False
    
    def has_valid_tokens(self, user_id: int) -> bool:
        """
        Vérifie si l'utilisateur a des tokens GLPI valides (non expirés).
        
        Args:
            user_id: ID de l'utilisateur
        
        Returns:
            True si des tokens valides existent, False sinon
        """
        tokens = self.get_tokens(user_id)
        return tokens is not None
    
    def cleanup_expired(self) -> int:
        """
        Nettoie les tokens expirés.
        
        Returns:
            Nombre de tokens supprimés
        """
        try:
            session = db_session_service.get_session()
            
            # Rechercher tous les tokens expirés
            # Utiliser datetime.utcnow() pour cohérence avec expires_at qui est en UTC
            expired_tokens = session.query(GLPIUserTokens).filter(
                GLPIUserTokens.expires_at < datetime.utcnow()
            ).all()
            
            count = len(expired_tokens)
            
            if expired_tokens:
                for glpi_token in expired_tokens:
                    session.delete(glpi_token)
                session.commit()
                logger.debug(f"Nettoyage de {count} token(s) GLPI expiré(s)")
            
            session.close()
            return count
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage des tokens GLPI: {str(e)}")
            if 'session' in locals():
                session.rollback()
                session.close()
            return 0


# Instance globale du service
glpi_token_service = GLPITokenService()
