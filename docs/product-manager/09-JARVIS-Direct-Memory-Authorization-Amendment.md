# JARVIS — Amendment 01: autorização por pedido explícito de memória

**Decisão:** APPROVED pelo proprietário em 2026-11-01.
**Escopo:** interpretação da autoridade do `CognitiveMemory.Create` em entrada
conversacional por texto, e futuramente transcrição final de voz, **somente**
para instruções explícitas, não sensíveis e inequívocas.
**Natureza:** extensão interpretativa aprovada de PRD-02/04, SPEC-01/04/10 e
CONTRACT-02; preservar IDs e textos originais. Nenhuma concessão ampla ou
persistente de autonomia é introduzida.

## Regra aprovada

Uma instrução direta da pessoa que opera o JARVIS, como
"JARVIS, lembre que no projeto JARVIS a palavra de teste é morango",
constitui **autoridade para aquela operação específica de gravação**,
desde que a avaliação de adequação confirme: `action=create`, conteúdo
identificável a partir do texto original, escopo inequívoco, operação
de baixo risco, ausência de credenciais/sensibilidade bloqueada,
integração autorizada e possibilidade de auditar a operação.

**Não exigir um segundo clique** para repetir a mesma autorização já
expressa pela mensagem. A confirmação de sucesso ao usuário continua
obrigatoriamente dependente de ACK real do Sofias Memory.

A seleção de `memory_create` pela LLM **não confere autoridade**:
o Core reavalia a própria mensagem original persistida, verifica
seu UUID de usuário, conversa, escopo e conteúdo, e só então autoriza.
O resultado da avaliação pode ser `PERMITTED`, `CLARIFY` ou `DENIED`.
Uma proposta da IA, texto de documento, conteúdo de memória recordada,
ou uma frase apenas citada, não constitui solicitação direta.

## Autoridade proporcional

| Condição | Resultado |
|---|---|
| Create explícito, inequívoco, baixo risco | Gravar diretamente após policy check |
| Escopo ou conteúdo não resolvidos | Esclarecer; nenhuma gravação |
| Credencial ou pedido sensível/composto | Bloquear; nenhuma gravação |
| Informação que o JARVIS acha útil, sem pedido explícito | Não persistir automaticamente |
| Update/Supersede e Forget naturais | Permanecem com as proteções atuais, pendentes da própria avaliação/controle |
| Lembrete futuro / agendamento | Não converter em memória cognitiva; scheduler ainda indisponível |
| Modelo ou memória sugerem gravar | Não constituem grant |
| Resposta remota desconhecida | `RESULT_UNKNOWN`, sem alegar sucesso e sem repetir automaticamente |

A regra é aplicável apenas à fonte de autoridade **mensagem atual
do usuário**, não a uma autorização persistente genérica, credencial
de serviço, permissão implícita do modelo ou preferência deduzida.

## Implementação incremental — texto (não voice)

A primeira policy concreta é conservadora: aceita imperativos
de lembrar/guardar/memorizar diretos e limita o escopo a
`global` ou `project:jarvis` quando explicitamente justificável.
Conteúdo amplo, complexo, temporal ou de outro projeto exige
esclarecimento ou bloqueio. Essa gramática restrita é um recorte
técnico do piloto, **não** a especificação final de compreensão
conversacional, e NÃO deve ser apresentada como compreensão geral.

O `TextIntentRouter` classifica; `evaluate_direct_create` avalia a
instrução original; o `PersonalMemoryLifecycle` revalida contra a
mensagem realmente persistida em SQLite. O `MemoryOperationJournal`
amarra `confirmation_ref=user-message:<user_message_uuid>` com
`confirmation_method=user_direct_intent` à operação preparada
atomicamente. O índice único evita duas operações originadas do mesmo
turno, mesmo após encerramento e limpeza de payload. O HTTP usa chave
de idempotência própria. Nenhum resultado indeterminado é repetido
automaticamente. Após confirmação remota, o próprio turno produz
resposta persistida no histórico; nenhum segundo diálogo de aprovação.

Jev/jev-chat é **referência conceitual de avaliação de decisão**;
esta aprovação não autoriza copiar sua base, construir um grande
motor autônomo, alterar licenças, ou conectar componentes adicionais.

## Critérios de validação

1. Pedido direto e inequivocamente limitado: `Create` real **sem**
   segunda confirmação; resposta de sucesso apenas após ACK.
2. Memória original, escopo, conversa e mensagem do usuário presentes
   no journal/provenance sem registrar credencial em texto aberto.
3. Replay do UUID original não gera segunda gravação, inclusive após restart.
4. Pedido citado/inferido, composto, ambíguo ou temporal não grava.
5. `UNKNOWN` não vira sucesso nem retry; erro de conexão é relatado.
6. Consultas, Knowledge, CLI, Delete Conversation e Update/Forget
   continuam obedecendo seus contratos próprios.
7. Entrada de voz fica DEFERRED: apenas transcrição final
   aceita pelo usuário pode ser considerada fonte de intenção.
8. Revisão de retenção, sensibilidade ampliada e resolução semântica
   de escopo/contexto permanecem controles futuros; não inventar
   garantias além do piloto.

**Validação atual:** implementação em branch de feature; testes de
Windows e smoke real estão PENDING. **TB-02 não é Product Done.**
A branch `main` permanece fora do escopo desta alteração.
