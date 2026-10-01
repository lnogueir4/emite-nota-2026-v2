import streamlit as st
import os
from dotenv import load_dotenv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from src.database.db_manager import SessionLocal, VendaPendente, Cliente, Venda
from src.processors.cpf_validator import CPFValidator
from src.processors.email_validator import EmailValidator

load_dotenv()

validador_email = EmailValidator()

USER = os.getenv("STREAMLIT_USER")
PASS = os.getenv("STREAMLIT_PASSWORD")

st.set_page_config(page_title="Emite Nota - Revisão", layout="wide")

def check_password():
    def password_entered():
        if st.session_state["username"] == USER and st.session_state["password"] == PASS:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("### Login")
        st.text_input("Usuário", key="username")
        st.text_input("Senha", type="password", key="password")
        st.button("Entrar", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("### Login")
        st.text_input("Usuário", key="username")
        st.text_input("Senha", type="password", key="password")
        st.button("Entrar", on_click=password_entered)
        st.error("Usuário/senha incorreto.")
        return False
    return True

if not check_password():
    st.stop()

st.title("Revisão de Vendas Capturadas")

col1, col2 = st.columns([6, 1])
with col1:
    st.write("Abaixo estão as vendas extraídas automaticamente pelo Agente IA. Confira os dados, corrija se necessário e aprove.")
with col2:
    if st.button("🔄 Recarregar"):
        st.rerun()

# Sempre cria uma session nova e fecha ao final — garante dados frescos
session = SessionLocal()
try:
    pendentes = session.query(VendaPendente).filter(VendaPendente.status == "aguardando_aprovacao").all()

except Exception as e:
    st.error(f"Erro ao conectar ao banco: {e}")
    session.close()
    st.stop()

if not pendentes:
    session.close()
    st.info("Não há vendas aguardando aprovação no momento.")
else:
    for p in pendentes:
        with st.expander(f"{p.nome} - {p.data_venda} - R$ {p.valor}", expanded=True):
            st.markdown("**Mensagem Original:**")
            msg_sequencial = str(p.raw_message).replace('\n', ' ').replace('\r', '')
            st.info(msg_sequencial)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                cpf = st.text_input("CPF", value=str(p.cpf) if p.cpf else "", key=f"cpf_{p.id}")
                nome = st.text_input("Nome", value=str(p.nome) if p.nome else "", key=f"nome_{p.id}")
                email = st.text_input("E-mail", value=str(p.email) if p.email else "", key=f"email_{p.id}")
                if email.strip() and not validador_email.validate(email):
                    sugestao = validador_email.sugestao(email)
                    st.warning(f"E-mail inválido. Seria {sugestao}?" if sugestao else "E-mail inválido (use um único endereço).")
            with col2:
                profissao = st.text_input("Profissão", value=str(p.profissao) if p.profissao else "", key=f"prof_{p.id}")
                aniversario = st.text_input("Aniversário", value=str(p.aniversario) if p.aniversario else "", key=f"aniv_{p.id}")
                como_conheceu = st.text_input("Como Conheceu", value=str(p.como_conheceu) if p.como_conheceu else "", key=f"como_{p.id}")
            with col3:
                plano = st.text_input("Plano", value=str(p.plano) if p.plano else "", key=f"plano_{p.id}")
                valor = st.number_input("Valor", value=float(p.valor) if p.valor else 0.0, key=f"valor_{p.id}")
                data_venda = st.date_input("Data Venda", value=p.data_venda, key=f"data_{p.id}")
                meio_pagto = st.text_input("Meio Pagto", value=str(p.meio_pagto) if p.meio_pagto else "", key=f"meio_{p.id}")
                parcelas = st.number_input("Parcelas", value=int(p.parcelas) if p.parcelas else 1, key=f"parc_{p.id}")
            with col4:
                categoria = st.text_input("Categoria", value=str(p.categoria) if p.categoria else "", key=f"cat_{p.id}")
                plano_ajustado = st.text_input("Plano Ajustado", value=str(p.plano_ajustado) if p.plano_ajustado else "", key=f"plano_aj_{p.id}")
                nivel_plano = st.text_input("Nível do Plano", value=str(p.nivel_plano) if p.nivel_plano else "", key=f"nivel_{p.id}")
            
            c1, c2 = st.columns([1, 5])
            with c1:
                if st.button("Aprovar Venda", key=f"btn_aprov_{p.id}", type="primary"):
                    validador = CPFValidator()
                    if not validador.validate(cpf):
                        st.error("CPF inválido! Por favor corrija o CPF antes de aprovar.")
                    elif email.strip() and not validador_email.validate(email):
                        st.error("E-mail inválido! Por favor corrija o e-mail antes de aprovar.")
                    else:
                        email = validador_email.clean(email)
                        cliente = session.query(Cliente).filter(Cliente.cpf == cpf).first()
                        if not cliente:
                            cliente = Cliente(cpf=cpf, nome=nome, email=email, profissao=profissao, aniversario=aniversario, como_conheceu=como_conheceu)
                            session.add(cliente)
                        else:
                            cliente.nome = nome
                            cliente.email = email
                            cliente.profissao = profissao
                            cliente.aniversario = aniversario
                            cliente.como_conheceu = como_conheceu
                        
                        venda = Venda(
                            cliente_cpf=cpf,
                            plano=plano,
                            valor=valor,
                            data_venda=data_venda,
                            meio_pagto=meio_pagto,
                            parcelas=parcelas,
                            categoria=categoria,
                            plano_ajustado=plano_ajustado,
                            nivel_plano=nivel_plano,
                            status="pendente"
                        )
                        session.add(venda)
                        
                        p.status = "aprovada"
                        session.commit()
                        st.success("Venda Aprovada com sucesso! Atualize a página.")
                        st.rerun()
            with c2:
                if st.button("Rejeitar / Descartar", key=f"btn_rej_{p.id}"):
                    p.status = "rejeitada"
                    session.commit()
                    st.warning("Venda Descartada.")
                    st.rerun()

session.close()
