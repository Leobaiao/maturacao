# Carrega variáveis do .env
import asyncio
import os
import pyodbc
from dotenv import load_dotenv
from GTI.instancia_GTI import AgenteGTI

load_dotenv()

server = os.getenv('SERVER')
database = os.getenv('DATABASE')
username = os.getenv('USERNAMEDB')
password = os.getenv('PASSWORD')
DB = (f"DRIVER={{ODBC Driver 18 for SQL Server}};"
      f"SERVER={server};"
      f"DATABASE={database};"
      f"UID={username};"
      f"PWD={password};"
      f"TrustServerCertificate=yes;")

# Conexão com o banco
conn = pyodbc.connect(DB)

cursor = conn.cursor()

async def carregar_agentes_async_do_banco_async():
    #Carrega agentes do banco de forma assíncrona e cria objetos AgenteGTI em paralelo.

    #Seleciona as instancias que quer maturar
    query = """
        SELECT TELEFONE, SENHA
        FROM [NEWWORK].[dbo].[ROTA]
        WHERE SERVICO='MATURACAO' 
          AND (TIPO_ROTA = 'MATURACAO') AND (TELEFONE LIKE 'web%') 
    """


    try:
        dsn = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={os.getenv("SERVER")};DATABASE={os.getenv("DATABASE")};UID={os.getenv("USERNAMEDB")};PWD={os.getenv("PASSWORD")};TrustServerCertificate=yes;'
        import aioodbc
        async with aioodbc.connect(dsn=dsn, autocommit=True) as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query)
                registros = await cursor.fetchall()
        #cria o agente de acordo com as instancias
        async def criar_agente(telefone_senha):
            telefone, senha = telefone_senha
            agente = AgenteGTI(nome=telefone, token=senha)
            await agente.atualizar_status_async()
            return agente

        # cria todos em paralelo
        agentes = await asyncio.gather(*(criar_agente(r) for r in registros))
        return agentes

    except Exception as e:
        print(f"❌ Erro ao carregar agentes: {e}")
        return []
