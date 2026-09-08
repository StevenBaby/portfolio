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
      <n-select
        v-model:value="netModes"
        :options="netModeOptions"
        multiple
        clearable
        max-tag-count="responsive"
        placeholder="净交易"
        size="small"
        style="width: 150px"
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
      <n-checkbox v-model:checked="invertOnly">反选</n-checkbox>
      <n-checkbox v-model:checked="showCleared">显示已清仓</n-checkbox>
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
        :class="{ active: subTab === 'summary' }"
        @click="subTab = 'summary'"
      >
        交易汇总
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
      :row-class-name="tradeRowClass"
      flex-height
      style="flex: 1"
    />
    <n-data-table
      v-show="subTab === 'summary'"
      :columns="summaryColumns"
      :data="tradeSummary"
      :pagination="summaryPagination"
      :bordered="false"
      :striped="true"
      size="small"
      :row-key="(row) => row.code"
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
        :update-options="{ notMerge: true }"
        autoresize
        @ready="activateDataZoomSelect"
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
        :update-options="{ notMerge: true }"
        autoresize
        @ready="activateDataZoomSelect"
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
  NPopover,
} from "naive-ui";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart, LineChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
  DataZoomComponent,
  ToolboxComponent,
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
  holdingProfiles,
  goldPerShare,
  calcTotalPnl,
} from "../parse.js";

use([
  CanvasRenderer,
  BarChart,
  LineChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  DataZoomComponent,
  ToolboxComponent,
]);

const API = import.meta.env.DEV ? "http://localhost:8090" : "";
const hideAmount = persistedRef("trades_hideAmount", false);
const subTab = persistedRef("trades_subTab", "table");
const legendSelected = ref({});
const chartMetric = persistedRef("trades_chartMetric_v3", "cumulative_pnl");
const metricOptions = [
  { value: "amount", label: "金额" },
  { value: "quantity", label: "数量" },
  { value: "fee", label: "手续费" },
  { value: "daily_pnl", label: "当日盈亏" },
  { value: "cumulative_pnl", label: "累计盈亏" },
];

function activateDataZoomSelect(chart) {
  requestAnimationFrame(() => {
    chart.dispatchAction({
      type: "takeGlobalCursor",
      key: "dataZoomSelect",
      dataZoomSelectActive: true,
    });
  });
}

function selectAllLegend() {
  const { series } = aggregateByDate(
    filteredTrades.value,
    chartMetric.value,
    props.trades,
    dailyMv.value,
    holdingProfiles.value,
    props.quotes,
  );
  const sel = {};
  series.forEach((s) => {
    sel[s.code] = true;
  });
  legendSelected.value = sel;
}

function clearAllLegend() {
  const { series } = aggregateByDate(
    filteredTrades.value,
    chartMetric.value,
    props.trades,
    dailyMv.value,
    holdingProfiles.value,
    props.quotes,
  );
  const sel = {};
  series.forEach((s) => {
    sel[s.code] = false;
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
  holdings: {
    type: Array,
    default: () => [],
  },
});

const selectedCode = persistedRef("trades_selectedCode", null);
const showCleared = persistedRef("trades_showCleared", false);
const selectedSide = persistedRef("trades_selectedSide", null);
const searchText = persistedRef("trades_searchText", "");
const dateRange = ref(null);
const dateSingle = ref(null);
const isDateRange = persistedRef("trades_isDateRange", false);
const dailyCloseValues = ref({});
const dailyClosePrices = ref({});

async function loadDailyCloseValues() {
  try {
    const [marketValueResponse, closePriceResponse] = await Promise.all([
      fetch(`${API}/api/daily_market_value`),
      fetch(`${API}/api/daily_close_prices`),
    ]);
    dailyCloseValues.value = await marketValueResponse.json();
    dailyClosePrices.value = await closePriceResponse.json();
  } catch (error) {
    console.error("加载收盘数据失败:", error);
  }
}

const selectedSummaryDate = computed(() =>
  (isDateRange.value && dateRange.value?.[1]) ||
  (!isDateRange.value && dateSingle.value)
    ? formatTs(isDateRange.value ? dateRange.value[1] : dateSingle.value)
    : "",
);
const summaryPriceDate = computed(() => {
  const selectedEnd = selectedSummaryDate.value;
  const dates = Object.keys(dailyClosePrices.value).sort();
  if (!dates.length) return "";
  return selectedEnd
    ? dates.filter((date) => date <= selectedEnd).at(-1) || dates[0]
    : dates.at(-1);
});
const todayDate = (() => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
})();
const isMarketOpenDate = computed(() => summaryPriceDate.value === todayDate);
const sharesAtDate = computed(() => {
  const cutoff = summaryPriceDate.value;
  const shares = {};
  for (const trade of props.trades) {
    if (
      isReverseRepo(trade.code) ||
      (cutoff && formatDate(trade.datetime.split(" ")[0]) > cutoff)
    )
      continue;
    shares[trade.code] =
      (shares[trade.code] || 0) +
      (trade.side === "买入" ? trade.quantity : -trade.quantity);
  }
  return shares;
});

