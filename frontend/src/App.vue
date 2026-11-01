<script setup>
import { onMounted, nextTick, ref, watch } from 'vue'

const ready = ref(false)
const conversations = ref([])
const messages = ref([])
const selected = ref('')
const model = ref('')
const draft = ref('')
const busy = ref(false)
const warning = ref('')
const credentialConfigured = ref(false)
const memoryConfigured = ref(false)
const useMemory = ref(false)
const memoryScope = ref('')
const memoryNotice = ref('')
const memoryPreviewBusy = ref(false)
const memoryPreviewDialog = ref(false)
const memoryPreview = ref(null)
const memoryPreviewReplacement = ref('')
const memoryAuthorizationToken = ref('')
const memoryRequiredPhrase = ref('')
const memoryAuthorizationInput = ref('')
const memoryMutationBusy = ref(false)
const useKnowledge = ref(false)
const knowledgeDataset = ref('')
const knowledgeNotice = ref('')
const knowledgeReferences = ref([])
const knowledgeQueryId = ref('')
const knowledgeItems = [
  { title: 'JARVIS Knowledge', value: 'jarvis-knowledge' },
]
const scopeItems = [
  { title: 'Global', value: 'global' },
  { title: 'Projeto JARVIS', value: 'project:jarvis' },
]
// Render only a small, explicitly supported subset of inline Markdown.
 // Vue interpolations escape all text; no v-html, HTML parser or arbitrary links.
function inlineParts(value) {
  const text = typeof value === 'string' ? value : ''
  const parts = []
  const pattern = /\*\*([^*\n]+)\*\*/g
  let cursor = 0
  for (const match of text.matchAll(pattern)) {
    if (match.index > cursor) {
      parts.push({ text: text.slice(cursor, match.index), bold: false })
    }
    parts.push({ text: match[1], bold: true })
    cursor = match.index + match[0].length
  }
  if (cursor < text.length || !parts.length) {
    parts.push({ text: text.slice(cursor), bold: false })
  }
  return parts
}

watch([useKnowledge, knowledgeDataset], () => {
  knowledgeNotice.value = ''
  knowledgeReferences.value = []
  knowledgeQueryId.value = ''
  if (knowledgeDataset.value && warning.value === 'Selecione um dataset antes de consultar Knowledge.') {
    warning.value = ''
  }
})

watch([useMemory, memoryScope], () => {
  // Retrieval evidence belongs to the last completed request and scope.
  memoryNotice.value = ''
  if (memoryScope.value && warning.value === 'Selecione um escopo antes de consultar o Sofias Memory.') {
    warning.value = ''
  }
})

const historyEnd = ref(null)
let bridge = null

function call(name, ...args) {
  return new Promise((resolve, reject) => {
    if (!bridge) { reject(new Error('Bridge not connected')); return }
    bridge[name](...args, (raw) => {
      try { resolve(JSON.parse(raw)) } catch (e) { reject(e) }
    })
  })
}

async function refreshConversations() {
  const result = await call('listConversations')
  if (result.ok) conversations.value = result.items
}

async function openConversation(id, preserveNotices = false) {
  if (id !== selected.value && memoryPreviewDialog.value) {
    await closeMemoryPreview()
  }
  selected.value = id
  const result = await call('listMessages', id)
  if (selected.value === id && result.ok) {
    messages.value = result.items
    if (!preserveNotices) {
      memoryNotice.value = ''
      knowledgeNotice.value = ''
      knowledgeReferences.value = []
      knowledgeQueryId.value = ''
    }
    await scrollToBottom()
  }
}

async function createConversation() {
  try {
    const created = await call('createConversation')
    if (!created.ok) return
    await refreshConversations()
    await openConversation(created.id)
    warning.value = ''
  } catch {
    warning.value = 'Não foi possível criar a conversa.'
  }
}

async function scrollToBottom() {
  await nextTick()
  historyEnd.value?.scrollIntoView({ block: 'end' })
}

