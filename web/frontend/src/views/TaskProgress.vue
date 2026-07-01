<!-- V6: awaiting_review uses in-browser Word editor -->
<template>
  <div v-loading="loading">
    <el-page-header @back="$router.push('/cases/' + caseId)" content="归档进度" style="margin-bottom: 16px" />
    <el-card style="margin-bottom: 16px">
      <el-progress :percentage="Math.round(task ? task.progress : 0)" :status="progressStatus" />
      <div style="margin-top: 10px; color: #4e5969">{{ task ? task.stage : '' }}</div>
    </el-card>

    <el-alert v-if="outcomeWarnings.length" type="warning" :closable="false" style="margin-bottom: 16px" title="审办结果需核对">
      <ul style="margin: 4px 0 0; padding-left: 18px"><li v-for="(w, i) in outcomeWarnings" :key="i">{{ w }}</li></ul>
    </el-alert>

    <el-card v-if="showReviewEditor" ref="reviewCardRef" class="review-card" style="margin-bottom: 16px">
      <template #header>
        <span>{{ task.status === 'done' ? '查看并编辑系统表' : '核对并编辑系统表（合并 PDF 前）' }}</span>
      </template>
      <p class="review-hint">
        {{ task.status === 'done'
          ? '在下方查看或修改 Word 内容与格式，保存后写入该任务的 Word 文书。'
          : '在下方直接修改 Word 内容与格式，保存后确认合并归档。' }}
      </p>
      <el-tabs v-model="previewTab" class="review-tabs" @tab-change="onTabChange">
        <el-tab-pane v-for="name in templateNames" :key="name" :label="name" :name="name">
          <DocxReviewEditor
            :ref="(el) => setEditorRef(name, el)"
            :task-id="taskId"
            :template-name="name"
            :active="previewTab === name"
          />
        </el-tab-pane>
      </el-tabs>
      <el-alert v-if="missingItems.length" type="info" :closable="false" title="缺失目录项（合并时可忽略）" style="margin:12px 0">
        <span v-for="m in missingItems" :key="m.seq" style="margin-right:8px">seq{{ m.seq }} {{ m.name }}</span>
      </el-alert>
      <el-button type="primary" :loading="saving" @click="onSaveCurrent">保存当前表格</el-button>
      <el-button type="primary" plain :loading="savingAll" @click="onSaveAll">保存全部表格</el-button>
      <el-button v-if="task.status === 'awaiting_review'" type="success" :loading="assembling" @click="onAssemble">确认无误，合并归档 PDF</el-button>
      <el-alert v-else-if="task.status === 'done'" type="info" :closable="false" title="提示" style="margin-top:12px">
        修改会保存至 Word 文书；如需更新归档 PDF，请返回案件页重新生成。
      </el-alert>
    </el-card>

    <el-card style="margin-bottom: 16px" v-if="task && (task.status === 'done' || task.status === 'failed')">
      <div v-if="task.status === 'done'">
        <el-result icon="success" title="归档完成" sub-title="归档结果长期保存在该案件下，可随时返回查看">
          <template #extra>
            <el-button type="primary" :icon="Download" @click="download('archive')">下载完整归档 PDF</el-button>
            <el-button :icon="Document" @click="download('docx')">下载 Word 文书</el-button>
            <el-button :icon="Files" @click="download('zip')">下载全部(ZIP)</el-button>
          </template>
        </el-result>
        <el-descriptions :column="2" border style="margin: 12px 10px 0">
          <el-descriptions-item label="任务编号">{{ task.id }}</el-descriptions-item>
          <el-descriptions-item label="归档状态">已完成</el-descriptions-item>
          <el-descriptions-item label="目录命中数" v-if="task.catalog_status">{{ foundCount }} / {{ task.catalog_status.length }}</el-descriptions-item>
        </el-descriptions>
      </div>
      <el-result v-else icon="error" :title="'归档失败'" :sub-title="task.error">
        <template #extra><el-button @click="retry">重新生成</el-button></template>
      </el-result>
    </el-card>

    <el-card>
      <template #header><span>实时日志</span></template>
      <div class="log-box" ref="logBox">
        <div v-for="(line, i) in logs" :key="i" class="log-line">{{ line }}</div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Download, Document, Files } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import client from '../api/client'
import DocxReviewEditor from '../components/DocxReviewEditor.vue'

const route = useRoute()
const router = useRouter()
const caseId = route.params.id as string
const taskId = route.params.taskId as string
const loading = ref(true)
const task = ref(null as any)
const logs = ref([] as string[])
const logBox = ref(null as any)
const reviewCardRef = ref(null as any)
const previewTab = ref('立案审批表')
const saving = ref(false)
const savingAll = ref(false)
const assembling = ref(false)
const editorRefs = ref<Record<string, any>>({})
let ws = null as WebSocket | null

const templateNames = ['立案审批表', '送达材料清单', '档案卷宗', '结案报告表', '质量监督卡']
const progressStatus = ref('' as '' | 'success' | 'exception' | 'warning')

