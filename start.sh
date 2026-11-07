#!/bin/bash
# Sobe a API FastAPI (8502) e o painel Streamlit (8501) em paralelo.
# Se qualquer um dos dois morrer, o container encerra com erro para que o
# Swarm o reinicie — antes, a API podia cair em silêncio enquanto o
# Streamlit mantinha o container "saudável" (502 no /webhook do n8n).
uvicorn api:app --host 0.0.0.0 --port 8502 &
streamlit run app_revisao.py --server.port=8501 --server.address=0.0.0.0 &

wait -n
echo "start.sh: um dos processos (uvicorn/streamlit) encerrou; finalizando o container para o Swarm reiniciar." >&2
exit 1
