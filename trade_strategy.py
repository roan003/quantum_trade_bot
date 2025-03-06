# trade_strategy.py

import os
import logging
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from typing import Dict, Any, List

class TradingSignalGenerator:
    def __init__(self, config, market_data_manager, risk_manager):
        """
        Générateur de signaux de trading avec approche hybride
        
        Args:
            config: Configuration du bot
            market_data_manager: Gestionnaire des données de marché
            risk_manager: Gestionnaire des risques
        """
        self.config = config
        self.market_data_manager = market_data_manager
        self.risk_manager = risk_manager
        self.logger = logging.getLogger(__name__)
        
        # Modèles de prédiction par symbole
        self.prediction_models = {}
        
        # Initialisation des modèles
        self._initialize_models()
    
    def _initialize_models(self):
        """
        Initialisation des modèles de prédiction pour chaque symbole
        """
        for symbol in self.config.SYMBOLS:
            try:
                # Créer un modèle de prédiction neuronal
                model = NeuralTradingModel(input_size=50)  # Taille d'entrée adaptative
                self.prediction_models[symbol] = model
                
                self.logger.info(f"Modèle initialisé pour {symbol}")
            
            except Exception as e:
                self.logger.error(f"Erreur d'initialisation du modèle pour {symbol}: {e}")
    
    async def generate_trading_signal(self, symbol: str) -> Dict[str, Any]:
        """
        Génération du signal de trading avec approche multi-critères
        
        Args:
            symbol: Symbole de trading
        
        Returns:
            Dictionnaire avec signal de trading et métriques
        """
        try:
            # Récupération des données de marché multi-timeframe
            market_features = await self.market_data_manager.get_multi_timeframe_features(symbol)
            
            # Détection du régime de marché
            market_regime = await self.market_data_manager.detect_market_regime(symbol)
            
            # Préparation des features pour le modèle de prédiction
            model_input = self._prepare_model_input(market_features)
            
            # Récupération du modèle de prédiction
            prediction_model = self.prediction_models.get(symbol)
            if not prediction_model:
                self.logger.warning(f"Pas de modèle de prédiction pour {symbol}")
                return self._default_signal()
            
            # Prédiction du modèle
            prediction = prediction_model(model_input)
            
            # Transformation de la prédiction en signal de trading
            signal_value, confidence = self._process_prediction(prediction, market_regime)
            
            # Évaluation des risques
            risk_assessment = self.risk_manager.assess_trade_risk(
                trade_signal=signal_value, 
                market_conditions={
                    'volatility': market_regime['volatility'],
                    'trend_strength': market_regime['trend_strength']
                }
            )
            
            return {
                'symbol': symbol,
                'signal': signal_value,
                'confidence': confidence,
                'market_regime': market_regime,
                'risk_assessment': risk_assessment
            }
        
        except Exception as e:
            self.logger.error(f"Erreur de génération de signal pour {symbol}: {e}")
            return self._default_signal()
    
    def _prepare_model_input(self, market_features: Dict[str, Any]) -> torch.Tensor:
        """
        Prépare les features pour le modèle de prédiction
        
        Args:
            market_features: Features de marché multi-timeframe
        
        Returns:
            Tenseur d'entrée pour le modèle
        """
        # Extraction et normalisation des features
        features_list = []
        
        for timeframe, features in market_features.items():
            # Sélection et normalisation des features clés
            timeframe_features = [
                features.get('rsi', 50),
                features.get('sma_20', 0),
                features.get('ema_50', 0),
                features.get('bb_width', 0),
                features.get('returns', 0)
            ]
            features_list.extend(timeframe_features)
        
        # Conversion en tenseur PyTorch
        return torch.FloatTensor(features_list).unsqueeze(0)
    
    def _process_prediction(self, prediction: torch.Tensor, market_regime: Dict[str, Any]) -> tuple:
        """
        Traitement de la prédiction du modèle
        
        Args:
            prediction: Sortie du modèle de prédiction
            market_regime: Informations sur le régime de marché
        
        Returns:
            Tuple (valeur du signal, confidence)
        """
        # Transformation de la prédiction
        _, predicted_class = torch.max(prediction, 1)
        confidence = torch.max(prediction).item()
        
        # Mapping des classes à des signaux
        signal_mapping = {0: -1, 1: 0, 2: 1}
        signal_value = signal_mapping.get(predicted_class.item(), 0)
        
        # Ajustement du signal selon le régime de marché
        regime_adjustments = {
            'bullish': 1.2,
            'bearish': 0.8,
            'volatile': 0.5,
            'neutral': 1.0
        }
        
        signal_value *= regime_adjustments.get(market_regime['regime'], 1.0)
        confidence *= market_regime['confidence']
        
        return signal_value, confidence
    
    def _default_signal(self) -> Dict[str, Any]:
        """
        Signal par défaut en cas d'erreur
        
        Returns:
            Dictionnaire de signal neutre
        """
        return {
            'symbol': None,
            'signal': 0,
            'confidence': 0.5,
            'market_regime': {
                'regime': 'neutral',
                'confidence': 0.5
            },
            'risk_assessment': {
                'executable': False,
                'risk_score': 0.5,
                'position_size_percent': 0
            }
        }

class NeuralTradingModel(nn.Module):
    def __init__(self, input_size: int, hidden_sizes: List[int] = [64, 32]):
        """
        Modèle de réseau de neurones pour prédiction de trading
        
        Args:
            input_size: Taille des features d'entrée
            hidden_sizes: Tailles des couches cachées
        """
        super().__init__()
        
        # Couches du réseau
        layers = []
        prev_size = input_size
        
        for size in hidden_sizes:
            layers.append(nn.Linear(prev_size, size))
            layers.append(nn.BatchNorm1d(size))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(0.2))
            prev_size = size
        
        # Couche de sortie (3 classes : baisse, neutre, hausse)
        layers.append(nn.Linear(prev_size, 3))
        layers.append(nn.Softmax(dim=1))
        
        self.model = nn.Sequential(*layers)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Passage avant du modèle
        
        Args:
            x: Tenseur d'entrée
        
        Returns:
            Prédictions de trading
        """
        return self.model(x)
    
    def train_model(self, X_train, y_train, epochs=100, learning_rate=0.001):
        """
        Entraînement du modèle
        
        Args:
            X_train: Features d'entraînement
            y_train: Labels d'entraînement
            epochs: Nombre d'époques
            learning_rate: Taux d'apprentissage
        """
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(self.parameters(), lr=learning_rate)
        
        for epoch in range(epochs):
            # Mode entraînement
            self.train()
            optimizer.zero_grad()
            
            # Passage avant et calcul de la perte
            outputs = self(X_train)
            loss = criterion(outputs, y_train)
            
            # Rétropropagation
            loss.backward()
            optimizer.step()