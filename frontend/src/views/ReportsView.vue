<script setup>
import { onMounted, ref } from "vue";

import { api, downloadReport } from "../api";

const brackets = ref([]);
const message = ref("");
const error = ref("");

async function load() {
  try {
    brackets.value = await api.brackets();
    error.value = "";
  } catch (e) {
    error.value = e.message;
  }
}

async function weighings() {
  try {
    await downloadReport("/api/reports/weighing.xlsx", "взвешивание.xlsx");
    message.value = "Протокол взвешивания скачан";
  } catch (e) {
    error.value = e.message;
  }
}

async function bracket(id) {
  try {
    await downloadReport(`/api/reports/bracket/${id}.xlsx`, `сетка-${id}.xlsx`);
    message.value = `Сетка #${id} скачана`;
  } catch (e) {
    error.value = e.message;
  }
}

async function results() {
  try {
    await downloadReport("/api/reports/results.docx", "итоги.docx");
    message.value = "Итоговый протокол скачан";
  } catch (e) {
    error.value = e.message;
  }
}

onMounted(load);
</script>

<template>
  <main class="app-shell">
    <div v-if="error" class="alert err">{{ error }}</div>
    <div v-if="message" class="alert ok">{{ message }}</div>

    <div class="card">
      <h1>Отчёты</h1>
      <p class="muted">Скачивание протоколов и сеток в Word / Excel.</p>

      <div class="row" style="margin-top: 14px">
        <button class="primary big" @click="weighings">Протокол взвешивания (Excel)</button>
        <button class="primary big" @click="results">Итоговый протокол (Word)</button>
      </div>
    </div>

    <div class="card" style="margin-top: 18px">
      <h2>Сетки по категориям</h2>
      <div class="list">
        <div v-for="b in brackets" :key="b.id" class="list-row">
          <div class="grow">
            <div class="name">{{ b.weight_category || b.name }}</div>
            <div class="muted" style="font-size: 0.85rem">участников: {{ b.athletes_count }}</div>
          </div>
          <button @click="bracket(b.id)">Скачать Excel</button>
        </div>
        <div v-if="!brackets.length" class="list-row muted">Сеток пока нет</div>
      </div>
    </div>
  </main>
</template>
