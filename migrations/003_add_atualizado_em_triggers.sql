-- 1. Adicionar a coluna na tabela mensagens_buffer se ela não existir
ALTER TABLE estudio_2026.mensagens_buffer 
ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ DEFAULT NOW();

-- 2. Criar a função genérica de trigger
CREATE OR REPLACE FUNCTION estudio_2026.update_atualizado_em_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.atualizado_em = CURRENT_TIMESTAMP;
   RETURN NEW;
END;
$$ language 'plpgsql';

-- 3. Criar os triggers nas 4 tabelas
-- Tabela: clientes
DROP TRIGGER IF EXISTS update_clientes_atualizado_em ON estudio_2026.clientes;
CREATE TRIGGER update_clientes_atualizado_em
BEFORE UPDATE ON estudio_2026.clientes
FOR EACH ROW
EXECUTE FUNCTION estudio_2026.update_atualizado_em_column();

-- Tabela: vendas
DROP TRIGGER IF EXISTS update_vendas_atualizado_em ON estudio_2026.vendas;
CREATE TRIGGER update_vendas_atualizado_em
BEFORE UPDATE ON estudio_2026.vendas
FOR EACH ROW
EXECUTE FUNCTION estudio_2026.update_atualizado_em_column();

-- Tabela: vendas_pendentes
DROP TRIGGER IF EXISTS update_vendas_pendentes_atualizado_em ON estudio_2026.vendas_pendentes;
CREATE TRIGGER update_vendas_pendentes_atualizado_em
BEFORE UPDATE ON estudio_2026.vendas_pendentes
FOR EACH ROW
EXECUTE FUNCTION estudio_2026.update_atualizado_em_column();

-- Tabela: mensagens_buffer
DROP TRIGGER IF EXISTS update_mensagens_buffer_atualizado_em ON estudio_2026.mensagens_buffer;
CREATE TRIGGER update_mensagens_buffer_atualizado_em
BEFORE UPDATE ON estudio_2026.mensagens_buffer
FOR EACH ROW
EXECUTE FUNCTION estudio_2026.update_atualizado_em_column();
