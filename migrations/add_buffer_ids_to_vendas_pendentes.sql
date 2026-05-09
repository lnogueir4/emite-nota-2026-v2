-- Migration: adiciona coluna mensagens_buffer_ids em vendas_pendentes
-- Executar UMA ÚNICA VEZ no banco de produção.
-- Conexão: docker exec -it <container_banco> psql -U postgres n8n

ALTER TABLE estudio_2026.vendas_pendentes
    ADD COLUMN IF NOT EXISTS mensagens_buffer_ids TEXT DEFAULT NULL;

COMMENT ON COLUMN estudio_2026.vendas_pendentes.mensagens_buffer_ids
    IS 'JSON array com os IDs de mensagens_buffer usados na extração desta venda. Ex: "[1, 2, 3]"';
