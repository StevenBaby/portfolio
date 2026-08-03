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
export function aggregateByDate(trades, metric = "amount") {
  const dateSet = new Set();
  const byCode = {};

  for (const t of trades) {
    if (isReverseRepo(t.code)) continue
    const date = t.datetime.split(" ")[0]
    dateSet.add(date)
    if (!byCode[t.code]) byCode[t.code] = { name: t.name, data: {} }
    let val
    if (metric === 'amount') {
      val = t.side === '买入' ? t.amount + t.fee : -(t.amount - t.fee)
    } else if (metric === 'quantity') {
      val = t.side === '买入' ? t.quantity : -t.quantity
    } else if (metric === 'fee') {
      val = t.fee
    }
    byCode[t.code].data[date] = (byCode[t.code].data[date] || 0) + val
  }

  const dates = [...dateSet].sort();
  const series = Object.entries(byCode).map(([code, info]) => ({
    code,
    name: info.name,
    data: dates.map((d) => info.data[d] || 0),
  }));

  return { dates: dates.map(formatDate), series };
}
