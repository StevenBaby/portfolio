<template>
  <div class="page-container tools-page">
    <div class="tool-grid">
      <section class="tool-panel">
        <div class="tool-panel-heading">
          <div class="tool-panel-title">黄金 ETF ⇄ 上海金</div>
          <div class="tool-badge">518880</div>
        </div>

        <div class="converter-rate">
          <span>每 1 份黄金 ETF 对应</span>
          <strong @dblclick="startGoldPerShareEdit">
            <n-input
              v-if="editingGoldPerShare"
              ref="goldPerShareInputRef"
              v-model:value="goldPerShareInput"
              size="small"
              type="text"
              @blur="saveGoldPerShareEdit"
              @keyup.enter="saveGoldPerShareEdit"
              @keyup.esc="cancelGoldPerShareEdit"
            />
            <span v-else>{{ goldPerShareLabel }}</span>
          </strong>
          <span>克黄金</span>
        </div>

        <div class="converter-grid">
          <div class="converter-field">
            <label for="gold-etf-price">黄金 ETF 价格</label>
            <div class="input-unit">
              <n-input
                id="gold-etf-price"
                v-model:value="etfPrice"
                type="text"
                placeholder="例如 6.125"
                :input-props="{ inputmode: 'decimal' }"
                @update:value="convertFromEtf"
              />
              <span>元/份</span>
            </div>
          </div>

          <div class="converter-arrow" aria-label="双向换算">⇄</div>

          <div class="converter-field">
            <label for="shanghai-gold-price">上海金价格</label>
            <div class="input-unit">
              <n-input
                id="shanghai-gold-price"
                v-model:value="shanghaiGoldPrice"
                type="text"
                placeholder="例如 643.80"
                :input-props="{ inputmode: 'decimal' }"
                @update:value="convertFromShanghaiGold"
              />
              <span>元/克</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from "vue";
import { NInput } from "naive-ui";
import { goldPerShare, loadGoldPerShare, saveGoldPerShare } from "../parse.js";

const defaultGoldPerShare = 0.00951;
const editingGoldPerShare = ref(false);
const goldPerShareInput = ref(String(defaultGoldPerShare));
const goldPerShareInputRef = ref(null);
const goldPerShareBeforeEdit = ref(defaultGoldPerShare);
const goldPerShareLabel = computed(() => goldPerShare.value.toFixed(5));
const etfPrice = ref("");
const shanghaiGoldPrice = ref("");

function validNumber(value) {
  const number = Number(String(value).trim());
  return Number.isFinite(number) && number > 0 ? number : null;
}

function convertFromEtf(value) {
  const price = validNumber(value);
  shanghaiGoldPrice.value = price === null ? "" : (price / goldPerShare.value).toFixed(2);
}

function convertFromShanghaiGold(value) {
  const price = validNumber(value);
  etfPrice.value = price === null ? "" : (price * goldPerShare.value).toFixed(3);
}

function cancelGoldPerShareEdit() {
  goldPerShare.value = goldPerShareBeforeEdit.value;
  goldPerShareInput.value = goldPerShareBeforeEdit.value.toFixed(5);
  editingGoldPerShare.value = false;
}

function startGoldPerShareEdit() {
  goldPerShareBeforeEdit.value = goldPerShare.value;
  goldPerShareInput.value = goldPerShare.value.toFixed(5);
  editingGoldPerShare.value = true;
  nextTick(() => goldPerShareInputRef.value?.focus());
}

async function saveGoldPerShareEdit() {
  if (!editingGoldPerShare.value) return;
  const value = validNumber(goldPerShareInput.value);
  if (value === null) return cancelGoldPerShareEdit();
  try {
    goldPerShare.value = await saveGoldPerShare(value);
    goldPerShareInput.value = goldPerShare.value.toFixed(5);
    editingGoldPerShare.value = false;
  } catch (error) {
    console.error("保存黄金 ETF 含金量失败:", error);
    cancelGoldPerShareEdit();
  }
}

onMounted(async () => {
  goldPerShare.value = await loadGoldPerShare();
  goldPerShareInput.value = goldPerShare.value.toFixed(5);
});
</script>
