import sys
import os
from pathlib import Path
import openpyxl
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.db_manager import SessionLocal, Cliente, Venda, init_db

def _parse_date(val):
    if not val: return None
    if isinstance(val, datetime): return val.date()
    try:
        return datetime.strptime(str(val).split()[0], "%d/%m/%Y").date()
    except:
        pass
    try:
        return datetime.strptime(str(val).split()[0], "%Y-%m-%d").date()
    except:
        return None

def migrate():
    print("Iniciando migração...")
    init_db()
    
    file_path = Path(__file__).parent.parent.parent / "Vendas-estudio-new.xlsx"
    if not file_path.exists():
        print(f"Arquivo não encontrado: {file_path}")
        return

    wb = openpyxl.load_workbook(file_path, data_only=True)
    session = SessionLocal()
    
    print("Lendo Pag1...")
    if 'Pag1' in wb.sheetnames:
        sheet = wb['Pag1']
        headers = [str(cell.value).lower().strip() if cell.value else f"col_{i}" for i, cell in enumerate(sheet[1])]
        
        for row in sheet.iter_rows(min_row=2, values_only=True):
            if not row or not any(row): continue
            
            row_data = dict(zip(headers, row))
            cpf = str(row_data.get('cpf', '')).strip()
            if not cpf or cpf == 'None': continue
            
            # Upsert Cliente
            cliente = session.query(Cliente).filter(Cliente.cpf == cpf).first()
            if not cliente:
                cliente = Cliente(
                    cpf=cpf,
                    nome=str(row_data.get('nome', '')),
                    email=str(row_data.get('email', '')),
                    profissao=str(row_data.get('profissao', '')),
                    aniversario=str(row_data.get('aniversario', '')),
                    como_conheceu=str(row_data.get('como_conheceu', ''))
                )
                session.add(cliente)
                session.commit()
            
            # Inserir Venda
            valor_raw = row_data.get('valor', 0)
            try:
                valor = float(valor_raw) if valor_raw else 0.0
            except:
                valor = 0.0
                
            parcelas_raw = row_data.get('parcelas', 1)
            try:
                parcelas = int(parcelas_raw) if parcelas_raw else 1
            except:
                parcelas = 1
                
            data_venda = _parse_date(row_data.get('data_venda')) or datetime.now().date()
            
            num_nota = row_data.get('num_nota')
            num_nota_str = str(num_nota).strip() if num_nota else None
            if num_nota_str == 'None' or num_nota_str == '': num_nota_str = None

            venda = Venda(
                cliente_cpf=cpf,
                plano=str(row_data.get('plano', '')),
                valor=valor,
                data_venda=data_venda,
                meio_pagto=str(row_data.get('meio_pagto', '')),
                parcelas=parcelas,
                num_nota=num_nota_str,
                status="emitida" if num_nota_str else "pendente"
            )
            session.add(venda)
            
        session.commit()
        print("Migração da Pag1 concluída com sucesso!")
        
    session.close()

if __name__ == "__main__":
    migrate()
