<template>
  <div class="page-container">
    <div class="stats-bar">
      <div class="stat-card"><div class="stat-label">总资产</div><div class="stat-value">{{ displayData(latest?.total, hideAmount, money, "***") }}</div></div>
      <div class="stat-card"><div class="stat-label">总资产增量</div><div class="stat-value" :class="totalDelta >= 0 ? 'amount-positive' : 'amount-negative'">{{ totalDeltaText }}</div></div>
      <div class="stat-card"><div class="stat-label">资产类别</div><div class="stat-value">{{ visibleAssets.length }}</div></div>
      <div class="stat-card"><div class="stat-label">快照数量</div><div class="stat-value">{{ rows.length }}</div></div>
      <div class="stat-card stat-right"><div class="stat-label">最新日期</div><div class="stat-value">{{ latest?.date || "--" }}</div></div>
    </div>

    <div class="filter-bar">
      <n-checkbox v-model:checked="showPension" class="ml-auto" :disabled="editPropertyInfo">公积金</n-checkbox>
      <n-checkbox v-model:checked="hideAmount">隐藏信息</n-checkbox>
      <n-checkbox v-model:checked="editPropertyInfo">编辑信息</n-checkbox>
    </div>

    <div class="sub-tabs">
      <div class="sub-tab" :class="{ active: subTab === 'summary' }" @click="subTab = 'summary'">资产汇总</div>
      <div class="sub-tab" :class="{ active: subTab === 'table' }" @click="subTab = 'table'">资产明细</div>
      <div class="sub-tab" :class="{ active: subTab === 'pie' }" @click="subTab = 'pie'">资产分布</div>
      <div class="sub-tab" :class="{ active: subTab === 'bar' }" @click="subTab = 'bar'">直方图</div>
      <div class="sub-tab" :class="{ active: subTab === 'line' }" @click="subTab = 'line'">时序图</div>
    </div>

    <div v-show="subTab === 'summary'" class="property-summary-actions">
      <template v-if="editPropertyInfo">
        <n-input v-model:value="addingAsset" size="small" placeholder="新增资产类型" style="width: 160px" @keyup.enter="addAsset" />
        <n-button size="small" type="primary" @click="addAsset">添加品种</n-button>
        <n-date-picker
          v-if="editingSnapshot"
          :value="dateToTimestamp(editingDate)"
          type="date"
          clearable="false"
          size="small"
          style="width: 150px"
          @update:value="editingDate = timestampToDate($event)"
        />
        <n-button v-if="editingSnapshot" size="small" type="primary" @click="saveSnapshotEdit">保存快照</n-button>
        <n-button v-if="editingSnapshot" size="small" @click="cancelSnapshotEdit">取消</n-button>
        <n-button v-else size="small" @click="startSnapshotEdit">编辑最新快照</n-button>
      </template>
    </div>
    <n-data-table v-show="subTab === 'summary'" :columns="summaryColumns" :data="summaryRows" :bordered="false" :striped="true" size="small" :row-key="(row) => row.asset" flex-height style="flex: 1" />
    <n-data-table v-show="subTab === 'table'" :columns="columns" :data="visibleRows" :pagination="pagination" :bordered="false" :striped="true" size="small" :row-key="(row) => row.date" flex-height style="flex: 1" />

    <div v-show="subTab === 'pie'" class="chart-container property-chart-container">
      <v-chart :key="chartRenderKey" :option="pieOption" :update-options="{ notMerge: true }" autoresize class="property-chart" />
    </div>

    <div v-show="subTab === 'bar'" class="chart-container property-chart-container">
      <div class="chart-toolbar">
        <span class="chart-btn ml-auto" @click="clearLegend">清空</span>
        <span class="chart-btn" @click="selectLegend">全选</span>
        <n-select v-model:value="chartMetric" :options="chartMetricOptions" size="small" style="width: 100px" />
      </div>
      <v-chart :key="chartRenderKey" :option="barOption" :update-options="{ notMerge: true }" autoresize class="property-chart" />
    </div>

    <div v-show="subTab === 'line'" class="chart-container property-chart-container">
      <div class="chart-toolbar">
        <span class="chart-btn ml-auto" @click="clearLegend">清空</span>
        <span class="chart-btn" @click="selectLegend">全选</span>
        <n-select v-model:value="chartMetric" :options="chartMetricOptions" size="small" style="width: 100px" />
      </div>
      <v-chart :key="chartRenderKey" :option="lineOption" :update-options="{ notMerge: true }" autoresize class="property-chart" />
    </div>
  </div>
