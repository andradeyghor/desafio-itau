# Decisões Nível 1

## Adequação de tipo de dado
Escolhi tratar converter a coluna 'data' para datetime com o intuito de facilitar operações entre datas, como contagem de dias por exemplo.

## Validação dos dados
* trade-offs: optei por validar somente algumas colunas do dataframe por se tratar de um desafio mais simples.
* limitaçoes: meu notebook falha quando os dados que deveriam ser iguais possuem valores similares (ex: deposito e depósito).
* com mais tempo: implementaria uma lógica para capturar palavras similares e as padronizaria.

## Escolha do modelo
* trade-offs: optei por utilizar o Gemini 3.6 Flash pela disponibilidade de camada gratuita, e pela facilidade da integração com a API. Além disso, é o modelo mais atual da Google, e supera o Flash 3.5 em tarefas que exigem conhecimento especializado, que é o nosso caso.
* limitaçoes: devido à camada gratuita, somente algumas chamadas à API são possíveis.
* com mais tempo: criar um ground-truth para testar a acurácia de outros modelos, além de um levantamento orçamentário.

## Comentários:
* Deveria ter feito o tratamento dos dados do nível 1 de forma modular (com funções) para reaproveitá-las no nível 2, e evitar duplicar a lógica e usar muito tempo.


# Decisões Nível 2

# Criação de Notebook para o nível 2.
Não estava explícito onde realizar a parte A do nível 2, portanto, tomei a decisão de copiar o notebook do nível 1 para reaproveitar o código e acelerar o processo de análise. Essa adição não interfere na funcionalidade do repositório.

# Acesso à base em tools.py
A base é carregada uma única vez no import do módulo sem precisar de banco de dados real.
As funções seguem exatamente a assinatura pedida no enunciado (cliente_id, sem parâmetro de DataFrame), para serem chamadas diretamente pelo agente como ferramentas.

# Docstrings
Mantive as docstrings das ferramentas puramente descritivas (o que cada uma retorna), e os critérios de quando usar cada ferramenta foi deixada a cargo do agente no system prompt. Isso evita duplicar orientação em dois lugares que são reenviados a cada chamada.

# Plano Confronto
Criaria condições aninhadas com base em flag_fracionamento e quantidade_valores_atipicos, por exemplo:
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
        
Registraria numa coluna do dataframe os valores obtidos no looping acima, bem como os valores apontados pelo agente em outra coluna.
Faria comparação de igualdade numa coluna 'concordancia': 1 se igual, 0 se diferente. Somaria os valores dessa coluna e faria uma porcentagem de concordância.
Onde 'concordancia' == 0, retornar a coluna 'parecer', que justifica a classificação feita pelo agente, estruturada num relatório.
Eu consumiria o relatório e adicionaria minhas percepções também.


# Fluxo Nivel 3
Seguiria com a ideia parecida do que realizei no Nível 2, porém, precisaria estudar alguns conceitos a fundo, como ter estado compartilhado e diagrama Mermaid. 
Precisaria criar uma lógica à parte, similar ao contexto inicial que forneço, que seria meu Triador. Aprimoraria a seleção de ferramentas com base no output do Triador, que seria meu Investigador. Criaria um agente que produz output específico para ser o Redator.