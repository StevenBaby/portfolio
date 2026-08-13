<template>
  <div class="page-container">
    <div class="sub-tabs">
      <div class="sub-tab" :class="{active: subTab==='probe'}" @click="subTab='probe'">探针</div>
      <div class="sub-tab" :class="{active: subTab==='flow'}" @click="subTab='flow'">资金流</div>
    </div>
    <div v-show="subTab==='probe'" style="overflow:auto;flex:1;padding:0 4px">
      <div v-if="loading" class="probe-loading">加载中...</div>

    <template v-if="data?.us && !loading">
      <div class="probe-section">
        <div class="probe-section-title">美股指数</div>
        <div class="probe-cards">
          <div v-for="(item,key) in data.us.indices" :key="key" class="probe-card">
            <div class="probe-name">{{ fmtName(item) }}</div>
            <div class="probe-price">{{ fmtNum(item.price) }}</div>
            <div class="probe-pct" :class="pctClass(item.pct)">{{ fmtPct(item.pct) }}</div>
          </div>
        </div>
      </div>
      <div class="probe-section">
        <div class="probe-section-title">杠杆 ETF</div>
        <div class="probe-cards">
          <div v-for="(item,key) in data.us.leveraged" :key="key" class="probe-card">
            <div class="probe-name">{{ fmtName(item) }}</div>
            <div class="probe-price">{{ fmtNum(item.price) }}</div>
            <div class="probe-pct" :class="pctClass(item.pct)">{{ fmtPct(item.pct) }}</div>
          </div>
        </div>
      </div>
      <div class="probe-section">
        <div class="probe-section-title">科技七巨头</div>
        <div class="probe-cards">
          <div v-for="(item,key) in data.us.tech" :key="key" class="probe-card">
            <div class="probe-name">{{ fmtName(item) }}</div>
            <div class="probe-price">{{ fmtNum(item.price) }}</div>
            <div class="probe-pct" :class="pctClass(item.pct)">{{ fmtPct(item.pct) }}</div>
          </div>
        </div>
      </div>
    </template>

    <template v-if="data?.cn && !loading">
      <div class="probe-section">
        <div class="probe-section-title">A股指数</div>
        <div class="probe-cards">
          <div v-for="(item,key) in data.cn.indices" :key="key" class="probe-card">
            <div class="probe-name">{{ fmtName(item) }}</div>
            <div class="probe-price">{{ fmtNum(item.price) }}</div>
            <div class="probe-pct" :class="pctClass(item.pct)">{{ fmtPct(item.pct) }}</div>
          </div>
        </div>
      </div>
    </template>

    <template v-if="data?.margin?.data && !loading">
      <div class="probe-section">
        <div class="probe-section-title">融资融券</div>
        <div class="probe-cards">
          <div class="probe-card">
            <div class="probe-name">融资余额{{ fmtDate(data.margin.data.date) }}</div>
            <div class="probe-price">{{ fmtYi(data.margin.data.rzye) }}</div>
            <div class="probe-pct" :class="pctClass(data.margin.data.rzmr_pct)">{{ fmtPct(data.margin.data.rzmr_pct) }}</div>
          </div>
          <div class="probe-card">
            <div class="probe-name">融券余额{{ fmtDate(data.margin.data.date) }}</div>
            <div class="probe-price">{{ fmtYi(data.margin.data.rqye) }}</div>
          </div>
          <div class="probe-card">
            <div class="probe-name">融资融券余额{{ fmtDate(data.margin.data.date) }}</div>
            <div class="probe-price">{{ fmtYi(data.margin.data.rzrqye) }}</div>
          </div>
          <div class="probe-card">
            <div class="probe-name">融资买入额{{ fmtDate(data.margin.data.date) }}</div>
            <div class="probe-price">{{ fmtYi(data.margin.data.rzmr) }}</div>
          </div>
        </div>
      </div>
    </template>

    <template v-if="data?.hk_connect?.data?.length && !loading">
      <div class="probe-section">
        <div class="probe-section-title">港股通</div>
        <div class="probe-cards">
          <div v-for="item in data.hk_connect.data" :key="item.type" class="probe-card">
            <div class="probe-name">{{ item.type }}{{ fmtDate(item.date) }}</div>
            <div class="probe-price">{{ fmtWanYi(item.deal_amt) }}</div>
            <div class="probe-pct" :class="pctClass(item.net_buy)">{{ item.net_buy != null ? fmtWanYi(item.net_buy) : '--' }}</div>
          </div>
        </div>
      </div>
    </template>

    <template v-if="data?.asia && !loading">
      <div class="probe-section" v-if="Object.keys(data.asia.indices||{}).length">
        <div class="probe-section-title">亚太指数</div>
        <div class="probe-cards">
          <template v-for="(item,key) in data.asia.indices" :key="key">
            <div v-if="item" class="probe-card">
              <div class="probe-name">{{ fmtName(item) }}</div>
              <div class="probe-price">{{ fmtNum(item.price) }}</div>
              <div class="probe-pct" :class="pctClass(item.pct)">{{ fmtPct(item.pct) }}</div>
            </div>
          </template>
        </div>
      </div>
      <div class="probe-section" v-if="Object.keys(data.asia.futures||{}).length">
        <div class="probe-section-title">亚太期货</div>
        <div class="probe-cards">
          <template v-for="(item,key) in data.asia.futures" :key="key">
            <div v-if="item" class="probe-card">
              <div class="probe-name">{{ fmtName(item) }}</div>
              <div class="probe-price">{{ fmtNum(item.price) }}</div>
              <div class="probe-pct" :class="pctClass(item.pct)">{{ fmtPct(item.pct) }}</div>
            </div>
          </template>
        </div>
      </div>
    </template>

    <template v-if="data?.macro && !loading">
      <div class="probe-section">
        <div class="probe-section-title">宏观</div>
        <div class="probe-cards">
          <div class="probe-card">
            <div class="probe-name">{{ data.macro.dxy?.name || '美元指数' }}</div>
            <div class="probe-price">{{ fmtNum(data.macro.dxy?.price) }}</div>
          </div>
          <div class="probe-card">
            <div class="probe-name">{{ data.macro.usdcnh?.name || '离岸人民币' }}</div>
            <div class="probe-price">{{ fmtNum(data.macro.usdcnh?.price) }}</div>
          </div>
        </div>
      </div>
    </template>

    <template v-if="data?.commodities && !loading">
      <div class="probe-section" v-if="Object.keys(data.commodities.spot||{}).length">
        <div class="probe-section-title">商品现货</div>
        <div class="probe-cards">
          <template v-for="(item,key) in data.commodities.spot" :key="key">
            <div v-if="item" class="probe-card">
              <div class="probe-name">{{ fmtName(item) }}</div>
              <div class="probe-price">{{ fmtNum(item.price) }}<span v-if="item.cny_per_gram != null" class="probe-sub"> (¥{{ item.cny_per_gram }}/g)</span></div>
              <div class="probe-pct" :class="pctClass(item.pct)">{{ fmtPct(item.pct) }}</div>
            </div>
          </template>
        </div>
      </div>
      <div class="probe-section" v-if="Object.keys(data.commodities.futures||{}).length">
        <div class="probe-section-title">商品期货</div>
        <div class="probe-cards">
          <template v-for="(item,key) in data.commodities.futures" :key="key">
            <div v-if="item" class="probe-card">
              <div class="probe-name">{{ fmtName(item) }}</div>
              <div class="probe-price">{{ fmtNum(item.price) }}<span v-if="item.cny_per_gram != null" class="probe-sub"> (¥{{ item.cny_per_gram }}/g)</span></div>
              <div class="probe-pct" :class="pctClass(item.pct)">{{ fmtPct(item.pct) }}</div>
            </div>
          </template>
        </div>
      </div>
    </template>
    </div>

    <div v-show="subTab==='flow'" style="overflow:auto;flex:1;padding:0 4px">
      <div v-if="flowLoading" class="probe-loading">加载中...</div>
      <template v-if="flowData && !flowLoading">
        <div v-for="item in flowData.data" :key="item.code" class="probe-section">
          <div class="probe-section-title">{{ item.name }}({{ item.date }}{{ item.time ? ' ' + item.time : '' }})</div>
          <div class="probe-cards">
            <div class="probe-card">
              <div class="probe-name">主力净流入</div>
              <div class="probe-price" :class="item.main >= 0 ? 'amount-positive' : 'amount-negative'">{{ fmtYi(item.main) }}</div>
              <div class="probe-pct" :class="item.main_pct >= 0 ? 'amount-positive' : 'amount-negative'">{{ fmtPct(item.main_pct) }}</div>
            </div>
            <div class="probe-card">
              <div class="probe-name">超大单</div>
              <div class="probe-price" :class="item.super_large >= 0 ? 'amount-positive' : 'amount-negative'">{{ fmtYi(item.super_large) }}</div>
            </div>
            <div class="probe-card">
              <div class="probe-name">大单</div>
              <div class="probe-price" :class="item.large >= 0 ? 'amount-positive' : 'amount-negative'">{{ fmtYi(item.large) }}</div>
            </div>
            <div class="probe-card">
              <div class="probe-name">中单</div>
              <div class="probe-price" :class="item.medium >= 0 ? 'amount-positive' : 'amount-negative'">{{ fmtYi(item.medium) }}</div>
            </div>
            <div class="probe-card">
              <div class="probe-name">小单</div>
              <div class="probe-price" :class="item.small >= 0 ? 'amount-positive' : 'amount-negative'">{{ fmtYi(item.small) }}</div>
            </div>
            <div v-if="item.close != null" class="probe-card">
              <div class="probe-name">收盘价</div>
              <div class="probe-price">{{ fmtNum(item.close) }}</div>
              <div class="probe-pct" :class="item.pct >= 0 ? 'amount-positive' : 'amount-negative'">{{ fmtPct(item.pct) }}</div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { persistedRef } from "../parse.js";

