import time
import requests
from datetime import datetime
import pytz
import os
import re
import json

# INÍCIO DO KEEP ALIVE (usado no Render.com)
if os.environ.get("RENDER"):
    from keep_alive import keep_alive
    keep_alive()

# CONFIGURAÇÕES DO TELEGRAM
TOKEN = '8390745428:AAHX5Iaahc3AKPVFxYCl7-EQvzSeiivuuvI'
CHAT_ID = '1800974676'
INTERVALO = 5  # segundos entre verificações

# TIMEZONE BRASÍLIA
fuso_brasilia = pytz.timezone("America/Sao_Paulo")

# CONTADORES DE SINAIS POR HORA
sinais_por_hora = {hora: 0 for hora in range(24)}
total_sinais_dia = 0
ultima_hora = datetime.now(fuso_brasilia).hour

# URLS DAS APIS DAS MESAS
MESAS_API = {
    "Brazilian Roulette": "https://api.revesbot.com.br/history/pragmatic-brazilian-roulette",
    "Auto Roulette": "https://api.revesbot.com.br/history/pragmatic-auto-roulette",
    "Immersive Roulette Deluxe": "https://api.revesbot.com.br/history/pragmatic-immersive-roulette-deluxe",
    "Mega Roulette": "https://api.revesbot.com.br/history/pragmatic-mega-roulette",
    "Auto Mega Roulette": "https://api.revesbot.com.br/history/pragmatic-auto-mega-roulette",
    "Evolution Roulette": "https://api.revesbot.com.br/history/evolution-roulette",
    "Evolution Immersive Roulette": "https://api.revesbot.com.br/history/evolution-immersive-roulette",
    "Evolution Auto Roulette VIP": "https://api.revesbot.com.br/history/evolution-auto-roulette-vip",
    "Evolution Roleta ao Vivo": "https://api.revesbot.com.br/history/evolution-roleta-ao-vivo",
    "Evolution Ruleta Bola Rápida EN Vivo": "https://api.revesbot.com.br/history/evolution-ruleta-bola-rapida-en-vivo",
    "Korean Roulette": "https://api.revesbot.com.br/history/pragmatic-korean-roulette"
}

# LINKS DAS MESAS PARA JOGAR
MESAS_LINK = {
    "Brazilian Roulette": "https://www.betano.bet.br/casino/live/games/brazilian-roulette/11354/tables/",
    "Auto Roulette": "https://www.betano.bet.br/casino/live/games/auto-roulette/3502/tables/?entrypoint=1",
    "Immersive Roulette Deluxe": "https://www.betano.bet.br/casino/live/games/immersive-roulette-deluxe/23563/tables/?entrypoint=1",
    "Mega Roulette": "https://www.betano.bet.br/casino/live/games/mega-roulette/3523/tables/?entrypoint=1",
    "Auto Mega Roulette": "https://www.betano.bet.br/casino/live/games/auto-mega-roulette/10842/tables/?entrypoint=1",
    "Evolution Roulette": "https://www.betano.bet.br/casino/live/games/roulette/1526/tables/",
    "Evolution Immersive Roulette": "https://www.betano.bet.br/casino/live/games/immersive-roulette/1527/tables/?entrypoint=1",
    "Evolution Auto Roulette VIP": "https://www.betano.bet.br/casino/live/games/auto-roulette-vip/1539/tables/?entrypoint=1",
    "Evolution Roleta ao Vivo": "https://www.betano.bet.br/casino/live/games/roleta-ao-vivo/7899/tables/?entrypoint=1",
    "Evolution Ruleta Bola Rápida EN Vivo": "https://www.betano.bet.br/casino/live/games/ruleta-bola-rapida-en-vivo/4695/tables/?entrypoint=1",
    "Korean Roulette": "https://www.betano.bet.br/casino/live/games/korean-roulette/11296/tables/"
}

# Fichas mínimas
FICHAS_MINIMAS = {
    "Brazilian Roulette": 0.50,
    "Auto Roulette": 2.50,
    "Immersive Roulette Deluxe": 0.50,
    "Mega Roulette": 0.50,
    "Auto Mega Roulette": 0.50,
    "Evolution Roulette": 2.50,
    "Evolution Immersive Roulette": 5.00,
    "Evolution Auto Roulette VIP": 1.00,
    "Evolution Roleta ao Vivo": 1.00,
    "Evolution Ruleta Bola Rápida EN Vivo": 2.50,
    "Korean Roulette": 0.50
}

# Alvos por número (soma dos dígitos)
ALVO_MAP = {
    1: [1, 10, 19, 28],
    2: [2, 11, 20, 29],
    3: [3, 12, 21, 30],
    4: [4, 13, 22, 31],
    5: [5, 14, 23, 32],
    6: [6, 15, 24, 33],
    7: [7, 16, 25, 34],
    8: [8, 17, 26, 35],
    9: [9, 18, 27, 36]
}

# Inverte o mapeamento: número -> alvo (1..9)
NUMBER_TO_ALVO = {}
for alvo, nums in ALVO_MAP.items():
    for n in nums:
        NUMBER_TO_ALVO[n] = alvo

# Gatilhos ativos guardados: {mesa: {gatilho: dict}}
gatilhos = {}

