<script setup lang="ts">
import { ElMessage } from "element-plus";
import { onMounted, reactive, ref } from "vue";
import { createAd, deleteAd, fetchAds, updateAd } from "@/api/admin";

defineOptions({ name: "AdminAdsPage" });

const loading = ref(false);
const dialogVisible = ref(false);
const items = ref<any[]>([]);
const editingId = ref<number | null>(null);
const form = reactive({
  slotKey: "",
  title: "",
  pageKey: "",
  imageUrl: "",
  targetUrl: "",
  description: "",
  ctaLabel: "",
  status: "draft",
  sortOrder: 0,
  startAt: "",
  endAt: "",
  payloadText: "{}"
});

function resetForm() {
  editingId.value = null;
  Object.assign(form, {
    slotKey: "",
    title: "",
    pageKey: "",
    imageUrl: "",
    targetUrl: "",
    description: "",
    ctaLabel: "",
    status: "draft",
    sortOrder: 0,
    startAt: "",
    endAt: "",
    payloadText: "{}"
  });
}

async function loadData() {
  loading.value = true;
  try {
    const res = await fetchAds();
    items.value = res.items;
  } catch (error: any) {
    ElMessage.error(error?.message || "加载广告失败");
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  resetForm();
  dialogVisible.value = true;
}

function openEdit(row: any) {
  editingId.value = row.id;
  Object.assign(form, {
    slotKey: row.slotKey || "",
    title: row.title || "",
    pageKey: row.pageKey || "",
    imageUrl: row.imageUrl || "",
    targetUrl: row.targetUrl || "",
    description: row.description || "",
    ctaLabel: row.ctaLabel || "",
    status: row.status || "draft",
    sortOrder: row.sortOrder ?? 0,
    startAt: row.startAt ? row.startAt.slice(0, 16) : "",
    endAt: row.endAt ? row.endAt.slice(0, 16) : "",
    payloadText: JSON.stringify(row.payload || {}, null, 2)
  });
  dialogVisible.value = true;
}

async function submit() {
  let payloadObject = {};
  try {
    payloadObject = JSON.parse(form.payloadText || "{}");
  } catch {
    ElMessage.error("附加配置 JSON 格式不正确");
    return;
  }

  const payload = {
    slotKey: form.slotKey,
    title: form.title,
    pageKey: form.pageKey,
    imageUrl: form.imageUrl,
    targetUrl: form.targetUrl,
    description: form.description,
    ctaLabel: form.ctaLabel,
    status: form.status,
    sortOrder: Number(form.sortOrder) || 0,
    startAt: form.startAt || null,
    endAt: form.endAt || null,
    payload: payloadObject
  };

  try {
    if (editingId.value) {
      await updateAd(editingId.value, payload);
      ElMessage.success("广告已更新");
    } else {
      await createAd(payload);
      ElMessage.success("广告已创建");
    }
    dialogVisible.value = false;
    await loadData();
  } catch (error: any) {
    ElMessage.error(error?.message || "保存广告失败");
  }
}

async function remove(row: any) {
  try {
    await deleteAd(row.id);
    ElMessage.success("广告已删除");
    await loadData();
  } catch (error: any) {
    ElMessage.error(error?.message || "删除广告失败");
  }
}

onMounted(loadData);
</script>

<template>
  <div class="p-4">
    <div class="mb-4 flex items-center justify-between">
      <div>
        <h2 class="text-xl font-semibold">广告管理</h2>
        <p class="text-sm text-gray-500">管理首页 Banner、文章推荐位、下载页推广卡等广告内容。</p>
      </div>
      <el-button type="primary" @click="openCreate">新建广告</el-button>
    </div>

    <el-card shadow="never">
      <el-table :data="items" v-loading="loading">
        <el-table-column prop="title" label="标题" min-width="180" />
        <el-table-column prop="slotKey" label="广告位" min-width="160" />
        <el-table-column prop="pageKey" label="页面" width="140" />
        <el-table-column prop="status" label="状态" width="110" />
        <el-table-column prop="sortOrder" label="排序" width="90" />
        <el-table-column prop="targetUrl" label="跳转地址" min-width="200" />
        <el-table-column prop="updatedAt" label="更新时间" min-width="180" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-popconfirm title="确认删除该广告？" @confirm="remove(row)">
              <template #reference>
                <el-button link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑广告' : '新建广告'" width="860px" destroy-on-close>
      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="广告标题"><el-input v-model="form.title" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="广告位 Key"><el-input v-model="form.slotKey" placeholder="home_hero / article_sidebar / downloads_banner" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="页面 Key"><el-input v-model="form.pageKey" placeholder="home / articles / downloads" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="状态"><el-select v-model="form.status" class="w-full"><el-option label="draft" value="draft" /><el-option label="active" value="active" /><el-option label="paused" value="paused" /></el-select></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="图片地址"><el-input v-model="form.imageUrl" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="跳转地址"><el-input v-model="form.targetUrl" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="按钮文案"><el-input v-model="form.ctaLabel" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="排序"><el-input-number v-model="form.sortOrder" class="w-full" :min="0" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="开始时间"><el-input v-model="form.startAt" placeholder="2026-05-05T12:00" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="结束时间"><el-input v-model="form.endAt" placeholder="2026-05-31T23:59" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="附加配置 JSON"><el-input v-model="form.payloadText" type="textarea" :rows="8" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
