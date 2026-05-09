from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("TESTE_DATABASE_URL")
engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute(text("SELECT id, nome, mensagens_buffer_ids FROM estudio_2026.vendas_pendentes ORDER BY id DESC LIMIT 5"))
    for row in result:
        print(f"id={row[0]}, nome={row[1]}, mensagens_buffer_ids={row[2]}")
