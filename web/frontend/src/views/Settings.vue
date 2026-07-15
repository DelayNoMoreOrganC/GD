<template>
  <div v-loading="loading">
    <h3 style="margin-top:0">我的 API 配置</h3>
    <el-card style="max-width: 640px">
      <el-alert
        title="以下密钥仅保存到当前登录账号，不会与同一律所或其他账号共享。"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 18px"
      />
      <el-form :model="form" label-width="150px" label-position="right">
        <el-divider content-position="left">DeepSeek (LLM)</el-divider>
        <div class="api-apply-link">
          <el-link
            href="https://platform.deepseek.com/api_keys"
            target="_blank"
            rel="noopener noreferrer"
            type="primary"
            :underline="false"
          >
            前往 DeepSeek 开放平台申请 API Key
            <el-icon class="link-icon"><TopRight /></el-icon>
          </el-link>
        </div>
        <el-form-item label="API Key">
          <el-input v-model="form.deepseek_api_key" placeholder="sk-..." show-password />
        </el-form-item>
        <el-form-item label="Base URL">
          <el-input v-model="form.deepseek_base_url" />
        </el-form-item>
        <el-form-item label="模型">
          <el-input v-model="form.deepseek_model" placeholder="deepseek-v4-flash" />
        </el-form-item>
        <el-divider content-position="left">MinerU (OCR)</el-divider>
        <div class="api-apply-link">
          <el-link
            href="https://mineru.net/apiManage/token"
            target="_blank"
            rel="noopener noreferrer"
            type="primary"
            :underline="false"
          >
            前往 MinerU 官网申请 API Token
            <el-icon class="link-icon"><TopRight /></el-icon>
          </el-link>
        </div>
        <el-form-item label="API Token">
          <el-input v-model="form.mineru_api_token" type="textarea" :rows="2" show-password />
        </el-form-item>
        <el-divider content-position="left">归档</el-divider>
        <el-form-item label="默认正文排序">
          <el-radio-group v-model="form.order_mode">
            <el-radio value="catalog">按目录序</el-radio>
            <el-radio value="original">按原页序</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="onSave">保存我的配置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import client from '../api/client'

const loading = ref(false)
const saving = ref(false)
const form = reactive({ deepseek_api_key: '', deepseek_base_url: 'https://api.deepseek.com', deepseek_model: 'deepseek-v4-flash', mineru_api_token: '', order_mode: 'catalog' })

async function load() {
  loading.value = true
  try {
    const { data } = await client.get('/settings')
    Object.assign(form, data)
  } catch { ElMessage.error('加载失败') }
  finally { loading.value = false }
}

async function onSave() {
  saving.value = true
  try {
    await client.put('/settings', { ...form })
    ElMessage.success('已保存')
  } catch { ElMessage.error('保存失败') }
  finally { saving.value = false }
}

onMounted(load)
</script>

<style scoped>
.api-apply-link {
  margin: -4px 0 14px 150px;
  font-size: 13px;
}

.link-icon {
  margin-left: 4px;
  vertical-align: -2px;
}

@media (max-width: 640px) {
  .api-apply-link { margin-left: 0; }
}
</style>
