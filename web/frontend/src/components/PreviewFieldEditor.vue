<template>
  <div class="preview-wrap">
    <div v-if="loading" class="state-text">正在加载预览数据…</div>
    <div v-else-if="error" class="state-text error">{{ error }}</div>
    <div v-else-if="layout" class="editor-content">
      <div class="format-toolbar">
        <span class="toolbar-hint">{{ activeStyleKey ? '单元格格式' : '请先点击可编辑单元格' }}</span>
        <el-select
          v-model="toolbarFont"
          class="font-select"
          size="small"
          :disabled="!activeStyleKey"
          @change="applyStyle('fontFamily', String($event))"
        >
          <el-option v-for="font in fontOptions" :key="font.value" :label="font.label" :value="font.value" />
        </el-select>
        <el-select
          v-model="toolbarSize"
          class="size-select"
          size="small"
          :disabled="!activeStyleKey"
          @change="applyStyle('fontSize', String($event))"
        >
          <el-option v-for="size in sizeOptions" :key="size" :label="size.replace('pt', '')" :value="size" />
        </el-select>
        <el-button-group>
          <el-button size="small" :disabled="!activeStyleKey" :type="isStyleActive('fontWeight', 'bold') ? 'primary' : 'default'" @click="toggleStyle('fontWeight', 'bold', 'normal')"><strong>B</strong></el-button>
          <el-button size="small" :disabled="!activeStyleKey" :type="isStyleActive('fontStyle', 'italic') ? 'primary' : 'default'" @click="toggleStyle('fontStyle', 'italic', 'normal')"><em>I</em></el-button>
          <el-button size="small" :disabled="!activeStyleKey" :type="isStyleActive('textDecoration', 'underline') ? 'primary' : 'default'" @click="toggleStyle('textDecoration', 'underline', 'none')"><u>U</u></el-button>
        </el-button-group>
        <el-button-group>
          <el-button v-for="alignment in alignmentOptions" :key="alignment.value" size="small" :disabled="!activeStyleKey" :type="isStyleActive('textAlign', alignment.value) ? 'primary' : 'default'" @click="applyStyle('textAlign', alignment.value)">{{ alignment.label }}</el-button>
        </el-button-group>
        <el-color-picker v-model="toolbarColor" size="small" :disabled="!activeStyleKey" @change="applyStyle('color', String($event || '#000000'))" />
        <el-button size="small" :disabled="!activeStyleKey" @click="clearActiveStyle">清除格式</el-button>
      </div>

      <div ref="previewRoot" class="page-stack">
        <section
          v-for="(page, pageIndex) in layout.pages"
          :key="pageIndex"
          class="preview-paper"
          :class="templateClass"
        >
          <h2 v-if="page.title" :class="page.titleClass">{{ page.title }}</h2>
          <div v-if="page.subtitle || page.subtitleFromOrganization" class="page-subtitle">{{ pageSubtitle(page) }}</div>

          <template v-for="(block, blockIndex) in page.blocks" :key="blockIndex">
            <table v-if="block.type === 'table'" class="word-table" :class="block.className">
              <colgroup>
                <col v-for="(width, colIndex) in block.columns" :key="colIndex" :style="{ width: width + '%' }" />
              </colgroup>
              <tbody>
                <tr v-for="(row, rowIndex) in block.rows" :key="rowIndex" :style="{ height: row.height + 'mm' }">
                  <td
                    v-for="(cell, cellIndex) in row.cells"
                    :key="cellIndex"
                    :colspan="cell.colspan || 1"
                    :class="[cell.className, cell.field || cell.linesField || customEditorKeys[customKey(pageIndex, blockIndex, rowIndex, cellIndex)] ? 'editable-cell' : 'fixed-cell']"
                    :style="{ textAlign: cell.align || 'left' }"
                  >
                    <div v-if="cell.prefix" class="prefix-field">
                      <span class="cell-prefix">{{ cell.prefix }}</span>
                      <textarea
                        class="word-input word-textarea"
                        :value="cellValue(cell)"
                        :style="cellInputStyle(cell)"
                        :aria-label="cell.field"
                        @focus="activateCell(styleKey(cell), $event)"
                        @input="onCellInput(cell, $event)"
                      />
                    </div>
                    <textarea
                      v-else-if="cell.multiline || cell.linesField"
                      class="word-input word-textarea"
                      :value="cellValue(cell)"
                      :style="cellInputStyle(cell)"
                      :aria-label="cell.field || cell.linesField"
                      @focus="activateCell(styleKey(cell), $event)"
                      @input="onCellInput(cell, $event)"
                    />
                    <input
                      v-else-if="cell.field"
                      class="word-input"
                      :value="cellValue(cell)"
                      :style="cellInputStyle(cell)"
                      :aria-label="cell.field"
                      @focus="activateCell(styleKey(cell), $event)"
                      @input="updateCell(cell, inputValue($event))"
                    />
                    <div v-else-if="isCustomizableCell(cell)" class="custom-cell">
                      <span v-if="cell.text" class="fixed-text custom-prompt">{{ cell.text }}</span>
                      <div
                        v-if="customEditorKeys[customKey(pageIndex, blockIndex, rowIndex, cellIndex)]"
                        class="custom-editor-wrap"
                      >
                        <textarea
                          class="word-input word-textarea custom-textarea"
                          :data-custom-key="customKey(pageIndex, blockIndex, rowIndex, cellIndex)"
                          :value="customValues[customKey(pageIndex, blockIndex, rowIndex, cellIndex)] || ''"
                          :style="customInputStyle(customKey(pageIndex, blockIndex, rowIndex, cellIndex))"
                          aria-label="补充信息"
                          @focus="activateCell('custom:' + customKey(pageIndex, blockIndex, rowIndex, cellIndex), $event)"
                          @input="onCustomInput(customKey(pageIndex, blockIndex, rowIndex, cellIndex), $event)"
                        />
                        <button
                          type="button"
                          class="remove-custom-button"
                          title="删除文本框"
                          @click.stop="removeCustomEditor(customKey(pageIndex, blockIndex, rowIndex, cellIndex))"
                        >×</button>
                      </div>
                      <button
                        v-else
                        type="button"
                        class="add-custom-button"
                        @click.stop="createCustomEditor(customKey(pageIndex, blockIndex, rowIndex, cellIndex))"
                      >＋ 添加文本框</button>
                    </div>
                    <span v-else class="fixed-text">{{ cell.organizationName ? organizationName : cell.text }}</span>
                  </td>
                </tr>
              </tbody>
            </table>

            <p v-else-if="block.type === 'paragraph'" :class="block.className">
              <template v-for="(run, runIndex) in block.runs" :key="runIndex">
                <span v-if="run.text">{{ run.text }}</span>
                <input
                  v-else-if="run.field"
                  class="word-input line-input"
                  :value="fieldValue(run.field)"
                  :style="fieldInputStyle(run.field)"
                  :aria-label="run.field"
                  @focus="activateCell('field:' + run.field, $event)"
                  @input="updateField(run.field, inputValue($event))"
                />
              </template>
            </p>

            <ol v-else-if="block.type === 'questions'" class="quality-questions">
              <li v-for="(question, questionIndex) in block.questions" :key="questionIndex">
                <span>{{ question }}</span><span class="checkboxes">是□　　否□</span>
              </li>
            </ol>

            <p v-else-if="block.type === 'text'" :class="block.className">{{ block.text }}</p>
          </template>

          <div v-if="layout.pages.length > 1" class="page-number">{{ pageIndex + 1 }}</div>
        </section>
      </div>
    </div>
    <div v-else class="state-text error">未找到该 Word 表格的网页布局</div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch, type CSSProperties } from 'vue'
