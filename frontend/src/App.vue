<script setup>
import { computed, onMounted, nextTick, ref } from 'vue'

const ready = ref(false)
const conversations = ref([])
const messages = ref([])
const selected = ref('')
const model = ref('')
const draft = ref('')
const busy = ref(false)
const warning = ref('')
const deletionTarget = ref(null)
const deletionBusy = ref(false)
const credentialConfigured = ref(false)
 const memoryNotice = ref('')
const memoryPreviewBusy = ref(false)
const memoryPreviewDialog = ref(false)
const memoryPreview = ref(null)
const memoryPreviewReplacement = ref('')
const memoryAuthorizationToken = ref('')
const memoryRequiredPhrase = ref('')
const memoryAuthorizationInput = ref('')
const memoryApprovalMode = ref('typed')
const memoryMutationBusy = ref(false)
const createProposal = ref(null)
const createScope = ref('')
const createDialog = ref(false)
const createBusy = ref(false)
const knowledgeNotice = ref('')
const voiceState = ref('IDLE')
const voiceConversation = ref('')
const voiceStarting = ref(false)
const voiceReleasePending = ref(false)
const integrationsDialog = ref(false)
const integrationProviders = ref([])
const integrationConnections = ref([])
const integrationBusy = ref(false)
const integrationNotice = ref('')
const githubLabel = ref('')
const githubToken = ref('')
const anthropicLabel = ref('')
const anthropicToken = ref('')
const aiProvider = ref('openai')
const aiConnectionId = ref('')
const aiModelPreferences = ref({})
const inferenceProfiles = ref([])
const conversationProfileId = ref('')
const resolvedInference = ref(null)
const inferenceProfileBusy = ref(false)
const profileName = ref('')
const profileSlug = ref('')
const profileProvider = ref('')
const profileConnectionId = ref('')
const profileModel = ref('')
const profileCreateBusy = ref(false)
const inferenceProfileItems = computed(() => [
  { title: 'Herdar do perfil global', value: '' },
  ...inferenceProfiles.value
    .filter(item => item.enabled)
    .map(item => ({
      title: item.name + ' · ' + item.providerId + '/' + item.model,
      value: item.id,
    })),
])
const aiConnections = computed(() =>
  integrationConnections.value.filter(item =>
    item.provider_type === 'ai_inference' &&
    item.configured && item.enabled
  )
)
const aiProviderItems = computed(() => {
  const seen = new Set()
  return aiConnections.value
    .filter(item => {
      if (seen.has(item.provider_id)) return false
      seen.add(item.provider_id)
      return true
    })
    .map(item => ({
      title: item.provider_name || item.provider_id,
      value: item.provider_id,
    }))
})
const aiConnectionItems = computed(() =>
  aiConnections.value
    .filter(item => item.provider_id === aiProvider.value)
    .map(item => ({
      title: item.configuration?.label || item.provider_name || item.id,
      value: item.id,
    }))
)
const selectedAIConnection = computed(() =>
  integrationConnections.value.find(item => item.id === aiConnectionId.value)
)
const aiModelItems = computed(() => {
  const models = selectedAIConnection.value?.configuration?.observed_models
  return Array.isArray(models) ? models : []
})
const profileConnectionItems = computed(() =>
  aiConnections.value
    .filter(item => item.provider_id === profileProvider.value)
    .map(item => ({
      title: item.configuration?.label || item.provider_name || item.id,
      value: item.id,
    }))
)
const selectedProfileConnection = computed(() =>
  integrationConnections.value.find(
    item => item.id === profileConnectionId.value
  )
)
const profileModelItems = computed(() => {
  const models = selectedProfileConnection.value?.configuration?.observed_models
  return Array.isArray(models) ? models : []
})
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
  if (createBusy.value || memoryMutationBusy.value) return
  if (id !== selected.value && memoryPreviewDialog.value) {
    await closeMemoryPreview()
  }
  if (id !== selected.value && createDialog.value) {
    await closeCreateProposal()
  }
  selected.value = id
  const result = await call('listMessages', id)
  if (selected.value === id && result.ok) {
    messages.value = result.items
    if (!preserveNotices) {
      memoryNotice.value = ''
      knowledgeNotice.value = ''
    }
    try {
      await refreshConversationInference(id)
    } catch {
      warning.value = 'Não foi possível resolver o perfil de inferência desta conversa.'
    }
    await scrollToBottom()
  }
}

function requestDeleteConversation(conversation) {
  if (busy.value || memoryPreviewBusy.value || memoryMutationBusy.value ||
      deletionBusy.value || createDialog.value || createBusy.value) return
  deletionTarget.value = conversation
}

async function confirmDeleteConversation() {
  const target = deletionTarget.value
  if (!target || deletionBusy.value || busy.value ||
      memoryPreviewBusy.value || memoryMutationBusy.value ||
      createBusy.value || createDialog.value) return
  deletionBusy.value = true
  try {
    const result = await call('deleteConversation', target.id)
    if (!result.ok) {
      warning.value = 'Não foi possível excluir a conversa: ' + (result.error || 'unknown')
      return
    }
    deletionTarget.value = null
    await refreshConversations()
    if (selected.value === target.id) {
      if (conversations.value.length) {
        await openConversation(conversations.value[0].id)
      } else {
        selected.value = ''
        messages.value = []
      }
    }
  } catch {
    warning.value = 'Falha ao excluir a conversa. Verifique o histórico antes de repetir.'
  } finally {
    deletionBusy.value = false
  }
}

