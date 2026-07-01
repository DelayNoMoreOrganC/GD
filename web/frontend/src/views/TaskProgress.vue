<template>
  <div v-loading="loading">
    <el-page-header @back="$router.push('/cases/' + caseId)" content="归档进度" style="margin-bottom: 16px" />
    <el-card style="margin-bottom: 16px">
      <el-progress :percentage="Math.round(task ? task.progress : 0)" :status="progressStatus" />
      <div style="margin-top: 10px; color: #4e5969">{{ task ? task.stage : '' }}</div>
    </el-card>

    <el-alert
      v-if="outcomeWarnings.length"
      type="warning"
      :closable="false"
      style="margin-bottom: 16px"
      title="审办结果需核对"
    >
      <ul style="margin: 4px 0 0; padding-left: 18px">
        <li v-for="(w, i) in outcomeWarnings" :key="i">{{ w }}</li>
      </ul>
    </el-alert>

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
          <el-descriptions-item label="目录命中数" v-if="task.catalog_status">
            {{ foundCount }} / {{ task.catalog_status.length }}
          </el-descriptions-item>
          <el-descriptions-item label="提取字段数" v-if="task.fields">
            {{ fieldCount }} 个
          </el-descriptions-item>
        </el-descriptions>

        <el-card shadow="never" style="margin: 12px 10px 0; border: 1px solid #e4e7ed">
          <template #header><span>审办结果 / 结案小结（可修改后重填模板）</span></template>
          <el-form label-position="top">
            <el-form-item label="执行结果类型（辅助）">
              <el-select v-model="outcomeType" style="width: 100%">
                <el-option v-for="o in outcomeTypeOptions" :key="o.value" :label="o.label" :value="o.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="审办结果">
              <el-input v-model="outcomeText" type="textarea" :rows="5" maxlength="150" show-word-limit />
            </el-form-item>
            <el-button type="primary" :loading="refilling" @click="onRefill">保存并重新生成 Word/PDF</el-button>
          </el-form>
        </el-card>

        <div v-if="task.fields" style="margin: 12px 10px 0">
          <el-collapse>
            <el-collapse-item title="查看全部已提取字段" name="fields">
              <el-table :data="fieldTable" size="small" border max-height="300">
                <el-table-column prop="name" label="字段名" width="180" />
                <el-table-column prop="value" label="提取值" min-width="200" />
              </el-table>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>
      <el-result v-else icon="error" :title="'归档失败'" :sub-title="task.error">
        <template #extra>
          <el-button @click="retry">重新生成</el-button>
        </template>
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
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Download, Document, Files } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import client from '../api/client'

const route = useRoute()
const router = useRouter()
const caseId = route.params.id as string
const taskId = route.params.taskId as string
const loading = ref(true)
const task = ref(null as any)
const logs = ref([] as string[])
const logBox = ref(null as any)
const outcomeText = ref('')
const outcomeType = ref('auto')
const refilling = ref(false)
let ws = null as WebSocket | null

const outcomeTypeOptions = [
  { value: 'auto', label: '自动（不覆盖）' },
  { value: 'zhiben', label: 'A · 常规终本' },
  { value: 'bankruptcy', label: 'B · 破产/执转破' },
  { value: 'settlement', label: 'C · 执行和解' },
  { value: 'withdraw', label: 'D · 撤回执行' },
  { value: 'completed', label: 'H · 执行完毕' },
  { value: 'none', label: '无执行（仅判决）' },
]

const progressStatus = ref('' as '' | 'success' | 'exception' | 'warning')

function pickOutcome(fields: Record<string, unknown>) {
  for (const k of ['结案小结', '审（办）结果', '审办结果']) {
    const v = fields[k]
    if (v && String(v).trim()) return String(v).trim()
  }
  return ''
}

function syncOutcomeFromTask() {
  if (!task.value?.fields) return
  outcomeText.value = pickOutcome(task.value.fields)
}

watch(() => task.value?.fields, syncOutcomeFromTask, { deep: true })

async function loadTask() {
  try {
    const { data } = await client.get('/tasks/' + taskId)
    task.value = data
    syncOutcomeFromTask()
    if (data.status === 'done') progressStatus.value = 'success'
    else if (data.status === 'failed') progressStatus.value = 'exception'
  } catch { /* ignore */ }
  finally { loading.value = false }
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
    else if (msg.type === 'done') { loadTask() }
    else if (msg.type === 'error') { loadTask() }
  }
}

function scrollLog() {
  nextTick(() => { if (logBox.value) logBox.value.scrollTop = logBox.value.scrollHeight })
}

function download(kind: string) {
  const tkn = localStorage.getItem('v5_token') || ''
  const url = '/api/tasks/' + taskId + '/download/' + kind + '?token=' + encodeURIComponent(tkn) + '&t=' + Date.now()
  const a = document.createElement('a')
  a.href = url
  a.download = ''
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

const foundCount = computed(() => {
  if (!task.value || !task.value.catalog_status) return 0
  return task.value.catalog_status.filter((c: any) => c.found).length
})

const outcomeWarnings = computed(() => {
  const w = task.value?.fields?._outcome_warnings
  return Array.isArray(w) ? w : []
})

const fieldCount = computed(() => {
  if (!task.value || !task.value.fields) return 0
  return Object.keys(task.value.fields).filter((k) => !k.startsWith('_')).length
})

const fieldTable = computed(() => {
  if (!task.value || !task.value.fields) return []
  return Object.entries(task.value.fields)
    .filter(([name]) => !name.startsWith('_'))
    .map(([name, value]) => ({
      name,
      value: String(value || '').slice(0, 200),
    }))
})

async function onRefill() {
  if (!outcomeText.value.trim()) {
    ElMessage.warning('请填写审办结果')
    return
  }
  refilling.value = true
  try {
    const fields: Record<string, string> = {
      '结案小结': outcomeText.value.trim(),
      '审（办）结果': outcomeText.value.trim(),
      '审办结果': outcomeText.value.trim(),
    }
    await client.post('/tasks/' + taskId + '/refill', {
      fields,
      order_mode: task.value?.order_mode || 'catalog',
      outcome_type: outcomeType.value,
    })
    ElMessage.success('已重新生成')
    await loadTask()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '重填失败')
  } finally {
    refilling.value = false
  }
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
.log-box { height: 320px; overflow-y: auto; background: #1d2129; border-radius: 6px; padding: 12px; font-family: 'Consolas', monospace; font-size: 12px; }
.log-line { color: #c9d1d9; line-height: 1.7; white-space: pre-wrap; word-break: break-all; }
</style>