function getSummaryPrice(code) {
  const latestTrade = props.trades.find((trade) => trade.code === code);
  if (!selectedSummaryDate.value)
    return props.quotes[code]?.price || latestTrade?.price || 0;
  if (isMarketOpenDate.value)
    return props.quotes[code]?.price || latestTrade?.price || 0;
  const value = dailyClosePrices.value[summaryPriceDate.value]?.[code] || 0;
  if (value > 0) return value;
  return latestTrade?.price || 0;
}

const datePickerValue = computed({
  get: () => (isDateRange.value ? dateRange.value : dateSingle.value),
  set: (val) => {
    if (isDateRange.value) dateRange.value = val;
    else dateSingle.value = val;
  },
});

onMounted(() => {
  loadDailyCloseValues();
});

// ============ 分页 ============
const pagination = reactive({
  page: 1,
  pageSize: 20,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100, 200],
  showQuickJumper: true,
  onChange: (page) => {
    pagination.page = page;
  },
  onUpdatePageSize: (size) => {
    pagination.pageSize = size;
    pagination.page = 1;
  },
});

const summaryPagination = reactive({
  page: 1,
  pageSize: 50,
  showSizePicker: true,
  pageSizes: [20, 50, 100],
  showQuickJumper: true,
  onChange: (page) => {
    summaryPagination.page = page;
  },
  onUpdatePageSize: (size) => {
    summaryPagination.pageSize = size;
    summaryPagination.page = 1;
  },
});

// ============ 筛选选项 ============
const clearedCodes = computed(
  () =>
    new Set(
      props.holdings
        .filter((holding) => holding.shares === 0)
        .map((holding) => holding.code),
    ),
);

// 净交易前置处理：清仓亏损不切断计算，累计到后续清仓转为盈利时整体删除。
const profitableClearedTrades = computed(() => {
  const removed = new Set();
  const codes = new Set(props.trades.map((trade) => trade.code));
  for (const code of codes) {
    if (isReverseRepo(code)) continue;
    const accumulated = [];
    let shares = 0;
    let accumulatedCost = 0;
    const codeTrades = props.trades
      .filter((trade) => trade.code === code)
      .sort((a, b) => a.datetime.localeCompare(b.datetime));
    for (const trade of codeTrades) {
      accumulated.push(trade);
      if (trade.side === "买入") {
        shares += trade.quantity;
        accumulatedCost += trade.amount + trade.fee;
      } else {
        shares -= trade.quantity;
        accumulatedCost -= trade.amount - trade.fee;
      }
      if (shares === 0 && accumulatedCost < 0) {
        accumulated.forEach((item) => removed.add(item));
        accumulated.length = 0;
        accumulatedCost = 0;
      }
    }
  }
  return removed;
});

const codeOptions = computed(() => {
  const codes = new Map();
  props.trades.forEach((trade) => {
    if (!showCleared.value && clearedCodes.value.has(trade.code)) return;
    if (!codes.has(trade.code))
      codes.set(trade.code, `${trade.code} ${trade.name}`);
  });
  return Array.from(codes.entries()).map(([value, label]) => ({
    value,
    label: displayData(label, hideAmount.value, null, "***"),
  }));
});

watch(
  [showCleared, () => props.holdings],
  () => {
    if (
      selectedCode.value &&
      !codeOptions.value.some((option) => option.value === selectedCode.value)
    ) {
      selectedCode.value = null;
    }
  },
  { deep: true },
);

const sideOptions = [
  { value: "buy", label: "买入" },
  { value: "sell", label: "卖出" },
  { value: "reverse_repo", label: "逆回购" },
];

// ============ 筛选后的数据 ============
const netModes = persistedRef("trades_netModes", []);
const netModeOptions = [
  { value: "profitable_clear", label: "盈利清仓" },
  { value: "perfect_t0", label: "完美 T+0" },
  { value: "adjacent", label: "相邻交易" },
  { value: "adjacent_group", label: "相邻组合" },
  { value: "time_nearest", label: "时间最近" },
  { value: "spread_min", label: "利差最小" },
];
const legacyNetModeMap = { nearest: "adjacent", global: "time_nearest" };
netModes.value = netModes.value.map((mode) => legacyNetModeMap[mode] || mode);
const invertOnly = persistedRef("trades_invertOnly", false);