import client from '../api/client'
import { wordFormLayouts, type LayoutCell, type WordFormPage } from './wordFormLayouts'

interface PreviewField {
  key: string
  label: string
  value: any
  multiline: boolean
}

const props = defineProps<{ taskId: string; templateName: string; active: boolean }>()
const fields = ref<PreviewField[]>([])
const organizationName = ref('')
const styles = ref<Record<string, CSSProperties>>({})
const customValues = ref<Record<string, string>>({})
const customEditorKeys = ref<Record<string, boolean>>({})
const activeStyleKey = ref('')
const previewRoot = ref<HTMLElement | null>(null)
const toolbarFont = ref('SimSun, "Songti SC", "Noto Serif CJK SC", serif')
const toolbarSize = ref('10.5pt')
const toolbarColor = ref('#000000')
const loading = ref(false)
const loaded = ref(false)
const error = ref('')
const layout = computed(() => wordFormLayouts[props.templateName])
const templateClass = computed(() => `template-${props.templateName}`)
const fieldMap = computed(() => Object.fromEntries(fields.value.map((item) => [item.key, item])))
const fontOptions = [
  { label: '宋体', value: 'SimSun, "Songti SC", "Noto Serif CJK SC", serif' },
  { label: '仿宋', value: 'FangSong, STFangsong, "Noto Serif CJK SC", serif' },
  { label: '楷体', value: 'KaiTi, STKaiti, "Noto Serif CJK SC", serif' },
  { label: '微软雅黑', value: 'Microsoft YaHei, "PingFang SC", "Noto Sans CJK SC", sans-serif' },
]
const sizeOptions = ['8pt', '9pt', '10pt', '10.5pt', '11pt', '12pt', '14pt', '16pt', '18pt', '20pt', '22pt', '24pt']
const alignmentOptions = [
  { label: '左', value: 'left' },
  { label: '中', value: 'center' },
  { label: '右', value: 'right' },
  { label: '两端', value: 'justify' },
]

