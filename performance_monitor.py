# performance_monitor.py

import os
import sqlite3
import logging
from datetime import datetime, timedelta

class PerformanceMonitoringSystem:
    def __init__(self, config):
        self.config = config
        self.db_path = os.path.join(config.DATA_DIR, "performance.db")
        self.logger = logging.getLogger(__name__)
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialisation de la base de données de performance"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Table des trades individuels
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT,
                        side TEXT,
                        quantity REAL,
                        entry_price REAL,
                        exit_price REAL,
                        profit_loss REAL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Table des performances quotidiennes
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS daily_performance (
                        date DATE PRIMARY KEY,
                        total_trades INTEGER,
                        winning_trades INTEGER,
                        total_profit REAL,
                        max_drawdown REAL,
                        capital_end REAL
                    )
                ''')
                
                conn.commit()
        except Exception as e:
            self.logger.error(f"Erreur d'initialisation de la base de données: {e}")
    
    def record_trade(self, trade_data):
        """Enregistrement détaillé d'un trade"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO trades 
                    (symbol, side, quantity, entry_price, exit_price, profit_loss) 
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    trade_data['symbol'],
                    trade_data['side'],
                    trade_data['quantity'],
                    trade_data['entry_price'],
                    trade_data.get('exit_price'),
                    trade_data.get('profit_loss', 0)
                ))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Erreur lors de l'enregistrement du trade: {e}")
    
    def update_daily_performance(self, capital_end):
        """Mise à jour des performances quotidiennes"""
        try:
            today = datetime.now().date()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Récupérer les trades de la journée
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                        SUM(profit_loss) as total_profit,
                        MIN(profit_loss) as max_drawdown
                    FROM trades
                    WHERE date(timestamp) = ?
                ''', (today,))
                
                performance = cursor.fetchone()
                
                # Insérer/Mettre à jour les performances
                cursor.execute('''
                    INSERT OR REPLACE INTO daily_performance 
                    (date, total_trades, winning_trades, total_profit, max_drawdown, capital_end)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    today, 
                    performance[0], 
                    performance[1], 
                    performance[2], 
                    performance[3],
                    capital_end
                ))
                
                conn.commit()
        except Exception as e:
            self.logger.error(f"Erreur lors de la mise à jour des performances quotidiennes: {e}")
    
    def get_performance_metrics(self, symbol=None, days=30):
        """Extraction des métriques de performance"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Requête de base
                query = """
                    SELECT 
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                        SUM(profit_loss) as total_profit,
                        MIN(profit_loss) as max_drawdown,
                        AVG(profit_loss) as average_trade_profit
                    FROM trades
                    WHERE timestamp >= date('now', ?)
                """
                
                # Ajout du filtre sur le symbole si spécifié
                params = [f'-{days} days']
                if symbol:
                    query += " AND symbol = ?"
                    params.append(symbol)
                
                cursor.execute(query, params)
                return cursor.fetchone()
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des métriques: {e}")
            return None