function tradeDateMatches(trade) {
  const date = formatDate(trade.datetime.split(" ")[0]);
  if (isDateRange.value && dateRange.value?.[0] && dateRange.value?.[1]) {
    const [start, end] = dateRange.value;
    const time = new Date(`${date}T00:00:00`).getTime();
    return time >= start && time <= end;
  }
  if (!isDateRange.value && dateSingle.value) {
    return date === formatTs(dateSingle.value);
  }
  return true;
}

function matchesTradeFilters(trade) {
  const hasFilter = Boolean(
    selectedCode.value ||
    selectedSide.value ||
    searchText.value.trim() ||
    (isDateRange.value
      ? dateRange.value?.[0] && dateRange.value?.[1]
      : dateSingle.value),
  );
  let matches = true;
  if (selectedCode.value)
    matches = matches && trade.code === selectedCode.value;
  if (selectedSide.value) {
    const sideMatches =
      selectedSide.value === "reverse_repo"
        ? isReverseRepo(trade.code)
        : selectedSide.value === "buy"
          ? trade.side === "买入"
          : trade.side === "卖出";
    matches = matches && sideMatches;
  }
  if (searchText.value.trim()) {
    const query = searchText.value.trim().toLowerCase();
    matches =
      matches &&
      (trade.code.includes(query) || trade.name.toLowerCase().includes(query));
  }
  if (
    (isDateRange.value && dateRange.value?.[0] && dateRange.value?.[1]) ||
    (!isDateRange.value && dateSingle.value)
  ) {
    matches = matches && tradeDateMatches(trade);
  }
  return invertOnly.value && hasFilter ? !matches : matches;
}

function tradeTimestamp(trade) {
  const [rawDate, rawTime = "00:00:00"] = trade.datetime.split(" ");
  const date = formatDate(rawDate);
  return new Date(`${date}T${rawTime}`).getTime();
}

function tradeNetProfit(buy, sell) {
  return sell.amount - sell.fee - (buy.amount + buy.fee);
}

function removePerfectT0(trades, removed) {
  const groups = {};
  for (const trade of trades) {
    if (removed.has(trade)) continue;
    const key = `${trade.datetime.split(" ")[0]}-${trade.code}`;
    if (!groups[key]) groups[key] = { buys: [], sells: [] };
    groups[key][trade.side === "买入" ? "buys" : "sells"].push(trade);
  }
  for (const { buys, sells } of Object.values(groups)) {
    const buyQty = buys.reduce((sum, trade) => sum + trade.quantity, 0);
    const sellQty = sells.reduce((sum, trade) => sum + trade.quantity, 0);
    const buyCost = buys.reduce((sum, trade) => sum + trade.amount + trade.fee, 0);
    const sellIncome = sells.reduce((sum, trade) => sum + trade.amount - trade.fee, 0);
    if (buyQty > 0 && buyQty === sellQty && sellIncome > buyCost) {
      buys.forEach((trade) => removed.add(trade));
      sells.forEach((trade) => removed.add(trade));
    }
  }
}

function removeNearestPairs(trades, removed) {
  const byCode = {};
  for (const trade of trades) {
    if (!byCode[trade.code]) byCode[trade.code] = [];
    byCode[trade.code].push(trade);
  }
  for (const codeTrades of Object.values(byCode)) {
    const remaining = codeTrades
      .filter((trade) => !removed.has(trade))
      .sort((a, b) => tradeTimestamp(a) - tradeTimestamp(b));
    let index = 0;
    while (index < remaining.length - 1) {
      const first = remaining[index];
      const second = remaining[index + 1];
      if (first.side === second.side || first.quantity !== second.quantity) {
        index += 1;
        continue;
      }
      const buy = first.side === "买入" ? first : second;
      const sell = first.side === "卖出" ? first : second;
      if (tradeNetProfit(buy, sell) <= 0) {
        index += 1;
        continue;
      }
      removed.add(first);
      removed.add(second);
      remaining.splice(index, 2);
      index = Math.max(0, index - 1);
    }
  }
}

