"""
tools.py — Ferramentas de consulta à base de operações para o agente PLD/AML.

Cada função retorna um dicionário serializável (JSON-friendly), pensado
para ser consumido por um agente baseado em LLM.
"""

import pandas as pd
import json

from pathlib import Path

# Carrega e trata a base uma única vez, no import do módulo.
_CAMINHO_DADOS = Path(__file__).resolve().parent.parent / "dados" / "dados_nivel_2.json"


def validar_estrutura_operacoes(operacoes: list[dict]) -> None:
    """Valida se todas as operações têm o mesmo conjunto de chaves.
    Levanta ValueError com o detalhe das inconsistências encontradas.
    """
    if not operacoes:
        raise ValueError("A lista de operações está vazia.")

    chaves_esperadas = set(operacoes[0].keys())
    inconsistencias = []

    for i, operacao in enumerate(operacoes):
        chaves = set(operacao.keys())
        if chaves != chaves_esperadas:
            inconsistencias.append({
                "indice": i,
                "faltando": sorted(chaves_esperadas - chaves),
                "a_mais": sorted(chaves - chaves_esperadas),
            })

    if inconsistencias:
        raise ValueError(f"Operações com estrutura inconsistente: {inconsistencias}")


def _carregar_base() -> pd.DataFrame:
    """Carrega e trata a base de operações a partir do JSON de entrada.

    Etapas aplicadas:
    - Remove linhas duplicadas.
    - Converte valores para USD->BRL usando a taxa de câmbio informada
      no arquivo, gerando a coluna valor_brl.
    - Converte a coluna 'data' para datetime, coagindo datas inválidas
      para NaT em vez de falhar (ver DECISOES.md).
    - Calcula flag_fracionamento (Regra 1) e flag_valor_atipico
      (Regra 2), reaproveitando a lógica validada no Nível 1.
    - Adiciona a coluna datas_fracionamento com as datas em que cada
      cliente disparou a Regra 1, necessária para as ferramentas do
      agente conseguirem consultar operacoes_do_dia sem inventar datas.

    Executada uma única vez no import do módulo (ver _df, abaixo).
    """
    with open(_CAMINHO_DADOS, "r", encoding="utf-8") as f:
        dados = json.load(f)

    TAXA_CAMBIO = float(dados["taxa_cambio_usd_brl"])
    operacoes = dados["operacoes"]

    validar_estrutura_operacoes(operacoes)

    df = pd.DataFrame(operacoes)
    df = df.drop_duplicates(keep="first")
    df["valor"] = df["valor"].astype(float)
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df["valor_brl"] = df["valor"]
    df.loc[df["moeda"] == "USD", "valor_brl"] = (
        df.loc[df["moeda"] == "USD", "valor"] * TAXA_CAMBIO
    )

    # --- Regra 1: fracionamento (flag em nível de cliente) ---
    fracionamento = (
        df.groupby(["cliente_id", "data"])
          .agg(
              quantidade_operacoes=("id", "count"),
              soma_valor_brl=("valor_brl", "sum"),
              maior_operacao_brl=("valor_brl", "max"),
          )
          .reset_index()
    )
    fracionamento["fracionamento"] = (
        (fracionamento["quantidade_operacoes"] >= 3)
        & (fracionamento["soma_valor_brl"] > 50_000)
        & (fracionamento["maior_operacao_brl"] < 20_000)
    )
    clientes_fracionamento = (
        fracionamento.loc[fracionamento["fracionamento"], "cliente_id"].unique()
    )
    df["flag_fracionamento"] = df["cliente_id"].isin(clientes_fracionamento)


    datas_fracionamento_por_cliente = (
        fracionamento.loc[fracionamento["fracionamento"]]
        .assign(data_str=lambda t: t["data"].dt.strftime("%Y-%m-%d"))
        .groupby("cliente_id")["data_str"]
        .apply(lambda s: sorted(s.tolist()))
        .rename("datas_fracionamento")
    )
    df = df.merge(datas_fracionamento_por_cliente, on="cliente_id", how="left")
    # Clientes sem fracionamento ficam com NaN no merge; troca por lista vazia.
    df["datas_fracionamento"] = df["datas_fracionamento"].apply(
        lambda v: v if isinstance(v, list) else []
    )

    # --- Regra 2: valor atípico (flag em nível de operação) ---
    estatisticas_cliente = (
        df.groupby("cliente_id")["valor_brl"]
          .agg(quantidade_operacoes="count", mediana_brl="median")
          .reset_index()
    )
    estatisticas_cliente["5x_mediana_brl"] = 5 * estatisticas_cliente["mediana_brl"]
    df = df.merge(estatisticas_cliente, on="cliente_id", how="left")
    df["flag_valor_atipico"] = (
        (df["quantidade_operacoes"] >= 4)
        & (df["valor_brl"] > df["5x_mediana_brl"])
    )

    return df


_df = _carregar_base()


