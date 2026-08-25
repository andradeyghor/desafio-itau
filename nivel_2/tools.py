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

    # --- Regra 1: fracionamento (flag em nível de cliente, mas
    # guardamos também as datas que dispararam a regra) ---
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
    """Resumo agregado das operações de um cliente, incluindo as datas
    em que ele disparou a regra de fracionamento e as datas/valores das
    operações classificadas como atípicas. Use esta ferramenta como
    ponto de partida para qualquer investigação, e para obter as datas
    necessárias caso precise depois consultar operacoes_do_dia.
    """
    df_cliente = _df[_df["cliente_id"] == cliente_id]

    if df_cliente.empty:
        return {"cliente_id": cliente_id, "erro": "cliente não encontrado na base"}

    df_atipicas = df_cliente[df_cliente["flag_valor_atipico"]]
    operacoes_atipicas = [
        {"data": str(row["data"].date()) if pd.notna(row["data"]) else None,
         "valor_brl": float(row["valor_brl"])}
        for _, row in df_atipicas.iterrows()
    ]

    return {
        "cliente_id": cliente_id,
        "quantidade_operacoes": int(len(df_cliente)),
        "volume_total_brl": float(df_cliente["valor_brl"].sum()),
        "mediana_valor_brl": float(df_cliente["valor_brl"].median()),
        "n_canais_distintos": int(df_cliente["canal"].nunique()),
        "n_contrapartes_distintas": int(df_cliente["contraparte"].nunique()),
        "possui_flag_fracionamento": bool(df_cliente["flag_fracionamento"].max()),
        "datas_fracionamento": df_cliente["datas_fracionamento"].iloc[0],
        "quantidade_valores_atipicos": int(df_cliente["flag_valor_atipico"].sum()),
        "operacoes_atipicas": operacoes_atipicas,
        "n_datas_nan": int(df_cliente["data"].isna().sum()),
    }


def operacoes_do_dia(cliente_id: str, data: str) -> dict:
    """Resumo agregado das operações de um cliente em uma data
    específica: quantidade, volume, valores mínimo/médio/máximo e
    diversidade de canais, tipos e contrapartes.

    `data` deve estar no formato 'YYYY-MM-DD' (ISO 8601), ex: '2026-03-15'.
    """
    df_cliente = _df[_df["cliente_id"] == cliente_id]
    df_dia = df_cliente[df_cliente["data"].dt.strftime("%Y-%m-%d") == str(data)]

    if df_dia.empty:
        return {
            "cliente_id": cliente_id,
            "data": data,
            "quantidade_operacoes": 0,
            "volume_total_brl": 0.0,
            "valor_minimo_brl": None,
            "valor_medio_brl": None,
            "valor_maximo_brl": None,
            "n_canais_distintos": 0,
            "n_tipos_operacao_distintos": 0,
            "n_contrapartes_distintas": 0,
        }

    return {
        "cliente_id": cliente_id,
        "data": data,
        "quantidade_operacoes": int(len(df_dia)),
        "volume_total_brl": float(df_dia["valor_brl"].sum()),
        "valor_minimo_brl": float(df_dia["valor_brl"].min()),
        "valor_medio_brl": float(df_dia["valor_brl"].mean()),
        "valor_maximo_brl": float(df_dia["valor_brl"].max()),
        "n_canais_distintos": int(df_dia["canal"].nunique()),
        "n_tipos_operacao_distintos": int(df_dia["tipo"].nunique()),
        "n_contrapartes_distintas": int(df_dia["contraparte"].nunique()),
    }


def perfil_canal(cliente_id: str) -> dict:
    """Distribuição de uso por canal para um cliente."""
    df_cliente = _df[_df["cliente_id"] == cliente_id]

    if df_cliente.empty:
        return {"cliente_id": cliente_id, "erro": "cliente não encontrado na base"}

    contagem = df_cliente["canal"].value_counts()
    volume = df_cliente.groupby("canal")["valor_brl"].sum()

    distribuicao = [
        {
            "canal": canal,
            "quantidade_operacoes": int(contagem[canal]),
            "volume_brl": float(volume[canal]),
            "percentual_operacoes": round(float(contagem[canal] / len(df_cliente) * 100), 1),
        }
        for canal in contagem.index
    ]

    return {
        "cliente_id": cliente_id,
        "canal_predominante": contagem.idxmax(),
        "distribuicao": distribuicao,
    }