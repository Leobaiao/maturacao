import asyncio
import requests
import httpx
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "https://api.gtiapi.workers.dev"

#cria o  objeto "agente" com funcoes do webhook
class AgenteGTI:
    def __init__(self, token, nome=None, timeout=20, debug=False):
        self.token = token
        self.nome = nome or "Agente GTI"
        self.timeout = timeout
        self.debug = debug

        self.numero = None
        self.conectado = False
        self.qrcode = None
        self.status_data = {}

        # Sessão síncrona para requests
        self.session = requests.Session()
        self.session.headers.update({"token": self.token, "Content-Type": "application/json"})

        # Cliente async para asyncio
        self.client = httpx.AsyncClient(timeout=timeout, headers={"token": self.token, "Content-Type": "application/json"})

        # Atualiza status inicial
        self.atualizar_status()

    # ======================== STATUS ========================
    def atualizar_status(self):
        try:
            resp = self.session.get(f"{BASE_URL}/instance/status", timeout=self.timeout)
            data = resp.json()
            self.numero = data.get("instance", {}).get("owner")
            self.conectado = data.get("status", {}).get("connected", False)
            self.qrcode = data.get("instance", {}).get("qrcode", "")
            self.status_data = data
        except Exception as e:
            print(f"[{self.nome}] Erro ao atualizar status: {e}")
            self.conectado = False

    async def atualizar_status_async(self):
        try:
            resp = await self.client.get(f"{BASE_URL}/instance/status")
            data = resp.json()
            self.numero = data.get("instance", {}).get("owner")
            self.conectado = data.get("status", {}).get("connected", False)
            self.qrcode = data.get("instance", {}).get("qrcode", "")
            self.status_data = data
        except Exception as e:
            print(f"[{self.nome}] Erro async ao atualizar status: {e}")
            self.conectado = False

    # ======================== ENVIAR MENSAGEM ========================
    def enviar_mensagem(self, numero, mensagem, mentions=""):
        if not mensagem:
            print(f"[{self.nome}] Mensagem vazia. Abortando envio.")
            return None
        payload = {
            "number": str(numero),
            "text": str(mensagem),
            "linkPreview": False,
            "replyid": str(mentions),
            "mentions": "",
            "readchat": True,
            "delay": 0
        }
        try:
            resp = self.session.post(f"{BASE_URL}/send/text", json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"[{self.nome}] Erro ao enviar mensagem: {e}")
            return None

    def verificar_webhook(self):
        try:
            resp = self.session.get(f"{BASE_URL}/webhook", timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"[{self.nome}] Erro ao enviar mensagem: {e}")
            return None

    def apagar_webhook(self):
        data = self.verificar_webhook()
        if data:
            id = data[0].get("id")
            payload = {
                "enabled": False,
                "url": 'webhook',
                "events": [
                    "messages",
                    "messages_update"
                ],
                "excludeMessages": [
                    "fromMeYes"
                ],
                "addUrlEvents": True,
                "addUrlTypesMessages": True,
                "action": "delete",
                "id": id
            }
            try:
                resp = self.session.post(f"{BASE_URL}/webhook", json=payload, timeout=self.timeout)
                resp.raise_for_status()
                print(f"webhook do {self.nome} apagado")
                return resp.json()
            except requests.RequestException as e:
                print(f"[{self.nome}] Erro ao atualizar webhook: {e}")
                return None
        else:
            return None
    def atualizar_webhook(self, webhook):
        payload ={
                "enabled": True,
                "url": webhook,
                "events": [
                    "connection",
                    "history",
                    "messages",
                    "messages_update",
                    "call",
                    "contacts",
                    "presence",
                    "groups",
                    "labels",
                    "chats",
                    "chat_labels",
                    "blocks",
                    "leads"
                ],
                "excludeMessages": [
                    "wasSentByApi",
                    "wasNotSentByApi",
                    "fromMeYes"
                ],
                "addUrlEvents": True,
                "addUrlTypesMessages": True,
                "action": "add"
            }
        try:
            resp = self.session.post(f"{BASE_URL}/webhook", json=payload, timeout=self.timeout)
            resp.raise_for_status()
            print(f"webhook do {self.nome} atualizado para {webhook}")
            return resp.json()
        except requests.RequestException as e:
            print(f"[{self.nome}] Erro ao atualizar webhook: {e}")
            return None

    async def enviar_mensagem_async(self, numero, mensagem, mentions=""):
        if not mensagem:
            print(f"[{self.nome}] Mensagem vazia. Abortando envio.")
            return None
        payload = {
            "number": str(numero),
            "text": str(mensagem),
            "linkPreview": False,
            "replyid": "",
            "mentions": str(mentions),
            "readchat": True,
            "delay": 0
        }
        try:
            resp = await self.client.post(f"{BASE_URL}/send/text", json=payload)
            resp.raise_for_status()
            return True, resp.json()
        except httpx.RequestError as e:
            print(f"[{self.nome}] Erro async ao enviar mensagem: {e}")
            return False, None


    # ======================== DESCONEXÃO ========================
    def desconectar(self):
        try:
            resp = self.session.post(f"{BASE_URL}/instance/disconnect", timeout=self.timeout)
            resp.raise_for_status()
            self.atualizar_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"[{self.nome}] Erro ao desconectar: {e}")
            return None

    async def desconectar_async(self):
        try:
            resp = await self.client.post(f"{BASE_URL}/instance/disconnect")
            resp.raise_for_status()
            await self.atualizar_status_async()
            return resp.json()
        except httpx.RequestError as e:
            print(f"[{self.nome}] Erro async ao desconectar: {e}")
            return None

    # ======================== DADOS ========================
    def dados(self):
        print(f"{self.nome} | Número: {self.numero} | Conectado: {self.conectado}")

# ======================== FUNÇÕES PARA VÁRIOS AGENTES ========================
async def atualizar_status_parallel(agentes):
    tasks = [ag.atualizar_status_async() for ag in agentes]
    await asyncio.gather(*tasks, return_exceptions=True)

def enviar_mensagens_parallel(agentes, numero, mensagem, max_workers=20):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(ag.enviar_mensagem, numero, mensagem): ag for ag in agentes}
        for f in futures:
            ag = futures[f]
            try:
                f.result()
            except Exception as e:
                print(f"[{ag.nome}] Erro paralelo: {e}")


