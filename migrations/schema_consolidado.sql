-- Schema Consolidado - Emite Nota (2026)
-- Este arquivo representa o estado final do banco de dados,
-- incluindo tabelas e triggers, para criar um banco do zero.

CREATE SCHEMA IF NOT EXISTS estudio_2026;

-- --------------------------------------------------------
-- FUNÇÕES GENÉRICAS
-- --------------------------------------------------------
CREATE OR REPLACE FUNCTION estudio_2026.update_atualizado_em_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.atualizado_em = CURRENT_TIMESTAMP;
   RETURN NEW;
END;
$$ language 'plpgsql';

-- --------------------------------------------------------
-- TABELAS
-- --------------------------------------------------------

CREATE TABLE IF NOT EXISTS estudio_2026.clientes (
    cpf VARCHAR PRIMARY KEY,
    nome VARCHAR NOT NULL,
    email VARCHAR,
    profissao VARCHAR,
    aniversario VARCHAR,
    como_conheceu VARCHAR,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS estudio_2026.vendas (
    id SERIAL PRIMARY KEY,
    cliente_cpf VARCHAR NOT NULL,
    plano VARCHAR NOT NULL,
    valor DOUBLE PRECISION NOT NULL,
    data_venda DATE NOT NULL,
    meio_pagto VARCHAR,
    parcelas INTEGER,
    num_nota VARCHAR,
    status VARCHAR DEFAULT 'pendente',
    data_nota DATE,
    categoria VARCHAR,
    plano_ajustado VARCHAR,
    nivel_plano VARCHAR,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_vendas_cliente_cpf ON estudio_2026.vendas (cliente_cpf);

CREATE TABLE IF NOT EXISTS estudio_2026.vendas_pendentes (
    id SERIAL PRIMARY KEY,
    raw_message VARCHAR,
    cpf VARCHAR,
    nome VARCHAR,
    email VARCHAR,
    profissao VARCHAR,
    aniversario VARCHAR,
    como_conheceu VARCHAR,
    plano VARCHAR,
    valor DOUBLE PRECISION,
    data_venda DATE,
    meio_pagto VARCHAR,
    parcelas INTEGER,
    status VARCHAR DEFAULT 'aguardando_aprovacao',
    data_nota DATE,
    categoria VARCHAR,
    mensagens_buffer_ids VARCHAR,
    plano_ajustado VARCHAR,
    nivel_plano VARCHAR,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS estudio_2026.mensagens_buffer (
    id SERIAL PRIMARY KEY,
    texto VARCHAR NOT NULL,
    processada BOOLEAN DEFAULT FALSE,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

-- --------------------------------------------------------
-- TRIGGERS
-- --------------------------------------------------------

DROP TRIGGER IF EXISTS update_clientes_atualizado_em ON estudio_2026.clientes;
CREATE TRIGGER update_clientes_atualizado_em
BEFORE UPDATE ON estudio_2026.clientes
FOR EACH ROW EXECUTE FUNCTION estudio_2026.update_atualizado_em_column();

DROP TRIGGER IF EXISTS update_vendas_atualizado_em ON estudio_2026.vendas;
CREATE TRIGGER update_vendas_atualizado_em
BEFORE UPDATE ON estudio_2026.vendas
FOR EACH ROW EXECUTE FUNCTION estudio_2026.update_atualizado_em_column();

DROP TRIGGER IF EXISTS update_vendas_pendentes_atualizado_em ON estudio_2026.vendas_pendentes;
CREATE TRIGGER update_vendas_pendentes_atualizado_em
BEFORE UPDATE ON estudio_2026.vendas_pendentes
FOR EACH ROW EXECUTE FUNCTION estudio_2026.update_atualizado_em_column();

DROP TRIGGER IF EXISTS update_mensagens_buffer_atualizado_em ON estudio_2026.mensagens_buffer;
CREATE TRIGGER update_mensagens_buffer_atualizado_em
BEFORE UPDATE ON estudio_2026.mensagens_buffer
FOR EACH ROW EXECUTE FUNCTION estudio_2026.update_atualizado_em_column();
