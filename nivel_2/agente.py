"""
agente.py — Agente PLD/AML que decide quais ferramentas consultar
para cada cliente, usando function calling nativo do Gemini
(SDK google-genai).

O agente recebe o cliente_id e as flags já calculadas pelas regras
determinísticas (Nível 1/2), e decide de forma autônoma quais
ferramentas de tools.py chamar antes de produzir o parecer final.
"""

import os
import json
import time

from google import genai
from google.genai import types
from dotenv import load_dotenv

from tools import historico_cliente, operacoes_do_dia, perfil_canal

load_dotenv()
_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

MODELO = "gemini-3.6-flash"
MAX_ITERACOES = 4

# Mapa nome -> função Python real, para executar o que o modelo pedir
_FERRAMENTAS_DISPONIVEIS = {
    "historico_cliente": historico_cliente,
    "operacoes_do_dia": operacoes_do_dia,
    "perfil_canal": perfil_canal,
}

_SYSTEM_INSTRUCTION = """
Você é um analista de Prevenção à Lavagem de Dinheiro (PLD) de um banco.

Você recebe o cliente_id e as flags já calculadas por regras
determinísticas (fracionamento e valor atípico). Essas flags são
confiáveis e não devem ser recalculadas por você: se necessário, 
use-as como gatilho para alguma ferramenta.

Você tem 3 ferramentas disponíveis: historico_cliente, operacoes_do_dia
e perfil_canal. Chamar todas elas sempre, para todo cliente, não é
investigação, é desperdício de chamadas — decida caso a caso, com base
no que cada resposta revela, não num roteiro fixo. 

Responda SOMENTE com um JSON
válido (sem markdown, sem texto adicional) com os campos:
{
    "nivel_risco": "baixo/médio/alto",
    "tipologia_suspeita": "possível tipologia ou ausência de tipologia evidente",
    "red_flags": ["sinal 1", "sinal 2"],
    "justificativa": "justificativa objetiva, mencionando quais ferramentas consultou e por quê — inclusive por que optou por NÃO consultar alguma das outras, se for o caso"
}
"""

_CONFIG_CHAT = types.GenerateContentConfig(
    system_instruction=_SYSTEM_INSTRUCTION,
    tools=[historico_cliente, operacoes_do_dia, perfil_canal],
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
)


def _parsear_parecer(texto: str) -> dict:
    """Tenta extrair um JSON válido da resposta final do modelo."""
    texto_limpo = texto.strip()
    if texto_limpo.startswith("```"):
        texto_limpo = texto_limpo.strip("`")
        texto_limpo = texto_limpo.replace("json\n", "", 1).strip()
    try:
        return json.loads(texto_limpo)
    except json.JSONDecodeError:
        return {
            "erro": "resposta do modelo não é um JSON válido",
            "resposta_bruta": texto,
        }


def avaliar_cliente(cliente_id: str, flags: dict) -> dict:
    """Roda o agente para um cliente, retornando o parecer final
    e metadados de execução (ferramentas chamadas, tokens, latência).
    """
    chat = _client.chats.create(model=MODELO, config=_CONFIG_CHAT)

    contexto_inicial = (
        f"cliente_id: {cliente_id}\n"
        f"flags detectadas pelas regras determinísticas: "
        f"{json.dumps(flags, ensure_ascii=False)}\n\n"
        "Se houver alguma flag com valor true, acione as ferramentas adequadas"
        "e produza o parecer. Caso todas as flags sejam false, não há indício "
        "determinístico que justifique investigação adicional."
    )

    ferramentas_chamadas = []
    inicio = time.time()
    tokens_total = 0

    resposta = chat.send_message(contexto_inicial)
    tokens_total += resposta.usage_metadata.total_token_count

    for _ in range(MAX_ITERACOES):
        function_calls = resposta.function_calls or []

        if not function_calls:
            # Modelo não pediu mais ferramentas: resposta final
            break

        partes_resultado = []
        for chamada in function_calls:
            nome_funcao = chamada.name
            argumentos = dict(chamada.args)
            ferramentas_chamadas.append({"ferramenta": nome_funcao, "argumentos": argumentos})

            funcao = _FERRAMENTAS_DISPONIVEIS.get(nome_funcao)
            if funcao is None:
                resultado = {"erro": f"ferramenta desconhecida: {nome_funcao}"}
            else:
                resultado = funcao(**argumentos)

            partes_resultado.append(
                types.Part.from_function_response(
                    name=nome_funcao,
                    response={"resultado": resultado},
                )
            )

        resposta = chat.send_message(partes_resultado)
        tokens_total += resposta.usage_metadata.total_token_count

    latencia_segundos = round(time.time() - inicio, 2)
    texto_final = resposta.text
    parecer = _parsear_parecer(texto_final)

    return {
        "cliente_id": cliente_id,
        "parecer": parecer,
        "ferramentas_chamadas": ferramentas_chamadas,
        "tokens_total": tokens_total,
        "latencia_segundos": latencia_segundos,
    }


def _flags_do_cliente(cliente_id: str) -> dict:
    """Extrai do histórico do cliente só as flags
    para servir de contexto inicial ao agente (sem repetir todo o
    histórico bruto na mensagem).
    """
    resumo = historico_cliente(cliente_id)
    return {
        "flag_fracionamento": bool(resumo.get("datas_fracionamento")),
        "flag_valores_atipicos": bool(resumo.get("datas_atipicas")),
    }


if __name__ == "__main__":
    # Teste rápido manual com um cliente real da base.
    cliente_teste = "CLI-004"
    flags = _flags_do_cliente(cliente_teste)
    resultado = avaliar_cliente(cliente_teste, flags)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))