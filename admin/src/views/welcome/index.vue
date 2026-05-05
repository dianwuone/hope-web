<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { fetchDashboard } from "@/api/admin";

defineOptions({
  name: "Welcome"
});

const loading = ref(false);
const stats = ref<Record<string, number>>({
  articles: 0,
  products: 0,
  games: 0,
  labs: 0,
  offers: 0,
  ads: 0,
  siteConfigs: 0,
  pageConfigs: 0,
  wishlistItems: 0,
  communityLeads: 0,
  betaApplications: 0,
  userInteractions: 0
});
const wishlistTopProjects = ref<Array<{ name: string; count: number }>>([]);

const cards = computed(() => [
  { label: "文章", value: stats.value.articles },
  { label: "产品", value: stats.value.products },
  { label: "游戏", value: stats.value.games },
  { label: "实验室", value: stats.value.labs },
  { label: "商品", value: stats.value.offers },
  { label: "广告", value: stats.value.ads },
  { label: "全站配置", value: stats.value.siteConfigs + stats.value.pageConfigs },
  { label: "心愿单", value: stats.value.wishlistItems },
  { label: "用户线索", value: stats.value.communityLeads },
  { label: "内测申请", value: stats.value.betaApplications },
  { label: "互动总量", value: stats.value.userInteractions }
]);

async function loadStats() {
  loading.value = true;
  try {
    const dashboard = await fetchDashboard();
    stats.value = dashboard.overview;
    wishlistTopProjects.value = dashboard.wishlist.topProjects;
  } catch (error: any) {
    ElMessage.error(error?.message || "加载仪表盘失败");
  } finally {
    loading.value = false;
  }
}

onMounted(loadStats);
</script>

<template>
  <div class="p-4">
    <el-page-header content="后台概览" />
    <el-row :gutter="16" class="mt-4">
      <el-col v-for="item in cards" :key="item.label" :xs="12" :sm="8" :md="6" :lg="4">
        <el-card shadow="hover" class="mb-4">
          <div class="text-sm text-gray-500">{{ item.label }}</div>
          <div class="mt-3 text-3xl font-bold">{{ item.value }}</div>
        </el-card>
      </el-col>
    </el-row>
    <el-card shadow="never">
      <template #header>当前状态</template>
      <el-space direction="vertical" alignment="start">
        <div>已接入互动数据统计，包括心愿单、用户线索与内测申请。</div>
        <div>当前页面基于 pure-admin 布局，适合作为轻量运营后台持续扩展。</div>
        <el-button type="primary" :loading="loading" @click="loadStats">刷新统计</el-button>
      </el-space>
    </el-card>
    <el-card shadow="never" class="mt-4">
      <template #header>最受期待项目</template>
      <el-table :data="wishlistTopProjects" empty-text="暂无心愿单数据">
        <el-table-column prop="name" label="项目" min-width="220" />
        <el-table-column prop="count" label="心愿数" width="120" />
      </el-table>
    </el-card>
  </div>
</template>
