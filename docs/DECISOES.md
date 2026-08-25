# Decisões Nível 1

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
* trade-offs: optei por criar docstrings bem detalhadas das funções em tools.py pois o SDK do google-genai introspecciona automaticamente cada função Python, porém, isso consumiu bastante tempo (mesmo com auxílio de IA).



