<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";

import { api, connectLive } from "../api";

const bouts = ref([]);
const health = ref(null);
const error = ref("");
let live = null;

const statusLabel = {
  pending: "Ожидает",
  ready: "Готова",
  on_mat: "На ковре",
  finished: "Завершена",
  cancelled: "Отменена",
};

const byMat = computed(() => {
  const result = new Map();
  for (const bout of bouts.value) {
    if (bout.mat === null || bout.mat === undefined) continue;
    if (!result.has(bout.mat)) result.set(bout.mat, []);
    result.get(bout.mat).push(bout);
  }
  for (const list of result.values()) {
    list.sort((a, b) => (a.order || 0) - (b.order || 0));
  }
  return [...result.entries()].sort((a, b) => a[0] - b[0]);
});

function statusClass(status) {
  if (status === "on_mat") return "badge ok";
  if (status === "finished") return "badge";
  if (status === "ready") return "badge";
  return "badge";
}

async function load() {
  try {
    const [h, program] = await Promise.all([api.health(), api.boutsProgram()]);
    health.value = h;
    bouts.value = program;
    error.value = "";
  } catch (e) {
    error.value = e.message;
  }
}

function onLive(event) {
  if (event.type !== "bout.updated") return;
  const index = bouts.value.findIndex((b) => b.id === event.bout_id);
  if (index === -1) return;
  bouts.value[index] = {
    ...bouts.value[index],
    status: event.status,
    score_a: event.score_a,
    score_b: event.score_b,
    winner_side: event.winner_side,
    result_text: event.result_text,
    started_at: event.started_at,
    finished_at: event.finished_at,
    a: event.a,
    b: event.b,
  };
}

onMounted(() => {
  load();
  live = connectLive(onLive);
});

onUnmounted(() => {
  if (live) live.close();
});
</script>

<template>
  <main class="app-shell">
    <div v-if="error" class="alert err">{{ error }}</div>

    <div class="card">
      <h1>Расписание</h1>
      <p v-if="health && health.tournament" class="muted">
        {{ health.tournament.name }}
        <template v-if="health.tournament.association">
          · {{ health.tournament.association }}
        </template>
      </p>
    </div>

    <div class="grid" style="margin-top: 18px; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));">
      <div v-for="[matNumber, list] in byMat" :key="matNumber" class="card">
        <h2>Ковёр {{ matNumber }}</h2>
        <div class="list">
          <transition-group name="bout">
            <div
              v-for="bout in list"
              :key="bout.id"
              class="list-row bout"
              :class="{ live: bout.status === 'on_mat', done: bout.status === 'finished' }"
            >
              <div class="grow">
                <div class="name">
                  {{ bout.a }} — {{ bout.b }}
                </div>
                <div class="muted" style="font-size: 0.85rem">
                  <span v-if="bout.category">{{ bout.category }} · </span>
                  <span v-if="bout.status === 'finished' && bout.score_a !== undefined">
                    {{ bout.score_a }}:{{ bout.score_b }}
                  </span>
                </div>
              </div>
              <span :class="statusClass(bout.status)">{{ statusLabel[bout.status] || bout.status }}</span>
            </div>
          </transition-group>
          <div v-if="!list.length" class="list-row muted">Схваток нет</div>
        </div>
      </div>

      <div v-if="!byMat.length" class="card muted">
        Схватки ещё не распределены по коврам. Проведите жеребьёвку и распределение.
      </div>
    </div>
  </main>
</template>

<style scoped>
.bout {
  transition: background 0.3s ease;
}
.bout.live {
  background: rgba(37, 99, 235, 0.2);
  border-left: 3px solid #2563eb;
}
.bout.done {
  opacity: 0.7;
}
.bout-enter-active,
.bout-leave-active {
  transition: all 0.35s ease;
}
.bout-enter-from {
  opacity: 0;
  transform: translateY(-8px);
}
.bout-leave-to {
  opacity: 0;
}
</style>
