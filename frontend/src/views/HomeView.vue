<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";

import { api, connectLive } from "../api";

const router = useRouter();
const progress = ref({ total: 0, done: 0, remaining: 0 });
const tournament = ref(null);
const error = ref("");
let live = null;

const roles = [
  {
    title: "Взвешивание",
    desc: "Текущий вес, отметка «прошёл / не прошёл», поиск по участникам",
    to: "/weighing",
    enabled: true,
  },
  {
    title: "Жеребьёвка",
    desc: "Жребий (случайный / посев / смешанный), предпросмотр сетки, ковры",
    to: "/draw",
    enabled: true,
  },
  {
    title: "Судейство",
    desc: "Ход схватки, очки, замечания, победитель",
    to: "/referee",
    enabled: true,
  },
  {
    title: "Табло (ТВ)",
    desc: "Второй экран: таймер, борцы, «кто готовится»",
    to: "/scoreboard",
    enabled: true,
  },
  { title: "Расписание", desc: "Очередь схваток по коврам", to: "/schedule", enabled: true },
  {
    title: "Отчёты",
    desc: "Протоколы взвешивания, сетки и итоги в Word / Excel",
    to: "/reports",
    enabled: true,
  },
];

const percent = computed(() =>
  progress.value.total
    ? Math.round((progress.value.done / progress.value.total) * 100)
    : 0
);

async function refresh() {
  try {
    const [prog, health] = await Promise.all([api.weighingProgress(), api.health()]);
    progress.value = prog;
    tournament.value = health.tournament || null;
    error.value = "";
  } catch (e) {
    error.value = e.message;
  }
}

function open(role) {
  if (role.enabled) router.push(role.to);
}

onMounted(() => {
  refresh();
  live = connectLive((event) => {
    if (event.type === "weighing.progress") {
      progress.value = {
        total: event.total,
        done: event.done,
        remaining: event.total - event.done,
      };
    }
  });
});

onUnmounted(() => {
  if (live) live.close();
});
</script>

<template>
  <main class="app-shell">
    <div v-if="error" class="alert err">{{ error }}</div>

    <div class="card">
      <h1>Этап: взвешивание</h1>
      <p class="muted">
        <template v-if="tournament">{{ tournament.name }} · </template>
        выберите рабочий экран
      </p>

      <div class="stat" style="margin: 16px 0 10px">
        <div>
          <div class="value">{{ progress.done }} / {{ progress.total }}</div>
          <div class="muted">взвешено</div>
        </div>
        <div>
          <div class="value">{{ progress.remaining }}</div>
          <div class="muted">осталось</div>
        </div>
        <div>
          <div class="value">{{ percent }}%</div>
          <div class="muted">готовность</div>
        </div>
      </div>

      <div class="progress"><span :style="{ width: percent + '%' }"></span></div>
    </div>

    <div class="grid cols-2" style="margin-top: 18px">
      <button
        v-for="role in roles"
        :key="role.title"
        class="card tile"
        :class="{ ghost: !role.enabled }"
        :disabled="!role.enabled"
        @click="open(role)"
      >
        <span class="tile-title">{{ role.title }}</span>
        <span class="muted">{{ role.desc }}</span>
        <span v-if="!role.enabled" class="badge">скоро</span>
      </button>
    </div>
  </main>
</template>
