/**
 * 格式化日期 YYYYMMDD -> YYYY-MM-DD
 */
export function formatDate(dateStr) {
  if (!dateStr) return dateStr;
  // 支持 "20260612 11:06:44" 格式，只取日期部分
  const d = dateStr.split(" ")[0];
  if (d.length !== 8) return dateStr;
  return `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`;
}

/**
 * 格式化金额
 */
export function formatMoney(val) {
  if (val === undefined || val === null || isNaN(val)) return "";
  return val.toLocaleString("zh-CN", {
    minimumFractionDigits: 3,
    maximumFractionDigits: 3,
  });
}

/**
 * 持久化 ref，同步到 sessionStorage
 */
import { ref, watch } from "vue";

export function persistedRef(key, defaultValue) {
  const stored = sessionStorage.getItem(key);
  let initial = defaultValue;
  if (stored !== null) {
    try {
      initial = JSON.parse(stored);
    } catch {
      initial = stored;
    }
  }
  const r = ref(initial);
  watch(r, (v) => sessionStorage.setItem(key, JSON.stringify(v)), {
    deep: true,
  });
  return r;
}

export const holdingProfiles = ref({});

const API_BASE = import.meta.env.DEV ? "http://localhost:8090" : "";

export async function loadHoldingProfiles() {
  try {
    const resp = await fetch(`${API_BASE}/api/profile`);
    const data = await resp.json();
    const map = {};
    for (const item of data) {
      map[item.code] = { name: item.name || "", color: item.color || "#d03050" };
    }
    holdingProfiles.value = map;
  } catch (e) {
    console.error("加载持仓配置失败:", e);
  }
}

const _saveTimers = {};
export function saveHoldingProfile(code, name, color) {
  if (_saveTimers[code]) clearTimeout(_saveTimers[code]);
  _saveTimers[code] = setTimeout(async () => {
    try {
      await fetch(`${API_BASE}/api/profile`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, name: name || "", color: color || "#d03050" }),
      });
    } catch (e) {
      console.error("保存持仓配置失败:", e);
    }
  }, 500);
}

export async function loadTotalCost() {
  try {
    const resp = await fetch(`${API_BASE}/api/profile/total_cost`);
    return (await resp.json()).total_cost || 0;
  } catch (e) {
    console.error("加载总成本失败:", e);
    return 0;
  }
}

export async function saveTotalCost(cost) {
  try {
    await fetch(`${API_BASE}/api/profile/total_cost`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ total_cost: cost }),
    });
  } catch (e) {
    console.error("保存总成本失败:", e);
  }
}

/**
 * 盈亏渲染：带正负号 + 红绿色 + 隐藏支持
 * 返回 { text, cls } 供调用方决定如何渲染
 */
export function pnlFormat(val, hide) {
  if (hide) return { text: "***", cls: "" };
  const cls = val >= 0 ? "amount-positive" : "amount-negative";
  const sign = val >= 0 ? "+" : "";
  return { text: sign + formatMoney(val), cls };
}

/**
 * 百分比渲染：带正负号 + 红绿色 + 隐藏支持
 */
export function pctFormat(val, hide, decimals) {
  if (hide) return { text: "***", cls: "" };
  const d = decimals || 3;
  const cls = val >= 0 ? "amount-positive" : "amount-negative";
  const sign = val >= 0 ? "+" : "";
  return { text: sign + val.toFixed(d) + "%", cls };
}

/**
 * 统一数据显示：隐藏时返回 ***，否则返回 formatter(val)
 * @param {*} val - 原始值
 * @param {boolean} hide - 是否隐藏
 * @param {function} formatter - 格式化函数，默认 formatMoney
 * @param {*} nullDisplay - 值为 null/undefined 时的显示，默认 '--'
 */
export function displayData(val, hide, formatter, nullDisplay) {
  if (hide) return "***";
  if (val === null || val === undefined) return nullDisplay || "--";
  return formatter ? formatter(val) : String(val);
}

/**
 * 判断是否为逆回购 (代码 131810 或 204001)
 */
export function isReverseRepo(code) {
  return code === "131810" || code === "204001";
}

/**
 * 判断交易方向类型
 */
