from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Configuración de BD Local
# Se guardará en el volumen persistente o local
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
os.makedirs(DB_PATH, exist_ok=True)
DATABASE_URL = f"sqlite:///{os.path.join(DB_PATH, 'trading_bot_v16.db')}"

Base = declarative_base()

# --- Modelos de Datos ---

class Signal(Base):
    __tablename__ = 'signals'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    symbol = Column(String(20), index=True)
    signal_type = Column(String(10)) # BUY/SELL
    price = Column(Float)
    reason = Column(String(200))
    strategy = Column(String(50))
    status = Column(String(20), default='NEW')

class MarketSnapshot(Base):
    __tablename__ = 'market_snapshots'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    symbol = Column(String(20), index=True)
    price = Column(Float)
    volume_24h = Column(Float)
    change_24h = Column(Float)

class Trade(Base):
    __tablename__ = 'trades'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    symbol = Column(String(20))
    side = Column(String(10)) # LONG/SHORT
    amount = Column(Float)
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)
    status = Column(String(20), default='OPEN')

class Wallet(Base):
    __tablename__ = 'wallet'
    id = Column(Integer, primary_key=True)
    usdt_balance = Column(Float, default=10000.0)
    total_equity = Column(Float, default=10000.0)
    last_updated = Column(DateTime, default=datetime.utcnow)

class PairsSignal(Base):
    __tablename__ = 'pairs_signals'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    asset_a = Column(String(10))
    asset_b = Column(String(10))
    correlation = Column(Float)
    z_score = Column(Float)
    signal = Column(String(50))  # "LONG A / SHORT B"
    status = Column(String(20), default='OPEN')

# --- Motor de BD ---
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Crea las tablas si no existen"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency para obtener sesión"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
