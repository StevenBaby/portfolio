<template>
  <div class="page-container">
    <div class="stats-bar">
      <div class="stat-card">
        <div class="stat-label">持仓品种</div>
        <div class="stat-value buy">{{ activeCount }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">持仓总成本</div>
        <div class="stat-value">
          {{ displayData(totalHoldingCost, hideAmount, (v) => "¥" + v.toFixed(2), "***") }}
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-label">持仓市值</div>
        <div class="stat-value">
          {{ displayData(totalMarketValue, hideAmount, (v) => "¥" + v.toFixed(2), "***") }}
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-label">总盈亏</div>
        <div class="stat-value" :class="totalPnlResult.cls">
          {{ totalPnlResult.text }}
        </div>
      </div>
    </div>
    <div class="filter-bar">
      <n-checkbox v-model:checked="showCleared" class="ml-auto">显示已清仓</n-checkbox>
      <n-checkbox v-model:checked="hideAmount">隐藏信息</n-checkbox>
      <n-checkbox v-model:checked="editHoldingInfo">编辑信息</n-checkbox>
    </div>
    <div class="sub-tabs">
      <div class="sub-tab" :class="{ active: subTab === 'table' }" @click="subTab = 'table'">持仓明细</div>
      <div class="sub-tab" :class="{ active: subTab === 'pie' }" @click="subTab = 'pie'">持仓占比</div>
      <div class="sub-tab" :class="{ active: subTab === 'plan' }" @click="subTab = 'plan'">定投计划</div>
    </div>
    <n-data-table
      v-show="subTab === 'table'"
      :columns="holdingColumns"
      :data="filteredHoldings"
      :bordered="false"
      :striped="true"
      size="small"
      flex-height
      style="flex: 1"
    />
    <div v-show="subTab === 'pie'" class="chart-container" style="flex: 1; overflow: hidden">
      <div class="chart-toolbar">
        <n-select v-model:value="pieMetric" :options="pieMetricOptions" size="small" style="width: 120px; margin-left: auto" />
      </div>
      <v-chart :option="pieOption" autoresize style="height: calc(100% - 30px); min-height: 270px" />
    </div>
    <InvestmentPlan v-show="subTab === 'plan'" :holdings="props.holdings" @plans-change="updatePlanCodes" />
  </div>
</template>

<script setup>
import { ref, computed, h, watch } from "vue";
import { NDataTable, NTag, NCheckbox, NSelect, NColorPicker } from "naive-ui";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { PieChart } from "echarts/charts";
import { LegendComponent, TooltipComponent } from "echarts/components";
import InvestmentPlan from "./InvestmentPlan.vue";
import {
  formatMoney,
  displayData,
  pnlFormat,
  pctFormat,
  persistedRef,
  holdingProfiles,
} from "../parse.js";

use([CanvasRenderer, PieChart, LegendComponent, TooltipComponent]);

const hideAmount = persistedRef("holdings_hideAmount", false);
const editHoldingInfo = persistedRef("holdings_editInfo", false);
const investmentPlanCodes = ref(new Set());

function updatePlanCodes(codes) {
  investmentPlanCodes.value = new Set(codes);
}
const subTab = persistedRef("holdings_subTab", "table");
const pieMetric = persistedRef("holdings_pieMetric", "marketValue");
const pieMetricOptions = [
  { value: "marketValue", label: "市值" },
  { value: "total_cost", label: "成本" },
  { value: "shares", label: "数量" },
];

const props = defineProps({
  holdings: { type: Array, default: () => [] },
  quotes: { type: Object, default: () => ({}) },
});

const showCleared = persistedRef("holdings_showCleared", false);

const allHoldings = computed(() => {
  return props.holdings
    .map((h) => {
      const q = props.quotes[h.code];
      const price = q?.price || 0;
      const marketValue = price * h.shares;
      const floatPnl = h.shares > 0 ? marketValue - h.total_cost : -h.total_cost;
      const pnlPct = h.total_cost > 0 ? (floatPnl / h.total_cost) * 100 : 0;
      const cleared = h.shares === 0;
      return { ...h, price, marketValue, floatPnl, pnlPct, cleared };
    })
    .sort((a, b) => b.total_cost - a.total_cost);
});

const filteredHoldings = computed(() => {
  if (showCleared.value) return allHoldings.value;
  return allHoldings.value.filter((h) => !h.cleared);
});

const activeCount = computed(
  () => props.holdings.filter((h) => h.shares > 0).length
);
const totalHoldingCost = computed(() =>
  allHoldings.value
    .filter((h) => !h.cleared)
    .reduce((s, h) => s + h.total_cost, 0)
);
const totalMarketValue = computed(() =>
  allHoldings.value
    .filter((h) => !h.cleared)
    .reduce((s, h) => s + h.marketValue, 0)
);
const totalFloatPnl = computed(
  () => totalMarketValue.value - totalHoldingCost.value
);
const totalPnlResult = computed(() =>
  pnlFormat(totalFloatPnl.value, hideAmount.value)
);

function pnlRender(val) {
  const { text, cls } = pnlFormat(val, hideAmount.value);
  return h("span", { class: cls }, text);
}

function pctRender(val) {
  const { text, cls } = pctFormat(val, hideAmount.value);
  return h("span", { class: cls }, text);
}

const presetColors = [
  "#d03050",
  "#18a058",
  "#2080f0",
  "#f0a020",
  "#8a2be2",
  "#00a6a6",
  "#e06c9f",
  "#7c9a2e",
];

function setHoldingColor(row, color) {
  updateHoldingProfile(row, "color", color);
}

function randomHoldingColor() {
  const hue = Math.floor(Math.random() * 360);
  const saturation = 0.68;
  const lightness = 0.58;
  const chroma = (1 - Math.abs(2 * lightness - 1)) * saturation;
  const segment = hue / 60;
  const second = chroma * (1 - Math.abs((segment % 2) - 1));
  const [red, green, blue] = segment < 1
    ? [chroma, second, 0]
    : segment < 2
    ? [second, chroma, 0]
    : segment < 3
    ? [0, chroma, second]
    : segment < 4
    ? [0, second, chroma]
    : segment < 5
    ? [second, 0, chroma]
    : [chroma, 0, second];
  const match = lightness - chroma / 2;
  return `#${[red, green, blue]
    .map((value) => Math.round((value + match) * 255).toString(16).padStart(2, "0"))
    .join("")}`;
}

function isValidHoldingColor(color) {
  return typeof color === "string" && /^#[0-9a-f]{6}$/i.test(color);
}

watch(
  () => props.holdings,
  (holdings) => {
    const next = { ...holdingProfiles.value };
    let changed = false;
    holdings.forEach((holding) => {
      if (!isValidHoldingColor(next[holding.code]?.color)) {
        next[holding.code] = {
          ...(next[holding.code] || {}),
          color: randomHoldingColor(),
        };
        changed = true;
      }
    });
    if (changed) holdingProfiles.value = next;
  },
  { immediate: true }
);

function updateHoldingProfile(row, field, value) {
  holdingProfiles.value = {
    ...holdingProfiles.value,
    [row.code]: {
      ...(holdingProfiles.value[row.code] || {}),
      [field]: value,
    },
  };
}

const holdingColumns = [
  {
    title: "代码",
    key: "code",
    width: 80,
    render: (row) => displayData(row.code, hideAmount.value, null, "***"),
  },
  {
    title: "名称",
    key: "name",
    width: 120,
    render: (row) => {
      const customName = holdingProfiles.value[row.code]?.name || "";
      const displayName = customName || row.name;
      if (hideAmount.value) return "***";
      if (!editHoldingInfo.value) {
        return h("span", { title: row.fullname }, displayName);
      }
      return h("input", {
        class: "holding-profile-input",
        value: customName,
        placeholder: row.name,
        onInput: (event) => updateHoldingProfile(row, "name", event.target.value),
      });
    },
  },
  {
    title: "颜色",
    key: "color",
    width: 90,
    render: (row) => {
      const color = holdingProfiles.value[row.code]?.color || "#d03050";
      if (hideAmount.value) return "***";
      if (!editHoldingInfo.value) {
        return h("span", { class: "holding-color-swatch", style: { backgroundColor: color }, title: color });
      }
      return h(NColorPicker, {
        value: color,
        swatches: presetColors,
        modes: ["hex"],
        showAlpha: false,
        size: "small",
        onUpdateValue: (value) => setHoldingColor(row, value),
        "onUpdate:value": (value) => setHoldingColor(row, value),
      });
    },
  },
  {
    title: "持仓",
    key: "shares",
    width: 90,
    render: (row) =>
      displayData(row.shares > 0 ? row.shares : null, hideAmount.value, (v) =>
        v.toLocaleString()
      ),
    sorter: (a, b) => a.shares - b.shares,
  },
  {
    title: "平均成本",
    key: "avg_cost",
    width: 90,
    render: (row) =>
      displayData(row.shares > 0 ? row.avg_cost : null, hideAmount.value, (v) =>
        v.toFixed(4)
      ),
    sorter: (a, b) => a.avg_cost - b.avg_cost,
  },
  {
    title: "现价",
    key: "price",
    width: 80,
    render: (row) =>
      displayData(row.price || null, hideAmount.value, (v) => v.toFixed(3)),
    sorter: (a, b) => a.price - b.price,
  },
  {
    title: "总成本",
    key: "total_cost",
    width: 110,
    render: (row) => {
      if (hideAmount.value) return "***";
      const cls = row.total_cost < 0 ? "amount-negative" : "";
      return h("span", { class: cls }, formatMoney(row.total_cost));
    },
    sorter: (a, b) => a.total_cost - b.total_cost,
  },
  {
    title: "市值",
    key: "marketValue",
    width: 110,
    render: (row) =>
      displayData(
        row.price && row.shares > 0 ? row.marketValue : null,
        hideAmount.value,
        formatMoney
      ),
    sorter: (a, b) => a.marketValue - b.marketValue,
  },
  {
    title: "浮动盈亏",
    key: "floatPnl",
    width: 110,
    render: (row) =>
      row.cleared
        ? pnlRender(row.floatPnl)
        : row.price
        ? pnlRender(row.floatPnl)
        : hideAmount.value
        ? "***"
        : "--",
    sorter: (a, b) => a.floatPnl - b.floatPnl,
  },
  {
    title: "收益率",
    key: "pnlPct",
    width: 80,
    render: (row) => {
      if (!row.price || row.shares === 0)
        return hideAmount.value ? "***" : "--";
      return pctRender(row.pnlPct);
    },
    sorter: (a, b) => a.pnlPct - b.pnlPct,
  },
  {
    title: "买卖",
    key: "trades",
    width: 60,
    render: (row) => `${row.buy_count}/${row.sell_count}`,
  },
  {
    title: "状态",
    key: "status",
    width: 70,
    render: (row) =>
      row.cleared
        ? h("span", { class: "tag-cleared" }, "已清仓")
        : h("span", { class: "status-tags" }, [
            h("span", { class: "tag-holding" }, "持有"),
            investmentPlanCodes.value.has(row.code)
              ? h("span", { class: "tag-plan" }, "定投")
              : null,
          ]),
  },
];

// ============ 饼图 ============
const pieData = computed(() => {
  return filteredHoldings.value
    .filter((h) => !h.cleared)
    .map((h) => ({
      name: h.name,
      customName: holdingProfiles.value[h.code]?.name || h.name,
      color: holdingProfiles.value[h.code]?.color || "#d03050",
      value: h[pieMetric.value] || 0,
    }))
    .filter((d) => d.value > 0)
    .sort((a, b) => b.value - a.value);
});

const pieOption = computed(() => {
  const data = pieData.value;
  if (!data.length) return {};
  const total = data.reduce((s, d) => s + d.value, 0);
  return {
    tooltip: {
      trigger: "item",
      formatter: (p) => {
        const name = hideAmount.value ? "***" : p.name;
        const val = hideAmount.value ? "***" : (pieMetric.value === "shares" ? Math.round(p.value).toLocaleString() : "¥" + p.value.toFixed(2));
        return `${name}<br/>${val} (${p.percent}%)`;
      },
    },
    legend: {
      type: "scroll",
      bottom: 0,
      textStyle: { color: "#aaa", fontSize: 11 },
      formatter: (name) => hideAmount.value ? "***" : name,
    },
    series: [{
      type: "pie",
      radius: "60%",
      center: ["50%", "45%"],
      data: data.map((d, i) => ({
        name: hideAmount.value ? `***${i}` : d.customName,
        value: d.value,
        itemStyle: { color: d.color },
      })),
      label: {
        show: true,
        color: "#aaa",
        fontSize: 11,
        formatter: (p) => hideAmount.value ? "***" : `${p.name}\n${p.percent}%`,
      },
      itemStyle: { borderColor: "#18181c", borderWidth: 2 },
    }],
  };
});

defineExpose({
  activeCount,
  totalHoldingCost,
  totalMarketValue,
  totalFloatPnl,
});
</script>