function handleStream(raw) {
  let event
  try { event = JSON.parse(raw) } catch { return }
  if (event.type === 'memory_preview') {
    memoryPreviewBusy.value = false
    if (event.ok && event.preview && typeof event.preview.memory_id === 'string'
        && event.conversationId === selected.value && event.authorizationToken
        && event.requiredPhrase) {
      memoryPreview.value = { ...event.preview, action: event.action }
      memoryAuthorizationToken.value = event.authorizationToken
      memoryRequiredPhrase.value = event.requiredPhrase
      memoryAuthorizationInput.value = ''
      memoryPreviewDialog.value = true
    } else {
      memoryPreview.value = null
      memoryAuthorizationToken.value = ''
      call('cancelPendingPersonalMutation').catch(() => {})
      warning.value = 'Prévia não autorizada ou contexto alterado. Nenhuma memória foi modificada.'
    }
    return
  }
  if (event.type === 'memory_mutation') {
    memoryMutationBusy.value = false
    memoryPreviewDialog.value = false
    memoryPreview.value = null
    memoryAuthorizationToken.value = ''
    memoryAuthorizationInput.value = ''
    memoryRequiredPhrase.value = ''
    if (event.ok && event.status === 'CONFIRMED') {
      memoryNotice.value = event.replacementMemoryId
        ? 'Memória substituída com confirmação do serviço. Novo UUID: ' + event.replacementMemoryId
        : 'Memória esquecida com confirmação do serviço.'
    } else {
      warning.value = event.status === 'RESULT_UNKNOWN'
        ? 'Resultado da operação é incerto. NÃO repita: é necessário reconciliar pelo journal.'
        : 'A alteração não foi confirmada (' + (event.status || event.error || 'unknown') +
          '). Não houve repetição automática.'
    }
    return
  }
  if (event.type === 'knowledge') {
    if (event.conversationId !== selected.value) return
    const descriptions = {
      RESULTS_FOUND: Array.isArray(event.references) && event.references.length
        ? 'Knowledge: documento recuperado com referência verificada.'
        : 'Knowledge: trecho recuperado, mas sem referência fornecida.',
      NO_RESULTS: 'Knowledge: consulta concluída sem trechos correspondentes.',
      UNAVAILABLE: 'Knowledge indisponível; nenhuma fonte foi confirmada.',
      NOT_ATTEMPTED: 'A consulta documental não foi executada.',
    }
    knowledgeNotice.value = descriptions[event.knowledgeStatus] || ''
    knowledgeReferences.value = Array.isArray(event.references) ? event.references : []
    knowledgeQueryId.value = typeof event.queryId === 'string' ? event.queryId : ''
    return
  }
  if (event.type === 'done') {
    busy.value = false
    if (event.conversationId === selected.value) {
      const statuses = {
        RESULTS_FOUND: 'Sofias Memory: memórias recuperadas para esta resposta.',
        NO_RESULTS: 'Sofias Memory: consulta concluída, sem memórias correspondentes.',
        UNAVAILABLE: 'Sofias Memory indisponível; nenhuma recuperação foi confirmada.',
        NOT_ATTEMPTED: 'A consulta de memória não foi executada.',
      }
      memoryNotice.value = statuses[event.memoryStatus] || ''
    }
    if (event.status !== 'completed') {
      warning.value = event.status === 'interrupted'
        ? 'Resposta interrompida.'
        : 'Resposta não concluída (' + (event.error || 'provider') + ').'
    }
    refreshConversations().catch(() => {})
    if (event.conversationId === selected.value) {
      openConversation(selected.value, true).catch(() => {})
    }
    return
  }
  if (event.type !== 'delta' || event.conversationId !== selected.value) return
  let target = [...messages.value].reverse().find(m => m.role === 'assistant' && m.status === 'streaming')
  if (!target) {
    target = { role: 'assistant', status: 'streaming', content: '' }
    messages.value.push(target)
  }
  target.content += event.text
  scrollToBottom()
}

