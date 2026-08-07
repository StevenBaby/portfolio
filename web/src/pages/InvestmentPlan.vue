<template>
  <div class="investment-plan">
    <div class="plan-form">
      <n-select v-model:value="form.code" :options="codeOptions" :disabled="Boolean(editingCode)" placeholder="选择持仓" size="small" style="width: 180px" />
      <n-input-number v-model:value="form.amount" :min="1" :precision="2" placeholder="定投金额" size="small" style="width: 140px" />
      <n-select v-model:value="form.frequency" :options="frequencyOptions" size="small" style="width: 100px" />
      <n-date-picker v-model:value="form.nextDate" type="date" clearable size="small" style="width: 150px" />
      <n-checkbox v-model:checked="form.enabled">启用</n-checkbox>
      <n-button type="primary" size="small" @click="savePlan">{{ editingCode ? "更新计划" : "保存计划" }}</n-button>
      <n-button v-if="editingCode" size="small" @click="resetForm">取消编辑</n-button>
    </div>

    <div v-if="error" class="plan-error">{{ error }}</div>
    <n-data-table
      v-if="plans.length"
      :columns="columns"
      :data="plans"
      :bordered="false"
      :striped="true"
      size="small"
      flex-height
      style="flex: 1"
    />
    <div v-else class="empty-state">暂无定投计划</div>
  </div>
</template>

<script setup>
import { computed, h, onMounted, reactive, ref } from "vue";
import {
  NButton,
  NCheckbox,
  NDataTable,
  NDatePicker,
  NInputNumber,
  NSelect,
  NSwitch,
} from "naive-ui";

import { holdingProfiles } from "../parse.js";

const props = defineProps({ holdings: { type: Array, default: () => [] } });
const emit = defineEmits(["plans-change"]);
const API = import.meta.env.DEV ? "http://localhost:8090" : "";
const plans = ref([]);
const error = ref("");
const editingCode = ref(null);
const form = reactive({ code: null, amount: null, frequency: "每月", nextDate: null, enabled: true });
const frequencyOptions = [{ value: "每周", label: "每周" }, { value: "每月", label: "每月" }];
const codeOptions = computed(() => props.holdings.filter((h) => h.shares > 0).map((h) => ({ value: h.code, label: `${h.code} ${h.name}` })));

function dateToText(timestamp) {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}
function textToDate(value) {
  if (!value) return null;
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day).getTime();
}
function emitEnabledPlans() {
  emit("plans-change", plans.value.filter((p) => p.enabled === "1").map((p) => p.code));
}
async function loadPlans() {
  try {
    const response = await fetch(`${API}/api/plan`);
    plans.value = await response.json();
    emitEnabledPlans();
  } catch { error.value = "定投计划加载失败"; }
}
function resetForm() {
  editingCode.value = null;
  Object.assign(form, { code: null, amount: null, frequency: "每月", nextDate: null, enabled: true });
}
function editPlan(plan) {
  editingCode.value = plan.code;
  Object.assign(form, { code: plan.code, amount: Number(plan.amount), frequency: plan.frequency, nextDate: textToDate(plan.next_date), enabled: plan.enabled === "1" });
}
async function savePlan() {
  error.value = "";
  if (!form.code || !form.amount || !form.nextDate) { error.value = "请选择持仓并填写金额和日期"; return; }
  const holding = props.holdings.find((item) => item.code === form.code);
  const response = await fetch(`${API}/api/plan`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code: form.code, name: holding?.name || "", amount: form.amount, frequency: form.frequency, next_date: dateToText(form.nextDate), enabled: form.enabled }) });
  if (!response.ok) { error.value = "定投计划保存失败"; return; }
  await loadPlans();
  resetForm();
}
async function togglePlan(plan, enabled) {
  await updatePlan({ ...plan, enabled });
}
async function updatePlan(plan) {
  const response = await fetch(`${API}/api/plan`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...plan, amount: Number(plan.amount), enabled: plan.enabled === "1" || plan.enabled === true }) });
  if (!response.ok) { error.value = "定投计划更新失败"; return; }
  await loadPlans();
}
async function removePlan(code) {
  const response = await fetch(`${API}/api/plan/${code}`, { method: "DELETE" });
  if (!response.ok) { error.value = "定投计划删除失败"; return; }
  await loadPlans();
}
const columns = [
  { title: "代码", key: "code", width: 80 },
  { title: "名称", key: "name", minWidth: 120, render: (row) => {
    const holding = props.holdings.find((item) => item.code === row.code);
    const name = holdingProfiles.value[row.code]?.name || row.name;
    const color = holdingProfiles.value[row.code]?.color || "#d03050";
    return h("div", { class: "holding-name-cell" }, [
      h("span", name),
      h("span", { class: "holding-name-color", style: { backgroundColor: color }, title: color }),
    ]);
  } },
  { title: "定投金额", key: "amount", width: 110, render: (row) => `¥${Number(row.amount).toFixed(2)}` },
  { title: "周期", key: "frequency", width: 75 },
  { title: "下次定投", key: "next_date", width: 120 },
  { title: "状态", key: "enabled", width: 85, render: (row) => h(NSwitch, { value: row.enabled === "1", size: "small", onUpdateValue: (value) => togglePlan(row, value) }) },
  { title: "操作", key: "actions", width: 100, render: (row) => h("span", { class: "plan-actions" }, [h(NButton, { text: true, size: "small", onClick: () => editPlan(row) }, { default: () => "编辑" }), h(NButton, { text: true, size: "small", type: "error", onClick: () => removePlan(row.code) }, { default: () => "删除" })]) },
];
onMounted(loadPlans);
</script>
