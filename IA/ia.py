import asyncio
import datetime
import random
import types
from http import client
import ollama
from utilis.utils import carregar_historico, salvar_historico, delay_ms_async


def get_ia_response_ollama(user_message, historico=None, prompt_extra=""):
    if not user_message:
        return "🤔 Não entendi sua mensagem."

    historico = historico or []
    if len(historico) > 3:
        resumo = " ".join([m["content"] for m in historico[:-3]])
        historico = historico[-3:]
        historico.insert(0, {
            "role": "system",
            "content": f"Resumo: {resumo[:150]}..."
        })

    mensagens = [{
        "role": "system",
        "content": (
            "Você é um amigo virtual que conversa no WhatsApp.\n"
            "Responda curto, casual, com gírias e emojis.\n"
            "Máx 60 caracteres.\n"
            "Considere o contexto e evite repetir."
        )
    }]

    if prompt_extra:
        mensagens.append({"role": "system", "content": prompt_extra})

    # Converte histórico para o formato correto
    for msg in historico:
        mensagens.append({
            "role": "user" if msg["role"].startswith("agente1") else "assistant",
            "content": msg["content"]
        })

    # Adiciona última fala do usuário
    mensagens.append({"role": "user", "content": user_message})

    try:
        response = ollama.chat(model="TinyLlama", messages=mensagens)
        return (
                response.get("message", {}).get("content", "").strip()
                or "😅 Não consegui pensar em nada agora."
        )
    except Exception as e:
        print(f"⚠️ Erro IA: {e}")
        return "⚠️ Deu ruim aqui 😅"


def get_ia_response_gemini(user_message, historico=None, prompt_extra=""):
    if not user_message:
        return "🤔 Não entendi sua mensagem."

    historico = historico or []

    # Resumo do histórico
    if len(historico) > 3:
        resumo = " ".join([m["content"] for m in historico[:-3]])
        historico = historico[-3:]
        historico.insert(0, {"role": "system", "content": f"Resumo: {resumo[:150]}..."})

    contexto = f"\n".join([f"{m['role']}: {m['content']}" for m in historico])
    prompt = 'Você é um amigo virtual que conversa no WhatsApp.\n Responda curto, casual, com gírias e emojis.\n Máx 60 caracteres.\n Considere o contexto e evite repetir.'
    prompt = prompt + f"{prompt_extra}\n{contexto}\nuser: {user_message}"

    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",  # ou "gemini-2.5-flash"
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0)
            ),
        )
        return response.text.strip()
    except Exception as e:
        print(f"⚠️ Erro IA Gemini: {e}")
        return "⚠️ Deu ruim aqui 😅"


async def conversar_async(agente1, agente2, max_turnos=10, test_mode=False, get_ia_response=get_ia_response_ollama):
    historico = carregar_historico(agente1, agente2)
    print(f"🤖 Iniciando conversa entre {agente1.nome} e {agente2.nome}")

    # Agente 1 inicia
    msg = await asyncio.to_thread(get_ia_response, " ", historico, "Inicie uma conversa casual")
    count1, count2 = 0, 0

    for _ in range(max_turnos):
        # Agente 1 envia
        enviado, resultado = await enviar_mensagem_async(agente1, agente2.numero, msg)
        if not enviado:
            print(f"{agente1.nome} falhou no envio. ({count1} msgs enviadas)")
            print(f"{agente2.nome}: {resultado['message']}")
            break
        historico.append({"role": agente1.nome, "content": msg, "number": agente1.numero,
                          "time": datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")})
        print(f"{agente1.nome}: {msg} → {agente2.nome} {datetime.datetime.now().strftime('%H:%M:%S')}")
        count1 += 1
        salvar_historico(agente1, agente2, historico)
        # já dispara a resposta do agente 2 em paralelo
        tarefa_resposta2 = asyncio.create_task(
            asyncio.to_thread(get_ia_response, msg, historico, "Responda curto e natural (<=80 caracteres)")
        )

        min = random.randint(1, 10)
        print(
            f"Proxima mensagem do {agente2.nome} em {min} minutos para {agente1.nome} {datetime.datetime.now().strftime('%H:%M:%S')}")
        await delay_ms_async(min, test_mode)

        # pega a resposta (se já estiver pronta sai na hora)
        resposta = await tarefa_resposta2
        enviado, resultado = await enviar_mensagem_async(agente2, agente1.numero, resposta)
        if not enviado:
            print(f"{agente2.nome} falhou no envio. ({count2} msgs enviadas)")
            print(f"{agente2.nome}: {resultado['message']}")
            break
        historico.append({"role": agente2.nome, "content": resposta, "number": agente2.numero,
                          "time": datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")})
        print(f"{agente2.nome}: {resposta} → {agente1.nome} {datetime.datetime.now().strftime('%H:%M:%S')}")
        count2 += 1
        salvar_historico(agente1, agente2, historico)
        # já dispara a próxima fala do agente1 em paralelo
        tarefa_resposta1 = asyncio.create_task(
            asyncio.to_thread(get_ia_response, resposta, historico,
                              "Continue a conversa de forma resumida (<=120 caracteres)")
        )

        min = random.randint(1, 10)
        print(
            f"Proxima mensagem do {agente1.nome} em {min} minutos para {agente2.nome} {datetime.datetime.now().strftime('%H:%M:%S')}")
        await delay_ms_async(min, test_mode)

        # pega a próxima fala do agente 1
        msg = await tarefa_resposta1

    print(f"✅ {agente1.nome} enviou {count1} msgs | {agente2.nome} enviou {count2} msgs")
    return True


async def enviar_mensagem_async(agente, numero, mensagem):
    resultado = None
    try:
        bol, resultado = await agente.enviar_mensagem_async(numero, mensagem)

        return bol, resultado
    except Exception as e:
        print(f"[{agente.nome}] Erro ao enviar mensagem async: {e}")
        return False, resultado