def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        'chat_id': CHAT_ID,
        'text': mensagem,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            print("[✅ MENSAGEM ENVIADA AO TELEGRAM]")
        else:
            print(f"[❌ ERRO AO ENVIAR TELEGRAM] Código {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"[❌ ERRO ENVIO TELEGRAM] {e}")

def extrair_numeros(json_data):
    try:
        if isinstance(json_data, str):
            return [int(n) for n in re.findall(r'\d+', json_data)]
        elif isinstance(json_data, list):
            return [int(n) for n in json_data if isinstance(n, int)]
        elif isinstance(json_data, dict):
            for chave in ["results", "data", "lastNumbers"]:
                if chave in json_data and isinstance(json_data[chave], list):
                    return [int(n) for n in json_data[chave] if isinstance(n, int)]
            for value in json_data.values():
                if isinstance(value, list) and all(isinstance(n, int) for n in value):
                    return value
        return []
    except Exception as e:
        print(f"[❌ ERRO AO EXTRAIR NÚMEROS] {e}")
        return []

def soma_digitos(n):
    return sum(int(d) for d in str(n))

def processar_numeros(mesa, numeros):
    global gatilhos, total_sinais_dia, sinais_por_hora

    if len(numeros) < 12:
        return

    # Vamos percorrer para achar gatilhos: posição i+1 == i+10
    # (ex: p2 == p11 na sua lógica; índices base 0: p2 = i+1, p11 = i+10)
    n = len(numeros)
    for i in range(n - 11):
        pos_p2 = i + 1
        pos_p11 = i + 10

        if numeros[pos_p2] == numeros[pos_p11]:
            gatilho = numeros[pos_p2]

            # A regra que disse: gatilho deve estar pelo menos 5 sorteios atrás
            if i < 5:
                continue

            # Verificar se gatilho já apareceu em posições mais recentes (0 até i)
            # Se sim, ignorar pois já retornou depois da detecção
            if gatilho in numeros[0:i+1]:
                continue

            # Se gatilho para esta mesa não existe, inicializa
            if mesa not in gatilhos:
                gatilhos[mesa] = {}

            # Se gatilho já salvo, ignorar para evitar duplicidade
            if gatilho in gatilhos[mesa]:
                continue

            # Obter p1 e p12 do momento da detecção
            p1 = numeros[i]
            p12 = numeros[i + 11]

            alvo1 = NUMBER_TO_ALVO.get(p1, None)
            alvo2 = NUMBER_TO_ALVO.get(p12, None)

            if alvo1 is None or alvo2 is None:
                continue

            # Salvar gatilho
            gatilhos[mesa][gatilho] = {
                'p1': p1,
                'p12': p12,
                'alvo1': alvo1,
                'alvo2': alvo2,
                'ativo': True
            }
            print(f"[🎯 NOVO GATILHO SALVO] Mesa {mesa} - Gatilho {gatilho} (p1={p1}, p12={p12}) Alvos: {alvo1}, {alvo2}")

    # Agora, verificar se número mais recente ativa algum gatilho
    recente = numeros[0]
    if mesa in gatilhos and recente in gatilhos[mesa]:
        entrada = gatilhos[mesa][recente]
        if entrada['ativo']:
            entrada['ativo'] = False

            ficha = FICHAS_MINIMAS.get(mesa, 0.0)
            msg = (
                f"🎯 *PADRÃO ENCONTRADO!*\n"
                f"🎰 Mesa: {mesa}\n"
                f"💰 Ficha mínima: R$ {ficha:.2f}\n"
                f"🔜 No próximo: {recente}\n"
                f"🎯 Entrada: {entrada['alvo1']} e {entrada['alvo2']} + Viz + 0.\n"
                f"🎮 Acessar Mesa Ao Vivo:\n"
                f"🔗 {MESAS_LINK.get(mesa, '')}"
            )
            enviar_telegram(msg)

            hora_brasilia = datetime.now(fuso_brasilia).hour
            sinais_por_hora[hora_brasilia] += 1
            total_sinais_dia += 1

def verificar_resultados():
    headers = {"User-Agent": "Mozilla/5.0"}
    for mesa, url in MESAS_API.items():
        print(f"\n🔎 Checando mesa: {mesa}")
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                json_data = response.json()
                numeros = extrair_numeros(json_data)
                print(f"📊 Últimos números (mais recente à esquerda): {numeros[:15]}")
                processar_numeros(mesa, numeros)
            else:
                print(f"[⚠️ ERRO API] Código {response.status_code} na mesa {mesa}")
        except Exception as e:
            print(f"[❌ ERRO CONEXÃO] Mesa {mesa}: {e}")

def checar_relatórios_horarios():
    global ultima_hora, sinais_por_hora, total_sinais_dia
    agora = datetime.now(fuso_brasilia)
    hora_atual = agora.hour
    minuto = agora.minute

    if minuto == 0 and hora_atual != ultima_hora:
        hora_passada = (hora_atual - 1) % 24
        enviados = sinais_por_hora[hora_passada]
        mensagem = f"📈 Sinais enviados entre {hora_passada:02d}:00 e {hora_atual:02d}:00: {enviados}"
        enviar_telegram(mensagem)

        if hora_atual == 22:
            horas_validas = [v for v in sinais_por_hora.values() if v > 0]
            media = total_sinais_dia / len(horas_validas) if horas_validas else 0
            resumo = f"📊 Média de sinais hoje: *{media:.2f} por hora* ({total_sinais_dia} no total)."
            enviar_telegram(resumo)

            sinais_por_hora = {hora: 0 for hora in range(24)}
            total_sinais_dia = 0
            print("[🔁 CONTADORES REINICIADOS PARA O NOVO DIA]")

        ultima_hora = hora_atual

print("[🤖 BOT INICIADO] Monitorando mesas...")
enviar_telegram("🤖 Bot de Gatilhos iniciado com sucesso!")

while True:
    verificar_resultados()
    checar_relatórios_horarios()
    time.sleep(INTERVALO)
