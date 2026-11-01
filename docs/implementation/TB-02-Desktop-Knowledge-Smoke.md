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

## Evidência Windows e bloqueio de estabilidade — 2026-10-31

O proprietário informou `168 passed in 4.69s`, seguido de
`npm run build` concluído no Vite 7.3.7 (557 módulos, 5.53s);
o aviso de chunk JavaScript maior que 500 kB foi não fatal.
Três capturas da aplicação mostram:

- Knowledge OFF e Cognitive Memory OFF: conversa de saudação funcional.
- Knowledge ON, dataset `JARVIS Knowledge`: resposta específica
  fundamentada no ADR-0001; aviso de recuperação e fonte expansível,
  com Source ID `f4ed6afc-e540-473c-8f3b-f916e0ead739`,
  Document ID `4adee7a1-b52d-40fc-8c83-c691f0308bd1` e
  Chunk ID `815aae96-91ad-506e-b566-9529d2903fd5`.
- Knowledge ON + Cognitive Memory ON, escopo Global: dois
  avisos independentes e resposta; detalhes de fonte disponíveis.

**BLOCKER — encerramento inesperado:** durante o teste combinado
houve **uma saída completa do processo desktop para o PowerShell**,
sem traceback apresentado no terminal. O proprietário precisou reiniciar
a aplicação e repetir o teste; a tentativa seguinte funcionou.
O transcript mostra dois lançamentos `main.py --desktop`, mas
não contém `$LASTEXITCODE`, registro de falha nativa ou sinal de
encerramento para distinguir saída normal de crash Qt/WebEngine/Python.

A suíte unitária atual testa chamadas diretas ao `ReplyWorker.run()`,
mas **não comprova** ausência de corridas no ciclo real
`QThread.finished` / `deleteLater` / fechamento de janela.

**Estado de aceite do desktop:** funcionalidade demonstrada;
estabilidade **NÃO APROVADA** até diagnóstico. Não atribuir causa
a QThread, Qt, WebEngine, rede ou GC sem evidência.

### Captura de diagnóstico na próxima execução, sem alterar código

```powershell
$env:PYTHONFAULTHANDLER = "1"
& .\.venv\Scripts\python.exe -X faulthandler -u main.py --desktop 2>&1 |
    Tee-Object -FilePath .\tb02-desktop-diagnostic.log
$exitCode = $LASTEXITCODE
Write-Host "JARVIS_EXIT_CODE=$exitCode"
```

A execução retorna o código apenas quando a janela termina.
Caso o encerramento inesperado aconteça, preservar o código e as
últimas linhas relevantes do log (sem segredos) e, se necessário,
consultar o Visualizador de Eventos do Windows. Não criar rotina de
reinicialização automática para mascarar o defeito.

### Achados de apresentação (não bloqueiam a captura da falha)

- UI utiliza duas barras de seleção independentes e uma seção expansível;
  ocupação vertical relativamente alta, especialmente em janelas menores.
- Delimitadores Markdown de itálico/IDs em algumas respostas aparecem
  literalmente; não interpretar a boa apresentação do `**negrito**`
  como suporte geral a Markdown.
- `reference.url=null` permanece não navegável como esperado.

Nenhum merge na `main`; TB-02 permanece `IN PROGRESS` por causa
da estabilidade ainda não verificada.