function inputValue(event: Event): string {
  return (event.target as HTMLInputElement | HTMLTextAreaElement).value
}

function fieldValue(key: string): string {
  const value = fieldMap.value[key]?.value
  if (Array.isArray(value)) return value.map(String).join('\n')
  return value == null ? '' : String(value)
}

function updateField(key: string, value: string) {
  const field = fieldMap.value[key]
  if (field) field.value = value
}

function lineValues(key: string): string[] {
  const raw = fieldMap.value[key]?.value
  if (Array.isArray(raw)) return raw.map((value) => String(value ?? ''))
  const text = String(raw ?? '')
  return text.includes('\n') ? text.split(/\r?\n/) : text.split(/[、，,；;]+/).map((value) => value.trim())
}

function pageSubtitle(page: WordFormPage): string {
  return page.subtitleFromOrganization ? `${organizationName.value || '律师事务所'}制` : (page.subtitle || '')
}

function styleKey(cell: LayoutCell): string {
  if (cell.linesField && cell.lineIndex != null) return `line:${cell.linesField}:${cell.lineIndex}`
  return cell.field ? `field:${cell.field}` : ''
}

function customKey(pageIndex: number, blockIndex: number, rowIndex: number, cellIndex: number): string {
  return `p${pageIndex}-b${blockIndex}-r${rowIndex}-c${cellIndex}`
}

function isCustomizableCell(cell: LayoutCell): boolean {
  const isEmpty = (cell.text ?? '') === ''
  return !cell.field && !cell.linesField && !cell.prefix && !cell.organizationName && (isEmpty || !!cell.allowCustomInput)
}

function fieldInputStyle(field: string): CSSProperties {
  return styles.value[`field:${field}`] || {}
}

function cellInputStyle(cell: LayoutCell): CSSProperties {
  const custom = styles.value[styleKey(cell)] || {}
  return { textAlign: cell.align || 'left', ...custom }
}

function customInputStyle(key: string): CSSProperties {
  return styles.value[`custom:${key}`] || {}
}

async function createCustomEditor(key: string) {
  customEditorKeys.value = { ...customEditorKeys.value, [key]: true }
  if (!(key in customValues.value)) customValues.value = { ...customValues.value, [key]: '' }
  await nextTick()
  const target = previewRoot.value?.querySelector<HTMLTextAreaElement>(`textarea[data-custom-key="${key}"]`)
  target?.focus()
  if (target) resizeTextarea(target)
}

