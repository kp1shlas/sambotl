<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";

import { api, connectLive } from "../api";

const mats = ref([]);
const mat = ref(null);
const bouts = ref([]);
const health = ref(null);
const current = ref(null);
const next = ref(null);
const now = ref(Date.now());
let live = null;
let clockTimer = null;

const duration = computed(() =>
  current.value && current.value.status === "on_mat"
    ? current.value.duration || 300
    : null
);

const remaining = computed(() => {
  const bout = current.value;
  if (!bout || !bout.started_at || !duration.value) return null;
  if (bout.status !== "on_mat") return 0;
  const end = new Date(bout.started_at).getTime() + duration.value * 1000;
  const left = Math.max(0, Math.round((end - now.value) / 1000));
  return left;
});

const timerText = computed(() => {
  if (mat.value === null) return "SamboTL";
  if (!current.value) return "Ожидание";
  if (current.value.status === "finished") return "Завершена";
  if (remaining.value === null) return "--:--";
  const m = Math.floor(remaining.value / 60);
  const s = String(remaining.value % 60).padStart(2, "0");
  return `${m}:${s}`;
});

function selectMat(number) {
  mat.value = number;
  partipateInMat();
}

async function load() {
  try {
    const [h, mts, program] = await Promise.all([
      api.health(),
      api.mats(),
      api.boutsProgram(),
    ]);
    health.value = h;
    mats.value = mts;
    bouts.value = program;
    if (mat.value === null && mts.length) {
      mat.value = mts[0].number;
    }
    partipateInMat();
  } catch (ignored) {
    /* nothing */
  }
}

function partipateInMat() {
  if (mat.value === null) return;
  const mine = bouts.value.filter((b) => b.mat === mat.value);
  const active = mine.find((b) => b.status === "on_mat") || current.value;
  if (active) {
    current.value = { ...active };
    next.value =
      mine.find((b) => b.order === active.order + 1) ||
      mine.find((b) => b.status === "ready") ||
      null;
  }
}

function onLive(event) {
  if (event.type === "bout.updated" && mat.value !== null && event.mat === mat.value) {
    current.value = {
      ...(current.value || {}),
      id: event.bout_id,
      ...event,
    };
    if (event.status === "finished") {
      setTimeout(load, 5000);
    }
  }
}

onMounted(() => {
  load();
  live = connectLive(onLive);
  clockTimer = setInterval(() => {
    now.value = Date.now();
  }, 1000);
});

onUnmounted(() => {
  if (live) live.close();
  clearInterval(clockTimer);
});
</script>

<template>
  <main class="scoreboard">
    <div class="sb-top">
      <span v-if="health && health.tournament" class="sb-brand">
        {{ health.tournament.name }}
      </span>
      <div class="row">
        <button
          v-for="m in mats"
          :key="m.id"
          class="ghost"
          :class="{ muted: mat !== m.number }"
          @click="selectMat(m.number)"
        >
          Ковёр {{ m.number }}
        </button>
      </div>
    </div>

    <div v-if="current" class="sb-center">
      <div class="sb-timer" :class="{ urgent: remaining !== null && remaining <= 10 }">
        {{ timerText }}
      </div>
      <div class="sb-fighters">
        <div class="sb-side" :class="{ win: current.winner_side === 'A' || (current.status === 'finished' && current.score_a > current.score_b) }">
          <div class="sb-name">{{ current.a }}</div>
          <div class="sb-score">{{ current.score_a }}</div>
        </div>
        <div class="sb-vs">VS</div>
        <div class="sb-side" :class="{ win: current.winner_side === 'B' || (current.status === 'finished' && current.score_b > current.score_a) }">
          <div class="sb-name">{{ current.b }}</div>
          <div class="sb-score">{{ current.score_b }}</div>
        </div>
      </div>
    </div>
    <div v-else class="sb-center">
      <div class="sb-timer">SamboTL</div>
      <div class="muted">ожидание схватки</div>
    </div>

    <div class="sb-bottom" v-if="next">
      Готовится: {{ next.a }} — {{ next.b }}
    </div>
    <div class="sb-bottom" v-else>—</div>
  </main>
</template>

<style scoped>
.scoreboard {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: radial-gradient(ellipse at 50% 20%, #152435, #060a14);
  color: #e2e8f0;
  padding: 16px;
}

.sb-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 1rem;
  color: #94a3b8;
}

.sb-center {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.sb-timer {
  font-size: 7rem;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}

.sb-timer.urgent {
  color: #f87171;
  animation: pulse 1s infinite;
}

.sb-fighters {
  display: flex;
  align-items: center;
  gap: 20px;
  width: 100%;
  justify-content: center;
}

.sb-side {
  flex: 0 1 45%;
  text-align: center;
  background: #0b1220;
  border: 1px solid #334155;
  border-radius: 18px;
  padding: 20px;
}

.sb-side.win {
  border-color: #16a34a;
  background: rgba(22, 101, 52, 0.15);
}

.sb-name {
  font-size: 2.2rem;
  font-weight: 600;
}

.sb-score {
  font-size: 4rem;
  font-weight: 800;
  margin-top: 6px;
}

.sb-vs {
  font-size: 2rem;
  color: #64748b;
}

.sb-bottom {
  text-align: center;
  font-size: 1.4rem;
  border-top: 1px solid #334155;
  padding-top: 12px;
  margin-top: 12px;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.55;
  }
}
</style>