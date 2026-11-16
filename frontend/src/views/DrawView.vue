<script setup>
import { onMounted, ref } from "vue";

import { api } from "../api";

const brackets = ref([]);
const strategy = ref("mixed");
const selected = ref(null);
const preview = ref(null);
const message = ref("");
const error = ref("");
const busy = ref(false);

const strategies = [
  { value: "random", label: "Случайная" },
  { value: "seeded", label: "Посев" },
  { value: "mixed", label: "Смешанная" },
];

const STRATEGY_LABEL = Object.fromEntries(strategies.map((s) => [s.value, s.label]));

async function refresh() {
  try {
    brackets.value = await api.brackets();
    error.value = "";
  } catch (e) {
    error.value = e.message;
  }
}

async function setupAll() {
  busy.value = true;
  error.value = "";
  try {
    const result = await api.bracketSetup();
    message.value = `Создано сеток: ${result.created.length}`;
    await refresh();
  } catch (e) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}

function select(bracket) {
  selected.value = bracket;
  preview.value = null;
}

async function runPreview() {
  if (!selected.value) return;
  busy.value = true;
  error.value = "";
  try {
    preview.value = await api.bracketPreview(selected.value.id, strategy.value);
  } catch (e) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}

async function runGenerate() {
  if (!selected.value) return;
  busy.value = true;
  error.value = "";
  try {
    const result = await api.bracketGenerate(selected.value.id, strategy.value);
    message.value = `Сетка #${result.bracket}: создано схваток — ${result.bouts}`;
    preview.value = null;
    await refresh();
  } catch (e) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}

function roundSize(round) {
  return round.length;
}

function athleteName(id) {
  if (id === null || id === undefined) return "—";
  const found = (preview.value?.athletes || []).find((a) => a.id === id);
  return found ? found.name : `#${id}`;
}

onMounted(refresh);
</script>

<template>
  <main class="app-shell">
    <div v-if="error" class="alert err">{{ error }}</div>
    <div v-if="message" class="alert ok">{{ message }}</div>

    <div class="card">
      <div class="row" style="align-items: center">
        <h2 style="margin: 0">Жеребьёвка</h2>
        <div class="spacer"></div>
        <button :disabled="busy" @click="setupAll">Создать сетки по категориям</button>
      </div>

      <div class="row" style="margin-top: 16px">
        <div style="flex: 1; min-width: 200px">
          <label for="strategy">Стратегия жеребьёвки</label>
          <select id="strategy" v-model="strategy">
            <option v-for="s in strategies" :key="s.value" :value="s.value">
              {{ s.label }}
            </option>
          </select>
        </div>
        <div style="flex: 1; min-width: 200px">
          <label>Действия</label>
          <div class="row">
            <button class="primary" :disabled="!selected || busy" @click="runPreview">
              Предпросмотр
            </button>
            <button class="ok" :disabled="!selected || busy" @click="runGenerate">
              Провести жеребьёвку
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="grid cols-2" style="margin-top: 18px">
      <div class="card">
        <h2>Сетки</h2>
        <div class="list">
          <div
            v-for="b in brackets"
            :key="b.id"
            class="list-row"
            :class="{ selected: selected && selected.id === b.id }"
            @click="select(b)"
          >
            <div class="grow">
              <div class="name">{{ b.weight_category || b.name }}</div>
              <div class="muted" style="font-size: 0.85rem">
                {{ b.system }} · участников: {{ b.athletes_count }}
              </div>
            </div>
            <span v-if="b.is_approved" class="badge ok">утверждена</span>
            <span v-else class="badge">не утверждена</span>
          </div>
          <div v-if="!brackets.length" class="list-row muted">
            Сеток пока нет — нажмите «Создать сетки по категориям»
          </div>
        </div>
      </div>

      <div class="card">
        <h2>
          Предпросмотр сетки
          <span v-if="preview" class="badge" style="margin-left: 8px">
            {{ STRATEGY_LABEL[preview.strategy] }}
          </span>
        </h2>

        <div v-if="preview">
          <p class="muted">
            Размер сетки: {{ preview.size }} · бай-мест: {{ preview.byes }}
          </p>
          <table class="bracket">
            <thead>
              <tr>
                <th>Раунд</th>
                <th>Пара</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(round, ri) in preview.rounds" :key="ri">
                <td>{{ ri + 1 }}</td>
                <td>
                  <template v-for="(pair, pi) in round" :key="pi">
                    <span v-if="pair.bye" class="muted">bye</span>
                    <span v-else>
                      {{ athleteName(pair.a) }} — {{ athleteName(pair.b) }}
                    </span>
                    <span v-if="pi < round.length - 1"> · </span>
                  </template>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="muted">
          Выберите сетку и нажмите «Предпросмотр», чтобы увидеть результат жеребьёвки.
        </p>
      </div>
    </div>
  </main>
</template>
