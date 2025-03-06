# trade_executor.py

import os
import asyncio
import logging
import ccxt
from typing import Dict, Any, Optional

class TradeExecutor:
    def __init__(self, config, security_manager, risk_manager, performance_monitor):
        """
        Exécuteur de trades avec gestion avancée des risques et sécurité
        
        Args:
            config: Configuration du bot
            security_manager: Gestionnaire de sécurité
            risk_manager: Gestionnaire des risques
            performance_monitor: Système de monitoring de performance
        """
        self.config = config
        self.security_manager = security_manager
        self.risk_manager = risk_manager
        self.performance_monitor = performance_monitor
        
        self.logger = logging.getLogger(__name__)
        
        # Initialisation des connexions d'échange
        self.exchanges = self._initialize_exchanges()
        
        # États des trades en cours
        self.active_trades = {}
        
        # Configuration des limites de trading
        self.trade_limits = {
            'max_open_trades': 3,
            'max_trade_duration_hours': 24
        }
    
    def _initialize_exchanges(self) -> Dict[str, ccxt.Exchange]:
        """
        Initialisation sécurisée des connexions d'échange
        
        Returns:
            Dictionnaire des instances d'échange
        """
        exchanges = {}
        for symbol in self.config.SYMBOLS:
            try:
                # Récupération sécurisée des clés API
                api_key = self.security_manager.decrypt_sensitive_data(
                    os.environ.get(f"{symbol.replace('/', '_')}_API_KEY")
                )
                api_secret = self.security_manager.decrypt_sensitive_data(
                    os.environ.get(f"{symbol.replace('/', '_')}_API_SECRET")
                )
                
                # Création de l'instance d'échange
                exchange = getattr(ccxt, 'binance')({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'spot'
                    }
                })
                
                exchanges[symbol] = exchange
                self.logger.info(f"Connexion échange initialisée pour {symbol}")
            
            except Exception as e:
                self.logger.error(f"Erreur d'initialisation de l'échange pour {symbol}: {e}")
        
        return exchanges
    
    async def execute_trade(self, trade_signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Exécution du trade avec gestion avancée des risques
        
        Args:
            trade_signal: Signal de trading généré
        
        Returns:
            Résultat du trade ou None
        """
        symbol = trade_signal['symbol']
        
        try:
            # Vérification des limites de trading
            if not self._can_open_new_trade(symbol):
                self.logger.warning(f"Limite de trades atteinte pour {symbol}")
                return None
            
            # Récupération de l'échange
            exchange = self.exchanges.get(symbol)
            if not exchange:
                self.logger.error(f"Pas d'échange disponible pour {symbol}")
                return None
            
            # Récupération du ticker et du prix actuel
            ticker = await exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            
            # Gestion des risques
            risk_assessment = trade_signal['risk_assessment']
            if not risk_assessment['executable']:
                self.logger.info(f"Trade non exécutable pour {symbol} - Risque trop élevé")
                return None
            
            # Calcul de la quantité
            balance = await self._get_available_balance(exchange, symbol)
            position_size = risk_assessment['position_size_percent'] * balance
            quantity = position_size / current_price
            
            # Détermination du côté du trade
            side = 'buy' if trade_signal['signal'] > 0 else 'sell'
            
            # Exécution du trade
            order = await self._place_order(
                exchange, 
                symbol, 
                side, 
                quantity, 
                current_price
            )
            
            # Suivi du trade
            trade_result = self._create_trade_result(
                symbol, 
                side, 
                quantity, 
                current_price, 
                order
            )
            
            # Mise à jour des gestionnaires
            self.active_trades[symbol] = trade_result
            self.risk_manager.update_capital_and_metrics(trade_result)
            self.performance_monitor.record_trade(trade_result)
            
            return trade_result
        
        except Exception as e:
            self.logger.error(f"Erreur lors de l'exécution du trade pour {symbol}: {e}")
            return None
    
    async def _place_order(self, exchange, symbol, side, quantity, price):
        """
        Placement de l'ordre avec gestion des erreurs
        
        Args:
            exchange: Instance de l'échange
            symbol: Symbole de trading
            side: Côté du trade (achat/vente)
            quantity: Quantité à trader
            price: Prix du trade
        
        Returns:
            Résultat de l'ordre
        """
        try:
            # Méthode de placement d'ordre adaptative
            if side == 'buy':
                order = await exchange.create_market_buy_order(symbol, quantity)
            else:
                order = await exchange.create_market_sell_order(symbol, quantity)
            
            self.logger.info(f"Ordre {side} exécuté pour {symbol}: {quantity} @ {price}")
            return order
        
        except Exception as e:
            self.logger.error(f"Erreur de placement d'ordre {side} pour {symbol}: {e}")
            raise
    
    def _can_open_new_trade(self, symbol: str) -> bool:
        """
        Vérifie si un nouveau trade peut être ouvert
        
        Args:
            symbol: Symbole de trading
        
        Returns:
            Booléen indiquant si un nouveau trade est possible
        """
        # Vérification du nombre maximum de trades ouverts
        if len(self.active_trades) >= self.trade_limits['max_open_trades']:
            return False
        
        # Vérification de l'existence d'un trade actif pour ce symbole
        if symbol in self.active_trades:
            trade = self.active_trades[symbol]
            trade_duration = (datetime.now() - trade['timestamp']).total_seconds() / 3600
            
            # Vérification de la durée maximale du trade
            if trade_duration > self.trade_limits['max_trade_duration_hours']:
                # Fermeture automatique du trade si durée dépassée
                self._close_trade(symbol)
                return True
            
            return False
        
        return True
    
    def _close_trade(self, symbol: str):
        """
        Fermeture automatique d'un trade
        
        Args:
            symbol: Symbole du trade à fermer
        """
        if symbol in self.active_trades:
            trade = self.active_trades.pop(symbol)
            self.logger.warning(f"Trade pour {symbol} fermé automatiquement après durée maximale")
            
            # TODO: Implémenter la logique de fermeture réelle du trade
    
    def _create_trade_result(self, symbol, side, quantity, price, order):
        """
        Création des détails du trade
        
        Args:
            symbol: Symbole de trading
            side: Côté du trade
            quantity: Quantité tradée
            price: Prix du trade
            order: Détails de l'ordre
        
        Returns:
            Dictionnaire avec les détails du trade
        """
        return {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'entry_price': price,
            'timestamp': datetime.now(),
            'order_details': order,
            'profit_loss': 0  # À calculer lors de la fermeture du trade
        }
    
    async def _get_available_balance(self, exchange, symbol):
        """
        Récupération du solde disponible
        
        Args:
            exchange: Instance de l'échange
            symbol: Symbole de trading
        
        Returns:
            Solde disponible
        """
        try:
            # Récupération du solde
            balance = await exchange.fetch_balance()
            quote_currency = symbol.split('/')[1]
            
            return balance['free'].get(quote_currency, 0)
        
        except Exception as e:
            self.logger.error(f"Erreur de récupération du solde pour {symbol}: {e}")
            return 0