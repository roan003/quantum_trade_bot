# market_data_manager.py

import os
import asyncio
import logging
import numpy as np
import pandas as pd
import ccxt.pro as ccxtpro
import ta

class MarketDataManager:
    def __init__(self, config, security_manager):
        """
        Gestionnaire de données de marché avec fonctionnalités avancées
        
        Args:
            config: Configuration du bot
            security_manager: Gestionnaire de sécurité
        """
        self.config = config
        self.security_manager = security_manager
        self.logger = logging.getLogger(__name__)
        
        # Répertoire de stockage des données
        self.data_dir = os.path.join(config.DATA_DIR, 'market_data')
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Connexions aux échanges
        self.exchanges = self._initialize_exchanges()
        
        # Cache des données
        self.market_data_cache = {}
        
        # Configuration de la fenêtre d'analyse
        self.analysis_windows = {
            'short': 50,   # Court terme
            'medium': 200, # Moyen terme
            'long': 500    # Long terme
        }
    
    def _initialize_exchanges(self):
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
                exchange = ccxtpro.binance({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'spot'
                    }
                })
                
                exchanges[symbol] = exchange
                self.logger.info(f"Connexion initialisée pour {symbol}")
            
            except Exception as e:
                self.logger.error(f"Erreur d'initialisation pour {symbol}: {e}")
        
        return exchanges
    
    async def fetch_historical_data(self, symbol, timeframe='1h', limit=500):
        """
        Récupération des données historiques avec gestion avancée
        
        Args:
            symbol: Symbole de trading
            timeframe: Intervalle de temps
            limit: Nombre de bougies à récupérer
        
        Returns:
            DataFrame pandas avec données OHLCV
        """
        try:
            exchange = self.exchanges.get(symbol)
            if not exchange:
                self.logger.error(f"Pas d'échange disponible pour {symbol}")
                return None
            
            # Récupération des données OHLCV
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            # Conversion en DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Mise en cache
            self.market_data_cache[f"{symbol}_{timeframe}"] = df
            
            return df
        
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des données pour {symbol}: {e}")
            return None
    
    def extract_advanced_features(self, df):
        """
        Extraction de features techniques avancées
        
        Args:
            df: DataFrame avec données OHLCV
        
        Returns:
            DataFrame avec features supplémentaires
        """
        try:
            # Copie pour éviter les modifications directes
            features_df = df.copy()
            
            # Indicateurs de tendance
            features_df['sma_20'] = ta.trend.sma_indicator(features_df['close'], window=20)
            features_df['ema_50'] = ta.trend.ema_indicator(features_df['close'], window=50)
            
            # Indicateurs de momentum
            features_df['rsi'] = ta.momentum.rsi(features_df['close'], window=14)
            
            # Indicateurs de volatilité
            bollinger = ta.volatility.BollingerBands(features_df['close'], window=20)
            features_df['bb_high'] = bollinger.bollinger_hband()
            features_df['bb_low'] = bollinger.bollinger_lband()
            features_df['bb_width'] = (features_df['bb_high'] - features_df['bb_low']) / features_df['close'] * 100
            
            # Indicateurs de volume
            features_df['obv'] = ta.volume.on_balance_volume(features_df['close'], features_df['volume'])
            
            # Rendements
            features_df['returns'] = features_df['close'].pct_change()
            
            return features_df
        
        except Exception as e:
            self.logger.error(f"Erreur lors de l'extraction des features: {e}")
            return df
    
    async def get_multi_timeframe_features(self, symbol):
        """
        Récupération de features sur différents intervalles
        
        Args:
            symbol: Symbole de trading
        
        Returns:
            Dictionnaire de features par intervalle
        """
        features_by_timeframe = {}
        
        for timeframe in self.config.TIMEFRAMES:
            try:
                # Récupération des données
                historical_data = await self.fetch_historical_data(symbol, timeframe)
                
                if historical_data is not None:
                    # Extraction des features
                    features = self.extract_advanced_features(historical_data)
                    features_by_timeframe[timeframe] = features.iloc[-1].to_dict()
            
            except Exception as e:
                self.logger.error(f"Erreur multi-timeframe pour {symbol} - {timeframe}: {e}")
        
        return features_by_timeframe
    
    async def detect_market_regime(self, symbol):
        """
        Détection du régime de marché
        
        Args:
            symbol: Symbole de trading
        
        Returns:
            Dictionnaire avec régime de marché
        """
        try:
            # Récupération des données sur différentes fenêtres
            features = await self.get_multi_timeframe_features(symbol)
            
            # Analyse de la volatilité
            volatility_indicators = [
                features.get('1h', {}).get('bb_width', 0),
                features.get('4h', {}).get('bb_width', 0)
            ]
            avg_volatility = np.mean(volatility_indicators)
            
            # Analyse de la tendance
            trend_indicators = [
                features.get('1h', {}).get('rsi', 50),
                features.get('4h', {}).get('rsi', 50)
            ]
            avg_trend = np.mean(trend_indicators)
            
            # Détermination du régime
            if avg_volatility > 3 and abs(avg_trend - 50) > 10:
                regime = 'volatile'
                confidence = min(1.0, avg_volatility / 5)
            elif avg_trend > 60:
                regime = 'bullish'
                confidence = (avg_trend - 50) / 50
            elif avg_trend < 40:
                regime = 'bearish'
                confidence = (50 - avg_trend) / 50
            else:
                regime = 'neutral'
                confidence = 0.5
            
            return {
                'regime': regime,
                'confidence': confidence,
                'volatility': avg_volatility,
                'trend_strength': abs(avg_trend - 50) / 50
            }
        
        except Exception as e:
            self.logger.error(f"Erreur de détection du régime de marché pour {symbol}: {e}")
            return {
                'regime': 'neutral',
                'confidence': 0.5,
                'volatility': 0,
                'trend_strength': 0
            }