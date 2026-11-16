<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";

import { api, setToken } from "../api";

const router = useRouter();
const password = ref("");
const error = ref("");
const busy = ref(false);

async function submit() {
  if (!password.value.trim()) {
    error.value = "Введите пароль доступа";
    return;
  }
  busy.value = true;
  error.value = "";
  setToken(password.value.trim());
  try {
    // Any authenticated endpoint validates the password.
    await api.participants();
    router.push("/home");
  } catch (e) {
    setToken("");
    error.value = e.message || "Не удалось войти";
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="center-wrap">
    <div class="card login-card">
      <h1>SamboTL</h1>
      <p class="muted">Введите пароль доступа к турниру</p>

      <div v-if="error" class="alert err">{{ error }}</div>

      <form @submit.prevent="submit">
        <label for="password">Пароль</label>
        <input
          id="password"
          v-model="password"
          type="password"
          autocomplete="current-password"
          autofocus
        />
        <button
          class="primary big"
          type="submit"
          :disabled="busy"
          style="width: 100%; margin-top: 16px"
        >
          {{ busy ? "Проверка…" : "Войти" }}
        </button>
      </form>

      <p class="muted" style="margin-top: 14px; font-size: 0.85rem">
        Пароль задаётся при создании турнира или в админке на сервере.
      </p>
    </div>
  </div>
</template>
