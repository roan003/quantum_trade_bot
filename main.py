# main.py

import os
import sys
import asyncio
import logging
import signal

# Imports des composants du bot
from config import UltimateTradeBotConfig
from logging_config import LoggingConfigurator
from security_manager import SecurityManager
from performance_monitor import PerformanceMonitoringSystem
from risk_manager import RiskManagementSystem
from market_data_manager import MarketDataManager
from trade_strategy import TradingSignalGenerator
from trade_executor import TradeExecutor

class QuantumTradeBot:
    def __init__(self, config):
        """
        Initialisation principale du bot de trading
        
        Args:
            config: Configuration du bot
        """
        self.config = config
        
        # Configuration du logging
        self.logger = LoggingConfigurator.configure_logging()
        
        # Initialisation des composants
        self.security_manager = SecurityManager()
        self.performance_monitor = PerformanceMonitoringSystem(config)
        
        # Initialisation des gestionnaires
        self.risk_manager = RiskManagementSystem(
            config, 
            initial_capital=config.INITIAL_CAPITAL
        )
        
        self.market_data_manager = MarketDataManager(
            config, 
            self.security_manager
        )
        
        self.trading_signal_generator = TradingSignalGenerator(
            config, 
            self.market_data_manager, 
            self.risk_manager
        )
        
        self.trade_executor = TradeExecutor(
            config, 
            self.security_manager, 
            self.risk_manager, 
            self.performance_monitor
        )
        
        # Gestion des signaux système
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """
        Configuration des gestionnaires de signaux système
        Pour une fermeture propre du bot
        """
        for sig in [signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, self._graceful_shutdown)
    
    def _graceful_shutdown(self, signum, frame):
        """
        Arrêt propre du bot
        """
        self.logger.info(f"Signal de fermeture reçu (signal {signum}). Arrêt en cours...")
        
        # Récupération du rapport de performance final
        performance_report = self.performance_monitor.get_performance_metrics()
        risk_report = self.risk_manager.get_risk_report()
        
        # Logging des rapports finaux
        self.logger.info("Rapport de performance final:")
        for key, value in performance_report.items():
            self.logger.info(f"{key}: {value}")
        
        self.logger.info("Rapport de risque final:")
        for key, value in risk_report.items():
            self.logger.info(f"{key}: {value}")
        
        # Fermeture des ressources si nécessaire
        sys.exit(0)
    
    async def _monitor_system_health(self):
        """
        Surveillance continue de la santé du système
        """
        while True:
            try:
                # Récupération des métriques de performance
                performance_metrics = self.performance_monitor.get_performance_metrics()
                risk_metrics = self.risk_manager.get_risk_report()
                
                # Logging périodique
                self.logger.info("Métriques système:")
                self.logger.info(f"Capital actuel: {risk_metrics.get('current_capital', 0)}")
                self.logger.info(f"Trades totaux: {performance_metrics.get('total_trades', 0)}")
                self.logger.info(f"Trades gagnants: {performance_metrics.get('winning_trades', 0)}")
                
                # Vérification des seuils critiques
                if risk_metrics.get('max_drawdown', 0) < -self.config.MAX_RISK_PER_TRADE * 10:
                    self.logger.warning("Seuil de drawdown critique atteint. Réduction des positions.")
                
                # Attente avant la prochaine vérification
                await asyncio.sleep(3600)  # Toutes les heures
            
            except Exception as e:
                self.logger.error(f"Erreur lors du monitoring système: {e}")
                await asyncio.sleep(600)  # Attente en cas d'erreur
    
    async def _trading_loop(self):
        """
        Boucle principale de trading
        """
        while True:
            try:
                # Trading pour chaque symbole
                for symbol in self.config.SYMBOLS:
                    # Génération du signal de trading
                    trade_signal = await self.trading_signal_generator.generate_trading_signal(symbol)
                    
                    # Exécution conditionnelle du trade
                    if trade_signal and trade_signal['risk_assessment']['executable']:
                        trade_result = await self.trade_executor.execute_trade(trade_signal)
                        
                        # Logging du résultat du trade
                        if trade_result:
                            self.logger.info(f"Trade exécuté pour {symbol}: {trade_result}")
                
                # Attente entre les cycles de trading
                await asyncio.sleep(self.config.TRADE_CYCLE_INTERVAL)
            
            except Exception as e:
                self.logger.error(f"Erreur dans la boucle de trading: {e}")
                await asyncio.sleep(60)  # Pause de sécurité
    
    async def run(self):
        """
        Démarrage du bot
        """
        try:
            self.logger.info("Démarrage de QuantumTrade Bot")
            
            # Tâches asynchrones
            trading_task = asyncio.create_task(self._trading_loop())
            monitoring_task = asyncio.create_task(self._monitor_system_health())
            
            # Attente de la complétion des tâches
            await asyncio.gather(trading_task, monitoring_task)
        
        except Exception as e:
            self.logger.critical(f"Erreur critique lors du démarrage: {e}")
            self._graceful_shutdown(None, None)

def main():
    """
    Point d'entrée principal
    """
    try:
        # Initialisation du bot
        bot = QuantumTradeBot(UltimateTradeBotConfig)
        
        # Exécution asynchrone
        asyncio.run(bot.run())
    
    except Exception as e:
        logging.critical(f"Erreur de démarrage du bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()