function removeAdjacentGroups(trades, removed) {
  const byCode = {};
  for (const trade of trades) {
    if (!byCode[trade.code]) byCode[trade.code] = [];
    byCode[trade.code].push(trade);
  }
  for (const codeTrades of Object.values(byCode)) {
    const remaining = codeTrades
      .filter((trade) => !removed.has(trade))
      .sort((a, b) => tradeTimestamp(a) - tradeTimestamp(b));
    let index = 0;
    while (index < remaining.length - 1) {
      const firstSide = remaining[index].side;
      let end = index;
      const firstGroup = [];
      while (end < remaining.length && remaining[end].side === firstSide) {
        firstGroup.push(remaining[end]);
        end += 1;
      }
      const secondGroup = [];
      while (end < remaining.length && remaining[end].side !== firstSide) {
        secondGroup.push(remaining[end]);
        end += 1;
      }
      if (!secondGroup.length) break;
      const firstQty = firstGroup.reduce((sum, trade) => sum + trade.quantity, 0);
      const secondQty = secondGroup.reduce((sum, trade) => sum + trade.quantity, 0);
      const buy = firstSide === "买入" ? firstGroup : secondGroup;
      const sell = firstSide === "卖出" ? firstGroup : secondGroup;
      const profit =
        sell.reduce((sum, trade) => sum + trade.amount - trade.fee, 0) -
        buy.reduce((sum, trade) => sum + trade.amount + trade.fee, 0);
      if (firstQty === secondQty && firstQty > 0 && profit > 0) {
        [...firstGroup, ...secondGroup].forEach((trade) => removed.add(trade));
        remaining.splice(index, firstGroup.length + secondGroup.length);
        index = Math.max(0, index - 1);
      } else {
        index += 1;
      }
    }
  }
}

function removeGlobalPairs(trades, removed) {
  while (true) {
    const remaining = trades
      .filter((trade) => !removed.has(trade))
      .sort((a, b) => tradeTimestamp(b) - tradeTimestamp(a));
    let selectedPair = null;
    for (const anchor of remaining) {
      const candidates = remaining.filter((trade) => {
        if (trade === anchor || trade.code !== anchor.code) return false;
        if (trade.quantity !== anchor.quantity || trade.side === anchor.side) return false;
        const buy = anchor.side === "买入" ? anchor : trade;
        const sell = anchor.side === "卖出" ? anchor : trade;
        return tradeNetProfit(buy, sell) > 0;
      });
      if (!candidates.length) continue;
      candidates.sort(
        (a, b) =>
          Math.abs(tradeTimestamp(a) - tradeTimestamp(anchor)) -
          Math.abs(tradeTimestamp(b) - tradeTimestamp(anchor)),
      );
      selectedPair = [anchor, candidates[0]];
      break;
    }
    if (!selectedPair) break;
    selectedPair.forEach((trade) => removed.add(trade));
  }
}

function removeSpreadMinPairs(trades, removed) {
  while (true) {
    let bestPair = null;
    let bestProfit = Infinity;
    const remaining = trades.filter((trade) => !removed.has(trade));
    for (const buy of remaining) {
      if (buy.side !== "买入") continue;
      for (const sell of remaining) {
        if (
          sell.side !== "卖出" ||
          sell.code !== buy.code ||
          sell.quantity !== buy.quantity
        ) continue;
        const profit = tradeNetProfit(buy, sell);
        if (profit > 0 && profit < bestProfit) {
          bestProfit = profit;
          bestPair = [buy, sell];
        }
      }
    }
    if (!bestPair) break;
    bestPair.forEach((trade) => removed.add(trade));
  }
}

const filteredTrades = computed(() => {
  const result = props.trades.filter((trade) => {
    if (!showCleared.value && clearedCodes.value.has(trade.code)) return false;
    return matchesTradeFilters(trade);
  });
  if (!netModes.value.length) return result;

  const modes = new Set(netModes.value);
  const nonRepo = result.filter((trade) => !isReverseRepo(trade.code));
  const removed = new Set();

  if (modes.has("profitable_clear")) {
    nonRepo
      .filter((trade) => profitableClearedTrades.value.has(trade))
      .forEach((trade) => removed.add(trade));
  }
  if (modes.has("perfect_t0")) removePerfectT0(nonRepo, removed);
  if (modes.has("adjacent")) removeNearestPairs(nonRepo, removed);
  if (modes.has("adjacent_group")) removeAdjacentGroups(nonRepo, removed);
  if (modes.has("time_nearest")) removeGlobalPairs(nonRepo, removed);
  if (modes.has("spread_min")) removeSpreadMinPairs(nonRepo, removed);

  return invertOnly.value
    ? nonRepo.filter((trade) => removed.has(trade))
    : nonRepo.filter((trade) => !removed.has(trade));
});