function removeCustomEditor(key: string) {
  const nextValues = { ...customValues.value }
  const nextEditors = { ...customEditorKeys.value }
  const nextStyles = { ...styles.value }
  delete nextValues[key]
  delete nextEditors[key]
  delete nextStyles[`custom:${key}`]
  customValues.value = nextValues
  customEditorKeys.value = nextEditors
  styles.value = nextStyles
  if (activeStyleKey.value === `custom:${key}`) activeStyleKey.value = ''
}

function onCustomInput(key: string, event: Event) {
  customValues.value = { ...customValues.value, [key]: inputValue(event) }
  resizeTextarea(event.target as HTMLTextAreaElement)
}

function activateCell(key: string, event: FocusEvent) {
  activeStyleKey.value = key
  const current = styles.value[key] || {}
  const computedStyle = window.getComputedStyle(event.target as Element)
  toolbarFont.value = String(current.fontFamily || fontOptions.find((font) => computedStyle.fontFamily.includes(font.label))?.value || fontOptions[0].value)
  toolbarSize.value = String(current.fontSize || '10.5pt')
  toolbarColor.value = String(current.color || '#000000')
}

function applyStyle(property: keyof CSSProperties, value: string) {
  if (!activeStyleKey.value) return
  styles.value[activeStyleKey.value] = { ...(styles.value[activeStyleKey.value] || {}), [property]: value }
  if (property === 'fontFamily') toolbarFont.value = value
  if (property === 'fontSize') toolbarSize.value = value
  if (property === 'color') toolbarColor.value = value
  resizeAllTextareas()
}

function isStyleActive(property: keyof CSSProperties, value: string): boolean {
  return styles.value[activeStyleKey.value]?.[property] === value
}

function toggleStyle(property: keyof CSSProperties, enabled: string, disabled: string) {
  applyStyle(property, isStyleActive(property, enabled) ? disabled : enabled)
}

function clearActiveStyle() {
  if (!activeStyleKey.value) return
  const next = { ...styles.value }
  delete next[activeStyleKey.value]
  styles.value = next
  toolbarFont.value = fontOptions[0].value
  toolbarSize.value = '10.5pt'
  toolbarColor.value = '#000000'
  resizeAllTextareas()
}

function resizeTextarea(target: HTMLTextAreaElement) {
  target.style.height = 'auto'
  target.style.height = `${target.scrollHeight}px`
}

async function resizeAllTextareas() {
  await nextTick()
  previewRoot.value?.querySelectorAll<HTMLTextAreaElement>('textarea.word-textarea').forEach(resizeTextarea)
}

function cellValue(cell: LayoutCell): string {
  if (cell.linesField && cell.lineIndex != null) return lineValues(cell.linesField)[cell.lineIndex] || ''
  return cell.field ? fieldValue(cell.field) : ''
}

function updateCell(cell: LayoutCell, value: string) {
  if (cell.linesField && cell.lineIndex != null) {
    const lines = lineValues(cell.linesField)
    while (lines.length <= cell.lineIndex) lines.push('')
    lines[cell.lineIndex] = value
    updateField(cell.linesField, lines.join('\n').replace(/\n+$/, ''))
    return
  }
  if (cell.field) updateField(cell.field, value)
}

function onCellInput(cell: LayoutCell, event: Event) {
  updateCell(cell, inputValue(event))
  resizeTextarea(event.target as HTMLTextAreaElement)
}

async function loadPreview() {
  if (!props.active) return
  loading.value = true
  loaded.value = false
  error.value = ''
  try {
    const { data } = await client.get(
      '/tasks/' + props.taskId + '/preview-fields/' + encodeURIComponent(props.templateName),
    )
    fields.value = data.fields || []
    organizationName.value = data.organization_name || ''
    styles.value = data.styles || {}
    customValues.value = data.custom_values || {}
    customEditorKeys.value = Object.fromEntries(Object.keys(customValues.value).map((key) => [key, true]))
    activeStyleKey.value = ''
    loaded.value = true
    await resizeAllTextareas()
  } catch (e: any) {
    error.value = e.response?.data?.detail || '无法加载预览数据'
  } finally {
    loading.value = false
  }
}

