import asyncio
import json
import os
import re
from dbo.dbo import carregar_agentes_async_do_banco_async

HISTORICO_DIR = "historicos"
os.makedirs(HISTORICO_DIR, exist_ok=True)

async def criar_pares(agentes_conectados, pares_atuais=set()):
    # Ordena pelos números do nome
    agentes_ordenados = sorted(agentes_conectados, key=lambda a: extrair_numero(a.nome))

    # Agrupa em pares sequenciais completos
    pares_agentes = [(agentes_ordenados[i], agentes_ordenados[i + 1])
                     for i in range(0, len(agentes_ordenados) - 1, 2)]

    # Filtra apenas pares novos usando ids
    novos_pares = []
    for a1, a2 in pares_agentes:
        chave = (id(a1), id(a2))
        if chave not in pares_atuais:
            novos_pares.append((a1, a2))
            pares_atuais.add(chave)  # marca como em execução

    print(f"Novos pares de agentes detectados: {len(novos_pares)}")
    return novos_pares


def extrair_numero(nome):
    m = re.search(r'\d+', nome)
    return int(m.group()) if m else 0


async def verificar_agentes(agentes):
    agentes_conectados = [ag for ag in agentes if ag.conectado]
    print(f"Agentes conectados: {len(agentes_conectados)}")
    return agentes_conectados


async def carregar_agentes():
    agentes = await carregar_agentes_async_do_banco_async()
    return agentes


def salvar_historico(ag1, ag2, historico: list):
    caminho = os.path.join(HISTORICO_DIR, f"{ag1.nome}_{ag2.nome}.json")
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(historico, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Erro ao salvar histórico de {ag1.nome} com {ag2.nome}: {e}")


def carregar_historico(ag1, ag2):
    caminho = os.path.join(HISTORICO_DIR, f"{ag1.nome}_{ag2.nome}.json")
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Erro ao ler histórico de {ag1.nome} com {ag2.nome}: {e}")
    return []

async def delay_ms_async(min, test_mode=False):
    min *= 60
    await asyncio.sleep(0.1 if test_mode else min)
    return True
