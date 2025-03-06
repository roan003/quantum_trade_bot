# security_manager.py

import os
import base64
import nacl.secret
import nacl.utils
import hashlib

class SecurityManager:
    def __init__(self, secret_key=None):
        self.secret_key = secret_key or self._generate_secret_key()
        self.encryption_box = nacl.secret.SecretBox(self.secret_key)
    
    def _generate_secret_key(self):
        """Génère une clé secrète sécurisée"""
        return nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)
    
    def encrypt_sensitive_data(self, data):
        """Chiffrement de données sensibles"""
        encrypted = self.encryption_box.encrypt(data.encode('utf-8'))
        return base64.b64encode(encrypted).decode('utf-8')
    
    def decrypt_sensitive_data(self, encrypted_data):
        """Déchiffrement de données sensibles"""
        try:
            decoded = base64.b64decode(encrypted_data.encode('utf-8'))
            decrypted = self.encryption_box.decrypt(decoded)
            return decrypted.decode('utf-8')
        except Exception as e:
            logging.error(f"Erreur de déchiffrement: {e}")
            return None
    
    def generate_api_key_hash(self, api_key):
        """Génère un hash sécurisé pour les clés API"""
        salt = os.urandom(16)
        key_hash = hashlib.pbkdf2_hmac('sha256', api_key.encode('utf-8'), salt, 100000)
        return base64.b64encode(salt + key_hash).decode('utf-8')