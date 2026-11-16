<script setup>
import { onMounted, onUnmounted, ref } from "vue";

import { api, connectLive } from "../api";

const mats = ref([]);
const selectedMat = ref(null);
const bouts = ref([]);
const current = ref(null);
const message = ref("");
const error = ref("");
const busy = ref(false);
let live = null;

async function loadMats() {
  try {
    mats.value = await api.mats();
    error.value = "";
  } catch (e) {
    error.value = e.message;
  }
}

async function loadProgram() {
  if (selectedMat.value === null) return;
  try {
    const all = await api.boutsProgram();
    bouts.value = all.filter((b) => b.mat === selectedMat.value);
    error.value = "";
  } catch (e) {
    error.value = e.message;
  }
}

function selectMat(mat) {
  selectedMat.value = mat.number;
  current.value = null;
  loadProgram();
}

async function start(bout) {
  busy.value = true;
  error.value = "";
  try {
    await api.boutStart(bout.id);
    message.value = `Схватка ${bout.a} — ${bout.b} начата`;
  } catch (e) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}

async function score(bout, side, value) {
  try {
    await api.boutScore(bout.id, side, value);
  } catch (e) {
    error.value = e.message;
  }
}

async function warning(bout, side) {
  try {
    await api.boutWarning(bout.id, side);
  } catch (e) {
    error.value = e.message;
  }
}

async function finish(bout, winnerSide) {
  try {
    await api.boutFinish(bout.id, winnerSide, "");
    message.value = `Схватка завершена. Победитель: ${winnerSide === "A" ? bout.a : bout.b}`;
  } catch (e) {
    error.value = e.message;
  }
}

function onLive(event) {
  if (event.type === "bout.updated" && current.value) {
    if (event.bout_id === current.value.id) {
      current.value = {
        ...current.value,
        score_a: event.score_a,
        score_b: event.score_b,
        warnings_a: event.warnings_a,
        warnings_b: event.warnings_b,
        status: event.status,
      };
    }
  }
}

onMounted(() => {
  loadMats();
  live = connectLive(onLive);
});

onUnmounted(() => {
  if (live) live.close();
});
</script>

<template>
  <main class="app-shell">
    <div v-if="error" class="alert err">{{ error }}</div>
    <div v-if="message" class="alert ok">{{ message }}</div>

    <div class="card">
      <h2>Судейство</h2>
      <div class="row">
        <div v-for="m in mats" :key="m.id">
          <button
            :class="selectedMat === m.number ? 'primary' : ''"
            @click="selectMat(m)"
          >
            Ковёр {{ m.number }}
          </button>
        </div>
      </div>
    </div>

    <div class="grid cols-2" style="margin-top: 18px">
      <div class="card">
        <h3>Очередь схваток</h3>
        <div class="list">
          <div
            v-for="b in bouts"
            :key="b.id"
            class="list-row"
            :class="{ selected: current && current.id === b.id }"
            @click="current = b"
          >
            <div class="grow">
              <div class="name">{{ b.a }} — {{ b.b }}</div>
              <div class="muted">{{ b.status }}</div>
            </div>
            <button v-if="b.status === 'ready'" class="ok" @click.stop="start(b)">
              Начать
            </button>
          </div>
          <div v-if="!bouts.length" class="list-row muted">Схваток нет</div>
        </div>
      </div>

      <div class="card" v-if="current">
        <h3>{{ current.a }} — {{ current.b }}</h3>
        <div class="row" style="margin-top: 12px">
          <button class="primary" @click="score(current, 'A', 1)">+1 A</button>
          <button class="primary" @click="score(current, 'A', 2)">+2 A</button>
          <button class="primary" @click="score(current, 'A', 4)">+4 A</button>
          <button @click="warning(current, 'A')">Замечание A</button>
        </div>
        <div class="row" style="margin-top: 12px">
          <button class="primary" @click="score(current, 'B', 1)">+1 B</button>
          <button class="primary" @click="score(current, 'B', 2)">+2 B</button>
          <button class="primary" @click="score(current, 'B', 4)">+4 B</button>
          <button @click="warning(current, 'B')">Замечание B</button>
        </div>
        <div class="row" style="margin-top: 16px">
          <button class="ok" @click="finish(current, 'A')">Победа A</button>
          <button class="ok" @click="finish(current, 'B')">Победа B</button>
        </div>
      </div>
    </div>
  </main>
</template>
