# Decisões Técnicas

## 1. Tratamento dos dados

### Taxa de câmbio
Criei a variável TAXA_CAMBIO para guardar o valor da taxa de câmbio como float, uma vez que é a mesma para toda as bases.

### Verificação da estrutura do JSON
Se verificou que todas as linhas do dataframe possuíam a mesma estrutura JSON. Visando possíveis dados incosistentes, se criou uma funçao para reportar incosistencias.

### Descarte de duplicata
Uma vez constatada que a duplicata não se tratava de duas operações semelhantes na mesma data (visto que o ID da operação era o mesmo), foi removida.

### Data Nan
Um valor Nan também é informativo, portanto, a data Nan foi mantida na base, visando uma possível implementação posterior que utilize essa informação. Se tivesse mais tempo, implementaria um teste automatizado que verificaria se o cliente entraria em fracionamento caso o valor_brl das datas ausentes fossem consideradas.

### Coluna 'valor' como float
Como estamos lidando com dados monetários, importante garantir que a coluna 'valor' possa assumir valor decimais, ao invés de inteiros.

### Verificar validade das datas
Como a base já apresentou sinais de possíveis inconsistências anteriores, é prudente verificar se as datas disponíveis são realmente datas possíveis. Por exemplo: 31/02/2026 não é uma data válida!

### Verificações dos demais dados
Importante verificar se nas demais colunas não há erros de ortografia que prejudiquem futuras agregações. Agregar valores por deposito e depósito não deveriam produzir resultados separados.

### Criações de Colunas e DataFrames auxiliares
Criar colunas no dataframe facilita no momento de validação de dados, assim como dataframes auxiliares, que carregam agregações mais ilustrativas.

## 2. LLM

### Escolha do modelo
foi utilizado o Gemini 3.6 Flash por apresentar um equilíbrio adequado entre capacidade de interpretação, velocidade, suporte a saídas estruturadas e disponibilidade de camada gratuita. O problema não exige raciocínio matemático pela LLM, pois os cálculos e regras determinísticas são realizados previamente com pandas. Dessa forma, priorizou-se um modelo Flash capaz de interpretar os indicadores e produzir uma resposta estruturada sem introduzir custo desnecessário.

Hoje, o Google lista gemini-3.6-flash como um modelo estável (GA), rápido, com structured outputs, function calling e janela de contexto de 1M tokens.



Escolhi o Google AI Studio/Gemini por disponibilizar uma camada gratuita adequada aos testes do desafio, possuir integração simples via API e oferecer suporte a respostas estruturadas em JSON. Como o objetivo da LLM é interpretar indicadores previamente calculados, e não realizar processamento numérico, priorizei um modelo com boa capacidade de seguir instruções e produzir respostas estruturadas, mantendo o custo da solução em zero. Além disso, a utilização de uma API permite registrar tempo de resposta e consumo de tokens, aspectos solicitados na avaliação.


“A solução utiliza cache para evitar chamadas redundantes à API, reduzindo consumo da cota gratuita, latência e custo.”


Testamos dois níveis de contexto para avaliar se informações comportamentais adicionais melhoram a interpretação da LLM. O primeiro prompt utiliza apenas indicadores agregados, enquanto o segundo inclui características temporais e distribuição das operações. A comparação foi realizada mantendo o mesmo modelo e os mesmos dados-base, alterando apenas o contexto fornecido.

O Prompt 1 utiliza indicadores agregados e produziu uma avaliação de risco alto, destacando a diversidade de canais e contrapartes. Já o Prompt 2 recebeu informações comportamentais adicionais, principalmente sobre concentração temporal, e classificou o risco como médio, concentrando sua justificativa no padrão de três operações realizadas na mesma data. A segunda versão apresentou uma justificativa mais específica e baseada nos padrões observados, enquanto a primeira realizou inferências mais abrangentes sobre o possível comportamento do cliente. O resultado demonstra que o aumento de contexto pode alterar a interpretação da LLM, não significando necessariamente uma classificação de risco mais elevada.

Eu não mandaria o prompt inteiro novamente no retry. A primeira chamada já recebeu todo o contexto do cliente. Se ela retornar JSON inválido, o retry acima pede apenas a correção de formato.

Isso reduz tokens e é particularmente interessante considerando que você está usando uma camada gratuita com limite de requisições.


# Criação de Notebook para o nível 2.
Não estava explícito onde realizar a parte A do nível 2, portanto, tomei a decisão de copiar o notebook do nível 1 para reaproveitar o código e acelerar o processo de análise. Essa adição não interfere na funcionalidade do repositório.

# Acesso à base em tools.py
A base é carregada uma única vez no import do módulo sem precisar de banco de dados real.
As funções seguem exatamente a assinatura pedida no enunciado (cliente_id, sem parâmetro de DataFrame), para serem chamadas diretamente pelo agente como ferramentas.

# Deveria ter feito o tratamento dos dados do nível 1 de forma modular (com funções) para reaproveitá-las no nível 2, e evitar duplicar a lógica.