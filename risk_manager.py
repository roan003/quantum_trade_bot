# risk_manager.py

import numpy as np
import logging
from typing import Dict, Any, List

class RiskManagementSystem:
    def __init__(self, config, initial_capital: float = 10000.0):
        """
        Système de gestion des risques avec plusieurs mécanismes de protection
        
        Args:
            config: Configuration du bot
            initial_capital: Capital initial de trading
        """
        self.config = config
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        
        # Historique des trades et statistiques
        self.trade_history: List[Dict[str, Any]] = []
        
        # Paramètres de risk management
        self.max_risk_per_trade = config.MAX_RISK_PER_TRADE
        self.stop_loss_percent = config.STOP_LOSS_PERCENT
        self.take_profit_percent = config.TAKE_PROFIT_PERCENT
        
        # Statistiques de risque
        self.risk_metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'max_drawdown': 0,
            'max_drawdown_percent': 0,
            'sharpe_ratio': 0,
            'sortino_ratio': 0
        }
        
        self.logger = logging.getLogger(__name__)
    
    def calculate_position_size(self, entry_price: float, stop_loss_price: float, symbol: str) -> float:
        """
        Calcule la taille de position basée sur le risque
        
        Args:
            entry_price: Prix d'entrée
            stop_loss_price: Prix de stop loss
            symbol: Symbole de trading
        
        Returns:
            Taille de position optimale
        """
        try:
            # Risque en capital par trade
            risk_amount = self.current_capital * self.max_risk_per_trade
            
            # Distance entre entrée et stop loss
            risk_per_unit = abs(entry_price - stop_loss_price)
            
            # Calcul de la taille de position
            position_size = risk_amount / risk_per_unit
            
            # Limites de sécurité
            max_allowed_position = self.current_capital / entry_price
            position_size = min(position_size, max_allowed_position)
            
            return position_size
        except Exception as e:
            self.logger.error(f"Erreur de calcul de taille de position pour {symbol}: {e}")
            return 0
    
    def assess_trade_risk(self, trade_signal: float, market_conditions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Évalue les risques d'un trade potentiel
        
        Args:
            trade_signal: Signal de trading (-1 à 1)
            market_conditions: Conditions de marché
        
        Returns:
            Dictionnaire d'évaluation des risques
        """
        risk_assessment = {
            'executable': False,
            'risk_score': 0,
            'position_size_percent': 0,
            'recommended_stop_loss': 0
        }
        
        try:
            # Facteurs de risque
            volatility = market_conditions.get('volatility', 0.5)
            trend_strength = market_conditions.get('trend_strength', 0.5)
            
            # Calcul du score de risque
            risk_components = [
                abs(trade_signal) * 0.4,      # Force du signal
                volatility * 0.3,             # Volatilité du marché
                (1 - trend_strength) * 0.3    # Incertitude de la tendance
            ]
            
            risk_score = np.mean(risk_components)
            
            # Décision d'exécution basée sur le score de risque
            risk_assessment['risk_score'] = risk_score
            risk_assessment['executable'] = risk_score < 0.6
            
            # Taille de position dynamique
            risk_assessment['position_size_percent'] = max(0.01, min(self.max_risk_per_trade, risk_score))
            
        except Exception as e:
            self.logger.error(f"Erreur d'évaluation des risques: {e}")
        
        return risk_assessment
    
    def update_capital_and_metrics(self, trade_result: Dict[str, Any]):
        """
        Met à jour le capital et les métriques de performance après un trade
        
        Args:
            trade_result: Résultats du trade
        """
        try:
            # Mise à jour du capital
            profit_loss = trade_result.get('profit_loss', 0)
            self.current_capital += profit_loss
            
            # Enregistrement du trade
            self.trade_history.append(trade_result)
            
            # Mise à jour des métriques
            self._update_risk_metrics()
        except Exception as e:
            self.logger.error(f"Erreur de mise à jour des métriques: {e}")
    
    def _update_risk_metrics(self):
        """Calcul des métriques de risque internes"""
        if not self.trade_history:
            return
        
        # Extraire les profits/pertes
        profits = [trade['profit_loss'] for trade in self.trade_history]
        
        # Mise à jour des statistiques de base
        self.risk_metrics.update({
            'total_trades': len(self.trade_history),
            'winning_trades': sum(1 for p in profits if p > 0),
            'losing_trades': sum(1 for p in profits if p <= 0),
            'max_drawdown': min(profits),
            'max_drawdown_percent': min(profits) / self.initial_capital * 100
        })
        
        # Calcul du ratio de Sharpe (approximatif)
        try:
            returns = np.array(profits) / self.initial_capital
            self.risk_metrics['sharpe_ratio'] = (
                np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
            )
        except Exception as e:
            self.logger.warning(f"Erreur de calcul du Sharpe Ratio: {e}")
    
    def get_risk_report(self) -> Dict[str, Any]:
        """
        Génère un rapport détaillé des risques
        
        Returns:
            Dictionnaire de métriques de risque
        """
        return {
            'current_capital': self.current_capital,
            'initial_capital': self.initial_capital,
            **self.risk_metrics
        }