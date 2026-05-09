"""
API HTTP para integração com n8n.
Expõe endpoints para receber mensagens do WhatsApp e disparar o processamento do buffer.

Endpoints:
  POST /webhook       → salva mensagem no buffer (chamar do n8n ao receber msg da Evolution API)
  POST /process-buffer → dispara o LLM para processar o buffer acumulado (acionado manualmente via "Processbuffer")

Uso:
  uvicorn api:app --host 0.0.0.0 --port 8502
"""
import logging
import os
import threading
from fastapi import FastAPI, HTTPException, Header, Request
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from src.parsers.agent_parser import add_message_to_buffer, process_buffer

logger = logging.getLogger(__name__)

app = FastAPI(title="Emite Nota API", version="1.0")

# Chave secreta simples para proteger os endpoints (configure no .env como API_SECRET)
API_SECRET = os.getenv("API_SECRET", "")

# Lock thread-safe: garante que apenas uma execução do /process-buffer ocorra por vez.
# Usar threading.Lock() com acquire(blocking=False) é atomicamente correto —
# ao contrário de uma variável booleana global que tem race condition intrínseca.
_process_lock = threading.Lock()


def _check_secret(x_api_secret: str | None):
    if API_SECRET and x_api_secret != API_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")


class WebhookPayload(BaseModel):
    message: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhook")
async def receive_webhook(payload: WebhookPayload, x_api_secret: str | None = Header(default=None)):
    """
    Recebe uma mensagem bruta do WhatsApp (via n8n) e salva no buffer.
    Corpo JSON: { "message": "texto da mensagem" }
    """
    _check_secret(x_api_secret)
    if not payload.message or not payload.message.strip():
        raise HTTPException(status_code=400, detail="Mensagem vazia")
    try:
        add_message_to_buffer(payload.message.strip())
        return {"status": "ok", "detail": "Mensagem salva no buffer"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process-buffer")
async def trigger_process_buffer(force: bool = False, x_api_secret: str | None = Header(default=None)):
    """
    Dispara o processamento do buffer de mensagens com o LLM.
    Acionado manualmente quando a Andrea digita "Processbuffer" no WhatsApp.

    Usa threading.Lock para garantir que não haja execuções paralelas acidentais.
    Retorna 409 imediatamente se já houver um processamento em andamento.
    """
    _check_secret(x_api_secret)

    if not _process_lock.acquire(blocking=False):
        logger.warning("Tentativa de /process-buffer ignorada: já há um processamento em andamento.")
        return {"status": "skip", "detail": "Processamento já em andamento. Aguarde terminar."}

    def run():
        try:
            process_buffer(force=force)
        except Exception as e:
            logger.error(f"Erro não capturado em process_buffer: {e}", exc_info=True)
        finally:
            _process_lock.release()

    thread = threading.Thread(target=run, daemon=True, name="process-buffer-thread")
    thread.start()
    return {"status": "ok", "detail": "Processamento iniciado em background"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8502)