const API = import.meta.env.DEV ? "http://localhost:8090" : "";
const subTab = persistedRef("market_subTab", "probe");
const data = ref(null);
const loading = ref(true);

const isAnyTrading = (() => {
  const now = new Date();
  const day = now.getDay();
  if (day === 0 || day === 6) return false;
  const hm = now.getHours() * 100 + now.getMinutes();
  if (hm >= 915 && hm <= 1530) return true;
  if (hm >= 2130 || hm <= 400) return true;
  if (hm >= 800 && hm <= 1600) return true;
  if (hm >= 900 || hm <= 300) return true;
  return false;
})();

const isUsTrading = (() => {
  const now = new Date();
  const day = now.getDay();
  if (day === 0 || day === 6) return false;
  const hm = now.getHours() * 100 + now.getMinutes();
  return hm >= 2130 || hm <= 400;
})();

const isAsiaTrading = (() => {
  const now = new Date();
  const day = now.getDay();
  if (day === 0 || day === 6) return false;
  const hm = now.getHours() * 100 + now.getMinutes();
  return hm >= 800 && hm <= 1600;
})();

const isCommodityTrading = (() => {
  const now = new Date();
  const day = now.getDay();
  if (day === 0 || day === 6) return false;
  const hm = now.getHours() * 100 + now.getMinutes();
  return hm >= 900 || hm <= 300;
})();

