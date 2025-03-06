# logging_config.py

import os
import sys
import logging
import logging.handlers

class LoggingConfigurator:
    @staticmethod
    def configure_logging(config):
        """Configuration sophistiquée du logging"""
        # Création du répertoire de logs s'il n'existe pas
        log_dir = config.LOGS_DIR
        os.makedirs(log_dir, exist_ok=True)
        
        # Configuration du logger principal
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                # Log dans un fichier tournant
                logging.handlers.RotatingFileHandler(
                    os.path.join(log_dir, 'quantum_trade.log'),
                    maxBytes=10*1024*1024,  # 10 Mo
                    backupCount=5
                ),
                # Log sur la console
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        # Configuration des loggers spécifiques
        logging.getLogger('ccxt').setLevel(logging.WARNING)
        logging.getLogger('websockets').setLevel(logging.WARNING)
        
        return logging.getLogger(__name__)