</template>

<script setup>
import { computed, h, onMounted, reactive, ref, watch } from "vue";
import { NButton, NCheckbox, NColorPicker, NDataTable, NDatePicker, NInput, NSelect } from "naive-ui";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { BarChart, LineChart, PieChart } from "echarts/charts";
import { CanvasRenderer } from "echarts/renderers";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import { displayData, persistedRef, propertyProfiles, loadPropertyProfiles, savePropertyProfile } from "../parse.js";

use([CanvasRenderer, BarChart, LineChart, PieChart, GridComponent, LegendComponent, TooltipComponent]);

const API = import.meta.env.DEV ? "http://localhost:8090" : "";
const hideAmount = persistedRef("property_hideAmount", false);
const showPension = persistedRef("property_showPension", true);
const editPropertyInfo = persistedRef("property_editInfo", false);
const subTab = persistedRef("property_subTab", "summary");
const assets = ref([]);
const rows = ref([]);
const legendSelected = ref({});
const chartMetric = persistedRef("property_chartMetric", "amount");
const chartMetricOptions = [
  { value: "amount", label: "金额" },
  { value: "delta", label: "增量" },
];
const money = (value) => Number(value || 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const presetColors = ["#d03050", "#18a058", "#2080f0", "#f0a020", "#8a2be2", "#00a6a6", "#e06c9f", "#7c9a2e"];
const chartRenderKey = computed(() => `${hideAmount.value}-${chartMetric.value}-${showPension.value}`);
const visibleAssets = computed(() => showPension.value ? assets.value : assets.value.filter((asset) => asset !== "公积金"));
const visibleRows = computed(() => rows.value.map((row) => {
  const values = Object.fromEntries(visibleAssets.value.map((asset) => [asset, row.values[asset] || 0]));
  return { ...row, values, total: Object.values(values).reduce((sum, value) => sum + value, 0) };
}));
const latest = computed(() => visibleRows.value[0] || null);
const previous = computed(() => visibleRows.value[1] || null);
const totalDelta = computed(() => (latest.value && previous.value ? latest.value.total - previous.value.total : 0));
const totalDeltaText = computed(() => {
  if (hideAmount.value) return "***";
  if (!previous.value) return "--";
  const sign = totalDelta.value >= 0 ? "+" : "";
  return `${sign}${money(totalDelta.value)}`;
});
const pagination = reactive({
  page: 1, pageSize: 20, showSizePicker: true, pageSizes: [20, 50, 100], showQuickJumper: true,
  onChange: (page) => { pagination.page = page; },
  onUpdatePageSize: (size) => { pagination.pageSize = size; pagination.page = 1; },
});
const editingSnapshot = ref(false);
const editingDate = ref("");
const editingValues = ref({});
const addingAsset = ref("");
const showPensionBeforeEdit = ref(true);
watch(editPropertyInfo, (editing) => {
  if (editing) {
    showPensionBeforeEdit.value = showPension.value;
    showPension.value = true;
  } else if (!editingSnapshot.value) {
    showPension.value = showPensionBeforeEdit.value;
  }
}, { immediate: true });

function isValidColor(color) { return typeof color === "string" && /^#[0-9a-f]{6}$/i.test(color); }
function assetColor(asset, index = 0) { return propertyProfiles.value[asset]?.color || presetColors[index % presetColors.length]; }
function valueText(value) { return displayData(value, hideAmount.value, money, "***"); }
function percentText(value) { return displayData(value, hideAmount.value, (v) => `${v.toFixed(2)}%`, "***"); }
function updateAssetColor(row, color) {
  propertyProfiles.value = { ...propertyProfiles.value, [row.asset]: { color } };
  savePropertyProfile(row.asset, color);
}
function dateToTimestamp(date) {
  const [year, month, day] = date.split("-").map(Number);
  return year && month && day ? new Date(year, month - 1, day).getTime() : null;
}
function timestampToDate(timestamp) {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}
function startSnapshotEdit() {
  const source = rows.value[0];
  if (!source) return;
  showPensionBeforeEdit.value = showPension.value;
  showPension.value = true;
  editingSnapshot.value = true;
  editingDate.value = source.date;
  editingValues.value = { ...source.values };
}
function cancelSnapshotEdit() {
  showPension.value = showPensionBeforeEdit.value;
  editingSnapshot.value = false;
  editingDate.value = "";
  editingValues.value = {};
}
async function saveSnapshotEdit() {
  const date = editingDate.value.trim();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return;
  const nextAssets = [...assets.value];
  const nextRows = rows.value.map((row) => ({ date: row.date, values: { ...row.values } }));
  const target = nextRows.find((row) => row.date === date) || { date, values: {} };
  target.date = date;
  target.values = Object.fromEntries(nextAssets.map((asset) => [asset, editingValues.value[asset] ?? 0]));
  if (!nextRows.some((row) => row.date === date)) nextRows.push(target);
  const response = await fetch(`${API}/api/properties`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ assets: nextAssets, rows: nextRows }) });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const data = await response.json();
  assets.value = data.assets;
  rows.value = data.rows;
  cancelSnapshotEdit();
}
async function addAsset() {
  const asset = addingAsset.value.trim();
  if (!asset || asset === "日期" || assets.value.includes(asset)) return;
  const nextAssets = [...assets.value, asset];
  const nextRows = rows.value.map((row) => ({ date: row.date, values: { ...row.values, [asset]: 0 } }));
  const response = await fetch(`${API}/api/properties`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ assets: nextAssets, rows: nextRows }) });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const data = await response.json();
  assets.value = data.assets;
  rows.value = data.rows;
  addingAsset.value = "";
}

