import os
import json
from datetime import datetime

def salvar_download(titulo, formato, pasta):
    if os.path.exists("historico.json"):
        with open("historico.json", "r") as f:
            historico = json.load(f)
    else:
        historico = []
    item = {
    "titulo": titulo,
    "formato": formato,
    "pasta": pasta,
    "data": datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    historico.append(item)
    with open("historico.json", "w") as f:
        json.dump(historico, f)

def carregar_historico():
    if os.path.exists("historico.json"):
        with open("historico.json", "r") as f:
            return json.load(f)
    return []

def limpar_historico():
    with open("historico.json", "w") as f:
        json.dump([], f)