async function saveChanges(): Promise<boolean> {
  if (!loaded.value) return true
  try {
    const values = Object.fromEntries(fields.value.map((item) => [item.key, item.value]))
    await client.put(
      '/tasks/' + props.taskId + '/preview-fields/' + encodeURIComponent(props.templateName),
      { values, styles: styles.value, custom_values: customValues.value },
    )
    return true
  } catch {
    return false
  }
}

defineExpose({ saveChanges, loadPreview })

watch(() => [props.templateName, props.active], () => {
  if (props.active) loadPreview()
}, { immediate: true })
</script>

<style scoped>
.preview-wrap {
  width: 100%;
  max-height: 78vh;
  padding: 18px;
  overflow: auto;
  border: 1px solid #dcdfe6;
  border-top: none;
  background: #e8eaed;
  box-sizing: border-box;
}

.editor-content {
  min-width: 210mm;
}

.format-toolbar {
  position: sticky;
  z-index: 20;
  top: -18px;
  display: flex;
  width: fit-content;
  min-width: 210mm;
  min-height: 46px;
  margin: -18px auto 18px;
  padding: 8px 12px;
  align-items: center;
  gap: 8px;
  border: 1px solid #dcdfe6;
  background: rgb(255 255 255 / 96%);
  box-shadow: 0 2px 8px rgb(0 0 0 / 8%);
  box-sizing: border-box;
  backdrop-filter: blur(6px);
}

.toolbar-hint {
  min-width: 108px;
  color: #606266;
  font-size: 12px;
}

.font-select { width: 132px; }
.size-select { width: 72px; }

.page-stack {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 18px;
  min-width: 210mm;
}

.preview-paper {
  position: relative;
  width: 210mm;
  min-height: 297mm;
  padding: 17mm 20mm 16mm;
  background: #fff;
  color: #000;
  box-shadow: 0 2px 10px rgb(0 0 0 / 8%);
  box-sizing: border-box;
  font-family: SimSun, "Songti SC", "Noto Serif CJK SC", serif;
  font-size: 10.5pt;
}

.preview-paper h2 {
  margin: 0 0 7mm;
  text-align: center;
  font-size: 20pt;
  font-weight: 500;
  letter-spacing: 0.42em;
  line-height: 1.25;
}

.preview-paper h2.archive-title {
  font-size: 18pt;
  letter-spacing: 0.16em;
}

.preview-paper h2.notice-title {
  margin-bottom: 2mm;
  font-size: 18pt;
}

.page-subtitle {
  margin: -4mm 0 3mm;
  text-align: right;
  font-size: 9pt;
  white-space: pre-line;
}

.template-质量监督卡 .page-subtitle {
  margin: 0 8mm 6mm;
  text-align: center;
  line-height: 1.5;
}

.word-table {
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
  border: 1.2px solid #000;
}

.word-table td {
  position: relative;
  padding: 0;
  border: 1px solid #000;
  vertical-align: middle;
  white-space: pre-line;
  box-sizing: border-box;
}

.word-table td.top-cell { vertical-align: top; }

.fixed-text {
  display: block;
  padding: 1.3mm 1.5mm;
  line-height: 1.35;
  white-space: pre-line;
}

.vertical-label .fixed-text { line-height: 1.05; }

.custom-cell,
.custom-editor-wrap {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: inherit;
}

.custom-cell {
  display: flex;
  flex-direction: column;
}

.custom-prompt {
  flex: none;
  padding-bottom: 0.5mm;
}

.custom-editor-wrap,
.add-custom-button { flex: 1; }