async function createConversation() {
  if (createBusy.value || memoryMutationBusy.value || busy.value) return
  if (createDialog.value) await closeCreateProposal()
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
  if (event.type === 'integration_connection') {
    integrationBusy.value = false
    githubToken.value = ''
    anthropicToken.value = ''
    if (!event.ok) {
      warning.value = 'Falha na conexão: ' + (event.error || 'unknown')
      integrationNotice.value = ''
    } else {
      warning.value = ''
      const connection = event.connection
      if (event.action === 'verify_ai' && connection) {
        const count = Array.isArray(connection.available_models)
          ? connection.available_models.length : 0
        integrationNotice.value = connection.availability === 'available'
          ? 'Credencial válida. Provider disponível' +
            (count ? ' · ' + count + ' modelos acessíveis.' : '.')
          : 'Verificação concluída: ' + connection.availability +
            (connection.last_error_code
              ? ' · ' + connection.last_error_code : '')
        if (connection.id === aiConnectionId.value) {
          if (connection.availability !== 'available') {
            credentialConfigured.value = false
          } else if (Array.isArray(connection.available_models) &&
                     connection.available_models.length) {
            const models = connection.available_models
              .map(item => item?.id)
              .filter(Boolean)
            if (models.length && !models.includes(model.value)) {
              model.value = models[0]
              aiModelPreferences.value = {
                ...aiModelPreferences.value,
                [connection.provider_id]: models[0],
              }
            }
          }
        }
      }
    }
    refreshIntegrations().catch(() => {})
    return
  }
  if (event.type === 'voice_state') {
    voiceState.value = event.state || 'IDLE'
    if (event.conversationId) voiceConversation.value = event.conversationId
    if (event.warning === 'SYNTHESIS_FAILED' ||
        event.warning === 'SYNTHESIS_UNAVAILABLE') {
      warning.value = 'A resposta textual foi preservada, mas a voz não pôde ser reproduzida.'
    }
    if (event.state === 'ERROR') {
      const messages = {
        INPUT_DEVICE_UNAVAILABLE: 'Microfone indisponível.',
        UNSUPPORTED_AUDIO_FORMAT: 'Formato do microfone não suportado.',
        EMPTY_AUDIO: 'Nenhum áudio foi capturado.',
        RECOGNITION_FAILED: 'Não foi possível reconhecer a fala.',
      }
      warning.value = messages[event.error] || 'Falha na entrada por voz.'
      voiceState.value = 'IDLE'
      voiceConversation.value = ''
    }
    return
  }
  if (event.type === 'voice_transcript') {
    voiceState.value = event.state || 'PROCESSING'
    voiceConversation.value = event.conversationId || ''
    if (event.conversationId === selected.value && typeof event.text === 'string') {
      messages.value.push({ role: 'user', content: event.text, status: 'completed' })
      messages.value.push({ role: 'assistant', content: '', status: 'streaming' })
      scrollToBottom()
    }
    return
  }
  if (event.type === 'create_proposal') {
    if (event.ok && event.conversationId === selected.value &&
        event.authorizationToken && typeof event.content === 'string') {
      createProposal.value = {
        token: event.authorizationToken,
        conversationId: event.conversationId,
        content: event.content,
        scope: event.scope,
      }
      createScope.value = event.scope || ''
      createDialog.value = true
    } else {
      createProposal.value = null
      createDialog.value = false
      call('cancelConversationalCreate').catch(() => {})
      warning.value = 'Não foi possível preparar a memória com segurança. Nada foi gravado.'
    }
    return
  }
  if (event.type === 'memory_preview') {
    memoryPreviewBusy.value = false
    const clickApproval = event.approvalMode === 'click'
    if (event.ok && event.preview && typeof event.preview.memory_id === 'string'
        && event.conversationId === selected.value && event.authorizationToken
        && (clickApproval || event.requiredPhrase)) {
      memoryPreview.value = { ...event.preview, action: event.action }
      memoryAuthorizationToken.value = event.authorizationToken
      memoryRequiredPhrase.value = event.requiredPhrase || ''
      memoryAuthorizationInput.value = ''
      memoryPreviewReplacement.value =
        typeof event.replacement === 'string' ? event.replacement : ''
      memoryApprovalMode.value = clickApproval ? 'click' : 'typed'
      memoryPreviewDialog.value = true
    } else {
      memoryPreview.value = null
      memoryAuthorizationToken.value = ''
      memoryApprovalMode.value = 'typed'
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
    memoryApprovalMode.value = 'typed'
    if (event.action === 'create') {
      createBusy.value = false
      createDialog.value = false
      createProposal.value = null
      createScope.value = ''
    }
    if (event.ok && event.status === 'CONFIRMED') {
      if (event.action === 'create') {
        if (event.transcriptPersisted === false) {
          warning.value = 'Memória gravada, mas a confirmação não pôde ser salva no histórico.'
        }
        if (selected.value) {
          openConversation(selected.value, true).catch(() => {})
          refreshConversations().catch(() => {})
        }
      }
      memoryNotice.value = event.action === 'create'
        ? 'Informação guardada no Sofias Memory com confirmação do serviço.'
        : event.replacementMemoryId
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
    knowledgeNotice.value = event.evidencePersistence !== 'SAVED'
      ? 'Não foi possível registrar fontes no histórico desta resposta.'
      : (descriptions[event.knowledgeStatus] || '')
    return
  }
  if (event.type === 'done') {
    busy.value = false
    // A voice-origin turn remains PROCESSING until TTS starts or reports unavailable.
    if (event.conversationId === voiceConversation.value && event.status !== 'completed') {
      voiceState.value = 'IDLE'
      voiceConversation.value = ''
    }
    if (event.conversationId === selected.value) {
      const statuses = {
        RESULTS_FOUND: 'Sofias Memory: memórias recuperadas para esta resposta.',
        NO_RESULTS: 'Sofias Memory: consulta concluída, sem memórias correspondentes.',
        UNAVAILABLE: 'Sofias Memory indisponível; nenhuma recuperação foi confirmada.',
        NOT_ATTEMPTED: 'A consulta de memória não foi executada.',
      }
      memoryNotice.value = statuses[event.memoryStatus] || ''
    }
    if (event.routingStatus === 'UNAVAILABLE' && event.conversationId === selected.value) {
      const routingErrors = {
        MODEL_NOT_AVAILABLE: 'O modelo selecionado não está disponível nesta conexão Anthropic.',
        BILLING_UNAVAILABLE: 'A Anthropic aceitou a credencial, mas a conta não está disponível para inferência por cobrança/créditos.',
        PROVIDER_REQUEST_INVALID: 'A Anthropic recusou a requisição estruturada do roteador.',
        RATE_LIMITED: 'A Anthropic limitou temporariamente as requisições.',
        PROVIDER_UNAVAILABLE: 'A Anthropic está temporariamente indisponível.',
        PROVIDER_TIMEOUT: 'A Anthropic excedeu o tempo de resposta.',
        PERMISSION_INSUFFICIENT: 'A conexão Anthropic não possui permissão para esta inferência.',
        AUTHENTICATION_FAILED: 'A autenticação Anthropic falhou durante a inferência.',
      }
      const base = routingErrors[event.routingError] ||
        ('Roteamento de intenções indisponível' +
          (event.routingError ? ' (' + event.routingError + ')' : '') +
          '; nenhuma ação automática de memória foi executada.')
      warning.value = event.routingErrorDetail
        ? base + ' Detalhe: ' + event.routingErrorDetail
        : base
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

async function closeCreateProposal() {
  if (createBusy.value) return
  createDialog.value = false
  createProposal.value = null
  createScope.value = ''
  try { await call('cancelConversationalCreate') } catch {}
}

async function confirmCreateProposal() {
  const proposal = createProposal.value
  if (!proposal || createBusy.value || !createScope.value ||
      proposal.conversationId !== selected.value) return
  createBusy.value = true
  warning.value = ''
  try {
    const result = await call(
      'confirmConversationalCreate',
      proposal.token, proposal.conversationId, createScope.value,
    )
    // Consume locally even when transport fails; do not retry blindly.
    createProposal.value = { ...proposal, token: '' }
    if (!result.ok) {
      createProposal.value = null
      createBusy.value = false
      createDialog.value = false
      warning.value = 'Autorização recusada: ' + (result.error || 'unknown') +
        '. Nada deve ser repetido sem verificar o journal.'
      await call('cancelConversationalCreate').catch(() => {})
    }
  } catch {
    createBusy.value = false
    createDialog.value = false
    createProposal.value = null
    warning.value = 'Resultado de envio incerto. Não repita sem consultar o journal.'
  }
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
  memoryApprovalMode.value = 'typed'
  memoryPreviewReplacement.value = ''
  try { await call('cancelPendingPersonalMutation') } catch {}
}

async function confirmMemoryMutation() {
  if (!memoryPreview.value || memoryMutationBusy.value ||
      !memoryAuthorizationToken.value ||
      (memoryApprovalMode.value === 'typed' &&
       memoryAuthorizationInput.value !== memoryRequiredPhrase.value)) return
  memoryMutationBusy.value = true
  warning.value = ''
  try {
    const result = memoryApprovalMode.value === 'click'
      ? await call('approvePersonalMutation',
          memoryAuthorizationToken.value, selected.value)
      : await call('confirmPersonalMutation',
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

function applyResolvedInference(plan) {
  resolvedInference.value = plan || null
  if (!plan) return

  aiProvider.value = plan.provider_id || ''
  aiConnectionId.value = plan.connection_id || ''
  model.value = plan.model || ''

  const connection = aiConnections.value.find(
    item => item.id === aiConnectionId.value &&
      item.provider_id === aiProvider.value
  )
  credentialConfigured.value = Boolean(connection)
  if (aiProvider.value && model.value) {
    aiModelPreferences.value = {
      ...aiModelPreferences.value,
      [aiProvider.value]: model.value,
    }
  }
}

function effectiveInferenceProfileId() {
  if (resolvedInference.value?.profile_id) {
    return resolvedInference.value.profile_id
  }
  return inferenceProfiles.value.find(item => item.slug === 'general')?.id || ''
}

async function refreshInferenceProfiles() {
  const result = await call('listInferenceProfiles')
  if (!result.ok) throw new Error(result.error || 'profiles_unavailable')
  inferenceProfiles.value = result.items || []
}

async function refreshConversationInference(conversationId) {
  if (!conversationId) {
    conversationProfileId.value = ''
    resolvedInference.value = null
    return
  }
  const result = await call('getConversationInference', conversationId)
  if (!result.ok) {
    conversationProfileId.value = ''
    resolvedInference.value = null
    throw new Error(result.error || 'inference_resolution_unavailable')
  }
  conversationProfileId.value = result.bindingProfileId || ''
  applyResolvedInference(result.resolved || null)
}

async function onConversationProfileChanged(profileId) {
  conversationProfileId.value = profileId || ''
  if (!selected.value || inferenceProfileBusy.value) return
  inferenceProfileBusy.value = true
  warning.value = ''
  try {
    const result = await call(
      'setConversationInferenceProfile',
      selected.value,
      conversationProfileId.value,
    )
    if (!result.ok) {
      warning.value = 'Não foi possível alterar o perfil da conversa: ' +
        (result.error || 'unknown')
      await refreshConversationInference(selected.value)
      return
    }
    conversationProfileId.value = result.bindingProfileId || ''
    applyResolvedInference(result.resolved || null)
  } catch {
    warning.value = 'Falha ao alterar o perfil de inferência da conversa.'
    await refreshConversationInference(selected.value).catch(() => {})
  } finally {
    inferenceProfileBusy.value = false
  }
}

function onProfileProviderChanged(providerId) {
  profileProvider.value = providerId || ''
  const first = aiConnections.value.find(
    item => item.provider_id === profileProvider.value
  )
  profileConnectionId.value = first?.id || ''
  profileModel.value = chooseModelForConnection(
    profileProvider.value, first,
  )
}

function onProfileConnectionChanged(connectionId) {
  profileConnectionId.value = connectionId || ''
  const connection = integrationConnections.value.find(
    item => item.id === profileConnectionId.value
  )
  if (connection) {
    profileProvider.value = connection.provider_id
    profileModel.value = chooseModelForConnection(
      connection.provider_id, connection,
    )
  } else {
    profileModel.value = ''
  }
}

async function createInferenceProfile() {
  if (profileCreateBusy.value || !profileName.value.trim() ||
      !profileSlug.value.trim() || !profileProvider.value ||
      !profileConnectionId.value || !profileModel.value.trim()) return
  profileCreateBusy.value = true
  warning.value = ''
  try {
    const result = await call(
      'createInferenceProfile',
      profileName.value.trim(),
      profileSlug.value.trim(),
      profileConnectionId.value,
      profileModel.value.trim(),
    )
    if (!result.ok) {
      warning.value = 'Não foi possível criar o perfil: ' +
        (result.error || 'unknown')
      return
    }
    profileName.value = ''
    profileSlug.value = ''
    await refreshInferenceProfiles()
    integrationNotice.value = 'Perfil de inferência criado: ' +
      (result.profile?.name || 'novo perfil') + '.'
  } catch {
    warning.value = 'Falha ao criar o perfil de inferência.'
  } finally {
    profileCreateBusy.value = false
  }
}

async function refreshIntegrations() {
  const [providers, connections] = await Promise.all([
    call('listIntegrationProviders'),
    call('listIntegrationConnections'),
  ])
  if (!providers.ok || !connections.ok) {
    throw new Error('integrations_unavailable')
  }
  integrationProviders.value = providers.items || []
  integrationConnections.value = connections.items || []
}

async function openIntegrations() {
  if (integrationBusy.value) return
  integrationsDialog.value = true
  warning.value = ''
  integrationNotice.value = ''
  try {
    await Promise.all([
      refreshIntegrations(),
      refreshInferenceProfiles(),
    ])
    if (!profileProvider.value) {
      profileProvider.value = aiProvider.value || aiProviderItems.value[0]?.value || ''
    }
    const currentProfileConnection = aiConnections.value.find(
      item => item.id === aiConnectionId.value &&
        item.provider_id === profileProvider.value
    )
    const firstProfileConnection = currentProfileConnection ||
      aiConnections.value.find(item => item.provider_id === profileProvider.value)
    profileConnectionId.value = firstProfileConnection?.id || ''
    profileModel.value = firstProfileConnection
      ? chooseModelForConnection(profileProvider.value, firstProfileConnection)
      : ''
  } catch {
    warning.value = 'Não foi possível carregar as integrações.'
  }
}

async function configureAnthropic() {
  if (integrationBusy.value || !anthropicToken.value.trim()) return
  integrationBusy.value = true
  warning.value = ''
  const token = anthropicToken.value
  try {
    const result = await call(
      'configureAIConnection', 'anthropic', anthropicLabel.value.trim(), token,
    )
    anthropicToken.value = ''
    if (!result.ok) {
      integrationBusy.value = false
      warning.value = 'Configuração Anthropic recusada: ' +
        (result.error || 'unknown')
    }
  } catch {
    anthropicToken.value = ''
    integrationBusy.value = false
    warning.value = 'Não foi possível entregar a credencial Anthropic ao Core.'
  }
}

function chooseModelForConnection(providerId, connection) {
  const observed = connection?.configuration?.observed_models
  const models = Array.isArray(observed) ? observed : []
  const saved = aiModelPreferences.value[providerId]
  if (saved && (!models.length || models.includes(saved))) return saved
  if (models.length) return models[0]
  return saved || (providerId === 'anthropic' ? 'claude-sonnet-5-5' : '')
}

function onAIProviderChanged(providerId) {
  aiProvider.value = providerId || ''
  const first = aiConnections.value.find(item => item.provider_id === providerId)
  aiConnectionId.value = first?.id || ''
  model.value = chooseModelForConnection(providerId, first)
  credentialConfigured.value = Boolean(first)
}

function onAIConnectionChanged(connectionId) {
  aiConnectionId.value = connectionId || ''
  const connection = integrationConnections.value.find(
    item => item.id === connectionId
  )
  if (connection) model.value = chooseModelForConnection(
    connection.provider_id, connection,
  )
}

async function ensureAISelection() {
  if (!aiProvider.value || !aiConnectionId.value || !model.value.trim()) {
    warning.value = 'Selecione Provider, conexão e modelo de IA.'
    return false
  }
  const profileId = effectiveInferenceProfileId()
  if (!profileId) {
    warning.value = 'Nenhum perfil de inferência efetivo está disponível.'
    return false
  }

  const alreadyResolved = (
    resolvedInference.value?.profile_id === profileId &&
    resolvedInference.value?.provider_id === aiProvider.value &&
    resolvedInference.value?.connection_id === aiConnectionId.value &&
    resolvedInference.value?.model === model.value.trim()
  )
  if (alreadyResolved) {
    return true
  }

  try {
    const result = await call(
      'updateInferenceProfilePrimary',
      profileId,
      aiProvider.value,
      aiConnectionId.value,
      model.value.trim(),
    )
    if (!result.ok) {
      warning.value = 'Configuração do perfil recusada: ' +
        (result.error || 'unknown')
      credentialConfigured.value = false
      return false
    }
    aiModelPreferences.value = {
      ...aiModelPreferences.value,
      [aiProvider.value]: model.value.trim(),
    }
    credentialConfigured.value = true
    await refreshInferenceProfiles()
    if (selected.value) {
      await refreshConversationInference(selected.value)
    }
    return true
  } catch {
    warning.value = 'Não foi possível atualizar o perfil de inferência.'
    return false
  }
}

async function saveEffectiveInferenceProfile() {
  if (busy.value || inferenceProfileBusy.value) return
  inferenceProfileBusy.value = true
  warning.value = ''
  try {
    const ok = await ensureAISelection()
    if (!ok) return
    if (selected.value) {
      await refreshConversationInference(selected.value)
    }
  } finally {
    inferenceProfileBusy.value = false
  }
}

async function configureGitHub() {
  if (integrationBusy.value || !githubToken.value.trim()) return
  integrationBusy.value = true
  warning.value = ''
  const token = githubToken.value
  try {
    const result = await call(
      'configureGitHubConnection', githubLabel.value.trim(), token,
    )
    // The UI never keeps a stored credential for later display/reuse.
    githubToken.value = ''
    if (!result.ok) {
      integrationBusy.value = false
      warning.value = 'Configuração recusada: ' + (result.error || 'unknown')
    }
  } catch {
    githubToken.value = ''
    integrationBusy.value = false
    warning.value = 'Não foi possível entregar a credencial ao Core.'
  }
}

async function checkAIConnection(connection) {
  if (integrationBusy.value || !connection?.id) return
  integrationBusy.value = true
  warning.value = ''
  integrationNotice.value = 'Verificando credencial e acesso ao provider…'
  try {
    const result = await call('checkAIConnection', connection.id)
    if (!result.ok) {
      integrationBusy.value = false
      integrationNotice.value = ''
      warning.value = 'Verificação recusada: ' + (result.error || 'unknown')
    }
  } catch {
    integrationBusy.value = false
    integrationNotice.value = ''
    warning.value = 'Não foi possível verificar o AI Provider.'
  }
}

async function checkIntegration(connectionId) {
  if (integrationBusy.value) return
  integrationBusy.value = true
  warning.value = ''
  try {
    const result = await call('checkIntegrationConnection', connectionId)
    if (!result.ok) {
      integrationBusy.value = false
      warning.value = 'Verificação recusada: ' + (result.error || 'unknown')
    }
  } catch {
    integrationBusy.value = false
    warning.value = 'Não foi possível verificar a conexão.'
  }
}

async function toggleIntegration(connection) {
  if (integrationBusy.value) return
  integrationBusy.value = true
  try {
    const result = await call(
      'setIntegrationConnectionEnabled', connection.id, !connection.enabled,
    )
    if (!result.ok) {
      warning.value = 'Não foi possível alterar a conexão: ' + (result.error || 'unknown')
    }
    await refreshIntegrations()
  } catch {
    warning.value = 'Falha ao alterar a conexão.'
  } finally {
    integrationBusy.value = false
  }
}

async function removeIntegration(connection) {
  if (integrationBusy.value) return
  integrationBusy.value = true
  try {
    const result = await call('removeIntegrationConnection', connection.id)
    if (!result.ok) {
      warning.value = 'Não foi possível remover a conexão: ' + (result.error || 'unknown')
    }
    await refreshIntegrations()
  } catch {
    warning.value = 'Falha ao remover a conexão.'
  } finally {
    integrationBusy.value = false
  }
}

async function startVoice(event) {
  if (!ready.value || busy.value || voiceStarting.value ||
      voiceState.value !== 'IDLE' || memoryPreviewBusy.value ||
      memoryMutationBusy.value || createDialog.value || createBusy.value) return
  if (!model.value.trim()) {
    warning.value = 'Informe o modelo de IA antes de usar voz.'
    return
  }
  if (!await ensureAISelection()) return
  voiceStarting.value = true
  voiceReleasePending.value = false
  warning.value = ''
  try {
    event?.currentTarget?.setPointerCapture?.(event.pointerId)
    let conversationId = selected.value
    if (!conversationId) {
      const created = await call('createConversation')
      if (!created.ok || !created.id) throw new Error('conversation_creation_failed')
      conversationId = created.id
      selected.value = conversationId
      messages.value = []
      await refreshConversations()
    }
    const result = await call('startVoiceCapture', conversationId)
    if (!result.ok) {
      warning.value = 'Não foi possível iniciar o microfone: ' + (result.error || 'unknown')
      voiceState.value = 'IDLE'
      return
    }
    voiceState.value = 'LISTENING'
    voiceConversation.value = conversationId
    const releasedWhileStarting = voiceReleasePending.value
    voiceStarting.value = false
    if (releasedWhileStarting) await stopVoice()
  } catch {
    voiceState.value = 'IDLE'
    warning.value = 'Não foi possível iniciar a entrada por voz.'
  } finally {
    voiceStarting.value = false
  }
}

async function stopVoice(event) {
  try { event?.currentTarget?.releasePointerCapture?.(event.pointerId) } catch {}
  if (voiceStarting.value) {
    voiceReleasePending.value = true
    return
  }
  if (voiceState.value !== 'LISTENING') return
  voiceState.value = 'TRANSCRIBING'
  try {
    const result = await call('stopVoiceCapture', model.value.trim())
    if (!result.ok) {
      voiceState.value = 'IDLE'
      voiceConversation.value = ''
      warning.value = 'Não foi possível transcrever o áudio: ' + (result.error || 'unknown')
    }
  } catch {
    voiceState.value = 'IDLE'
    voiceConversation.value = ''
    warning.value = 'Falha ao encerrar a captura de voz.'
  }
}

async function stopSpeech() {
  if (voiceState.value !== 'SPEAKING') return
  try {
    const result = await call('stopSpeech')
    if (!result.ok && result.error !== 'speech_not_active') {
      warning.value = 'Não foi possível interromper a reprodução de voz.'
    }
  } catch {
    warning.value = 'Falha ao interromper a reprodução de voz.'
  }
}

async function sendMessage() {
  const text = draft.value.trim()
  if (!ready.value || busy.value || memoryPreviewBusy.value ||
      memoryMutationBusy.value || createDialog.value || createBusy.value ||
      !text) return

  const legacyMutation = /^\/(?:esquecer|atualizar)(?:\s|$)/i.test(text)
  if (!legacyMutation && !model.value.trim()) {
    warning.value = 'Informe o modelo de IA antes de enviar a mensagem.'
    return
  }

  if (!legacyMutation && !await ensureAISelection()) return

  // Acquire the send lock before awaiting Qt: Ctrl+Enter and click must not
  // create two conversations or dispatch the same message twice.
  busy.value = true
  warning.value = ''
  memoryNotice.value = ''
  knowledgeNotice.value = ''
  let conversationId = selected.value

  try {
    // Deleting the last conversation intentionally leaves the sidebar empty.
    // The next actual send creates a conversation, not an idle startup.
    if (!conversationId) {
      const created = await call('createConversation')
      if (!created.ok || !created.id) {
        throw new Error('conversation_creation_failed')
      }
      conversationId = created.id
      selected.value = conversationId
      messages.value = []
      await refreshConversations()
    }

    if (legacyMutation) {
      busy.value = false
      await previewMemoryCommand(text)
      return
    }

    draft.value = ''
    messages.value.push({ role: 'user', content: text, status: 'completed' })
    messages.value.push({ role: 'assistant', content: '', status: 'streaming' })
    scrollToBottom()
    const result = await call('sendConversationalMessage',
      conversationId, text, model.value.trim())
    if (!result.ok) {
      busy.value = false
      draft.value = text
      warning.value = 'Envio recusado: ' + (result.error || 'unknown')
      if (selected.value === conversationId) {
        await openConversation(conversationId, true)
      }
    }
  } catch {
    busy.value = false
    draft.value = text
    warning.value = 'Não foi possível enviar. Confira a conexão com o Core e a conversa selecionada.'
    if (conversationId && selected.value === conversationId) {
      await openConversation(conversationId, true).catch(() => {})
    }
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
    aiProvider.value = initial.aiProvider || 'openai'
    aiConnectionId.value = initial.aiConnectionId || ''
    integrationConnections.value = initial.aiConnections || []
    aiModelPreferences.value = initial.aiModelPreferences || {}
    await refreshInferenceProfiles()
    ready.value = true
    if (conversations.value.length) await openConversation(conversations.value[0].id)
    else {
      selected.value = ''
      messages.value = []
      conversationProfileId.value = ''
      resolvedInference.value = null
    }
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
          <div class="brand">JARVIS <span>TB-04</span></div>
          <v-btn block color="primary" variant="flat" :disabled="!ready || busy || createBusy || memoryMutationBusy" @click="createConversation">
            Nova conversa
          </v-btn>
        </div>
        <v-list density="compact" nav>
          <v-list-item v-for="c in conversations" :key="c.id"
            :active="selected === c.id" :title="c.title"
            @click="openConversation(c.id)">
            <template #append>
              <v-btn size="x-small" variant="text" color="error"
                aria-label="Excluir conversa" title="Excluir esta conversa"
                :disabled="busy || memoryPreviewBusy || memoryMutationBusy || deletionBusy || createDialog || createBusy"
                @click.stop="requestDeleteConversation(c)">
                Excluir
              </v-btn>
            </template>
          </v-list-item>
        </v-list>
        <div class="sidebar-footer">
          <v-btn block variant="text" size="small" :disabled="integrationBusy"
            @click="openIntegrations">Integrações</v-btn>
          <div>Operação local · Windows</div>
        </div>
      </v-navigation-drawer>
      <v-main>
        <div class="main-column">
          <div class="toolbar">
            <div>
              <div class="heading">Conversa</div>
              <div class="small-text">Core Python · AI Provider · SQLite</div>
              <div v-if="resolvedInference" class="small-text inference-resolution">
                Perfil: {{ resolvedInference.profile_slug }} ·
                origem: {{ resolvedInference.selected_from }} ·
                {{ resolvedInference.provider_id }}/{{ resolvedInference.model }}
              </div>
            </div>
            <div class="ai-selector">
              <v-select
                v-model="conversationProfileId"
                :items="inferenceProfileItems"
                label="Perfil da conversa"
                variant="outlined"
                density="compact"
                hide-details
                :disabled="busy || inferenceProfileBusy || !selected"
                @update:model-value="onConversationProfileChanged"/>
              <v-select
                v-model="aiProvider"
                :items="aiProviderItems"
                label="Provider"
                variant="outlined"
                density="compact"
                hide-details
                :disabled="busy"
                @update:model-value="onAIProviderChanged"/>
              <v-select
                v-model="aiConnectionId"
                :items="aiConnectionItems"
                label="Conexão"
                variant="outlined"
                density="compact"
                hide-details
                :disabled="busy || !aiProvider"
                @update:model-value="onAIConnectionChanged"/>
              <v-select v-if="aiModelItems.length"
                v-model="model"
                :items="aiModelItems"
                class="model-input"
                label="Modelo de IA"
                variant="outlined" density="compact" hide-details/>
              <v-text-field v-else v-model="model" class="model-input"
                label="Modelo de IA"
                variant="outlined" density="compact" hide-details
                placeholder="Digite o modelo habilitado"/>
              <v-btn
                variant="outlined"
                color="primary"
                :loading="inferenceProfileBusy"
                :disabled="busy || inferenceProfileBusy || !aiProvider ||
                  !aiConnectionId || !model.trim()"
                @click="saveEffectiveInferenceProfile">
                Salvar perfil
              </v-btn>
            </div>
          </div>
          <div v-if="!credentialConfigured" class="inline-alert" role="alert">
            Configure e habilite um AI Provider em Integrações.
          </div>
          <div v-if="warning" class="inline-alert" role="alert" aria-live="assertive">
            {{ warning }}
          </div>
          <div class="history">
            <div v-if="!messages.length" class="empty">
              {{ selected ? 'Conversa pronta. Envie sua primeira mensagem.' :
                'Escreva sua mensagem. O JARVIS criará a conversa ao enviar.' }}
            </div>
            <div v-for="(m, i) in messages" :key="m.id || i"
              class="message" :class="m.role === 'user' ? 'mine' : 'assistant'">
              <div class="speaker">{{ m.role === 'user' ? 'Você' : 'JARVIS' }}</div>
              <div class="content">
                <template v-for="(part, j) in inlineParts(m.content || (m.status === 'streaming' ? 'Respondendo…' : ''))" :key="j">
                  <strong v-if="part.bold">{{ part.text }}</strong><template v-else>{{ part.text }}</template>
                </template>
              </div>
              <div v-if="m.status !== 'completed'" class="status">
                {{ m.status === 'interrupted' ? 'Resposta interrompida' :
                   m.status === 'failed' ? 'Resposta não concluída' : m.status }}
              </div>
              <div v-if="m.role === 'assistant' && m.knowledgeEvidence"
                class="message-knowledge">
                <div class="source-meta">
                  Consulta Knowledge: {{ m.knowledgeEvidence.knowledgeStatus }}
                  <span v-if="m.status !== 'completed'">
                    · Evidências obtidas, mas resposta incompleta
                  </span>
                </div>
                <details v-if="m.knowledgeEvidence.references.length"
                  class="knowledge-sources">
                  <summary>
                    Fontes documentais verificadas
                    ({{ m.knowledgeEvidence.references.length }})
                  </summary>
                  <div class="source-meta">Dataset: {{ m.knowledgeEvidence.dataset }}</div>
                  <div v-if="m.knowledgeEvidence.queryId" class="source-meta">
                    Consulta: {{ m.knowledgeEvidence.queryId }}
                  </div>
                  <div class="source-meta">
                    Recuperação: {{ m.knowledgeEvidence.retrievedAt }}
                  </div>
                  <div v-for="source in m.knowledgeEvidence.references"
                    :key="source.chunk_id" class="knowledge-source">
                    <div class="source-title">{{ source.source_name }}</div>
                    <div class="source-meta">Documento: {{ source.document_id }}</div>
                    <div class="source-meta">Fonte: {{ source.source_id }}</div>
                    <div class="source-meta">Trecho: {{ source.chunk_id }}</div>
                  </div>
                </details>
              </div>
            </div>
            <div ref="historyEnd"></div>
          </div>
          <div v-if="memoryNotice || knowledgeNotice" class="context-notice"
            role="status" aria-live="polite">
            <span v-if="memoryNotice">{{ memoryNotice }}</span>
            <span v-if="knowledgeNotice">{{ knowledgeNotice }}</span>
          </div>
          <div class="composer">
            <v-textarea v-model="draft" rows="2" auto-grow :max-rows="5"
              variant="outlined" density="comfortable" hide-details
              label="Mensagem" :disabled="busy || voiceState !== 'IDLE' || memoryPreviewBusy || memoryMutationBusy || createDialog || createBusy || !ready"
              @keydown.ctrl.enter.prevent="sendMessage"/>
            <v-btn
              variant="outlined"
              size="large"
              :color="voiceState === 'LISTENING' || voiceState === 'SPEAKING' ? 'error' : 'primary'"
              :disabled="!ready || busy || memoryPreviewBusy || memoryMutationBusy ||
                createDialog || createBusy ||
                !['IDLE', 'LISTENING', 'SPEAKING'].includes(voiceState)"
              @pointerdown.prevent="voiceState === 'SPEAKING' ? null : startVoice($event)"
              @pointerup.prevent="voiceState === 'SPEAKING' ? null : stopVoice($event)"
              @pointercancel.prevent="voiceState === 'SPEAKING' ? null : stopVoice($event)"
              @click="stopSpeech">
              {{ voiceState === 'LISTENING' ? 'Ouvindo…' :
                 voiceState === 'TRANSCRIBING' ? 'Transcrevendo…' :
                 voiceState === 'PROCESSING' ? 'Processando…' :
                 voiceState === 'SPEAKING' ? 'Parar voz' : 'Falar' }}
            </v-btn>
            <v-btn color="primary" size="large" :loading="busy || memoryPreviewBusy"
               :disabled="!ready || !draft.trim() || busy || voiceState !== 'IDLE' ||
                memoryPreviewBusy || memoryMutationBusy || createDialog || createBusy"
              @click="sendMessage">Enviar</v-btn>
          </div>
        </div>
      </v-main>
    </v-layout>
    <v-dialog v-model="integrationsDialog" max-width="760">
      <v-card title="Integrações">
        <v-card-text>
          <div class="heading mb-2">AI Providers</div>
          <div v-if="integrationNotice" class="small-text mb-3">
            {{ integrationNotice }}
          </div>
          <div class="integration-section mb-4">
            <strong>Anthropic</strong>
            <div class="small-text">
              API key · armazenada somente no Windows Credential Manager.
            </div>
            <v-text-field v-model="anthropicLabel" label="Identificação opcional"
              variant="outlined" density="compact" class="mt-4"/>
            <v-text-field v-model="anthropicToken" label="Anthropic API key"
              type="password" autocomplete="off" variant="outlined" density="compact"/>
            <v-btn color="primary" :loading="integrationBusy"
              :disabled="integrationBusy || !anthropicToken.trim()"
              @click="configureAnthropic">Conectar Anthropic</v-btn>
          </div>
          <div v-if="!integrationConnections.some(
              item => item.provider_type === 'ai_inference')" class="small-text">
            Nenhum AI Provider configurado.
          </div>
          <v-card v-for="connection in integrationConnections.filter(
              item => item.provider_type === 'ai_inference')"
            :key="connection.id" variant="outlined" class="mb-3">
            <v-card-text>
              <div class="integration-row">
                <div>
                  <strong>{{ connection.provider_name }}</strong>
                  <div>{{ connection.configuration?.label || 'Conexão de inferência' }}</div>
                  <div class="small-text">
                    configurada: {{ connection.configured ? 'sim' : 'não' }} ·
                    habilitada: {{ connection.enabled ? 'sim' : 'não' }} ·
                    disponibilidade: {{ connection.availability }}
                  </div>
                  <div v-if="connection.last_error_code" class="small-text">
                    último erro: {{ connection.last_error_code }}
                  </div>
                </div>
                <div class="integration-actions">
                  <v-btn v-if="connection.status_check_support"
                    size="small" variant="text" :disabled="integrationBusy"
                    @click="checkAIConnection(connection)">Verificar</v-btn>
                  <v-btn size="small" variant="text" :disabled="integrationBusy"
                    @click="toggleIntegration(connection)">
                    {{ connection.enabled ? 'Desabilitar' : 'Habilitar' }}
                  </v-btn>
                  <v-btn v-if="connection.configuration?.migration_source !==
                      'legacy_openai_credential'"
                    size="small" variant="text" color="error"
                    :disabled="integrationBusy" @click="removeIntegration(connection)">
                    Remover
                  </v-btn>
                </div>
              </div>
            </v-card-text>
          </v-card>

          <v-divider class="my-5"/>

          <div class="heading mb-2">Perfis de inferência</div>
          <div class="small-text mb-3">
            Um perfil aponta para um Provider, uma Connection e um modelo.
            Os seletores do topo refletem e editam o perfil efetivo da conversa:
            <strong>Geral</strong> quando herdado, ou o perfil específico quando
            houver um binding de Conversation.
          </div>
          <v-card v-for="profile in inferenceProfiles" :key="profile.id"
            variant="outlined" class="mb-2">
            <v-card-text>
              <strong>{{ profile.name }}</strong>
              <div class="small-text">
                {{ profile.slug }} · {{ profile.providerId }}/{{ profile.model }}
                <span v-if="profile.slug === 'general'"> · global</span>
              </div>
            </v-card-text>
          </v-card>
          <div class="integration-section mt-4">
            <strong>Novo perfil</strong>
            <div class="small-text">
              Escolha explicitamente o Provider, a Connection e o modelo deste perfil.
            </div>
            <div class="profile-create-grid mt-3">
              <v-text-field v-model="profileName" label="Nome"
                variant="outlined" density="compact" hide-details/>
              <v-text-field v-model="profileSlug" label="Slug"
                placeholder="coding-deep"
                variant="outlined" density="compact" hide-details/>
              <v-select
                v-model="profileProvider"
                :items="aiProviderItems"
                label="Provider do perfil"
                variant="outlined"
                density="compact"
                hide-details
                @update:model-value="onProfileProviderChanged"/>
              <v-select
                v-model="profileConnectionId"
                :items="profileConnectionItems"
                label="Conexão do perfil"
                variant="outlined"
                density="compact"
                hide-details
                :disabled="!profileProvider"
                @update:model-value="onProfileConnectionChanged"/>
              <v-select v-if="profileModelItems.length"
                v-model="profileModel"
                :items="profileModelItems"
                label="Modelo do perfil"
                variant="outlined"
                density="compact"
                hide-details/>
              <v-text-field v-else
                v-model="profileModel"
                label="Modelo do perfil"
                variant="outlined"
                density="compact"
                hide-details
                placeholder="Digite o modelo habilitado"/>
              <v-btn color="primary" :loading="profileCreateBusy"
                :disabled="profileCreateBusy || !profileName.trim() ||
                  !profileSlug.trim() || !profileProvider ||
                  !profileConnectionId || !profileModel.trim()"
                @click="createInferenceProfile">Criar perfil</v-btn>
            </div>
          </div>

          <v-divider class="my-5"/>

          <div class="heading mb-2">Integrações externas</div>
          <div class="integration-section">
            <strong>GitHub</strong>
            <div class="small-text">
              Fine-grained PAT · a credencial será armazenada somente no Windows Credential Manager.
            </div>
            <v-text-field v-model="githubLabel" label="Identificação opcional"
              variant="outlined" density="compact" class="mt-4"/>
            <v-text-field v-model="githubToken" label="Fine-grained personal access token"
              type="password" autocomplete="off" variant="outlined" density="compact"/>
            <v-btn color="primary" :loading="integrationBusy"
              :disabled="integrationBusy || !githubToken.trim()"
              @click="configureGitHub">Conectar GitHub</v-btn>
          </div>

          <v-card v-for="connection in integrationConnections.filter(
              item => item.provider_type === 'external_integration')"
            :key="connection.id" variant="outlined" class="mt-4 mb-3">
            <v-card-text>
              <div class="integration-row">
                <div>
                  <strong>{{ connection.provider_name }}</strong>
                  <div>
                    {{ connection.display_identity ||
                      connection.configuration?.label || 'Identidade ainda não verificada' }}
                  </div>
                  <div class="small-text">
                    configurada: {{ connection.configured ? 'sim' : 'não' }} ·
                    habilitada: {{ connection.enabled ? 'sim' : 'não' }} ·
                    disponibilidade: {{ connection.availability }}
                  </div>
                  <div v-if="connection.last_error_code" class="small-text">
                    último erro: {{ connection.last_error_code }}
                  </div>
                  <div v-if="connection.observed_permissions?.length" class="small-text">
                    permissões observadas: {{ connection.observed_permissions.join(', ') }}
                  </div>
                </div>
                <div class="integration-actions">
                  <v-btn size="small" variant="text" :disabled="integrationBusy"
                    @click="checkIntegration(connection.id)">Verificar</v-btn>
                  <v-btn size="small" variant="text" :disabled="integrationBusy"
                    @click="toggleIntegration(connection)">
                    {{ connection.enabled ? 'Desabilitar' : 'Habilitar' }}
                  </v-btn>
                  <v-btn size="small" variant="text" color="error"
                    :disabled="integrationBusy" @click="removeIntegration(connection)">
                    Remover
                  </v-btn>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-card-text>
        <v-card-actions>
          <v-spacer/>
          <v-btn variant="text" :disabled="integrationBusy"
            @click="integrationsDialog = false">Fechar</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog :model-value="Boolean(deletionTarget)" max-width="480" persistent>
      <v-card title="Excluir conversa?">
        <v-card-text>
          Esta ação excluirá permanentemente as mensagens e referências
          documentais desta conversa no histórico local.
          <strong>Não apagará memórias cognitivas do Sofias Memory</strong>
          nem os registros de auditoria das operações.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" :disabled="deletionBusy"
            @click="deletionTarget = null">Cancelar</v-btn>
          <v-btn color="error" :loading="deletionBusy" :disabled="deletionBusy"
            @click="confirmDeleteConversation">Excluir conversa</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-dialog v-model="createDialog" max-width="620" persistent>
      <v-card v-if="createProposal" title="Guardar esta informação?">
        <v-card-text>
          <p>O JARVIS identificou um pedido para lembrar uma informação.</p>
          <div class="memory-preview-content">{{ createProposal.content }}</div>
          <p class="memory-preview-disclaimer">
            Confira o conteúdo e o alcance antes de autorizar.
            Nenhuma informação foi gravada até agora.
          </p>
          <div v-if="createProposal.scope" class="source-meta">
            Alcance: {{ createProposal.scope === 'global'
              ? 'Preferência geral' : 'Projeto JARVIS' }}
          </div>
          <div v-else>
            <p>Essa informação vale para qual contexto?</p>
            <v-radio-group v-model="createScope" :disabled="createBusy">
              <v-radio label="Minha preferência geral" value="global" />
              <v-radio label="Somente para o projeto JARVIS" value="project:jarvis" />
            </v-radio-group>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" :disabled="createBusy"
            @click="closeCreateProposal">Não guardar</v-btn>
          <v-btn color="primary" :loading="createBusy"
            :disabled="createBusy || !createScope"
            @click="confirmCreateProposal">Guardar informação</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-dialog v-model="memoryPreviewDialog" max-width="700" persistent>
      <v-card v-if="memoryPreview" title="Confirmação supervisionada da memória">
        <v-card-text>
          <p>Operação solicitada: <strong>{{ memoryPreview.action === 'forget' ? 'Esquecer' : 'Substituir' }}</strong></p>
          <p v-if="memoryApprovalMode === 'typed'">UUID: <code>{{ memoryPreview.memory_id }}</code></p>
          <p>Escopo: {{ memoryPreview.scope }} · Tipo: {{ memoryPreview.memory_type }}</p>
          <p>Estado: {{ memoryPreview.lifecycle }}</p>
          <p>Conteúdo atual:</p>
          <div class="memory-preview-content">{{ memoryPreview.content }}</div>
          <template v-if="memoryPreview.action === 'supersede'">
            <p>Substituição proposta:</p>
            <div class="memory-preview-content">{{ memoryPreviewReplacement }}</div>
          </template>
          <p class="memory-preview-disclaimer">
            A prévia não modifica nada. A autorização vale apenas para esta memória e
            esta operação. No esquecimento, o conteúdo será eliminado permanentemente.
          </p>
          <template v-if="memoryApprovalMode === 'typed'">
            <div class="source-meta">Confirmação necessária: {{ memoryRequiredPhrase }}</div>
            <v-text-field v-model="memoryAuthorizationInput"
              label="Digite a confirmação exata"
              variant="outlined" density="compact" autocomplete="off"
              :disabled="memoryMutationBusy"/>
          </template>

        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" :disabled="memoryMutationBusy" @click="closeMemoryPreview">
            Fechar sem alterar
          </v-btn>
          <v-btn color="error" :loading="memoryMutationBusy"
            :disabled="memoryMutationBusy || !memoryAuthorizationToken ||
              (memoryApprovalMode === 'typed' &&
               memoryAuthorizationInput !== memoryRequiredPhrase)"
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
.context-notice { display: flex; flex-direction: column; gap: 2px;
  flex: 0 0 auto; padding: 6px 26px; border-top: 1px solid #243441;
  color: #7bceca; background: #101e28; font-size: 12px; }
 .message-knowledge { margin-top: 12px; border-top: 1px solid #29444a; padding-top: 9px; }
.knowledge-sources { flex: 0 0 100%; color: #a3d9d4; font-size: 12px;
  border-left: 2px solid #008080; padding: 6px 10px;
  background: rgba(0,128,128,.06); max-height: 160px; overflow-y: auto; overflow-wrap: anywhere; }
.knowledge-sources summary { cursor: pointer; font-weight: 600; }
.knowledge-source { padding: 7px 0 4px; border-top: 1px solid #29444a; }
.source-title { color: #b7e6e2; font-weight: 600; }
.source-meta { color: #829fa4; font-size: 11px; }
.source-quote { white-space: pre-wrap; max-height: 70px; overflow: auto; }
.composer { display: flex; align-items: end; gap: 14px; padding: 18px 26px 26px;
  border-top: 1px solid #243441; }
.composer .v-input { flex: 1; }
.ai-selector { display: grid;
  grid-template-columns: 210px 140px 165px minmax(185px, 1fr) auto;
  gap: 10px; min-width: 840px; align-items: center; }
.inference-resolution { margin-top: 4px; color: #79b9b5; }
.profile-create-grid { display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px;
  align-items: center; }
.profile-create-grid .v-btn { justify-self: start; }
.integration-section { padding: 4px 0; }
.integration-row { display: flex; gap: 20px; justify-content: space-between; align-items: flex-start; }
.integration-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 4px; }
</style>

<style scoped>
.memory-preview-content { white-space: pre-wrap; overflow-wrap: anywhere; padding: 12px;
  border: 1px solid #32545b; border-radius: 8px; background: #132932; }
.memory-preview-disclaimer { margin-top: 16px; font-size: 13px; color: #b5b9c9; }
</style>