async function previewMemoryCommand(text) {
  // Only the explicit slash grammar can enter the memory control path.
  // No LLM answer, retrieved content or ordinary chat triggers a mutation.
  const forget = text.match(/^\/esquecer\s+([a-f0-9-]{36})$/i)
  const update = text.match(/^\/atualizar\s+([a-f0-9-]{36})\s+\|\s+(.+)$/is)
  if (!forget && !update) {
    warning.value = 'Use /esquecer UUID ou /atualizar UUID | nova informação.'
    return
  }
  const action = forget ? 'forget' : 'supersede'
  const memoryId = (forget || update)[1]
  const replacement = update ? update[2].trim() : ''
  if (update && (!replacement || replacement.length > 16384)) {
    warning.value = 'A nova informação deve ter de 1 a 16384 caracteres.'
    return
  }
  warning.value = ''
  memoryPreview.value = null
  memoryPreviewReplacement.value = replacement
  memoryPreviewBusy.value = true
  try {
    const result = await call('previewPersonalMutation', action, memoryId,
      replacement, selected.value)
    if (!result.ok) {
      memoryPreviewBusy.value = false
      warning.value = 'Prévia recusada: ' + (result.error || 'unavailable')
      return
    }
    draft.value = ''
  } catch {
    memoryPreviewBusy.value = false
    warning.value = 'Falha ao solicitar a prévia da memória.'
  }
}

async function closeMemoryPreview() {
  if (memoryMutationBusy.value) return
  memoryPreviewDialog.value = false
  memoryPreview.value = null
  memoryAuthorizationToken.value = ''
  memoryRequiredPhrase.value = ''
  memoryAuthorizationInput.value = ''
  memoryPreviewReplacement.value = ''
  try { await call('cancelPendingPersonalMutation') } catch {}
}

async function confirmMemoryMutation() {
  if (!memoryPreview.value || memoryMutationBusy.value ||
      memoryAuthorizationInput.value !== memoryRequiredPhrase.value ||
      !memoryAuthorizationToken.value) return
  memoryMutationBusy.value = true
  warning.value = ''
  try {
    const result = await call('confirmPersonalMutation',
      memoryAuthorizationToken.value, memoryAuthorizationInput.value, selected.value)
    memoryAuthorizationToken.value = '' // No local replay, even on error.
    if (!result.ok) {
      memoryMutationBusy.value = false
      warning.value = 'Autorização recusada (' + (result.error || 'unknown') +
        '). Será necessária uma nova prévia.'
      await closeMemoryPreview()
    }
  } catch {
    memoryAuthorizationToken.value = ''
    memoryMutationBusy.value = false
    warning.value = 'Não foi possível confirmar o envio. Não repita sem verificar o journal.'
    await closeMemoryPreview()
  }
}

async function sendMessage() {
  const text = draft.value.trim()
  if (!ready.value || busy.value || memoryPreviewBusy.value || memoryMutationBusy.value || !selected.value || !text) return
  if (/^\/(?:esquecer|atualizar)(?:\s|$)/i.test(text)) {
    await previewMemoryCommand(text)
    return
  }
  if (!model.value.trim()) return
  if (useMemory.value && !memoryScope.value) {
    warning.value = 'Selecione um escopo antes de consultar o Sofias Memory.'
    return
  }
  if (useKnowledge.value && knowledgeDataset.value !== 'jarvis-knowledge') {
    warning.value = 'Selecione um dataset antes de consultar Knowledge.'
    return
  }
  warning.value = ''
  memoryNotice.value = ''
  knowledgeNotice.value = ''
  knowledgeReferences.value = []
  knowledgeQueryId.value = ''
  busy.value = true
  draft.value = ''
  const conversationId = selected.value
  messages.value.push({ role: 'user', content: text, status: 'completed' })
  messages.value.push({ role: 'assistant', content: '', status: 'streaming' })
  scrollToBottom()
  try {
    const result = useKnowledge.value
      ? await call('sendMessageWithContext', conversationId, text, model.value.trim(),
          useMemory.value ? memoryScope.value : '', knowledgeDataset.value)
      : useMemory.value
        ? await call('sendMessageWithMemory', conversationId, text, model.value.trim(), memoryScope.value)
        : await call('sendMessage', conversationId, text, model.value.trim())
    if (!result.ok) {
      busy.value = false
      draft.value = text
      warning.value = 'Envio recusado: ' + result.error
      if (selected.value === conversationId) await openConversation(conversationId)
    }
  } catch {
    busy.value = false
    warning.value = 'Falha de comunicação com o Core.'
    if (selected.value === conversationId) await openConversation(conversationId)
  }
}

