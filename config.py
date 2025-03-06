# config.py

import os

class UltimateTradeBotConfig:
    # Configuration détaillée du bot
    BASE_DIR = os.path.expanduser("~/quantum_trade_ai")
    DATA_DIR = os.path.join(BASE_DIR, "data")
    MODEL_DIR = os.path.join(BASE_DIR, "models")
    LOGS_DIR = os.path.join(BASE_DIR, "logs")
    
    # Créer les répertoires si nécessaire
    os.makedirs(BASE_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    # Paramètres de trading
    SYMBOLS = ["BTC/EUR", "ETH/EUR", "SOL/EUR"]
    TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h"]
    
    # Gestion des risques
    INITIAL_CAPITAL = 10000.0
    MAX_RISK_PER_TRADE = 0.01  # 1% du capital par trade
    STOP_LOSS_PERCENT = 0.02   # 2% de stop loss
    TAKE_PROFIT_PERCENT = 0.05 # 5% de take profit
    
    # Apprentissage et optimisation
    LEARNING_RATE = 0.001
    BATCH_SIZE = 64
    EPOCHS = 100
    TRADE_CYCLE_INTERVAL = 300  # 5 minutes entre chaque cycle
    
    # Seuils de décision
    CONFIDENCE_THRESHOLD = 0.7
    
    # Chemins de sauvegarde
    MODEL_SAVE_PATH = os.path.join(MODEL_DIR, "trading_model_{symbol}.pt")