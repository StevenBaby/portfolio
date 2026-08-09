<template>
  <n-config-provider :theme="darkTheme" :locale="zhCN" :date-locale="dateZhCN">
    <n-message-provider>
      <div class="app-container">
        <div class="app-header">
          <div class="header-brand">
            <img class="logo" src="/favicon.svg" alt="logo" />
            <span class="title">portfolio 分析系统</span>
          </div>
          <nav class="header-nav">
            <div
              v-for="item in tabs"
              :key="item.key"
              class="nav-item"
              :class="{ active: tab === item.key }"
              @click="tab = item.key"
            >
              {{ item.label }}
            </div>
          </nav>
        </div>

        <div class="app-content">
          <MarketPage
            v-if="tab === 'market'"
          />
          <TradesPage
            v-if="tab === 'trades'"
            ref="tradesRef"
            :trades="trades"
            :quotes="quotes"
            :holdings="holdings"
          />
          <HoldingsPage
            v-else-if="tab === 'holdings'"
            ref="holdingsRef"
            :holdings="holdings"
            :quotes="quotes"
          />
        </div>
      </div>

      <n-global-style />
    </n-message-provider>
  </n-config-provider>
</template>

<script setup>
import "./style.css";
import { ref, onMounted } from "vue";
import {
  NConfigProvider,
  NMessageProvider,
  NGlobalStyle,
  darkTheme,
  zhCN,
  dateZhCN,
} from "naive-ui";
import { persistedRef } from "./parse.js";
import TradesPage from "./pages/TradesPage.vue";
import HoldingsPage from "./pages/HoldingsPage.vue";
import MarketPage from "./pages/MarketPage.vue";

const tabs = [
  { key: "market", label: "市场" },
  { key: "holdings", label: "持仓" },
  { key: "trades", label: "明细" },
];
const tab = persistedRef("app_tab", "holdings");
const trades = ref([]);
const holdings = ref([]);
const quotes = ref({});

const API = import.meta.env.DEV ? "http://localhost:8090" : "";

onMounted(async () => {
  try {
    const [tradesResp, holdingsResp] = await Promise.all([
      fetch(`${API}/api/trades`),
      fetch(`${API}/api/holdings`),
    ]);
    const data = await tradesResp.json();
    trades.value = data;
    holdings.value = await holdingsResp.json();
    await fetchQuotes();
  } catch (e) {
    console.error("加载数据失败:", e);
  }
});

async function fetchQuotes() {
  const active = holdings.value.filter((h) => h.shares > 0);
  if (!active.length) return;
  const codes = active.map((h) => h.code).join(",");
  try {
    const resp = await fetch(`${API}/api/quotes?codes=${codes}`);
    const data = await resp.json();
    quotes.value = Object.fromEntries(data.map((quote) => [quote.code, quote]));
  } catch (e) {
    console.error("行情获取失败:", e);
  }
}
</script>
