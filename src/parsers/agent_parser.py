"""
Módulo de parsing e processamento do buffer de mensagens WhatsApp.

Responsabilidades:
  - add_message_to_buffer(): salva mensagem bruta no banco
  - process_buffer(): chama LLM, extrai vendas, valida CPF, notifica via WhatsApp
"""
import os
import json
import logging
import sys
import requests
from pathlib import Path
from datetime import datetime, date, timezone
from pydantic import BaseModel, Field
from typing import Optional, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.database.db_manager import SessionLocal, VendaPendente, MensagensBuffer
from src.processors.cpf_validator import CPFValidator
from config.settings import CATEGORIA_MAPPING
from dotenv import load_dotenv

load_dotenv()

# ── Logging estruturado ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── LLM imports opcionais ────────────────────────────────────────────────────
from langchain_openai import ChatOpenAI
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None
try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None
try:
    from langchain_groq import ChatGroq
except ImportError:
    ChatGroq = None

# ── Evolution API (notificação WhatsApp) ────────────────────────────────────
_EVOLUTION_URL      = os.getenv("EVOLUTION_URL", "")
_EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "")
_EVOLUTION_KEY      = os.getenv("EVOLUTION_KEY", "")
_PHONE       = os.getenv("PHONE", "")

_cpf_validator = CPFValidator()


# ── Schemas Pydantic ─────────────────────────────────────────────────────────

class VendaExtraction(BaseModel):
    cpf: str = Field(description="CPF do cliente. Apenas números.")
    nome: str = Field(description="Nome completo do cliente.")
    email: str = Field(description="E-mail do cliente.")
    profissao: str = Field(description="Profissão do cliente.")
    aniversario: str = Field(description="Data de nascimento do cliente. OBRIGATÓRIO padronizar usando barras (DD/MM/AAAA). Ex: 04.08.1982 vira 04/08/1982.")
    como_conheceu: str = Field(description="Resuma OBRIGATORIAMENTE em uma das categorias: 'Indicação', 'Instagram', 'Google', Exemplo: 'Pela Mayara' vira 'Indicação'. 'Rede social' vira 'Instagram'")
    plano: str = Field(description="Pegar da linha 'Fez ensaio...'.")
    valor: float = Field(description="Valor total da venda (float). Se houver '100 no pix e 1130 no cartão', o total é 1230.")
    data_venda: date = Field(description="Data da venda inferida da mensagem (YYYY-MM-DD).")
    meio_pagto: str = Field(description="Meio de pagamento principal (Pix ou Cartão ou Infinity ou Dinheiro) pegar o meio de maior valor. exemplo: 'pg 100 no pix e 570 no cartão em 3x (infiniti', vira Infinity")
    parcelas: int = Field(description="Número de parcelas (ex: 6). À vista é 1.", default=1)
    categoria: str = Field(description="Categoria do ensaio (Gestante, Aniversario, Infantil, Newborn, Familia, Corporativo, Formatura, Natal, Feminino, Mães).", default="")

class VendaExtractionList(BaseModel):
    vendas: List[VendaExtraction] = Field(description="Lista de vendas identificadas nas mensagens.")


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_llm():
    if os.getenv("OPENAI_API_KEY"):
        return ChatOpenAI(model="gpt-5.4-mini", temperature=0)
    elif os.getenv("ANTHROPIC_API_KEY") and ChatAnthropic:
        return ChatAnthropic(model="claude-3-haiku-20240307", temperature=0)
    elif os.getenv("GOOGLE_API_KEY") and ChatGoogleGenerativeAI:
        return ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
    elif os.getenv("GROQ_API_KEY") and ChatGroq:
        return ChatGroq(model="llama3-70b-8192", temperature=0)
    else:
        raise ValueError("Nenhuma chave de API configurada (OPENAI, ANTHROPIC, GOOGLE ou GROQ).")


