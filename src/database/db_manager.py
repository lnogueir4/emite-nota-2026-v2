from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Boolean, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# NullPool desativa o pooling de conexões, garantindo que cada session
# sempre abra e feche uma conexão real — evita dados stale no Streamlit
engine = create_engine(DATABASE_URL, poolclass=NullPool)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Cliente(Base):
    __tablename__ = "clientes"
    __table_args__ = {'schema': 'estudio_2026'}
    
    cpf = Column(String, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String)
    profissao = Column(String)
    aniversario = Column(String)
    como_conheceu = Column(String)
    criado_em = Column(DateTime(timezone=True), server_default=text("now()"))
    atualizado_em = Column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"))

class Venda(Base):
    __tablename__ = "vendas"
    __table_args__ = {'schema': 'estudio_2026'}
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cliente_cpf = Column(String, nullable=False, index=True)
    plano = Column(String, nullable=False)
    valor = Column(Float, nullable=False)
    data_venda = Column(Date, nullable=False)
    meio_pagto = Column(String)
    parcelas = Column(Integer)
    num_nota = Column(String, nullable=True)
    status = Column(String, default="pendente") # pendente, emitida
    data_nota = Column(Date, nullable=True)
    categoria = Column(String, nullable=True)
    plano_ajustado = Column(String, nullable=True)
    nivel_plano = Column(String, nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=text("now()"))
    atualizado_em = Column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"))

class VendaPendente(Base):
    __tablename__ = "vendas_pendentes"
    __table_args__ = {'schema': 'estudio_2026'}
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    raw_message = Column(String, nullable=True)
    cpf = Column(String)
    nome = Column(String)
    email = Column(String)
    profissao = Column(String)
    aniversario = Column(String)
    como_conheceu = Column(String)
    plano = Column(String)
    valor = Column(Float)
    data_venda = Column(Date)
    meio_pagto = Column(String)
    parcelas = Column(Integer)
    status = Column(String, default="aguardando_aprovacao") # aguardando_aprovacao, aprovada, rejeitada
    data_nota = Column(Date, nullable=True)
    categoria = Column(String, nullable=True)
    mensagens_buffer_ids = Column(String, nullable=True)  # JSON: "[1, 2, 3]" — IDs de MensagensBuffer usados na extração
    plano_ajustado = Column(String, nullable=True)
    nivel_plano = Column(String, nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=text("now()"))
    atualizado_em = Column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"))

class MensagensBuffer(Base):
    __tablename__ = "mensagens_buffer"
    __table_args__ = {'schema': 'estudio_2026'}
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    texto = Column(String, nullable=False)
    processada = Column(Boolean, default=False)
    criado_em = Column(DateTime(timezone=True), server_default=text("now()"))
    atualizado_em = Column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"))

def init_db():
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS estudio_2026"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