export function getTradeType(record) {
  if (isReverseRepo(record.code)) return "reverse_repo";
  return record.side === "买入" ? "buy" : "sell";
}

/**
 * 按日期+品种聚合交易金额，用于直方图
 * 返回 { dates: [...], series: [{ name, data: [...] }] }
 */
export function aggregateByDate(trades, metric = "amount", calculationTrades = trades, dailyMarketValue = {}, profiles = {}, quotes = {}) {
  const byCode = {};
  const costByCode = {};
  const snapshots = {};
  const cashFlowByCode = {};

  const visibleCodes = new Set(trades.map((t) => t.code));
  const isPnlMetric = metric === "daily_pnl" || metric === "cumulative_pnl";
  const orderedTrades = [...(isPnlMetric ? calculationTrades : trades)]
    .filter((t) => !isPnlMetric || visibleCodes.has(t.code))
    .sort((a, b) => a.datetime.localeCompare(b.datetime));
  for (const t of orderedTrades) {
    if (isReverseRepo(t.code)) continue;
    const date = t.datetime.split(" ")[0];
    if (!byCode[t.code]) byCode[t.code] = { name: profiles[t.code]?.name || t.name, color: profiles[t.code]?.color, data: {} };
    if (!costByCode[t.code]) costByCode[t.code] = { shares: 0, cost: 0, realized: 0 };
    if (isPnlMetric) {
      cashFlowByCode[t.code] ||= {};
      cashFlowByCode[t.code][date] ||= 0;
      cashFlowByCode[t.code][date] +=
        t.side === "买入" ? -(t.amount + t.fee) : t.amount - t.fee;
    }
    let val = 0;
    if (metric === "amount") {
      val = t.side === "买入" ? t.amount + t.fee : -(t.amount - t.fee);
    } else if (metric === "quantity") {
      val = t.side === "买入" ? t.quantity : -t.quantity;
    } else if (metric === "fee") {
      val = t.fee;
    } else if (metric === "daily_pnl" || metric === "cumulative_pnl") {
      const position = costByCode[t.code];
      if (t.side === "买入") {
        position.shares += t.quantity;
        position.cost += t.amount + t.fee;
      } else {
        const averageCost = position.shares > 0 ? position.cost / position.shares : 0;
        position.realized += t.amount - averageCost * t.quantity - t.fee;
        position.shares -= t.quantity;
        position.cost = averageCost * position.shares;
        if (position.shares === 0) position.cost = 0;
      }
      snapshots[t.code] ||= {};
      snapshots[t.code][date] = {
        shares: position.shares,
        cost: position.cost,
        realized: position.realized,
      };
    }
    const visibleDate = trades.some((visible) => visible.datetime.split(" ")[0] === date);
    if (visibleDate && metric !== "pnl") {
      byCode[t.code].data[date] = (byCode[t.code].data[date] || 0) + val;
    }
  }

  const dates = (isPnlMetric && Object.keys(dailyMarketValue).length)
    ? Object.keys(dailyMarketValue).sort()
    : [...new Set(trades.map((t) => t.datetime.split(" ")[0]))].sort();
  if (isPnlMetric) {
    for (const [code, info] of Object.entries(byCode)) {
      let snapshot = { shares: 0, cost: 0, realized: 0 };
      let previousMarketValue = 0;
      for (const date of dates) {
        snapshot = snapshots[code]?.[date] || snapshot;
        let marketValue = dailyMarketValue[date.replace(/-/g, "")]?.[code] || 0;
        if (date === dates[dates.length - 1] && quotes[code]?.price) {
          marketValue = quotes[code].price * snapshot.shares;
        }
        const floating = marketValue - snapshot.cost;
        if (metric === "cumulative_pnl") {
          info.data[date] = snapshot.realized + floating;
        } else {
          const previousValue = previousMarketValue;
          info.data[date] = marketValue - previousValue + (cashFlowByCode[code]?.[date] || 0);
          previousMarketValue = marketValue;
        }
      }
    }
  }

  const series = Object.entries(byCode).map(([code, info]) => ({
    code,
    name: info.name,
    color: info.color,
    data: dates.map((d) => info.data[d] || 0),
  }));
  return { dates: dates.map(formatDate), series };
}