onMounted(async () => {
  try {
    if (!window.qt?.webChannelTransport || !window.QWebChannel) {
      warning.value = 'Esta interface deve ser aberta pelo desktop JARVIS.'
      return
    }
    await new Promise(resolve => new window.QWebChannel(window.qt.webChannelTransport, channel => {
      bridge = channel.objects.jarvis
      bridge.streamEvent.connect(handleStream)
      resolve()
    }))
    const initial = await call('bootstrap')
    conversations.value = initial.conversations
    model.value = initial.model
    credentialConfigured.value = initial.credentialConfigured
    memoryConfigured.value = initial.memoryConfigured === true
    ready.value = true
    if (conversations.value.length) await openConversation(conversations.value[0].id)
    else await createConversation()
  } catch {
    warning.value = 'Não foi possível inicializar a interface.'
  }
})
</script>

<template>
  <v-app>
    <v-layout>
      <v-navigation-drawer permanent width="285" color="surface">
        <div class="sidebar-heading">
          <div class="brand">JARVIS <span>TB-02</span></div>
          <v-btn block color="primary" variant="flat" :disabled="!ready" @click="createConversation">
            Nova conversa
          </v-btn>
        </div>
        <v-list density="compact" nav>
          <v-list-item v-for="c in conversations" :key="c.id"
            :active="selected === c.id" :title="c.title"
            @click="openConversation(c.id)"/>
        </v-list>
        <div class="sidebar-footer">Operação local · Windows</div>
      </v-navigation-drawer>
      <v-main>
        <div class="main-column">
          <div class="toolbar">
            <div>
              <div class="heading">Conversa</div>
              <div class="small-text">Core Python · OpenAI Responses · SQLite</div>
            </div>
            <v-text-field v-model="model" class="model-input" label="Modelo OpenAI"
              variant="outlined" density="compact" hide-details
              placeholder="Digite o modelo habilitado"/>
          </div>
          <div v-if="!credentialConfigured" class="inline-alert" role="alert">
            Configure sua chave pelo console: main.py --configure-openai-key
          </div>
          <div v-if="warning" class="inline-alert" role="alert" aria-live="assertive">
            {{ warning }}
          </div>
          <div class="history">
            <div v-if="!messages.length" class="empty">Conversa pronta. Envie sua primeira mensagem.</div>
            <div v-for="(m, i) in messages" :key="m.id || i"
              class="message" :class="m.role === 'user' ? 'mine' : 'assistant'">
              <div class="speaker">{{ m.role === 'user' ? 'Você' : 'JARVIS' }}</div>
              <div class="content">
                <template v-for="(part, j) in inlineParts(m.content || (m.status === 'streaming' ? 'Respondendo…' : ''))" :key="j">
                  <strong v-if="part.bold">{{ part.text }}</strong><template v-else>{{ part.text }}</template>
                </template>
              </div>
              <div v-if="m.status !== 'completed'" class="status">{{ m.status }}</div>
            </div>
            <div ref="historyEnd"></div>
          </div>
          <div class="memory-bar">
            <v-switch v-model="useMemory" color="primary" density="compact"
              hide-details label="Consultar Sofias Memory"
              :disabled="!memoryConfigured || busy"/>
            <v-select v-if="useMemory" v-model="memoryScope" :items="scopeItems"
              label="Escopo da memória" variant="outlined" density="compact"
              hide-details clearable :disabled="busy" class="memory-scope"/>
            <span v-if="useMemory" class="memory-caption">
              A pergunta será consultada no Sofias Memory; evidências selecionadas serão enviadas ao modelo.
            </span>
            <span class="memory-caption" v-else-if="!memoryConfigured">
              Configure a URL e chave do Sofias Memory pelo console.
            </span>
            <span class="memory-caption" v-else>
              Desligado: esta conversa não consulta memórias cognitivas.
            </span>
            <div v-if="useMemory && memoryNotice" class="memory-feedback"
              role="status" aria-live="polite">{{ memoryNotice }}</div>
          </div>
          <div class="knowledge-bar">
            <v-switch v-model="useKnowledge" color="primary" density="compact"
              hide-details label="Consultar Knowledge"
              :disabled="!memoryConfigured || busy"/>
            <v-select v-if="useKnowledge" v-model="knowledgeDataset" :items="knowledgeItems"
              label="Dataset documental" variant="outlined" density="compact"
              hide-details clearable :disabled="busy" class="memory-scope"/>
            <span v-if="useKnowledge" class="memory-caption">
              A pergunta consultará documentos do dataset selecionado; as evidências serão enviadas ao modelo.
            </span>
            <span v-else-if="!memoryConfigured" class="memory-caption">
              Configure o Sofias Memory pelo console antes de usar Knowledge.
            </span>
            <span v-else class="memory-caption">
              Desligado: não consulta documentos do Sofias Memory.
            </span>
            <div v-if="useKnowledge && knowledgeNotice" class="memory-feedback"
              role="status" aria-live="polite">{{ knowledgeNotice }}</div>
            <details v-if="useKnowledge && knowledgeReferences.length"
              class="knowledge-sources">
              <summary>Fontes documentais verificadas ({{ knowledgeReferences.length }})</summary>
              <div v-if="knowledgeQueryId" class="source-meta">Consulta: {{ knowledgeQueryId }}</div>
              <div v-for="(source, index) in knowledgeReferences" :key="source.chunk_id || index"
                class="knowledge-source">
                <div class="source-title">{{ source.source_name }}</div>
                <div class="source-meta">Documento: {{ source.document_id }}</div>
                <div class="source-meta">Fonte: {{ source.source_id }}</div>
                <div class="source-meta">Trecho: {{ source.chunk_id }}</div>
                <div v-if="source.quote" class="source-quote">{{ source.quote }}</div>
              </div>
            </details>
          </div>
          <div class="memory-command-hint">
            Comandos supervisionados: /esquecer UUID
            ou /atualizar UUID | nova informação.
          </div>
          <div class="composer">
            <v-textarea v-model="draft" rows="2" auto-grow :max-rows="5"
              variant="outlined" density="comfortable" hide-details
              label="Mensagem" :disabled="busy || memoryPreviewBusy || memoryMutationBusy || !ready"
              @keydown.ctrl.enter.prevent="sendMessage"/>
            <v-btn color="primary" size="large" :loading="busy || memoryPreviewBusy"
              :disabled="!ready || !selected || !draft.trim() || busy || memoryPreviewBusy || memoryMutationBusy ||
                (!model.trim() && !draft.trim().startsWith('/'))"
              @click="sendMessage">Enviar</v-btn>
          </div>
        </div>
      </v-main>
    </v-layout>
    <v-dialog v-model="memoryPreviewDialog" max-width="700" persistent>
      <v-card v-if="memoryPreview" title="Confirmação supervisionada da memória">
        <v-card-text>
          <p>Operação solicitada: <strong>{{ memoryPreview.action === 'forget' ? 'Esquecer' : 'Substituir' }}</strong></p>
          <p>UUID: <code>{{ memoryPreview.memory_id }}</code></p>
          <p>Escopo: {{ memoryPreview.scope }} · Tipo: {{ memoryPreview.memory_type }}</p>
          <p>Estado: {{ memoryPreview.lifecycle }}</p>
          <p>Conteúdo atual:</p>
          <div class="memory-preview-content">{{ memoryPreview.content }}</div>
          <template v-if="memoryPreview.action === 'supersede'">
            <p>Substituição proposta:</p>
            <div class="memory-preview-content">{{ memoryPreviewReplacement }}</div>
          </template>
          <p class="memory-preview-disclaimer">
            A prévia não modifica nada. Para autorizar a operação REAL e persistente,
            digite exatamente a frase abaixo. A autorização vale apenas para esta prévia.
            No esquecimento, o conteúdo será eliminado permanentemente.
          </p>
          <div class="source-meta">Confirmação necessária: {{ memoryRequiredPhrase }}</div>
          <v-text-field v-model="memoryAuthorizationInput"
            label="Digite a confirmação exata"
            variant="outlined" density="compact" autocomplete="off"
            :disabled="memoryMutationBusy"/>

        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" :disabled="memoryMutationBusy" @click="closeMemoryPreview">
            Fechar sem alterar
          </v-btn>
          <v-btn color="error" :loading="memoryMutationBusy"
            :disabled="memoryMutationBusy || !memoryAuthorizationToken ||
              memoryAuthorizationInput !== memoryRequiredPhrase"
            @click="confirmMemoryMutation">
            {{ memoryPreview.action === 'forget' ? 'Confirmar esquecimento' : 'Confirmar substituição' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-app>
</template>

<style>
html, body, #app { height: 100%; margin: 0; }
.main-column { display: flex; flex-direction: column; height: 100vh; min-height: 0; }
.sidebar-heading { padding: 25px 16px 20px; }
.brand { color: #ebffff; font-size: 22px; font-weight: 700; letter-spacing: 3px; margin-bottom: 20px; }
.brand span { color: #008f8f; font-size: 11px; letter-spacing: 1px; }
.sidebar-footer { position: absolute; bottom: 24px; left: 20px; font-size: 12px; color: #82969e; }
.toolbar { display: flex; justify-content: space-between; align-items: center; gap: 22px;
  padding: 22px 26px 16px; border-bottom: 1px solid #243441; }
.heading { font-size: 20px; font-weight: 600; }
.small-text { font-size: 12px; color: #82969e; }
.model-input { max-width: 300px; }
.inline-alert { flex: 0 0 auto; align-self: stretch; margin: 10px 26px 0;
  padding: 10px 12px; border-left: 2px solid #de9d48; border-radius: 5px;
  background: rgba(222,157,72,.09); color: #edb968; font-size: 13px;
  line-height: 1.45; overflow-wrap: anywhere; }
.history { flex: 1; overflow-y: auto; padding: 26px 8%; min-height: 0; }
.empty { text-align: center; color: #82969e; margin-top: 18vh; }
.message { max-width: 76%; margin-bottom: 18px; padding: 13px 17px;
  border: 1px solid #293f4d; border-radius: 14px; background: #132330; }
.message.mine { margin-left: auto; background: #123d40; border-color: #186668; }
.speaker { font-size: 11px; letter-spacing: 0.4px; color: #85d1c9; margin-bottom: 7px; }
.content { white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.55; }
.status { font-size: 11px; color: #c69d6b; margin-top: 6px; }
.memory-bar { display: flex; flex: 0 0 auto; flex-wrap: wrap; align-items: center; gap: 10px 14px;
  padding: 8px 26px; border-top: 1px solid #243441; background: #101e28; }
.memory-feedback { flex: 0 0 100%; min-height: 0; max-height: 76px; overflow-y: auto;
  align-self: flex-start; color: #7bceca; font-size: 12px; line-height: 1.45;
  border-left: 2px solid #008080; padding: 4px 10px; background: rgba(0,128,128,.06);
  overflow-wrap: anywhere; }
.memory-scope { max-width: 240px; min-width: 180px; }
.knowledge-bar { display: flex; flex: 0 0 auto; flex-wrap: wrap; align-items: center;
  gap: 10px 14px; padding: 8px 26px; border-top: 1px solid #243441; background: #101e28; }
.knowledge-sources { flex: 0 0 100%; color: #a3d9d4; font-size: 12px;
  border-left: 2px solid #008080; padding: 6px 10px;
  background: rgba(0,128,128,.06); max-height: 160px; overflow-y: auto; overflow-wrap: anywhere; }
.knowledge-sources summary { cursor: pointer; font-weight: 600; }
.knowledge-source { padding: 7px 0 4px; border-top: 1px solid #29444a; }
.source-title { color: #b7e6e2; font-weight: 600; }
.source-meta { color: #829fa4; font-size: 11px; }
.source-quote { white-space: pre-wrap; max-height: 70px; overflow: auto; }
.memory-caption { color: #82969e; font-size: 12px; }
.composer { display: flex; align-items: end; gap: 14px; padding: 18px 26px 26px;
  border-top: 1px solid #243441; }
.composer .v-input { flex: 1; }
</style>

<style scoped>
.memory-command-hint { padding: 5px 26px; font-size: 12px; color: #819ca2; }
.memory-preview-content { white-space: pre-wrap; overflow-wrap: anywhere; padding: 12px;
  border: 1px solid #32545b; border-radius: 8px; background: #132932; }
.memory-preview-disclaimer { margin-top: 16px; font-size: 13px; color: #b5b9c9; }
</style>