// ============ 交易汇总 ============
function summaryCodeSort(a, b) {
  if (a.cleared !== b.cleared) return Number(a.cleared) - Number(b.cleared);
  return a.code.localeCompare(b.code);
}

const summaryTrades = computed(() => {
  return props.trades.filter((trade) => {
    if (!showCleared.value && clearedCodes.value.has(trade.code)) return false;
    return matchesTradeFilters(trade);
  });
});

const tradeSummary = computed(() => {
  const groups = new Map();
  for (const trade of summaryTrades.value) {
    if (isReverseRepo(trade.code)) continue;
    if (!groups.has(trade.code)) {
      groups.set(trade.code, {
        code: trade.code,
        name: trade.name,
        shares: 0,
        total_cost: 0,
        buy_count: 0,
        sell_count: 0,
      });
    }
    const group = groups.get(trade.code);
    const quantity = trade.quantity || 0;
    const amount = trade.amount || 0;
    const fee = trade.fee || 0;
    if (trade.side === "买入") {
      group.shares += quantity;
      group.total_cost += amount + fee;
      group.buy_count += 1;
    } else {
      group.shares -= quantity;
      group.total_cost -= amount - fee;
      group.sell_count += 1;
    }
  }
  return [...groups.values()]
    .map((group) => {
      const price = getSummaryPrice(group.code);
      const avgCost = group.shares > 0 ? group.total_cost / group.shares : 0;
      const marketValue = price * group.shares;
      const floatPnl =
        group.shares > 0 ? marketValue - group.total_cost : -group.total_cost;
      const pnlPct =
        group.total_cost > 0 ? (floatPnl / group.total_cost) * 100 : 0;
      return {
        ...group,
        avg_cost: avgCost,
        price,
        marketValue,
        floatPnl,
        pnlPct,
        cleared: group.shares === 0,
      };
    })
    .filter((group) => showCleared.value || !group.cleared)
    .sort(summaryCodeSort);
});

const summaryColumns = [
  {
    title: "代码",
    key: "code",
    width: 80,
    render: (row) => displayData(row.code, hideAmount.value, null, "***"),
  },
  {
    title: "名称",
    key: "name",
    width: 110,
    render: (row) => {
      const name = holdingProfiles.value[row.code]?.name || row.name;
      const color = holdingProfiles.value[row.code]?.color || "#d03050";
      if (hideAmount.value) return "***";
      return h("div", { class: "holding-name-cell" }, [
        h("span", { title: row.name }, name),
        h("span", {
          class: "holding-name-color",
          style: { backgroundColor: color },
          title: color,
        }),
      ]);
    },
  },
  {
    title: "持仓",
    key: "shares",
    width: 90,
    render: (row) =>
      displayData(
        row.shares > 0 ? row.shares : null,
        hideAmount.value,
        (v) => v.toLocaleString(),
        "***",
      ),
  },
  {
    title: "平均成本",
    key: "avg_cost",
    width: 100,
    render: (row) => {
      if (hideAmount.value) return "***";
      if (!row.shares || row.shares <= 0) return "--";
      const val = row.avg_cost.toFixed(4);
      const cny =
        row.code === "518880"
          ? ` ¥${(row.avg_cost / goldPerShare.value).toFixed(2)}/g`
          : "";
      return h("span", {}, [val, h("span", { class: "holding-sub" }, cny)]);
    },
  },
  {
    title: "当日价",
    key: "price",
    width: 100,
    render: (row) => {
      if (hideAmount.value) return "***";
      if (!row.price) return "--";
      const val = row.price.toFixed(3);
      const cny =
        row.code === "518880"
          ? ` ¥${(row.price / goldPerShare.value).toFixed(2)}/g`
          : "";
      return h("span", {}, [val, h("span", { class: "holding-sub" }, cny)]);
    },
  },
  {
    title: "总成本",
    key: "total_cost",
    width: 110,
    render: (row) =>
      displayData(
        row.total_cost,
        hideAmount.value,
        (v) => `¥${v.toFixed(2)}`,
        "***",
      ),
  },
  {
    title: "市值",
    key: "marketValue",
    width: 110,
    render: (row) =>
      displayData(
        row.price && row.shares > 0 ? row.marketValue : null,
        hideAmount.value,
        (v) => `¥${v.toFixed(2)}`,
        "***",
      ),
  },
  {
    title: "浮动盈亏",
    key: "floatPnl",
    width: 110,
    render: (row) => pnlRender(row.floatPnl),
  },
  {
    title: "收益率",
    key: "pnlPct",
    width: 85,
    render: (row) =>
      row.price && row.shares > 0
        ? pctRender(row.pnlPct)
        : hideAmount.value
          ? "***"
          : "--",
  },
  {
    title: "买卖",
    key: "trades",
    width: 65,
    render: (row) => `${row.buy_count}/${row.sell_count}`,
  },
  {
    title: "状态",
    key: "status",
    width: 70,
    render: (row) =>
      row.cleared
        ? h("span", { class: "tag-cleared" }, "已清仓")
        : h("span", { class: "tag-holding" }, "持有"),
  },
];