const isChinaTrading = (() => {
  const now = new Date();
  const day = now.getDay();
  if (day === 0 || day === 6) return false;
  const hm = now.getHours() * 100 + now.getMinutes();
  return hm >= 915 && hm <= 1530;
})();

const isUsMarketItem = (name) => {
  const usKeywords = ['道琼斯','纳斯达克','标普','半导体ETF','TQQQ','英伟达','苹果','微软','谷歌','亚马逊','特斯拉'];
  return usKeywords.some(k => name?.includes(k));
};

const isAsiaMarketItem = (name) => {
  const asiaKeywords = ['日经','恒生','KOSPI','韩国'];
  return asiaKeywords.some(k => name?.includes(k));
};

const isCommodityItem = (name) => {
  const commKeywords = ['金','银','原油','WTI','COMEX','伦敦'];
  return commKeywords.some(k => name?.includes(k));
};

const isChinaMarketItem = (name) => {
  const cnKeywords = ['上证','深证','创业板','沪深','中证','科创'];
  return cnKeywords.some(k => name?.includes(k));
};

const fmtDate = (date, name) => {
  if (!date) return "";
  if (name && isUsMarketItem(name) && isUsTrading) return "";
  if (name && isAsiaMarketItem(name) && isAsiaTrading) return "";
  if (name && isCommodityItem(name) && isCommodityTrading) return "";
  if (name && isChinaMarketItem(name) && isChinaTrading) return "";
  return `(${date})`;
};

const fmtName = (item) => {
  if (!item?.date) return item?.name;
  const suffix = fmtDate(item.date, item.name);
  return suffix ? `${item.name}${suffix}` : item.name;
};
const fmtNum = (v) => (v != null ? Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 3 }) : "--");
const fmtYi = (v) => (v != null ? `${(v / 1e8).toFixed(2)}亿` : "--");
const fmtWanYi = (v) => (v != null ? `${(v / 100).toFixed(2)}亿` : "--");
const fmtPct = (v) => (v != null ? `${v >= 0 ? "+" : ""}${v.toFixed(2)}%` : "--");
const pctClass = (v) => (v != null ? (v >= 0 ? "amount-positive" : "amount-negative") : "");

const flowData = ref(null);
const flowLoading = ref(false);

async function loadFlowData() {
  if (flowData.value) return;
  flowLoading.value = true;
  try {
    const resp = await fetch(`${API}/api/probe/capital_flow`);
    flowData.value = await resp.json();
  } catch (e) {
    console.error("资金流加载失败:", e);
  } finally {
    flowLoading.value = false;
  }
}

import { watch } from "vue";
watch(subTab, (val) => {
  if (val === "flow") loadFlowData();
});

onMounted(async () => {
  try {
    const resp = await fetch(`${API}/api/probe/all`);
    data.value = await resp.json();
  } catch (e) {
    console.error("探针加载失败:", e);
  } finally {
    loading.value = false;
  }
  if (subTab.value === "flow") loadFlowData();
});
</script>
