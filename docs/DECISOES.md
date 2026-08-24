# Decisões Técnicas

## 1. Tratamento dos dados

### Taxa de câmbio
Por se tratar da mesma taxa de câmbio para toda a base (verificado), optei por não incluir essa informação no DataFrame. Caso venha a se tornar um fluxo em produção, importante deixar explicito na base os valores das taxas cambiais e uma lógica que capte esses valores.

### Verificação da estrutura do JSON
Caso houvesse mais tempo, seria interessante criar um pipeline exclusivo para validar a estrutra JSON de cada linha, além de criar tratamentos específicos de cada exceção.

### Descarte de duplicata
Uma vez constatada que a duplicata não se tratava de duas operações semelhantes na mesma data (visto que o ID da operação era o mesmo), decidi removê-la.

### Data Nan
Um valor Nan também é informativo, portanto, decidi por manter este registro na base, mas sempre mantendo-o sob o radar. Posteriormente, nas análises de volume de operações por data, tal registro não impactou o fracionamento.

### Coluna 'valor' como float
Como estamos lidando com dados monetários, importante garantir que a coluna 'valor' possa assumir valor decimais, ao invés de inteiros.

### Verificar validade das datas
Como a base já apresentou sinais de possíveis inconsistências anteriores, é prudente verificar se as datas disponíveis são realmente datas possíveis. Por exemplo: 31/02/2026 não é uma data válida!

### Verificações dos demais dados
Importante verificar se nas demais colunas não há erros de ortografia que prejudiquem futuras agregações. Agregar valores por deposito e depósito não deveriam produzir resultados separados.

### Criações de Colunas e DataFrames auxiliares
Criar colunas no dataframe facilita no momento de validação de dados, assim como dataframes auxiliares, que carregam agregações mais ilustrativas.