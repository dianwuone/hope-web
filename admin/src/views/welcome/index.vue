<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { fetchArticles, fetchOffers, fetchPageConfigs, fetchProjects, fetchSiteConfigs } from "@/api/admin";

defineOptions({
  name: "Welcome"
});

const loading = ref(false);
const stats = ref({
  articles: 0,
  products: 0,
  games: 0,
  labs: 0,
  offers: 0,
  siteConfigs: 0,
  pageConfigs: 0
});

const cards = computed(() => [
  { label: "文章", value: stats.value.articles },
  { label: "产品", value: stats.value.products },
  { label: "游戏", value: stats.value.games },
  { label: "实验室", value: stats.value.labs },
  { label: "商品", value: stats.value.offers },
  { label: "全站配置", value: stats.value.siteConfigs + stats.value.pageConfigs }
]);

async function loadStats() {
  loading.value = true;
  try {
    const [articles, projects, offers, siteConfigs, pageConfigs] = await Promise.all([
      fetchArticles(),
      fetchProjects(),
      fetchOffers(),
      fetchSiteConfigs(),
      fetchPageConfigs()
    ]);
    stats.value = {
      articles: articles.total,
      products: projects.items.filter(item => item.projectType === "product").length,
      games: projects.items.filter(item => item.projectType === "game").length,
      labs: projects.items.filter(item => item.projectType === "lab").length,
      offers: offers.total,
      siteConfigs: siteConfigs.total,
      pageConfigs: pageConfigs.total
    };
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
        <div>已接入 FastAPI 后台真实数据接口。</div>
        <div>当前页面基于 pure-admin 布局，后续继续完善为完整运营后台。</div>
        <el-button type="primary" :loading="loading" @click="loadStats">刷新统计</el-button>
      </el-space>
    </el-card>
  </div>
</template>