// ============ 直方图 ============
const chartOption = computed(() => {
  const { dates, series } = aggregateByDate(
    filteredTrades.value,
    chartMetric.value,
    props.trades,
    dailyMv.value,
    holdingProfiles.value,
    props.quotes,
  );
  const filteredSeries = series.filter((s) => s.data.some((v) => v !== 0));
  return {
    tooltip: {
      trigger: "axis",
      formatter: (params) => {
        if (!params?.length) return "";
        const date = params[0]?.axisValue || "";
        const lines = params.filter(
          (p) => p && p.value !== 0 && p.value != null,
        );
        if (!lines.length) return "";
        return [
          date,
          ...lines.map(
            (p) =>
              `${p.marker}${hideAmount.value ? "***" : filteredSeries.find((s) => s.code === p.seriesName)?.name || p.seriesName}: ${
                chartMetric.value === "quantity"
                  ? Math.round(p.value)
                  : p.value.toFixed(2)
              }`,
          ),
        ].join("<br/>");
      },
    },
    legend: {
      type: "scroll",
      bottom: 0,
      textStyle: { color: "#aaa", fontSize: 11 },
      data: filteredSeries.map((s) => s.code),
      selected: legendSelected.value,
      formatter: (code) =>
        hideAmount.value
          ? "***"
          : filteredSeries.find((s) => s.code === code)?.name || code,
    },
    dataZoom: [
      { type: "inside", xAxisIndex: 0 },
      { type: "slider", xAxisIndex: 0, bottom: 35, height: 20 },
    ],
    toolbox: { show: false, feature: { dataZoom: { yAxisIndex: "none" } } },
    grid: { left: 20, right: 20, top: 10, bottom: 80 },
    xAxis: {
      type: "category",
      data: dates,
      axisLabel: { color: "#888" },
      axisLine: { lineStyle: { color: "#333" } },
      splitLine: { lineStyle: { color: "#222" } },
    },
    yAxis: {
      type: "value",
      axisLabel: {
        color: "#888",
        formatter: () => (hideAmount.value ? "***" : ""),
      },
      axisLine: { lineStyle: { color: "#333" } },
      splitLine: { lineStyle: { color: "#222" } },
    },
    series: filteredSeries.map((s, i) => ({
      name: s.code,
      type: "bar",
      stack: "amount",
      itemStyle: s.color ? { color: s.color } : undefined,
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
    (v === "line" || v === "chart") &&
    (chartMetric.value === "amount" ||
      chartMetric.value === "daily_pnl" ||
      chartMetric.value === "cumulative_pnl") &&
    !Object.keys(dailyMv.value).length
  ) {
    loadDailyMv();
  }
});
watch(chartMetric, (v) => {
  if (
    (subTab.value === "line" || subTab.value === "chart") &&
    (v === "amount" || v === "daily_pnl" || v === "cumulative_pnl") &&
    !Object.keys(dailyMv.value).length
  ) {
    loadDailyMv();
  }
});
onMounted(() => {
  if (
    (subTab.value === "line" || subTab.value === "chart") &&
    (chartMetric.value === "amount" ||
      chartMetric.value === "daily_pnl" ||
      chartMetric.value === "cumulative_pnl") &&
    !Object.keys(dailyMv.value).length
  ) {
    loadDailyMv();
  }
});

const lineChartOption = computed(() => {
  const { dates, series } = aggregateByDate(
    filteredTrades.value,
    chartMetric.value,
    props.trades,
    dailyMv.value,
    holdingProfiles.value,
    props.quotes,
  );

  let cumSeries;
  if (chartMetric.value === "amount") {
    // 金额模式: 每日收盘市值 = 累计持仓 × 当日收盘价
    cumSeries = series.map((s) => ({
      code: s.code,
      name: s.name,
      color: s.color,
      data: dates.map((d) => {
        return dailyMv.value[d]?.[s.code] || 0;
      }),
    }));
  } else if (
    chartMetric.value === "daily_pnl" ||
    chartMetric.value === "cumulative_pnl"
  ) {
    // 盈亏模式已经是每日收盘市值减移动平均持仓成本的快照。
    cumSeries = series;
  } else if (chartMetric.value === "quantity") {
    cumSeries = series;
  } else {
    // 手续费: 累计值
    cumSeries = series.map((s) => {
      let cum = 0;
      return {
        code: s.code,
        name: s.name,
        color: s.color,
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
        if (!params?.length) return "";
        const date = params[0]?.axisValue || "";
        const lines = params.filter(
          (p) => p && p.value !== 0 && p.value != null,
        );
        if (!lines.length) return "";
        return [
          date,
          ...lines.map(
            (p) =>
              `${p.marker}${hideAmount.value ? "***" : filteredSeries.find((s) => s.code === p.seriesName)?.name || p.seriesName}: ${
                chartMetric.value === "quantity"
                  ? Math.round(p.value)
                  : p.value.toFixed(2)
              }`,
          ),
        ].join("<br/>");
      },
    },
    legend: {
      type: "scroll",
      bottom: 0,
      textStyle: { color: "#aaa", fontSize: 11 },
      data: filteredSeries.map((s) => s.code),
      selected: legendSelected.value,
      formatter: (code) =>
        hideAmount.value
          ? "***"
          : filteredSeries.find((s) => s.code === code)?.name || code,
    },
    dataZoom: [
      { type: "inside", xAxisIndex: 0 },
      { type: "slider", xAxisIndex: 0, bottom: 35, height: 20 },
    ],
    toolbox: { show: false, feature: { dataZoom: { yAxisIndex: "none" } } },
    grid: { left: 20, right: 20, top: 10, bottom: 80 },
    xAxis: {
      type: "category",
      data: dates,
      axisLabel: { color: "#888" },
      axisLine: { lineStyle: { color: "#333" } },
      splitLine: { lineStyle: { color: "#222" } },
    },
    yAxis: {
      type: "value",
      axisLabel: {
        color: "#888",
        formatter: () => (hideAmount.value ? "***" : ""),
      },
      axisLine: { lineStyle: { color: "#333" } },
      splitLine: { lineStyle: { color: "#222" } },
    },
    series: filteredSeries.map((s, i) => ({
      name: s.code,
      type: "line",
      smooth: true,
      lineStyle: s.color ? { color: s.color } : undefined,
      itemStyle: s.color ? { color: s.color } : undefined,
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
      (t) => t.side === "买入" && !isReverseRepo(t.code),
    ).length,
);
const sellCount = computed(
  () =>
    filteredTrades.value.filter(
      (t) => t.side === "卖出" && !isReverseRepo(t.code),
    ).length,
);
const repoCount = computed(
  () => filteredTrades.value.filter((t) => isReverseRepo(t.code)).length,
);
const totalFee = computed(() =>
  filteredTrades.value.reduce((sum, t) => sum + (t.fee || 0), 0),
);
const formatTs = (ts) => {
  if (!ts) return "";
  const d = new Date(ts);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
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

const filteredPnl = computed(() => {
  if (subTab.value === "summary") {
    return tradeSummary.value.reduce(
      (sum, item) => sum + (item.floatPnl || 0),
      0,
    );
  }
  return calcTotalPnl(filteredTrades.value, props.quotes);
});
const totalPnl = computed(() => calcTotalPnl(props.trades, props.quotes));
const filteredPnlResult = computed(() =>
  pnlFormat(filteredPnl.value, hideAmount.value),
);
const totalPnlResult = computed(() =>
  pnlFormat(totalPnl.value, hideAmount.value),
);

// ============ 表格列定义 ============
const rowKey = (row, index) => index;

function tradeRowClass(row) {
  if (isReverseRepo(row.code) || !row.price) return "";
  const cur = props.quotes[row.code]?.price;
  if (!cur) return "";
  const profile = holdingProfiles.value[row.code] || {};
  const rise = Number(profile.rise_pct ?? 5) / 100;
  const fall = Number(profile.fall_pct ?? 5) / 100;
  const buyTarget = row.price * (1 - fall);
  const sellTarget = row.price * (1 + rise);
  if (row.side === "买入" && cur >= sellTarget) return "trade-row-hit-buy";
  if (row.side === "卖出" && cur <= buyTarget) return "trade-row-hit-sell";
  return "";
}

function sideTag(side, code) {
  if (side === "买入")
    return h(
      NTag,
      { type: "error", size: "small", bordered: false },
      () => "买入",
    );
  return h(
    NTag,
    { type: "success", size: "small", bordered: false },
    () => "卖出",
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
    render: (row) => {
      if (hideAmount.value) return "***";
      const name = holdingProfiles.value[row.code]?.name || row.name;
      const color = holdingProfiles.value[row.code]?.color || "#d03050";
      return h("div", { class: "holding-name-cell" }, [
        h("span", { title: row.fullname }, name),
        h("span", {
          class: "holding-name-color",
          style: { backgroundColor: color },
          title: color,
        }),
      ]);
    },
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
    width: 100,
    render: (row) => {
      if (hideAmount.value) return "***";
      const val = row.price.toFixed(3);
      const cny =
        row.code === "518880"
          ? ` ¥${(row.price / goldPerShare.value).toFixed(2)}/g`
          : "";
      return h("span", {}, [val, h("span", { class: "holding-sub" }, cny)]);
    },
    sorter: (a, b) => a.price - b.price,
  },
  {
    title: "现价",
    key: "currentPrice",
    width: 100,
    render: (row) => {
      if (hideAmount.value) return "***";
      const cur = props.quotes[row.code]?.price;
      if (!cur) return "--";
      const val = cur.toFixed(3);
      const cny =
        row.code === "518880"
          ? ` ¥${(cur / goldPerShare.value).toFixed(2)}/g`
          : "";
      return h("span", {}, [val, h("span", { class: "holding-sub" }, cny)]);
    },
    sorter: (a, b) =>
      (props.quotes[a.code]?.price || 0) - (props.quotes[b.code]?.price || 0),
  },
  {
    title: "建议价",
    key: "suggestedPrice",
    width: 120,
    render: (row) => {
      if (isReverseRepo(row.code)) return "--";
      if (hideAmount.value) return "***";
      const profile = holdingProfiles.value[row.code] || {};
      const rise = Number(profile.rise_pct ?? 5) / 100;
      const fall = Number(profile.fall_pct ?? 5) / 100;
      const buyPrice = row.price * (1 - fall);
      const sellPrice = row.price * (1 + rise);
      const cny = (price) =>
        row.code === "518880"
          ? ` ¥${(price / goldPerShare.value).toFixed(2)}/g`
          : "";
      const targetText = (price, className, showCny = true) =>
        h("span", { class: className }, [
          price.toFixed(3),
          showCny ? h("span", { class: "holding-sub" }, cny(price)) : null,
        ]);
      const trigger = h("span", { class: "suggested-price-cell" }, [
        targetText(buyPrice, "amount-positive", false),
        " / ",
        targetText(sellPrice, "amount-negative", false),
      ]);
      const levels = [1, 2, 3, 4, 5, 6, 7];
      return h(
        NPopover,
        { trigger: "hover", placement: "top", showArrow: false },
        {
          trigger: () => trigger,
          default: () =>
            h("div", { class: "suggested-price-popover" }, [
              h("div", { class: "suggested-price-popover-title" }, [
                "均价 ",
                row.price.toFixed(3),
                h("span", { class: "holding-sub" }, cny(row.price)),
              ]),
              ...levels.map((level) => {
                const ratio = level / 100;
                const lower = row.price * (1 - ratio);
                const upper = row.price * (1 + ratio);
                return h("div", { class: "suggested-price-popover-row" }, [
                  h("span", `±${level}%`),
                  targetText(lower, "amount-positive"),
                  targetText(upper, "amount-negative"),
                ]);
              }),
            ]),
        },
      );
    },
    sorter: (a, b) => {
      const profileA = holdingProfiles.value[a.code] || {};
      const profileB = holdingProfiles.value[b.code] || {};
      const valueA = a.price * (1 + Number(profileA.rise_pct ?? 5) / 100);
      const valueB = b.price * (1 + Number(profileB.rise_pct ?? 5) / 100);
      return valueA - valueB;
    },
  },
  {
    title: "浮动盈亏",
    key: "floatPnl",
    width: 145,
    render: (row) => {
      if (hideAmount.value) return "***";
      const cur = props.quotes[row.code]?.price;
      if (!cur || !(row.price > 0)) return "--";
      const direction = row.side === "买入" ? 1 : -1;
      const pnl = (cur - row.price) * row.quantity * direction;
      const pct = ((cur - row.price) / row.price) * 100 * direction;
      const cls = pnl >= 0 ? "amount-positive" : "amount-negative";
      const pnlSign = pnl >= 0 ? "+" : "";
      const pctSign = pct >= 0 ? "+" : "";
      return h("span", { class: cls }, `${pnlSign}${formatMoney(pnl)} (${pctSign}${pct.toFixed(2)}%)`);
    },
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
        "0.000",
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
