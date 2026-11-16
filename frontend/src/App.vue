<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { api, isAuthed, logout } from "./api";

const router = useRouter();
const route = useRoute();
const tournament = ref(null);

const showShell = computed(() => isAuthed() && route.name !== "login");

async function loadTournament() {
  try {
    const data = await api.health();
    tournament.value = data.tournament || null;
  } catch (ignored) {
    tournament.value = null;
  }
}

function signOut() {
  logout();
  router.push({ name: "login" });
}

onMounted(loadTournament);
watch(
  () => route.fullPath,
  () => {
    if (isAuthed()) loadTournament();
  }
);
</script>

<template>
  <header v-if="showShell" class="topbar">
    <div class="brand">SamboTL <span>· рабочие экраны</span></div>
    <div v-if="tournament" class="muted">
      {{ tournament.name }}
      <template v-if="tournament.association"> · {{ tournament.association }}</template>
      · ковров: {{ tournament.mats }}
    </div>
    <div class="spacer"></div>
    <nav class="row">
      <button class="ghost" @click="router.push('/home')">Меню</button>
      <button class="ghost" @click="router.push('/weighing')">Взвешивание</button>
      <button class="ghost" @click="router.push('/draw')">Жеребьёвка</button>
      <button class="ghost" @click="router.push('/referee')">Судейство</button>
      <button class="ghost" @click="router.push('/scoreboard')">Табло</button>
      <button class="ghost" @click="router.push('/schedule')">Расписание</button>
      <button class="ghost" @click="router.push('/reports')">Отчёты</button>
      <button class="ghost" @click="signOut">Выйти</button>
    </nav>
  </header>

  <RouterView />
</template>