.add-custom-button {
  width: 100%;
  height: 100%;
  min-height: 7mm;
  padding: 1mm;
  border: 0;
  background: transparent;
  color: #909399;
  cursor: pointer;
  font: inherit;
  font-size: 8pt;
  opacity: 0.32;
  transition: opacity 0.15s, background 0.15s;
}

.fixed-cell:hover .add-custom-button,
.add-custom-button:focus {
  background: rgb(64 158 255 / 6%);
  color: #409eff;
  opacity: 1;
}

.custom-textarea { padding-right: 6mm; }

.remove-custom-button {
  position: absolute;
  z-index: 2;
  top: 1px;
  right: 1px;
  width: 18px;
  height: 18px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: rgb(245 108 108 / 12%);
  color: #f56c6c;
  cursor: pointer;
  font-size: 15px;
  line-height: 18px;
  opacity: 0.35;
}

.custom-editor-wrap:hover .remove-custom-button,
.remove-custom-button:focus { opacity: 1; }

.word-input {
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 7mm;
  margin: 0;
  padding: 1.1mm 1.5mm;
  border: 0;
  border-radius: 0;
  outline: 0;
  background: transparent;
  color: #000;
  box-shadow: none;
  box-sizing: border-box;
  font: inherit;
  line-height: 1.35;
}

.word-textarea {
  display: block;
  height: auto;
  field-sizing: content;
  resize: none;
  overflow: hidden;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
  word-break: break-word;
}

.word-input:focus {
  background: rgb(64 158 255 / 6%);
  box-shadow: inset 0 0 0 1px rgb(64 158 255 / 32%);
}

.prefix-field {
  display: flex;
  width: 100%;
  height: 100%;
  min-height: inherit;
  align-items: stretch;
}

.cell-prefix {
  flex: none;
  padding: 1.3mm 0 1.3mm 1.5mm;
  line-height: 1.35;
  white-space: nowrap;
}

.prefix-field .word-input { padding-left: 0.5mm; }

.delivery-meta {
  display: flex;
  align-items: baseline;
  width: 55%;
  margin: 0 0 1.5mm;
  line-height: 7mm;
}

.delivery-meta.case-number { margin-top: -2mm; }

.line-input {
  display: inline-block;
  flex: 1;
  height: 7mm;
  min-height: 0;
  padding: 0 1mm;
}

.delivery-note {
  margin: 0 0 3mm;
  text-align: right;
  font-size: 8.5pt;
}

.quality-questions {
  margin: 4mm 0 0;
  padding-left: 6mm;
  font-size: 10pt;
  line-height: 1.45;
}

.quality-questions li {
  position: relative;
  min-height: 8mm;
  padding: 0 26mm 0 1mm;
}

.checkboxes {
  position: absolute;
  top: 0;
  right: 0;
  white-space: nowrap;
}

.quality-evaluation,
.quality-suggestion,
.quality-signature,
.quality-note {
  white-space: pre-line;
  font-size: 9.5pt;
  line-height: 1.45;
}

.quality-evaluation { margin: 2mm 0 3mm; }
.quality-suggestion { min-height: 22mm; margin: 0; }
.quality-signature { margin: 0 0 4mm; text-align: right; }
.quality-note { margin: 0; text-indent: 2em; }

.notice-paragraph {
  margin: 0 0 2.2mm;
  text-align: justify;
  text-indent: 2em;
  font-size: 10.5pt;
  line-height: 1.55;
}

.notice-signature {
  margin: 6mm 0 7mm;
  text-align: right;
  white-space: pre;
}

.complaint-phones {
  margin: 0;
  line-height: 1.7;
  white-space: pre-line;
}

.page-number {
  position: absolute;
  right: 0;
  bottom: 8mm;
  left: 0;
  text-align: center;
  font-size: 9pt;
}

.state-text {
  padding: 40px;
  text-align: center;
  color: #606266;
}

.state-text.error { color: #f56c6c; }

@media (max-width: 900px) {
  .preview-wrap { padding: 10px; }
  .format-toolbar { top: -10px; margin-top: -10px; }
}
</style>