const summaryRows = computed(() => {
  const total = latest.value?.total || 0;
  return visibleAssets.value.map((asset, index) => ({
    asset,
    value: latest.value?.values?.[asset] || 0,
    percent: total ? ((latest.value?.values?.[asset] || 0) / total) * 100 : 0,
    color: assetColor(asset, index),
  })).sort((a, b) => b.value - a.value);
});
const summaryColumns = computed(() => [
  { title: "日期", key: "date", width: 150, render: () => latest.value?.date },
  { title: "资产类型", key: "asset", width: 150, render: (row) => h("div", { class: "holding-name-cell" }, [h("span", row.asset), h("span", { class: "holding-name-color", style: { backgroundColor: row.color }, title: row.color })]) },
  { title: "最新金额", key: "value", align: "right", render: (row) => editingSnapshot.value ? h(NInput, { value: String(editingValues.value[row.asset] ?? 0), size: "small", type: "text", onUpdateValue: (value) => { editingValues.value = { ...editingValues.value, [row.asset]: value }; } }) : h("span", { class: "amount-positive" }, valueText(row.value)), sorter: (a, b) => a.value - b.value },
  { title: "增量", key: "delta", align: "right", render: (row) => {
    if (!previous.value) return "--";
    const delta = row.value - (previous.value.values[row.asset] || 0);
    return h("span", { class: delta >= 0 ? "amount-positive" : "amount-negative" }, displayData(delta, hideAmount.value, money, "***"));
  }, sorter: (a, b) => a.value - b.value },
  { title: "占比", key: "percent", align: "right", render: (row) => percentText(row.percent), sorter: (a, b) => a.percent - b.percent },
  ...(editPropertyInfo.value ? [{ title: "颜色", key: "color", width: 100, render: (row) => hideAmount.value ? "***" : h(NColorPicker, { value: row.color, swatches: presetColors, modes: ["hex"], showAlpha: false, size: "small", onUpdateValue: (value) => updateAssetColor(row, value), "onUpdate:value": (value) => updateAssetColor(row, value) }) }] : []),
]);
const columns = computed(() => [
  { title: "日期", key: "date", width: 120 },
  ...visibleAssets.value.map((asset, index) => ({ title: asset, key: asset, align: "right", render: (row) => h("span", { style: { color: assetColor(asset, index) } }, valueText(row.values[asset])) })),
  { title: "总资产", key: "total", align: "right", render: (row) => h("span", { class: "amount-positive" }, valueText(row.total)) },
]);
const chartDates = computed(() => visibleRows.value.slice().reverse().map((row) => row.date));
const chartRows = computed(() => {
  const chronological = visibleRows.value.slice().reverse();
  return chronological.map((row, index) => ({
    ...row,
    values: Object.fromEntries(visibleAssets.value.map((asset) => [
      asset,
      chartMetric.value === "delta" && index > 0
        ? (row.values[asset] || 0) - (chronological[index - 1].values[asset] || 0)
        : chartMetric.value === "delta" ? 0 : (row.values[asset] || 0),
    ])),
  }));
});
const latestValues = computed(() => visibleAssets.value.map((asset) => latest.value?.values?.[asset] || 0));
function axisValue(value) {
  if (hideAmount.value) return "***";
  return Number(value || 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

const barOption = computed(() => ({
  backgroundColor: "transparent", grid: { left: 72, right: 24, top: 36, bottom: 64 },
  tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, formatter: (params) => params?.length ? `${params[0].axisValue}<br/>${params.map((p) => `${p.marker}${hideAmount.value ? "***" : p.seriesName}: ${axisValue(p.value)}`).join("<br/>")}` : "" },
  legend: { type: "scroll", bottom: 4, textStyle: { color: "#999" }, selected: legendSelected.value, formatter: (name) => hideAmount.value ? "***" : name },
  xAxis: { type: "category", data: chartDates.value, axisLabel: { color: "#999" }, axisLine: { lineStyle: { color: "#333" } } },
  yAxis: { type: "value", axisLabel: { color: "#888", formatter: (value) => axisValue(value) }, splitLine: { lineStyle: { color: "#222" } } },
  series: visibleAssets.value.map((asset, index) => ({ name: asset, type: "bar", stack: "asset-total", data: chartRows.value.map((row) => row.values[asset] || 0), itemStyle: { color: assetColor(asset, index) }, barMaxWidth: 42 })),
}));
const pieOption = computed(() => ({
  backgroundColor: "transparent",
  tooltip: { trigger: "item", formatter: (params) => `${hideAmount.value ? "***" : params.name}<br/>${axisValue(params.value)} (${params.percent}%)` },
  legend: { type: "scroll", bottom: 4, textStyle: { color: "#999", fontSize: 11 }, formatter: (name) => hideAmount.value ? "***" : name },
  series: [{
    type: "pie", radius: "60%", center: ["50%", "45%"],
    data: latestValues.value.map((value, index) => ({ name: visibleAssets.value[index], value, itemStyle: { color: assetColor(visibleAssets.value[index], index) } })).filter((item) => item.value > 0),
    label: { show: true, color: "#aaa", fontSize: 11, formatter: (params) => hideAmount.value ? "***" : `${params.name}\n${params.percent}%` },
    itemStyle: { borderColor: "#18181c", borderWidth: 2 },
  }],
}));
const lineOption = computed(() => ({
  backgroundColor: "transparent", grid: { left: 72, right: 24, top: 36, bottom: 44 },
  legend: { type: "scroll", bottom: 4, textStyle: { color: "#999" }, selected: legendSelected.value, formatter: (name) => hideAmount.value ? "***" : name },
  tooltip: { trigger: "axis", formatter: (params) => params?.length ? `${params[0].axisValue}<br/>${params.filter((p) => p.value !== 0).map((p) => `${p.marker}${hideAmount.value ? "***" : p.seriesName}: ${axisValue(p.value)}`).join("<br/>")}` : "" },
  xAxis: { type: "category", data: chartDates.value, axisLabel: { color: "#999" }, axisLine: { lineStyle: { color: "#333" } } },
  yAxis: { type: "value", axisLabel: { color: "#888", formatter: (value) => axisValue(value) }, splitLine: { lineStyle: { color: "#222" } } },
  series: visibleAssets.value.map((asset, index) => ({ name: asset, type: "line", smooth: true, symbol: "circle", symbolSize: 4, data: chartRows.value.map((row) => row.values[asset] || 0), itemStyle: { color: assetColor(asset, index) }, lineStyle: { color: assetColor(asset, index) } })),
}));
function selectLegend() { legendSelected.value = Object.fromEntries(visibleAssets.value.map((asset) => [asset, true])); }
function clearLegend() { legendSelected.value = Object.fromEntries(visibleAssets.value.map((asset) => [asset, false])); }

watch(assets, (nextAssets) => {
  const next = { ...propertyProfiles.value };
  nextAssets.forEach((asset, index) => {
    if (!isValidColor(next[asset]?.color)) {
      next[asset] = { color: presetColors[index % presetColors.length] };
      savePropertyProfile(asset, next[asset].color);
    }
  });
  propertyProfiles.value = next;
  selectLegend();
});

onMounted(async () => {
  await loadPropertyProfiles();
  try {
    const response = await fetch(`${API}/api/properties`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    assets.value = data.assets || [];
    rows.value = data.rows || [];
  } catch (error) { console.error("加载资产数据失败:", error); }
});
</script>
