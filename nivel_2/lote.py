# lote.py

import json
from pathlib import Path

import pandas as pd

from agente import avaliar_cliente, _flags_do_cliente


def executar_lote(clientes):
    resultados = []

    for cliente_id in clientes:
        print(f"Processando {cliente_id}...")

        flags = _flags_do_cliente(cliente_id)
        resultado = avaliar_cliente(cliente_id, flags)

        parecer = resultado["parecer"]

        resultados.append({
            "cliente_id": cliente_id,
            "nivel_risco": parecer.get("nivel_risco"),
            "tipologia_suspeita": parecer.get("tipologia_suspeita"),
            "red_flags": json.dumps(
                parecer.get("red_flags", []),
                ensure_ascii=False
            ),
            "justificativa": parecer.get("justificativa"),
            "ferramentas_chamadas": json.dumps(
                resultado["ferramentas_chamadas"],
                ensure_ascii=False
            ),
            "tokens_total": resultado["tokens_total"],
            "latencia_segundos": resultado["latencia_segundos"],
        })

    return pd.DataFrame(resultados)


def salvar_resultados(df_resultados, caminho="outputs/lote.csv"):
    script_dir = Path(__file__).parent
    caminho_final = script_dir.parent / caminho 
    caminho_final.parent.mkdir(parents=True, exist_ok=True)
    df_resultados.to_csv(caminho_final, index=False, encoding="utf-8-sig")
    print(f"\nResultados salvos em: {caminho_final}")


if __name__ == "__main__":

    clientes = [
        "CLI-014",
        "CLI-023",
        "CLI-028",
        "CLI-013",
        "CLI-005",
    ]

    df_resultados = executar_lote(clientes)

    salvar_resultados(df_resultados)