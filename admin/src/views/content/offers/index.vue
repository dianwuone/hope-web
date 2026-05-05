<script setup lang="ts">
import { ElMessage } from "element-plus";
import { onMounted, reactive, ref } from "vue";
import { createOffer, deleteOffer, fetchOffers, updateOffer } from "@/api/admin";

defineOptions({ name: "AdminOffersPage" });

const loading = ref(false);
const dialogVisible = ref(false);
const items = ref<any[]>([]);
const editingId = ref<number | null>(null);
const form = reactive({
  slug: "",
  title: "",
  subtitle: "",
  category: "",
  status: "",
  statusTone: "",
  price: "",
  originalPrice: "",
  bannerImage: "",
  summary: "",
  ctaLabel: "",
  benefitsText: "",
  metaText: "",
  extraText: ""
});

function parseCommaList(value: string) {
  return value.split(",").map(item => item.trim()).filter(Boolean);
}
function formatCommaList(items: string[] = []) {
  return items.join(", ");
}
function parseKeyValueLines(value: string) {
  return value.split("\n").map(line => line.trim()).filter(Boolean).reduce((acc, line) => {
    const [rawKey, ...rest] = line.split("=");
    const key = rawKey?.trim();
    if (!key) return acc;
    acc[key] = rest.join("=").trim();
    return acc;
  }, {});
}
function formatKeyValueLines(obj: Record<string, any> = {}) {
  return Object.entries(obj).map(([key, value]) => `${key} = ${value}`).join("\n");
}
function resetForm() {
  editingId.value = null;
  Object.assign(form, {
    slug: "",
    title: "",
    subtitle: "",
    category: "",
    status: "",
    statusTone: "",
    price: "",
    originalPrice: "",
    bannerImage: "",
    summary: "",
    ctaLabel: "",
    benefitsText: "",
    metaText: "",
    extraText: ""
  });
}

async function loadData() {
  loading.value = true;
  try {
    const res = await fetchOffers();
    items.value = res.items;
  } catch (error: any) {
    ElMessage.error(error?.message || "加载商品失败");
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
    slug: row.slug,
    title: row.title,
    subtitle: row.subtitle,
    category: row.category || "",
    status: row.status || "",
    statusTone: row.statusTone || "",
    price: row.price,
    originalPrice: row.originalPrice || "",
    bannerImage: row.bannerImage || "",
    summary: row.summary || "",
    ctaLabel: row.ctaLabel || "",
    benefitsText: (row.benefits || []).join("\n"),
    metaText: formatCommaList(row.meta || []),
    extraText: formatKeyValueLines(row.extra || {})
  });
  dialogVisible.value = true;
}

async function submit() {
  const payload = {
    slug: form.slug,
    title: form.title,
    subtitle: form.subtitle,
    category: form.category,
    status: form.status,
    statusTone: form.statusTone,
    price: form.price,
    originalPrice: form.originalPrice,
    bannerImage: form.bannerImage,
    summary: form.summary,
    ctaLabel: form.ctaLabel,
    benefits: form.benefitsText.split("\n").map(item => item.trim()).filter(Boolean),
    meta: parseCommaList(form.metaText),
    extra: parseKeyValueLines(form.extraText)
  };
  try {
    if (editingId.value) {
      await updateOffer(editingId.value, payload);
      ElMessage.success("商品已更新");
    } else {
      await createOffer(payload);
      ElMessage.success("商品已创建");
    }
    dialogVisible.value = false;
    await loadData();
  } catch (error: any) {
    ElMessage.error(error?.message || "保存商品失败");
  }
}

async function remove(row: any) {
  try {
    await deleteOffer(row.id);
    ElMessage.success("商品已删除");
    await loadData();
  } catch (error: any) {
    ElMessage.error(error?.message || "删除商品失败");
  }
}

onMounted(loadData);
</script>

<template>
  <div class="p-4">
    <div class="mb-4 flex items-center justify-between">
      <div>
        <h2 class="text-xl font-semibold">商品管理</h2>
        <p class="text-sm text-gray-500">管理快来尝鲜和购买链路中的商品内容。</p>
      </div>
      <el-button type="primary" @click="openCreate">新建商品</el-button>
    </div>
    <el-card shadow="never">
      <el-table :data="items" v-loading="loading">
        <el-table-column prop="title" label="标题" min-width="220" />
        <el-table-column prop="slug" label="Slug" min-width="160" />
        <el-table-column prop="category" label="分类" width="120" />
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column prop="price" label="价格" width="100" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-popconfirm title="确认删除该商品？" @confirm="remove(row)">
              <template #reference>
                <el-button link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑商品' : '新建商品'" width="760px" destroy-on-close>
      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="Slug"><el-input v-model="form.slug" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="标题"><el-input v-model="form.title" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="副标题"><el-input v-model="form.subtitle" type="textarea" :rows="2" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="分类"><el-input v-model="form.category" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="状态"><el-input v-model="form.status" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="状态色调"><el-input v-model="form.statusTone" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="按钮文案"><el-input v-model="form.ctaLabel" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="价格"><el-input v-model="form.price" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="原价"><el-input v-model="form.originalPrice" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="横幅图路径"><el-input v-model="form.bannerImage" /></el-form-item>
        <el-form-item label="摘要"><el-input v-model="form.summary" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="权益（每行一条）"><el-input v-model="form.benefitsText" type="textarea" :rows="4" /></el-form-item>
        <el-form-item label="补充信息（逗号分隔）"><el-input v-model="form.metaText" /></el-form-item>
        <el-form-item label="额外属性（每行：键 = 值）"><el-input v-model="form.extraText" type="textarea" :rows="4" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
