<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";

import { api, connectLive } from "../api";

const search = ref("");
const participants = ref([]);
const weighIns = ref([]);
const progress = ref({ total: 0, done: 0, remaining: 0 });
const selected = ref(null);
const currentWeight = ref("");
const passed = ref(true);
const weighedBy = ref("");
const note = ref("");
const saving = ref(false);
const message = ref("");
const error = ref("");
let live = null;

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase();
  if (!q) return participants.value;
  return participants.value.filter((p) =>
    `${p.full_name} ${p.club_name} ${p.region} ${p.category || ""}`
      .toLowerCase()
      .includes(q)
  );
});

function isWeighed(participant) {
  return participant.status === "weighed";
}

function select(participant) {
  selected.value = participant;
  currentWeight.value = participant.current_weight
    ? String(participant.current_weight)
    : participant.declared_weight
      ? String(participant.declared_weight)
      : "";
  passed.value = true;
  note.value = "";
  message.value = "";
  error.value = "";
}

async function refresh() {
  try {
    const [ps, ws, prog] = await Promise.all([
      api.participants(search.value),
      api.weighIns(),
      api.weighingProgress(),
    ]);
    participants.value = ps;
    weighIns.value = ws;
    progress.value = prog;
    error.value = "";
  } catch (e) {
    error.value = e.message;
  }
}

async function save() {
  if (!selected.value) return;
  saving.value = true;
  message.value = "";
  error.value = "";
  try {
    await api.weighIn({
      participant_id: selected.value.id,
      current_weight: currentWeight.value,
      passed: passed.value,
      weighed_by: weighedBy.value,
      note: note.value,
    });
    message.value = `${selected.value.full_name} — взвешен (${currentWeight.value} кг)`;
    await refresh();
    selected.value = null;
  } catch (e) {
    error.value = e.message;
  } finally {
    saving.value = false;
  }
}

let searchTimer = null;
function onSearch() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(refresh, 250);
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
  clearTimeout(searchTimer);
});
</script>

<template>
  <main class="app-shell">
    <div v-if="error" class="alert err">{{ error }}</div>
    <div v-if="message" class="alert ok">{{ message }}</div>

    <div class="grid cols-2">
      <div>
        <div class="card">
          <h2>Участники</h2>
          <div class="search">
            <input
              v-model="search"
              type="search"
              placeholder="Поиск по ФИО, клубу, региону…"
              @input="onSearch"
            />
          </div>

          <div class="progress" style="margin-bottom: 12px">
            <span
              :style="{ width: (progress.total ? (progress.done / progress.total) * 100 : 0) + '%' }"
            ></span>
          </div>
          <div class="muted" style="margin-bottom: 8px">
            Взвешено {{ progress.done }} из {{ progress.total }} ·
            осталось {{ progress.remaining }}
          </div>

          <div class="list">
            <div
              v-for="p in filtered"
              :key="p.id"
              class="list-row"
              :class="{ selected: selected && selected.id === p.id }"
              @click="select(p)"
            >
              <div class="grow">
                <div class="name">{{ p.short_name }}</div>
                <div class="muted" style="font-size: 0.85rem">
                  {{ p.club_name || "—" }} · {{ p.category || "категория не определена" }}
                </div>
              </div>
              <span v-if="isWeighed(p)" class="badge ok">взвешен</span>
              <span v-else class="badge">ожидает</span>
            </div>
            <div v-if="!filtered.length" class="list-row muted">Никого не найдено</div>
          </div>
        </div>
      </div>

      <div>
        <div class="card">
          <h2>Взвешивание</h2>
          <template v-if="selected">
            <h3>{{ selected.full_name }}</h3>
            <p class="muted">
              {{ selected.club_name || "—" }}
              · заявленный вес: {{ selected.declared_weight || "—" }} кг
              · {{ selected.category || "категория не определена" }}
            </p>

            <label for="w-current">Текущий вес, кг</label>
            <input
              id="w-current"
              v-model="currentWeight"
              type="number"
              step="0.1"
              min="0"
              placeholder="0.0"
            />

            <label style="margin-top: 14px">Результат</label>
            <div class="row">
              <button :class="passed ? 'ok' : ''" type="button" @click="passed = true">
                Прошёл
              </button>
              <button :class="!passed ? 'err' : ''" type="button" @click="passed = false">
                Не прошёл
              </button>
            </div>

            <label style="margin-top: 14px" for="w-by">Кто взвешивал</label>
            <input id="w-by" v-model="weighedBy" placeholder="ФИО судьи" />

            <label style="margin-top: 14px" for="w-note">Примечание</label>
            <input id="w-note" v-model="note" placeholder="необязательно" />

            <div class="row" style="margin-top: 18px">
              <button class="primary big" :disabled="saving" @click="save">
                {{ saving ? "Сохранение…" : "Сохранить" }}
              </button>
              <button class="ghost big" @click="selected = null">Отмена</button>
            </div>
          </template>
          <p v-else class="muted">Выберите участника слева, чтобы взвесить.</p>
        </div>
      </div>
    </div>
  </main>
</template>
