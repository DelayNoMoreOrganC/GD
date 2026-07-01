<template>
  <div v-loading="loading">
    <el-page-header @back="$router.push('/cases')" :content="detail ? detail.title : '案件'" style="margin-bottom: 16px" />
    <el-row :gutter="20">
      <el-col :span="14">
        <el-card v-if="hasDoneTasks" style="margin-bottom: 16px; border: 1px solid #67c23a">
          <template #header>
            <span style="color: #67c23a; font-weight: 600">
              <el-icon><CircleCheckFilled /></el-icon> 已完成归档
            </span>
          </template>
          <div v-for="t in doneTasks" :key="t.id" style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0">
            <div>
              <div style="font-weight: 500">任务 #{{ t.id }}</div>
              <div style="font-size: 12px; color: #909399">完成时间: {{ fmtDate(t.finished_at) }}</div>
            </div>
            <div>
              <el-button size="small" type="warning" :icon="Edit" @click="goReview(t.id)">预览编辑</el-button>
              <el-button size="small" type="primary" :icon="Download" @click="downloadTask(t.id, 'archive')">PDF</el-button>
              <el-button size="small" :icon="Document" @click="downloadTask(t.id, 'docx')">DOCX</el-button>
              <el-button size="small" :icon="Files" @click="downloadTask(t.id, 'zip')">ZIP</el-button>
              <el-button size="small" type="danger" :icon="Delete" @click="onDeleteTask(t)">删除</el-button>
            </div>
          </div>
        </el-card>
        <el-card>
          <template #header><span>归档文件</span></template>
          <el-alert type="info" :closable="false" style="margin-bottom: 12px">
            路径A（单卷综合）：只上传1个PDF，选「默认（综合文档）」。路径B（多文件分类）：分别上传各文书并标注类型；同一目录序号可上传多份文档。
          </el-alert>
          <el-form-item label="上传类型" style="margin-bottom: 12px">
            <el-select v-model="uploadDocType" filterable style="width: 100%">
              <el-option v-for="t in docTypes" :key="t.value" :label="t.label" :value="t.value" />
            </el-select>
          </el-form-item>
          <el-upload
            drag
            :show-file-list="false"
            :auto-upload="true"
            :http-request="onUpload"
            accept=".pdf"
            multiple
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽 PDF 到此处，或<em>点击上传</em></div>
          </el-upload>
          <el-table :data="detail ? detail.files : []" style="margin-top: 12px" size="small">
            <el-table-column prop="filename" label="文件名" min-width="200" />
            <el-table-column label="类型" min-width="280">
              <template #default="{ row }">
                <el-select v-model="row.doc_type" size="small" filterable style="width: 100%" @change="onTypeChange(row)">
                  <el-option v-for="t in docTypes" :key="t.value" :label="t.label" :value="t.value" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="大小" width="90">
              <template #default="{ row }">{{ Math.round(row.file_size / 1024) }} KB</template>
            </el-table-column>
            <el-table-column label="操作" width="70" align="center">
              <template #default="{ row }">
                <el-button size="small" type="danger" :icon="Delete" circle @click="onDeleteFile(row)" />
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card>
          <template #header><span>生成归档</span></template>
          <el-form label-position="top">
            <el-form-item label="案件类型">
              <el-select v-model="caseType" style="width: 100%" @change="loadDocTypes">
                <el-option v-for="t in caseTypes" :key="t.value" :label="t.label" :value="t.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="正文排序">
              <el-radio-group v-model="orderMode">
                <el-radio value="catalog">按目录序</el-radio>
                <el-radio value="original">按原页序</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-button type="primary" :icon="MagicStick" :loading="generating" style="width: 100%" @click="onGenerate">一键生成完整归档</el-button>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { UploadFilled, Delete, MagicStick, Download, Document, Files, CircleCheckFilled, Edit } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import client from '../api/client'

const route = useRoute()
const router = useRouter()
const caseId = route.params.id as string
const loading = ref(false)
const detail = ref(null as any)
const caseType = ref('civil')
const orderMode = ref('catalog')
const generating = ref(false)
const uploadDocType = ref('default')
const docTypes = ref([{ value: 'default', label: '默认（综合文档）', seq: null as number | null }])
const caseTypes = [
  { value: 'civil', label: '民事' }, { value: 'criminal', label: '刑事' },
  { value: 'admin', label: '行政' }, { value: 'nonlit', label: '非诉' }, { value: 'counsel', label: '顾问' },
]
const hasDoneTasks = ref(false)
const doneTasks = ref([] as any[])

function fmtDate(v: string | null) {
  return v ? v.replace("T", " ").slice(0, 16) : ""
}

function downloadTask(taskId: number, kind: string) {
  const tkn = localStorage.getItem("v5_token") || ""
  const url = "/api/tasks/" + taskId + "/download/" + kind + "?token=" + encodeURIComponent(tkn) + "&t=" + Date.now()
  const a = document.createElement("a")
  a.href = url
  a.download = ""
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

function goReview(taskId: number) {
  router.push('/cases/' + caseId + '/tasks/' + taskId + '?review=1')
}

async function loadDocTypes() {
  try {
    const { data } = await client.get('/cases/meta/doc-types', { params: { case_type: caseType.value } })
    docTypes.value = data
    if (!docTypes.value.some(t => t.value === uploadDocType.value)) {
      uploadDocType.value = 'default'
    }
  } catch {
    docTypes.value = [{ value: 'default', label: '默认（综合文档）', seq: null }]
  }
}

function docTypeLabel(value: string) {
  return docTypes.value.find(t => t.value === value)?.label || value
}

async function load() {
  loading.value = true
  try {
    const { data } = await client.get('/cases/' + caseId)
    detail.value = data
    caseType.value = data.case_type || 'civil'
    doneTasks.value = data.done_tasks || []
    hasDoneTasks.value = doneTasks.value.length > 0
    await loadDocTypes()
  } catch { ElMessage.error('加载失败') }
  finally { loading.value = false }
}

async function onUpload(req: any) {
  const fd = new FormData()
  fd.append('file', req.file)
  fd.append('doc_type', uploadDocType.value)
  try {
    await client.post('/cases/' + caseId + '/files', fd)
    ElMessage.success('上传成功：' + docTypeLabel(uploadDocType.value))
    await load()
  } catch { ElMessage.error('上传失败') }
}

async function onTypeChange(row: any) {
  try {
    await client.patch('/cases/' + caseId + '/files/' + row.id, { doc_type: row.doc_type })
    ElMessage.success('类型已更新')
  } catch {
    ElMessage.error('类型更新失败')
    await load()
  }
}

async function onDeleteFile(row: any) {
  try {
    await ElMessageBox.confirm('确认删除该文件？', '提示', { type: 'warning' })
    await client.delete('/cases/' + caseId + '/files/' + row.id)
    await load()
  } catch { /* cancelled */ }
}

async function onDeleteTask(row: any) {
  try {
    await ElMessageBox.confirm('确认删除该归档结果？下载项将被移除且不可恢复。', '删除归档结果', { type: 'warning' })
    await client.delete('/tasks/' + row.id)
    ElMessage.success('已删除')
    await load()
  } catch { /* cancelled */ }
}

async function onGenerate() {
  if (!detail.value || detail.value.files.length === 0) { ElMessage.warning('请先上传文件'); return }
  generating.value = true
  try {
    const { data } = await client.post('/cases/' + caseId + '/generate', { order_mode: orderMode.value })
    router.push('/cases/' + caseId + '/tasks/' + data.id)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '生成失败')
  } finally { generating.value = false }
}

onMounted(load)
</script>
