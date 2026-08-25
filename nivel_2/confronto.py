"""
confronto.py — Parte D: Confronto entre regra e modelo.

Compara o nivel_risco atribuído pelo agente a cada cliente do top 10
com o nível de risco que as regras determinísticas apontariam para
esse mesmo cliente, usando um critério de correspondência explícito.

Critério de correspondência (regra -> nível de risco esperado):
  - Fracionamento E pelo menos 1 valor atípico  -> "alto"
    (dois sinais independentes reforçando um ao outro)
  - Só fracionamento, OU 2+ valores atípicos    -> "médio"
    (um sinal mais estrutural, ou vários sinais isolados)
  - Só 1 valor atípico (isolado)                -> "baixo"
    (pode ser apenas ruído estatístico natural em torno da mediana)
  - Nenhuma sinalização                          -> "baixo"

Este é um critério de "soma de evidências", coerente com o espírito
das próprias regras (mais sinais simultâneos = maior suspeita), mas
é uma escolha nossa — outros critérios razoáveis existem. Ver
DECISOES.md para a justificativa completa.
"""

import json
import pandas as pd

from pathlib import Path
from tools import historico_cliente

_DIR_OUTPUTS = Path(__file__).resolve().parent.parent / "outputs"


def risco_esperado_pela_regra(cliente_id: str) -> dict:
    """Aplica o critério de correspondência às flags determinísticas
    de um cliente, retornando o nível de risco esperado e o motivo.
    """
    resumo = historico_cliente(cliente_id)
    tem_fracionamento = bool(resumo.get("possui_flag_fracionamento"))
    n_atipicos = int(resumo.get("quantidade_valores_atipicos", 0))

    if tem_fracionamento and n_atipicos >= 1:
        nivel = "alto"
        motivo = "fracionamento confirmado e ao menos um valor atípico"
    elif tem_fracionamento or n_atipicos >= 2:
        nivel = "médio"
        if tem_fracionamento:
            motivo = "fracionamento confirmado, sem valores atípicos"
        else:
            motivo = f"{n_atipicos} valores atípicos, sem fracionamento"
    elif n_atipicos == 1:
        nivel = "baixo"
        motivo = "apenas um valor atípico isolado, sem fracionamento"
    else:
        nivel = "baixo"
        motivo = "nenhuma sinalização determinística"

    return {
        "cliente_id": cliente_id,
        "nivel_risco_regra": nivel,
        "motivo_regra": motivo,
        "flag_fracionamento": tem_fracionamento,
        "quantidade_valores_atipicos": n_atipicos,
    }

# aqui nao podemos assumir que teremos esses arquivos em  _DIR_OUTPUTS 
# vamos ter que mudar para obter o parecer de outra forma
def _carregar_parecer_agente(cliente_id: str) -> dict:
    caminho = _DIR_OUTPUTS / f"parecer_{cliente_id}.json"
    if not caminho.exists():
        return {"nivel_risco": None, "justificativa": None, "erro": "parecer não encontrado"}
    with open(caminho, "r", encoding="utf-8") as f:
        resultado = json.load(f)
    return {
        "nivel_risco": resultado.get("parecer", {}).get("nivel_risco"),
        "tipologia_suspeita": resultado.get("parecer", {}).get("tipologia_suspeita"),
        "justificativa": resultado.get("parecer", {}).get("justificativa"),
    }


def rodar_confronto(caminho_top10: str = None) -> pd.DataFrame:
    caminho_top10 = caminho_top10 or (_DIR_OUTPUTS / "top10_sinalizados.csv")
    top10 = pd.read_csv(caminho_top10)

    linhas = []
    for cliente_id in top10["cliente_id"]:
        regra = risco_esperado_pela_regra(cliente_id)
        agente = _carregar_parecer_agente(cliente_id)

        nivel_regra = regra["nivel_risco_regra"]
        nivel_agente = agente["nivel_risco"]
        concordou = (nivel_regra == nivel_agente) if nivel_agente else None

        linhas.append({
            "cliente_id": cliente_id,
            "nivel_risco_regra": nivel_regra,
            "motivo_regra": regra["motivo_regra"],
            "nivel_risco_agente": nivel_agente,
            "tipologia_agente": agente.get("tipologia_suspeita"),
            "justificativa_agente": agente.get("justificativa"),
            "concordou": concordou,
        })

    df_confronto = pd.DataFrame(linhas)
    df_confronto.to_csv(_DIR_OUTPUTS / "confronto.csv", index=False)
    return df_confronto


def analisar_divergencias(df_confronto: pd.DataFrame) -> dict:
    """Calcula a taxa de concordância e isola as linhas divergentes
    para leitura manual (a interpretação de quem 'está certo' exige
    julgamento humano, não é automatizável).
    """
    avaliaveis = df_confronto[df_confronto["nivel_risco_agente"].notna()]
    taxa_concordancia = (
        float(avaliaveis["concordou"].mean()) if len(avaliaveis) > 0 else None
    )

    divergencias = avaliaveis[~avaliaveis["concordou"]][
        [
            "cliente_id",
            "nivel_risco_regra",
            "motivo_regra",
            "nivel_risco_agente",
            "justificativa_agente",
        ]
    ]

    resumo = {
        "total_clientes_avaliados": int(len(avaliaveis)),
        "taxa_concordancia": round(taxa_concordancia, 3) if taxa_concordancia is not None else None,
        "total_divergencias": int(len(divergencias)),
        "divergencias": divergencias.to_dict(orient="records"),
    }

    with open(_DIR_OUTPUTS / "confronto_analise.json", "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=2)

    return resumo


if __name__ == "__main__":
    df_resultado = rodar_confronto()
    resumo = analisar_divergencias(df_resultado)

    print(f"Taxa de concordância: {resumo['taxa_concordancia']}")
    print(f"Divergências: {resumo['total_divergencias']} de {resumo['total_clientes_avaliados']}\n")

    for div in resumo["divergencias"]:
        print(f"--- {div['cliente_id']} ---")
        print(f"Regra:  {div['nivel_risco_regra']} ({div['motivo_regra']})")
        print(f"Agente: {div['nivel_risco_agente']}")
        print(f"Justificativa do agente: {div['justificativa_agente']}\n")