import { createRouter, createWebHistory } from "vue-router";

import { isAuthed } from "./api";
import DrawView from "./views/DrawView.vue";
import HomeView from "./views/HomeView.vue";
import LoginView from "./views/LoginView.vue";
import RefereeView from "./views/RefereeView.vue";
import ReportsView from "./views/ReportsView.vue";
import ScheduleView from "./views/ScheduleView.vue";
import ScoreboardView from "./views/ScoreboardView.vue";
import WeighingView from "./views/WeighingView.vue";

const routes = [
  { path: "/", name: "login", component: LoginView, meta: { public: true } },
  { path: "/home", name: "home", component: HomeView },
  { path: "/weighing", name: "weighing", component: WeighingView },
  { path: "/draw", name: "draw", component: DrawView },
  { path: "/referee", name: "referee", component: RefereeView },
  { path: "/scoreboard", name: "scoreboard", component: ScoreboardView },
  { path: "/schedule", name: "schedule", component: ScheduleView },
  { path: "/reports", name: "reports", component: ReportsView },
  { path: "/:pathMatch(.*)*", redirect: "/" },
];

const router = createRouter({
  history: createWebHistory("/app/"),
  routes,
});

// Every screen except the login form requires the shared access password.
router.beforeEach((to) => {
  if (!to.meta.public && !isAuthed()) {
    return { name: "login" };
  }
  return true;
});

export default router;