def historico_cliente(cliente_id: str) -> dict:
    """Resumo agregado das operações de um cliente: quantidade,
    volume, mediana de valores, diversidade de canais e contrapartes,
    as flags de fracionamento e valor atípico já calculadas, e as
    datas em que cada uma delas foi disparada.
    """
    df_cliente = _df[_df["cliente_id"] == cliente_id]
 
    if df_cliente.empty:
        return {"cliente_id": cliente_id, "erro": "cliente não encontrado na base"}
 
    df_atipicas = df_cliente[df_cliente["flag_valor_atipico"]]
    datas_atipicas = [
        str(row["data"].date()) if pd.notna(row["data"]) else None
        for _, row in df_atipicas.iterrows()
    ]
 
    volume_total_brl = float(df_cliente["valor_brl"].sum())
    volume_nan_brl = float(df_cliente[df_cliente["data"].isna()]["valor_brl"].sum())
    percent_nan = (volume_nan_brl / volume_total_brl) if volume_total_brl > 0 else 0.0
 
    return {
        "cliente_id": cliente_id,
        "quantidade_operacoes": int(len(df_cliente)),
        "volume_total_brl": volume_total_brl,
        "mediana_valor_brl": float(df_cliente["valor_brl"].median()),
        "n_canais_distintos": int(df_cliente["canal"].nunique()),
        "n_contrapartes_distintas": int(df_cliente["contraparte"].nunique()),
        "datas_fracionamento": df_cliente["datas_fracionamento"].iloc[0],
        "datas_atipicas": datas_atipicas,
        "n_datas_nan": int(df_cliente["data"].isna().sum()),
        "percent_nan_volume": round(percent_nan, 4),
    }

def operacoes_do_dia(cliente_id: str, data: str) -> dict:
    """Resumo agregado das operações de um cliente em uma data
    específica: quantidade, volume, valores mínimo/médio/máximo,
    diversidade de canais/tipos/contrapartes, e o percentual que o
    volume desse dia representa do volume total do cliente .

    `data` deve estar no formato 'YYYY-MM-DD' (ISO 8601), ex: '2026-03-15'.
    """
    df_cliente = _df[_df["cliente_id"] == cliente_id]
    df_dia = df_cliente[df_cliente["data"].dt.strftime("%Y-%m-%d") == str(data)]

    volume_total_cliente = float(df_cliente["valor_brl"].sum())

    if df_dia.empty:
        return {
            "cliente_id": cliente_id,
            "data": data,
            "quantidade_operacoes": 0,
            "volume_total_brl": 0.0,
            "percentual_do_volume_total_cliente": 0.0,
            "valor_minimo_brl": None,
            "valor_mediano_brl": None,
            "valor_maximo_brl": None,
            "n_canais_distintos": 0,
            "n_tipos_operacao_distintos": 0,
            "n_contrapartes_distintas": 0,
        }

    volume_dia = float(df_dia["valor_brl"].sum())
    percentual_do_volume_total = (
        round(volume_dia / volume_total_cliente * 100, 1)
        if volume_total_cliente > 0 else 0.0
    )

    return {
        "cliente_id": cliente_id,
        "data": data,
        "quantidade_operacoes": int(len(df_dia)),
        "volume_total_brl": volume_dia,
        "percentual_do_volume_total_cliente": percentual_do_volume_total,
        "valor_minimo_brl": float(df_dia["valor_brl"].min()),
        "valor_mediano_brl": float(df_dia["valor_brl"].median()),
        "valor_maximo_brl": float(df_dia["valor_brl"].max()),
        "n_canais_distintos": int(df_dia["canal"].nunique()),
        "n_tipos_operacao_distintos": int(df_dia["tipo"].nunique()),
        "n_contrapartes_distintas": int(df_dia["contraparte"].nunique()),
    }


def perfil_canal(cliente_id: str) -> dict:
    """Distribuição de uso por canal para um cliente: quantidade de
    operações, volume e percentual de operações e de volume em cada
    canal usado.
    """
    df_cliente = _df[_df["cliente_id"] == cliente_id]

    if df_cliente.empty:
        return {"cliente_id": cliente_id, "erro": "cliente não encontrado na base"}

    resumo = (
        df_cliente.groupby("canal")
        .agg(
            quantidade_operacoes=("id", "count"),
            volume_brl=("valor_brl", "sum"),
        )
        .assign(
            percentual_operacoes=lambda t: (
                t["quantidade_operacoes"] / t["quantidade_operacoes"].sum() * 100
            ).round(1),
            percentual_volume=lambda t: (
                t["volume_brl"] / t["volume_brl"].sum() * 100
            ).round(1),
        )
        .sort_values("quantidade_operacoes", ascending=False)
        .reset_index()
    )

    return {
        "cliente_id": cliente_id,
        "canal_predominante": resumo.iloc[0]["canal"],
        "distribuicao": resumo.to_dict(orient="records"),
    }