def inferir_categoria(texto_plano_ou_categoria: str) -> str:
    if not texto_plano_ou_categoria:
        return "Gestante"
    texto = str(texto_plano_ou_categoria).lower()
    for cat_key, aliases in CATEGORIA_MAPPING.items():
        if any(alias in texto for alias in aliases):
            mapping = {
                "corp": "Corporativo", "forma": "Formatura", "fami": "Familia",
                "bday": "Aniversario", "kids": "Infantil", "rn": "Newborn",
                "natal": "Natal", "femi": "Feminino", "mãe": "Mães"
            }
            return mapping.get(cat_key, "Gestante")
    if "gestante" in texto:
        return "Gestante"
    return "Gestante"


def _notify_whatsapp(text: str) -> None:
    """Envia mensagem para o número da Andrea via Evolution API. Falha silenciosa se não configurado."""
    if not all([_EVOLUTION_URL, _EVOLUTION_INSTANCE, _EVOLUTION_KEY, _PHONE]):
        logger.warning("Notificação WhatsApp não configurada (EVOLUTION_URL/INSTANCE/KEY/PHONE ausentes).")
        return
    try:
        resp = requests.post(
            f"{_EVOLUTION_URL}/message/sendText/{_EVOLUTION_INSTANCE}",
            json={"number": _PHONE, "text": text},
            headers={"apikey": _EVOLUTION_KEY},
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("Notificação WhatsApp enviada para Andrea.")
    except Exception as exc:
        logger.error(f"Falha ao enviar notificação WhatsApp: {exc}")


# ── Funções públicas ─────────────────────────────────────────────────────────

def add_message_to_buffer(raw_message: str) -> None:
    """Salva mensagem bruta no buffer de processamento."""
    with SessionLocal() as session:
        buffer = MensagensBuffer(texto=raw_message)
        session.add(buffer)
        session.commit()
    logger.info("Mensagem adicionada ao buffer de processamento.")


def process_buffer(force: bool = False) -> None:
    """
    Lê mensagens não processadas do buffer, chama o LLM para extração estruturada,
    valida CPFs, salva em vendas_pendentes com rastreabilidade e notifica a Andrea via WhatsApp.

    Parâmetros:
        force: aceito por compatibilidade (janela de 15 min removida — processamento sempre manual).
    """
    # ── 1. Buscar IDs e textos das mensagens pendentes ───────────────────────
    with SessionLocal() as session:
        unprocessed = (
            session.query(MensagensBuffer)
            .filter(MensagensBuffer.processada == False)
            .order_by(MensagensBuffer.criado_em.asc())
            .all()
        )

        if not unprocessed:
            logger.info("Nenhuma mensagem não processada no buffer.")
            return

        buffer_ids   = [m.id for m in unprocessed]
        buffer_texts = [m.texto for m in unprocessed]
        buffer_metas = [(m.id, m.criado_em, m.texto) for m in unprocessed]

    logger.info(f"Processando {len(buffer_ids)} mensagens do buffer (IDs: {buffer_ids}).")
    full_text = "\n\n---\n\n".join(
        [f"Mensagem ID {mid} enviada em: {ts}\n{txt}" for mid, ts, txt in buffer_metas]
    )

    # ── 2. Chamar LLM ────────────────────────────────────────────────────────
    try:
        llm = get_llm()
        structured_llm = llm.with_structured_output(VendaExtractionList)

        prompt = f"""Você é um assistente do estúdio fotográfico 'Estudio Andréa Sabbá Fotografia'.
    Abaixo está um log de mensagens do WhatsApp recebidas em sequência. Muitas mensagens são apenas a continuação da anterior e referem-se à mesma pessoa.
    Sua tarefa é analisar o bloco inteiro, agrupar mentalmente as mensagens que pertencem à mesma venda (mesmo cliente) e extrair os dados.

    REGRA CRÍTICA DE AGRUPAMENTO:
    - Se o mesmo cliente (mesmo nome ou CPF) for mencionado em múltiplas mensagens, você deve UNIFICAR as informações em UMA ÚNICA venda.
    - NUNCA crie registros duplicados para a mesma pessoa.

    REGRA CRÍTICA SOBRE O PLANO/ENSAIO:
    - Os clientes preenchem um formulário que pode conter "Tipo de ensaio (plano)" ou apenas "Ensaio X". IGNORE COMPLETAMENTE essa informação que vem junto com o Nome/CPF.
    - O plano e a categoria REAIS e DEFINITIVOS devem ser extraídos EXCLUSIVAMENTE da mensagem que começa com "Fez ensaio ...". É essa mensagem que dita o que foi vendido.

    Hoje é {datetime.now().strftime("%d/%m/%Y")}.
    Calcule o valor total de cada venda somando os pagamentos, determine o meio de pagamento principal (maior valor), parcelas 
    Meio de pagamento principal (Pix ou Cartão ou Infinity ou Dinheiro) pegar o meio de maior valor. exemplo: 'pg 100 no pix e 570 no cartão em 3x (infiniti', vira Infinity"
    e infira a categoria do ensaio baseada EXCLUSIVAMENTE no plano contido na linha "Fez ensaio ...".

    MENSAGENS RAW:
    {full_text}
    """

        result: VendaExtractionList = structured_llm.invoke(prompt)

    except Exception as e:
        logger.error(f"Erro ao processar as mensagens com o LLM: {e}", exc_info=True)
        _notify_whatsapp(f"❌ Erro ao processar buffer de mensagens.\nDetalhe: {e}")
        return

    # ── 3. Salvar vendas + validar CPFs ─────────────────────────────────────
    vendas_salvas = 0
    avisos_cpf: list[str] = []

    raw_msg_resumo = f"Buffer IDs: {buffer_ids}\n\n" + "\n---\n".join(buffer_texts)

    with SessionLocal() as session:
        try:
            for ext_venda in result.vendas:
                categoria_final = ext_venda.categoria or inferir_categoria(ext_venda.plano)

                # Validação de CPF antes de salvar
                cpf_limpo = _cpf_validator.clean(ext_venda.cpf)
                if _cpf_validator.validate(cpf_limpo):
                    cpf_final = cpf_limpo
                else:
                    aviso = f"⚠️ CPF inválido para {ext_venda.nome}: '{ext_venda.cpf}' — deixado em branco para correção manual."
                    logger.warning(aviso)
                    avisos_cpf.append(aviso)
                    cpf_final = ""

                pendente = VendaPendente(
                    raw_message=raw_msg_resumo,
                    mensagens_buffer_ids=json.dumps(buffer_ids),
                    cpf=cpf_final,
                    nome=ext_venda.nome,
                    email=ext_venda.email,
                    profissao=ext_venda.profissao,
                    aniversario=ext_venda.aniversario,
                    como_conheceu=ext_venda.como_conheceu,
                    plano=ext_venda.plano,
                    valor=ext_venda.valor,
                    data_venda=ext_venda.data_venda,
                    meio_pagto=ext_venda.meio_pagto,
                    parcelas=ext_venda.parcelas,
                    categoria=categoria_final,
                    status="aguardando_aprovacao",
                )
                session.add(pendente)
                vendas_salvas += 1

            # Marcar mensagens como processadas
            msgs = (
                session.query(MensagensBuffer)
                .filter(MensagensBuffer.id.in_(buffer_ids))
                .all()
            )
            for msg in msgs:
                msg.processada = True

            session.commit()
            logger.info(f"Sucesso! {vendas_salvas} venda(s) extraída(s) e colocadas na fila de aprovação.")

        except Exception as e:
            session.rollback()
            logger.error(f"Erro ao salvar vendas no banco: {e}", exc_info=True)
            _notify_whatsapp(f"❌ LLM extraiu dados, mas erro ao salvar no banco.\nDetalhe: {e}")
            return

    # ── 4. Notificar Andrea ──────────────────────────────────────────────────
    aviso_cpf_str = ("\n\n" + "\n".join(avisos_cpf)) if avisos_cpf else ""
    _notify_whatsapp(
        f"✅ {vendas_salvas} venda(s) extraída(s) e prontas para revisão."
        f"{aviso_cpf_str}"
    )


if __name__ == "__main__":
    print(get_llm())
