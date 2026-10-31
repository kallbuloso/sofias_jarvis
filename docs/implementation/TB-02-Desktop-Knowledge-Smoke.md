# TB-02 — Desktop Knowledge Retrieval | Windows validation

**Estado:** implementação publicada somente na feature branch; **pytest, Vite build e smoke
visual desta alteração ainda não executados pelo proprietário**. Não afirmar Product Done.

## Contrato e isolamento

- UI mantém o fluxo original `sendMessage` e `sendMessageWithMemory`.
- Para Knowledge ativado, utiliza `sendMessageWithContext` com dataset literal
  `jarvis-knowledge` e, opcionalmente, escopo cognitivo independente `global`
  ou `project:jarvis`.
- Ambos os switches iniciam **OFF** ao abrir o desktop. Dataset e escopo
  não são selecionados automaticamente; exigem escolha explícita.
- O worker consulta o Sofias Memory e envia ao OpenAI apenas contexto
  temporário, como dado de baixa confiança. O histórico SQLite mantém
  exclusivamente a pergunta e a resposta do chat.
- O Qt WebChannel transmite `knowledgeStatus`, `queryId` e referências
  delimitadas (`source_name`, `source_id`, `document_id`, `chunk_id`,
  `quote` limitada a 500 bytes, `url=null`); nunca a API key.
- Não há novo dataset, ingestão, Supersede/Forget ou operação executável
  autorizada pelo conteúdo documental. O serviço pode registrar auditoria
  da Query.
- Limite de teste: dataset `jarvis-knowledge` ativo com ADR-0001 e um chunk.
  Não há seleção genérica de datasets ou referências por URL.

## 1. Preparar o ambiente

```powershell
git switch feat/tb-02-memory-knowledge
git pull --ff-only origin feat/tb-02-memory-knowledge

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
.\.venv\Scripts\python.exe -m pytest -q

cd frontend
npm run build
cd ..

.\.venv\Scripts\python.exe main.py --desktop
```

Use `JARVIS_MODEL` já configurado, ou preencha o campo de modelo na
interface. Não altere tokens nem imprima credenciais.

Não prossiga se pytest ou o build falhar.

## 2. Teste OFF (controle negativo)

1. Confirme que os switches **Consultar Sofias Memory** e
   **Consultar Knowledge** iniciam desativados.
2. Abra uma nova conversa, pergunte
   `Por que o Core do JARVIS usa Modular Monolith?`.
3. Confirme que o texto flui incrementalmente, que o histórico permanece,
   e que não surge aviso de Knowledge nem seção de fontes. O modelo
   ainda pode responder por conhecimento geral; ausência de referências
   **não comprova isoladamente** inexistência de consultas: a garantia
   de não dispatch depende dos testes de worker/bridge.
4. Após encerrar/reabrir o desktop, ambos os switches devem estar OFF.

## 3. Teste Knowledge ON

1. Em nova conversa, mantenha Cognitive Memory OFF.
2. Ative `Consultar Knowledge`. Selecione explicitamente
   `JARVIS Knowledge` no dropdown.
3. Pergunte `Por que escolhemos Modular Monolith e não microsserviços?`
4. Verifique resposta fundamentada no ADR-0001, aviso
   `Knowledge: documento recuperado com referência verificada.`
   e o expansível `Fontes documentais verificadas (1)`.
5. Expanda e confirme os IDs observados anteriormente:
   - Query ID: novo UUID a cada consulta
   - Source: `f4ed6afc-e540-473c-8f3b-f916e0ead739`
   - Document: `4adee7a1-b52d-40fc-8c83-c691f0308bd1`
   - Chunk: `815aae96-91ad-506e-b566-9529d2903fd5`
   - Nome: `JARVIS ADR-0001 — Modular Monolith`
   - `url=null` não é convertido em link.
6. Desative Knowledge e faça outra pergunta. A interface não deve
   apresentar novas fontes, e o fluxo padrão deve continuar íntegro.

## 4. Teste Knowledge + Cognitive Memory

1. Ative Cognitive Memory, selecione `Global`.
2. Ative Knowledge, selecione `JARVIS Knowledge`.
3. Faça uma pergunta que exija arquitetura documentada e preferências,
   por exemplo `Qual é a minha preferência de cor para interfaces e por
   que o JARVIS usa Modular Monolith?`.
4. Confirme status de Memory e Knowledge independentes, resposta
   incremental, fontes documentais, sem mutações e sem duplicações no
   histórico. Uma recuperação vazia de memória não significa falha
   documental; registros são distintos.

## 5. Falhas e segurança

- Knowledge indisponível: status `UNAVAILABLE`, nenhuma fonte inventada;
  o chat pode continuar com conhecimento geral.
- Dataset não selecionado: bloqueio local antes do dispatch.
- Dataset diferente de `jarvis-knowledge`: bloqueio no Core antes
  de criar thread.
- Referência fora do chunk recuperado: falha fechada, sem resposta
  fundamentada em fonte falsa.
- A origem deve ser checada usando UUIDs, não pelo texto do modelo,
  que pode inventar citações.
- Uma referência é apresentada **somente para o último turno** e não
  persiste como metadado por mensagem na SQLite neste incremento.
  Ao trocar de conversa, evidências do turno são limpas.

## Critérios de aceite

- Pytest e npm build passam no Windows.
- Desktop abre/fecha sem regressão, com texto incremental e histórico.
- Knowledge OFF realmente não consulta o serviço (teste de worker),
  Knowledge ON retorna fonte verificada e status.
- Memory isolada continua funcionando, e combinação não cria
  permissões nem mutações.
- O layout mantém os controles e fontes legíveis, sem expansão vertical
  excessiva; registrar screenshot se houver problema.

**TB-02 permanece IN PROGRESS até o aceite humano.**
Não há merge para `main` nem início do TB-03.
