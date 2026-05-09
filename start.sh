#!/bin/bash
# Inicia a API FastAPI em background na porta 8502
uvicorn api:app --host 0.0.0.0 --port 8502 &

# Inicia o Streamlit em foreground na porta 8501
exec streamlit run app_revisao.py --server.port=8501 --server.address=0.0.0.0