const showReviewEditor = computed(() =>
  task.value && (task.value.status === 'awaiting_review' || task.value.status === 'done'),
)

function scrollToReview() {
  nextTick(() => {
    const el = reviewCardRef.value?.$el as HTMLElement | undefined
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

function setEditorRef(name: string, el: any) {
  if (el) editorRefs.value[name] = el
}

function onTabChange() { /* active prop handles reload */ }

async function loadTask() {
  try {
    const { data } = await client.get('/tasks/' + taskId)
    task.value = data
    if (data.status === 'done') progressStatus.value = 'success'
    else if (data.status === 'failed') progressStatus.value = 'exception'
    else if (data.status === 'awaiting_review') progressStatus.value = 'warning'
    else progressStatus.value = ''
    if (route.query.review === '1' && (data.status === 'done' || data.status === 'awaiting_review')) {
      scrollToReview()
    }
  } finally { loading.value = false }
}

function connectWs() {
  const token = localStorage.getItem('v5_token') || ''
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  ws = new WebSocket(proto + '://' + location.host + '/api/ws/tasks/' + taskId + '?token=' + token)
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data)
    if (msg.type === 'log') { logs.value.push(msg.text); scrollLog() }
    else if (msg.type === 'progress') {
      if (task.value) { task.value.progress = msg.progress; task.value.stage = msg.stage }
    }
    else if (msg.type === 'done' || msg.type === 'error') { loadTask() }
  }
}

function scrollLog() {
  nextTick(() => { if (logBox.value) logBox.value.scrollTop = logBox.value.scrollHeight })
}

function download(kind: string) {
  const tkn = localStorage.getItem('v5_token') || ''
  const url = '/api/tasks/' + taskId + '/download/' + kind + '?token=' + encodeURIComponent(tkn) + '&t=' + Date.now()
  const a = document.createElement('a')
  a.href = url; a.download = ''; document.body.appendChild(a); a.click(); document.body.removeChild(a)
}

const foundCount = computed(() => task.value?.catalog_status?.filter((c: any) => c.found).length ?? 0)
const outcomeWarnings = computed(() => {
  const w = task.value?.fields?._outcome_warnings
  return Array.isArray(w) ? w : []
})
const missingItems = computed(() => (task.value?.catalog_status || []).filter((c: any) => !c.found))

async function onSaveCurrent() {
  const ed = editorRefs.value[previewTab.value]
  if (!ed?.saveDocx) { ElMessage.warning('编辑器未就绪'); return }
  saving.value = true
  try {
    if (await ed.saveDocx()) ElMessage.success('已保存：' + previewTab.value)
    else ElMessage.error('保存失败')
  } finally { saving.value = false }
}

async function onSaveAll() {
  savingAll.value = true
  let ok = 0
  try {
    for (const name of templateNames) {
      const ed = editorRefs.value[name]
      if (ed?.saveDocx && await ed.saveDocx()) ok++
    }
    ElMessage.success('已保存 ' + ok + ' / ' + templateNames.length + ' 份表格')
  } finally { savingAll.value = false }
}

async function onAssemble() {
  try {
    await ElMessageBox.confirm('合并前是否已保存全部修改？', '确认合并', { confirmButtonText: '已保存，继续合并', cancelButtonText: '取消', type: 'warning' })
  } catch { return }
  assembling.value = true
  try {
    await onSaveAll()
    await client.post('/tasks/' + taskId + '/assemble', {
      order_mode: task.value?.order_mode || 'catalog',
      skipped: missingItems.value.map((m: any) => m.seq),
    })
    ElMessage.success('正在合并归档 PDF')
    await loadTask()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '合并失败')
  } finally { assembling.value = false }
}

function retry() {
  client.post('/cases/' + caseId + '/generate', { order_mode: 'catalog' }).then(({ data }) => {
    router.replace('/cases/' + caseId + '/tasks/' + data.id)
    setTimeout(() => location.reload(), 300)
  })
}

onMounted(() => { loadTask(); connectWs() })
onUnmounted(() => { if (ws) ws.close() })
</script>

<style scoped>
.review-hint { color: #606266; margin: 0 0 8px; font-size: 13px; }
.review-tabs :deep(.el-tabs__header) { margin-bottom: 0; }
.review-tabs :deep(.el-tabs__nav-wrap::after) { height: 1px; }
.review-tabs :deep(.el-tabs__content) { padding: 0; }
.review-tabs :deep(.el-tab-pane) { padding: 0; }
.review-card :deep(.el-card__body) { padding-top: 12px; }

.log-box { height: 320px; overflow-y: auto; background: #1d2129; border-radius: 6px; padding: 12px; font-family: Consolas, monospace; font-size: 12px; }
.log-line { color: #c9d1d9; line-height: 1.7; white-space: pre-wrap; word-break: break-all; }
</style>
