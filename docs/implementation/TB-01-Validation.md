# JARVIS — TB-01 Completion Evidence

**Slice:** TB-01 — Primeira conversa funcional  
**Status:** PRODUCT DONE — validated by owner  
**Validation date:** 2026-10-31  
**Repository:** `kallbuloso/sofias_jarvis`  
**Implementation branch:** `feat/tb-01-first-conversation`  
**Target branch:** `main` — merge pending explicit approval

## Delivered capability

O proprietário abre a aplicação desktop no Windows, envia mensagem a uma
integração OpenAI real, acompanha resposta incremental e reabre a mesma
conversa após reiniciar a aplicação. A chave é acessada no Windows Credential
Manager, sem ser disponibilizada à interface Vue.

Componentes implementados: bootstrap Python; SQLite conversation store;
conversação e histórico; OpenAI Responses streaming adapter; armazenamento
protegido via `keyring`; interface candidata PySide6 + Qt WebEngine +
Vue 3/Vuetify 3; Qt WebChannel restrito.

## Evidence by acceptance criterion

| Critério | Evidência | Estado |
|---|---|---|
| TB01-AC01 — execução independente | Aplicação Windows aberta pelo próprio repositório; captura e relato humano | PASS |
| TB01-AC02 — resposta real | `--chat --model gpt-6-luna` retornou resposta real; interface também respondeu | PASS |
| TB01-AC03 — streaming | Proprietário confirmou visualização progressiva em UI | PASS |
| TB01-AC04 — persistência e associação | Testes de persistência/isolamento; histórico visual correto | PASS |
| TB01-AC05 — reabertura e continuidade | Proprietário confirmou histórico e novo envio após reiniciar | PASS |
| TB01-AC06 — falha explícita | Modelo inválido produziu `NotFoundError`; UI notificou, permaneceu responsiva e retomou com modelo válido | PASS |
| TB01-AC07 — secrets protegidos | `WinVaultKeyring` verificado no Windows, chave armazenada; testes de bloqueio de backend inseguro e ponte sem exposição | PASS |
| TB01-AC08 — encerramento | Proprietário confirmou encerramento sem recursos/processos abandonados | PASS |

### Automated tests

No Windows do proprietário, com `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`:

```text
................ [100%]
16 passed in 1.96s
```

Uma execução anterior do pytest foi interrompida durante a importação de
plugins externos (`KeyboardInterrupt`), antes da coleta dos testes; ela não
constitui falha de teste. A importação de `sniffio` e `anyio` funcionou na
verificação isolada. A suite passou com autodiscovery de plugins desabilitado.

**Proveniência:** execução real, saída de console, captura da aplicação e
validação humana relatadas pelo proprietário; não alegar verificação de CI
que ainda não ocorreu.

## Scope boundaries and follow-ups

- A validação do desktop comprova o comportamento de **texto** do TB-01, não
  prova integração de áudio nem confirmação protegida. Estes cenários serão
  tratados nos Slices correspondentes.
- PySide6 + Vue/Vuetify + Qt WebChannel demonstrou viabilidade para o TB-01;
  a prova arquitetural completa ainda tem cenários futuros.
- Não foram incluídos Sofias Memory, ferramentas externas, agente,
  fallback automático ou dashboard definitivo.
- Dependências Python estão delimitadas por ranges, e o frontend ainda não
  possui lockfile versionado; tornar builds reprodutíveis deve ser priorizado
  antes de ampliar o número de integrações. Não confundir isso com falha dos
  critérios funcionais aprovados do TB-01.
- Sem workflow CI confirmado nesta entrega; testes automatizados foram
  executados no ambiente do proprietário.
- O merge não será executado sem autorização explícita.

## Review and merge

1. Conferir o diff e a branch do TB-01.
2. Revisar o registro de evidências e as limitações remanescentes.
3. Obter aprovação do proprietário para integrar à `main`.
4. Abrir planejamento individual de TB-02, sem assumir autorização implícita
   para implementar Slices futuros.
