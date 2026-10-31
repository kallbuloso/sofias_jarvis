<script setup>
import { onMounted, nextTick, ref } from 'vue'

const ready = ref(false)
const conversations = ref([])
const messages = ref([])
const selected = ref('')
const model = ref('')
const draft = ref('')
const busy = ref(false)
const warning = ref('')
const credentialConfigured = ref(false)
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

async function openConversation(id) {
  selected.value = id
  const result = await call('listMessages', id)
  if (selected.value === id && result.ok) {
    messages.value = result.items
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
  if (event.type === 'done') {
    busy.value = false
    if (event.status !== 'completed') {
      warning.value = event.status === 'interrupted'
        ? 'Resposta interrompida.'
        : 'Resposta não concluída (' + (event.error || 'provider') + ').'
    }
    refreshConversations().catch(() => {})
    if (event.conversationId === selected.value) {
      openConversation(selected.value).catch(() => {})
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

async function sendMessage() {
  const text = draft.value.trim()
  if (!ready.value || busy.value || !selected.value || !model.value.trim() || !text) return
  warning.value = ''
  busy.value = true
  draft.value = ''
  const conversationId = selected.value
  messages.value.push({ role: 'user', content: text, status: 'completed' })
  messages.value.push({ role: 'assistant', content: '', status: 'streaming' })
  scrollToBottom()
  try {
    const result = await call('sendMessage', conversationId, text, model.value.trim())
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
          <div class="brand">JARVIS <span>TB-01</span></div>
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
          <v-alert v-if="!credentialConfigured" color="warning" variant="tonal" density="compact"
            class="mx-6 mt-4">Configure sua chave pelo console: main.py --configure-openai-key</v-alert>
          <v-alert v-if="warning" color="warning" variant="tonal" density="compact"
            class="mx-6 mt-4">{{ warning }}</v-alert>
          <div class="history">
            <div v-if="!messages.length" class="empty">Conversa pronta. Envie sua primeira mensagem.</div>
            <div v-for="(m, i) in messages" :key="m.id || i"
              class="message" :class="m.role === 'user' ? 'mine' : 'assistant'">
              <div class="speaker">{{ m.role === 'user' ? 'Você' : 'JARVIS' }}</div>
              <div class="content">{{ m.content || (m.status === 'streaming' ? 'Respondendo…' : '') }}</div>
              <div v-if="m.status !== 'completed'" class="status">{{ m.status }}</div>
            </div>
            <div ref="historyEnd"></div>
          </div>
          <div class="composer">
            <v-textarea v-model="draft" rows="2" auto-grow :max-rows="5"
              variant="outlined" density="comfortable" hide-details
              label="Mensagem" :disabled="busy || !ready"
              @keydown.ctrl.enter.prevent="sendMessage"/>
            <v-btn color="primary" size="large" :loading="busy"
              :disabled="!ready || !selected || !draft.trim() || !model.trim() || busy"
              @click="sendMessage">Enviar</v-btn>
          </div>
        </div>
      </v-main>
    </v-layout>
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
.history { flex: 1; overflow-y: auto; padding: 26px 8%; min-height: 0; }
.empty { text-align: center; color: #82969e; margin-top: 18vh; }
.message { max-width: 76%; margin-bottom: 18px; padding: 13px 17px;
  border: 1px solid #293f4d; border-radius: 14px; background: #132330; }
.message.mine { margin-left: auto; background: #123d40; border-color: #186668; }
.speaker { font-size: 11px; letter-spacing: 0.4px; color: #85d1c9; margin-bottom: 7px; }
.content { white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.55; }
.status { font-size: 11px; color: #c69d6b; margin-top: 6px; }
.composer { display: flex; align-items: end; gap: 14px; padding: 18px 26px 26px;
  border-top: 1px solid #243441; }
.composer .v-input { flex: 1; }
</style>
