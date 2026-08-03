<template>
  <div class="page-container">
    <div class="stats-bar">
      <div class="stat-card">
        <div class="stat-label">买入笔数</div>
        <div class="stat-value buy">{{ buyCount }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">卖出笔数</div>
        <div class="stat-value sell">{{ sellCount }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">逆回购</div>
        <div class="stat-value repo">{{ repoCount }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">手续费合计</div>
        <div class="stat-value">
          {{
            displayData(totalFee, hideAmount, (v) => "¥" + v.toFixed(2), "***")
          }}
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-label">筛选盈亏</div>
        <div class="stat-value" :class="filteredPnlResult.cls">
          {{ filteredPnlResult.text }}
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-label">总盈亏</div>
        <div class="stat-value" :class="totalPnlResult.cls">
          {{ totalPnlResult.text }}
        </div>
      </div>
      <div class="stat-card stat-right">
        <div class="stat-label">交易日期范围</div>
        <div class="stat-value">
          {{ formatDate(displayDateStart) }}
          ~
          {{ formatDate(displayDateEnd) }}
        </div>
      </div>
    </div>
    <div class="filter-bar">
      <n-date-picker
        v-model:value="datePickerValue"
        :type="isDateRange ? 'daterange' : 'date'"
        clearable
        size="small"
        style="width: 250px"
      />
      <n-select
        v-model:value="selectedCode"
        :options="codeOptions"
        placeholder="按品种"
        clearable
        size="small"
        style="width: 160px"
      />
      <n-select
        v-model:value="selectedSide"
        :options="sideOptions"
        placeholder="按方向"
        clearable
        size="small"
        style="width: 120px"
      />
      <n-input
        v-model:value="searchText"
        placeholder="搜索代码/名称..."
        clearable
        size="small"
        style="width: 180px"
      />
      <n-checkbox v-model:checked="isDateRange" class="ml-auto"
        >日期范围</n-checkbox
      >
      <n-checkbox v-model:checked="hideAmount">隐藏信息</n-checkbox>
    </div>
    <div class="sub-tabs">
      <div
        class="sub-tab"
        :class="{ active: subTab === 'table' }"
        @click="subTab = 'table'"
      >
        交易流水
      </div>
      <div
        class="sub-tab"
        :class="{ active: subTab === 'chart' }"
        @click="subTab = 'chart'"
      >
        直方图
      </div>
      <div
        class="sub-tab"
        :class="{ active: subTab === 'line' }"
        @click="subTab = 'line'"
      >
        时序图
      </div>
    </div>
    <n-data-table
      v-show="subTab === 'table'"
      :columns="columns"
      :data="filteredTrades"
      :pagination="pagination"
      :bordered="false"
      :striped="true"
      size="small"
      :row-key="rowKey"
      flex-height
      style="flex: 1"
    />
    <div
      v-show="subTab === 'chart'"
      class="chart-container"
      style="flex: 1; overflow: hidden"
    >
      <div class="chart-toolbar">
        <span class="chart-btn ml-auto" @click="clearAllLegend">清空</span>
        <span class="chart-btn" @click="selectAllLegend">全选</span>
        <n-select
          v-model:value="chartMetric"
          :options="metricOptions"
          size="small"
          style="width: 100px"
        />
      </div>
      <v-chart
        :option="chartOption"
        autoresize
        style="height: calc(100% - 30px); min-height: 270px"
      />
    </div>
    <div
      v-show="subTab === 'line'"
      class="chart-container"
      style="flex: 1; overflow: hidden"
    >
      <div class="chart-toolbar">
        <span class="chart-btn ml-auto" @click="clearAllLegend">清空</span>
        <span class="chart-btn" @click="selectAllLegend">全选</span>
        <n-select
          v-model:value="chartMetric"
          :options="metricOptions"
          size="small"
          style="width: 100px"
        />
      </div>
      <v-chart
        :option="lineChartOption"
        autoresize
        style="height: calc(100% - 30px); min-height: 270px"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, h, reactive, watch, onMounted } from "vue";
import {
  NDataTable,
  NTag,
  NSelect,
  NInput,
  NDatePicker,
  NCheckbox,
} from "naive-ui";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart, LineChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import {
  formatDate,
  formatMoney,
  displayData,
  pnlFormat,
  pctFormat,
  aggregateByDate,
  persistedRef,
  isReverseRepo,
} from "../parse.js";

use([
  CanvasRenderer,
  BarChart,
  LineChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
]);

const API = import.meta.env.DEV ? "http://localhost:8090" : "";
const hideAmount = persistedRef("trades_hideAmount", false);
const subTab = persistedRef("trades_subTab", "table");
const legendSelected = ref({});
const chartMetric = persistedRef("trades_chartMetric", "amount");
const metricOptions = [
  { value: "amount", label: "金额" },
  { value: "quantity", label: "数量" },
  { value: "fee", label: "手续费" },
];

function selectAllLegend() {
  const { series } = aggregateByDate(filteredTrades.value, chartMetric.value);
  const sel = {};
  series.forEach((s) => {
    sel[s.name] = true;
  });
  legendSelected.value = sel;
}

function clearAllLegend() {
  const { series } = aggregateByDate(filteredTrades.value, chartMetric.value);
  const sel = {};
  series.forEach((s) => {
    sel[s.name] = false;
  });
  legendSelected.value = sel;
}

const props = defineProps({
  trades: {
    type: Array,
    default: () => [],
  },
  quotes: {
    type: Object,
    default: () => ({}),
  },
});

const selectedCode = persistedRef("trades_selectedCode", null);
const selectedSide = persistedRef("trades_selectedSide", null);
const searchText = persistedRef("trades_searchText", "");
const dateRange = ref(null);
const dateSingle = ref(null);
const isDateRange = persistedRef("trades_isDateRange", false);

const datePickerValue = computed({
  get: () => (isDateRange.value ? dateRange.value : dateSingle.value),
  set: (val) => {
    if (isDateRange.value) dateRange.value = val;
    else dateSingle.value = val;
  },
});

// ============ 分页 ============
const pagination = reactive({
  page: 1,
  pageSize: 50,
  showSizePicker: true,
  pageSizes: [20, 50, 100, 200],
  showQuickJumper: true,
  onChange: (page) => {
    pagination.page = page;
  },
  onUpdatePageSize: (size) => {
    pagination.pageSize = size;
    pagination.page = 1;
  },
});

// ============ 筛选选项 ============
const codeOptions = computed(() => {
  const codes = new Map();
  props.trades.forEach((t) => {
    if (!codes.has(t.code)) codes.set(t.code, `${t.code} ${t.name}`);
  });
  return Array.from(codes.entries()).map(([value, label]) => ({
    value,
    label: displayData(label, hideAmount.value, null, "***"),
  }));
});

const sideOptions = [
  { value: "buy", label: "买入" },
  { value: "sell", label: "卖出" },
  { value: "reverse_repo", label: "逆回购" },
];

// ============ 筛选后的数据 ============
const filteredTrades = computed(() => {
  return props.trades.filter((t) => {
    if (selectedCode.value && t.code !== selectedCode.value) return false;
    if (selectedSide.value) {
      if (selectedSide.value === "reverse_repo" && !isReverseRepo(t.code))
        return false;
      if (selectedSide.value === "buy" && t.side !== "买入") return false;
      if (selectedSide.value === "sell" && t.side !== "卖出") return false;
    }
    if (searchText.value) {
      const q = searchText.value.toLowerCase();
      if (!t.code.includes(q) && !t.name.toLowerCase().includes(q))
        return false;
    }
    if (isDateRange.value && dateRange.value) {
      const [start, end] = dateRange.value;
      if (!start || !end) return true;
      const dateStr = t.datetime.split(" ")[0];
      const d = new Date(
        parseInt(dateStr.slice(0, 4)),
        parseInt(dateStr.slice(4, 6)) - 1,
        parseInt(dateStr.slice(6, 8))
      );
      const tradeTime = d.getTime();
      if (tradeTime < start) return false;
      if (tradeTime > end) return false;
    }
    if (!isDateRange.value && dateSingle.value) {
      const dateStr = t.datetime.split(" ")[0];
      const d = new Date(
        parseInt(dateStr.slice(0, 4)),
        parseInt(dateStr.slice(4, 6)) - 1,
        parseInt(dateStr.slice(6, 8))
      );
      const tradeDate = `${dateStr.slice(0, 4)}-${dateStr.slice(
        4,
        6
      )}-${dateStr.slice(6, 8)}`;
      const selectedDate = new Date(dateSingle.value);
      const selStr = `${selectedDate.getFullYear()}-${String(
        selectedDate.getMonth() + 1
      ).padStart(2, "0")}-${String(selectedDate.getDate()).padStart(2, "0")}`;
      if (tradeDate !== selStr) return false;
    }
    return true;
  });
});

// ============ 直方图 ============
const chartOption = computed(() => {
  const { dates, series } = aggregateByDate(
    filteredTrades.value,
    chartMetric.value
  );
  const filteredSeries = series.filter((s) => s.data.some((v) => v !== 0));
  return {
    tooltip: {
      trigger: "axis",
      formatter: (params) => {
        const date = params[0].axisValue;
        const lines = params.filter((p) => p.value && p.value !== 0);
        if (!lines.length) return "";
        return [
          date,
          ...lines.map(
            (p) =>
              `${p.marker}${hideAmount.value ? "***" : p.seriesName}: ${
                chartMetric.value === "quantity"
                  ? Math.round(p.value)
                  : p.value.toFixed(2)
              }`
          ),
        ].join("<br/>");
      },
    },
    legend: {
      type: "scroll",
      bottom: 0,
      textStyle: { color: "#aaa", fontSize: 11 },
      data: filteredSeries.map((s, i) =>
        hideAmount.value ? `***${i}` : s.name
      ),
      selected: legendSelected.value,
      formatter: (name) => (hideAmount.value ? "***" : name),
    },
    grid: { top: 10, left: 50, right: 20, bottom: 60 },
    xAxis: {
      type: "category",
      data: dates,
      axisLabel: { color: "#888" },
      axisLine: { lineStyle: { color: "#333" } },
      splitLine: { lineStyle: { color: "#222" } },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#888" },
      axisLine: { lineStyle: { color: "#333" } },
      splitLine: { lineStyle: { color: "#222" } },
    },
    series: filteredSeries.map((s, i) => ({
      name: hideAmount.value ? `***${i}` : s.name,
      type: "bar",
      stack: "amount",
      data: s.data,
    })),
  };
});

// ============ 时序图 ============
const dailyMv = ref({});

async function loadDailyMv() {
  try {
    const resp = await fetch(`${API}/api/daily_market_value`);
    dailyMv.value = await resp.json();
  } catch (e) {
    console.error("load daily mv failed:", e);
  }
}
watch(subTab, (v) => {
  if (
    v === "line" &&
    chartMetric.value === "amount" &&
    !Object.keys(dailyMv.value).length
  ) {
    loadDailyMv();
  }
});
watch(chartMetric, (v) => {
  if (
    subTab.value === "line" &&
    v === "amount" &&
    !Object.keys(dailyMv.value).length
  ) {
    loadDailyMv();
  }
});
onMounted(() => {
  if (
    subTab.value === "line" &&
    chartMetric.value === "amount" &&
    !Object.keys(dailyMv.value).length
  ) {
    loadDailyMv();
  }
});

const lineChartOption = computed(() => {
  const { dates, series } = aggregateByDate(
    filteredTrades.value,
    chartMetric.value
  );

  let cumSeries;
  if (chartMetric.value === "amount") {
    // 金额模式: 每日收盘市值 = 累计持仓 × 当日收盘价
    cumSeries = series.map((s) => ({
      name: s.name,
      data: dates.map((d, i) => {
        const formatted = d.replace(/-/g, "");
        return dailyMv.value[formatted]?.[s.code] || 0;
      }),
    }));
  } else {
    // 数量/手续费: 累计值
    cumSeries = series.map((s) => {
      let cum = 0;
      return {
        name: s.name,
        data: s.data.map((v) => {
          cum += v;
          return cum;
        }),
      };
    });
  }
  const filteredSeries = cumSeries.filter((s) => s.data.some((v) => v !== 0));
  return {
    tooltip: {
      trigger: "axis",
      formatter: (params) => {
        const date = params[0].axisValue;
        const lines = params.filter((p) => p.value && p.value !== 0);
        if (!lines.length) return "";
        return [
          date,
          ...lines.map(
            (p) =>
              `${p.marker}${hideAmount.value ? "***" : p.seriesName}: ${
                chartMetric.value === "quantity"
                  ? Math.round(p.value)
                  : p.value.toFixed(2)
              }`
          ),
        ].join("<br/>");
      },
    },
    legend: {
      type: "scroll",
      bottom: 0,
      textStyle: { color: "#aaa", fontSize: 11 },
      data: filteredSeries.map((s, i) =>
        hideAmount.value ? `***${i}` : s.name
      ),
      selected: legendSelected.value,
      formatter: (name) => (hideAmount.value ? "***" : name),
    },
    grid: { top: 10, left: 50, right: 20, bottom: 60 },
    xAxis: {
      type: "category",
      data: dates,
      axisLabel: { color: "#888" },
      axisLine: { lineStyle: { color: "#333" } },
      splitLine: { lineStyle: { color: "#222" } },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#888" },
      axisLine: { lineStyle: { color: "#333" } },
      splitLine: { lineStyle: { color: "#222" } },
    },
    series: filteredSeries.map((s, i) => ({
      name: hideAmount.value ? `***${i}` : s.name,
      type: "line",
      smooth: true,
      data: s.data,
      symbol: "circle",
      symbolSize: 5,
    })),
  };
});

// ============ 统计 ============
const buyCount = computed(
  () =>
    filteredTrades.value.filter(
      (t) => t.side === "买入" && !isReverseRepo(t.code)
    ).length
);
const sellCount = computed(
  () =>
    filteredTrades.value.filter(
      (t) => t.side === "卖出" && !isReverseRepo(t.code)
    ).length
);
const repoCount = computed(
  () => filteredTrades.value.filter((t) => isReverseRepo(t.code)).length
);
const totalFee = computed(() =>
  filteredTrades.value.reduce((sum, t) => sum + (t.fee || 0), 0)
);
const formatTs = (ts) => {
  if (!ts) return "";
  const d = new Date(ts);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}${m}${day}`;
};
const displayDateStart = computed(() => {
  if (isDateRange.value && dateRange.value && dateRange.value[0])
    return formatTs(dateRange.value[0]);
  if (!isDateRange.value && dateSingle.value) return formatTs(dateSingle.value);
  return props.trades.length
    ? props.trades[props.trades.length - 1]?.datetime.split(" ")[0]
    : "";
});
const displayDateEnd = computed(() => {
  if (isDateRange.value && dateRange.value && dateRange.value[1])
    return formatTs(dateRange.value[1]);
  if (!isDateRange.value && dateSingle.value) return formatTs(dateSingle.value);
  return props.trades.length ? props.trades[0]?.datetime.split(" ")[0] : "";
});
function calcPnl(tradesList) {
  const byCode = {};
  const repoPairs = {};
  for (const t of tradesList) {
    if (isReverseRepo(t.code)) {
      const contract = t.contract || t.datetime;
      if (!repoPairs[contract]) repoPairs[contract] = {};
      if (t.net < 0) {
        repoPairs[contract].lend = Math.abs(t.net);
      } else {
        repoPairs[contract].collect = t.amount - t.fee;
      }
      continue;
    }
    if (!byCode[t.code])
      byCode[t.code] = { shares: 0, buyCost: 0, sellIncome: 0 };
    const g = byCode[t.code];
    if (t.side === "买入") {
      g.shares += t.quantity;
      g.buyCost += t.amount + t.fee;
    } else {
      g.shares -= t.quantity;
      g.sellIncome += t.amount - t.fee;
    }
  }
  let pnl = 0;
  for (const [code, g] of Object.entries(byCode)) {
    const price = props.quotes[code]?.price || 0;
    const marketValue = price * g.shares;
    pnl += g.sellIncome + marketValue - g.buyCost;
  }
  for (const pair of Object.values(repoPairs)) {
    if (pair.lend != null && pair.collect != null) {
      pnl += pair.collect - pair.lend;
    }
  }
  return pnl;
}

const filteredPnl = computed(() => calcPnl(filteredTrades.value));
const totalPnl = computed(() => calcPnl(props.trades));
const filteredPnlResult = computed(() =>
  pnlFormat(filteredPnl.value, hideAmount.value)
);
const totalPnlResult = computed(() =>
  pnlFormat(totalPnl.value, hideAmount.value)
);

// ============ 表格列定义 ============
const rowKey = (row, index) => index;

function sideTag(side, code) {
  if (side === "买入")
    return h(
      NTag,
      { type: "error", size: "small", bordered: false },
      () => "买入"
    );
  return h(
    NTag,
    { type: "success", size: "small", bordered: false },
    () => "卖出"
  );
}

function marketTag(market) {
  const type = market?.includes("沪") ? "info" : "warning";
  return h(NTag, { type, size: "tiny", bordered: false }, () => market);
}

// 盈亏渲染
function pnlRender(val) {
  const { text, cls } = pnlFormat(val, hideAmount.value);
  return h("span", { class: cls }, text);
}

// 收益率渲染
function pctRender(val) {
  const { text, cls } = pctFormat(val, hideAmount.value);
  return h("span", { class: cls }, text);
}

const columns = [
  {
    title: "时间",
    key: "datetime",
    width: 150,
    render: (row) => {
      const [d, t] = row.datetime.split(" ");
      return `${formatDate(d)} ${t || ""}`;
    },
    sorter: (a, b) => a.datetime.localeCompare(b.datetime),
  },
  {
    title: "代码",
    key: "code",
    width: 80,
    render: (row) => displayData(row.code, hideAmount.value, null, "***"),
  },
  {
    title: "名称",
    key: "name",
    width: 100,
    render: (row) =>
      displayData(row.name, hideAmount.value, (v) =>
        h("span", { title: row.fullname }, v)
      ),
  },
  {
    title: "方向",
    key: "side",
    width: 80,
    render: (row) => sideTag(row.side, row.code),
  },
  {
    title: "数量",
    key: "quantity",
    width: 90,
    render: (row) =>
      displayData(row.quantity, hideAmount.value, (v) => v.toLocaleString()),
    sorter: (a, b) => a.quantity - b.quantity,
  },
  {
    title: "均价",
    key: "price",
    width: 80,
    render: (row) =>
      displayData(row.price, hideAmount.value, (v) => v.toFixed(3)),
    sorter: (a, b) => a.price - b.price,
  },
  {
    title: "现价",
    key: "currentPrice",
    width: 80,
    render: (row) =>
      displayData(props.quotes[row.code]?.price, hideAmount.value, (v) =>
        v.toFixed(3)
      ),
    sorter: (a, b) =>
      (props.quotes[a.code]?.price || 0) - (props.quotes[b.code]?.price || 0),
  },
  {
    title: "成交金额",
    key: "amount",
    width: 110,
    render: (row) => displayData(row.amount, hideAmount.value, formatMoney),
    sorter: (a, b) => a.amount - b.amount,
  },
  {
    title: "手续费",
    key: "fee",
    width: 70,
    render: (row) =>
      displayData(
        row.fee,
        hideAmount.value,
        (v) => (v > 0 ? v.toFixed(3) : "0.000"),
        "0.000"
      ),
    sorter: (a, b) => a.fee - b.fee,
  },
  {
    title: "发生金额",
    key: "net",
    width: 110,
    render: (row) => {
      if (hideAmount.value) return "***";
      if (row.net === null) return "--";
      const cls = row.net >= 0 ? "amount-positive" : "amount-negative";
      return h("span", { class: cls }, formatMoney(row.net));
    },
    sorter: (a, b) => (a.net ?? 0) - (b.net ?? 0),
  },
  {
    title: "资金余额",
    key: "balance",
    width: 110,
    render: (row) => displayData(row.balance, hideAmount.value, formatMoney),
    sorter: (a, b) => (a.balance ?? 0) - (b.balance ?? 0),
  },
  {
    title: "市场",
    key: "market",
    width: 60,
    render: (row) => marketTag(row.market),
  },
];

// ============ 暴露给父组件（统计栏用） ============
defineExpose({
  filteredTrades,
  buyCount,
  sellCount,
  repoCount,
  totalFee,
  displayDateStart,
  displayDateEnd,
  filteredPnl,
  totalPnl,
});
</script>
