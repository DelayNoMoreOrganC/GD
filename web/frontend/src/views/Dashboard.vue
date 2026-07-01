<template>
  <div>
    <div class="page-header">
      <h3>案件管理</h3>
      <el-button type="primary" :icon="Plus" @click="showCreate = true">新建案件</el-button>
    </div>
    <el-table :data="cases" v-loading="loading" stripe style="width: 100%">
      <el-table-column prop="title" label="案件名称" min-width="200" />
      <el-table-column prop="case_type" label="类型" width="100">
        <template #default="{ row }">{{ typeLabel(row.case_type) }}</template>
      </el-table-column>
      <el-table-column prop="file_count" label="文件数" width="90" align="center" />
      <el-table-column label="最近任务" width="110" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.last_task_status" :type="statusType(row.last_task_status)" size="small">{{ statusLabel(row.last_task_status) }}</el-tag>
          <span v-else style="color:#c0c4cc">—</span>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">{{ fmtDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" :width="auth.isAdmin ? 180 : 120" align="center">
        <template #default="{ row }">
          <el-button size="small" @click="goDetail(row.id)">打开</el-button>
          <el-button v-if="auth.isAdmin" size="small" type="danger" @click="onDeleteCase(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showCreate" title="新建案件" width="440px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="案件名称">
          <el-input v-model="form.title" placeholder="如：2014-兴泰贸易" />
        </el-form-item>
        <el-form-item label="案件类型">
          <el-select v-model="form.case_type" style="width: 100%">
            <el-option v-for="t in types" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="onCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import client from '../api/client'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const cases = ref([])
const loading = ref(false)
const showCreate = ref(false)
const creating = ref(false)
const form = reactive({ title: '', case_type: 'civil' })
const types = [
  { value: 'civil', label: '民事' },
  { value: 'criminal', label: '刑事' },
  { value: 'admin', label: '行政' },
  { value: 'nonlit', label: '非诉' },
  { value: 'counsel', label: '顾问' },
]

async function load() {
  loading.value = true
  try {
    const { data } = await client.get('/cases')
    cases.value = data
  } catch (e: any) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

async function onCreate() {
  if (!form.title.trim()) { ElMessage.warning('请输入案件名称'); return }
  creating.value = true
  try {
    const { data } = await client.post('/cases', { ...form })
    showCreate.value = false
    form.title = ''
    form.case_type = 'civil'
    ElMessage.success('已创建')
    router.push('/cases/' + data.id)
  } catch (e: any) {
    ElMessage.error('创建失败')
  } finally {
    creating.value = false
  }
}

function goDetail(id: string) { router.push('/cases/' + id) }

async function onDeleteCase(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除案件「${row.title}」？此操作不可恢复。`, '删除案件', { type: 'warning' })
    await client.delete('/cases/' + row.id)
    ElMessage.success('已删除')
    await load()
  } catch { /* cancelled */ }
}

function typeLabel(v: string) { return types.find(t => t.value === v)?.label || v }
function statusLabel(v: string) { return { pending: '等待', running: '进行中', awaiting_review: '待核对', done: '完成', failed: '失败' }[v] || v }
function statusType(v: string) { return { pending: 'info', running: 'warning', awaiting_review: 'warning', done: 'success', failed: 'danger' }[v] || 'info' }
function fmtDate(v: string) { return v ? v.replace('T', ' ').slice(0, 16) : '' }

onMounted(load)
</script>

<style scoped>
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.page-header h3 { margin: 0; }
</style>
