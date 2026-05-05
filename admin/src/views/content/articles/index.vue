<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";
import { createArticle, deleteArticle, fetchArticles, fetchColumns, fetchTags, updateArticle } from "@/api/admin";

defineOptions({ name: "AdminArticlesPage" });

const loading = ref(false);
const dialogVisible = ref(false);
const items = ref<any[]>([]);
const columns = ref<any[]>([]);
const tags = ref<any[]>([]);
const editingId = ref<number | null>(null);
const form = reactive({
  title: "",
  slug: "",
  summary: "",
  contentBody: "",
  authorName: "昆廷",
  columnId: 1,
  tagInput: "",
  status: "draft"
});

const titleMap = computed(() => (editingId.value ? "编辑文章" : "新建文章"));

function resolveTagIds(input: string) {
  return input
    .split(",")
    .map(item => item.trim())
    .filter(Boolean)
    .map(token => {
      if (/^\d+$/.test(token)) return Number(token);
      const found = tags.value.find(tag => tag.name === token || tag.slug === token);
      return found?.id;
    })
    .filter(id => Number.isInteger(id));
}

function resetForm() {
  editingId.value = null;
  Object.assign(form, {
    title: "",
    slug: "",
    summary: "",
    contentBody: "",
    authorName: "昆廷",
    columnId: columns.value[0]?.id ?? 1,
    tagInput: "",
    status: "draft"
  });
}

async function loadData() {
  loading.value = true;
  try {
    const [articleRes, columnRes, tagRes] = await Promise.all([fetchArticles(), fetchColumns(), fetchTags()]);
    items.value = articleRes.items;
    columns.value = columnRes.items;
    tags.value = tagRes.items;
    if (!form.columnId && columns.value.length) form.columnId = columns.value[0].id;
  } catch (error: any) {
    ElMessage.error(error?.message || "加载文章失败");
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
    title: row.title,
    slug: row.slug,
    summary: row.summary,
    contentBody: row.contentBody,
    authorName: row.authorName,
    columnId: row.columnId,
    tagInput: (row.tags || []).map(tag => tag.name).join(", "),
    status: row.status
  });
  dialogVisible.value = true;
}

async function submit() {
  const payload = {
    title: form.title,
    slug: form.slug,
    summary: form.summary,
    contentBody: form.contentBody,
    authorName: form.authorName,
    columnId: Number(form.columnId),
    tagIds: resolveTagIds(form.tagInput),
    status: form.status
  };
  try {
    if (editingId.value) {
      await updateArticle(editingId.value, payload);
      ElMessage.success("文章已更新");
    } else {
      await createArticle(payload);
      ElMessage.success("文章已创建");
    }
    dialogVisible.value = false;
    await loadData();
  } catch (error: any) {
    ElMessage.error(error?.message || "保存文章失败");
  }
}

async function remove(row: any) {
  try {
    await deleteArticle(row.id);
    ElMessage.success("文章已删除");
    await loadData();
  } catch (error: any) {
    ElMessage.error(error?.message || "删除文章失败");
  }
}

onMounted(loadData);
</script>

<template>
  <div class="p-4">
    <div class="mb-4 flex items-center justify-between">
      <div>
        <h2 class="text-xl font-semibold">文章管理</h2>
        <p class="text-sm text-gray-500">管理文章、栏目和标签映射关系。</p>
      </div>
      <el-button type="primary" @click="openCreate">新建文章</el-button>
    </div>

    <el-card shadow="never">
      <el-table :data="items" v-loading="loading">
        <el-table-column prop="title" label="标题" min-width="220" />
        <el-table-column prop="slug" label="Slug" min-width="160" />
        <el-table-column prop="authorName" label="作者" width="120" />
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column label="标签" min-width="220">
          <template #default="{ row }">
            <el-space wrap>
              <el-tag v-for="tag in row.tags" :key="tag.id" size="small">{{ tag.name }}</el-tag>
            </el-space>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-popconfirm title="确认删除这篇文章？" @confirm="remove(row)">
              <template #reference>
                <el-button link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="titleMap" width="760px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="标题"><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="Slug"><el-input v-model="form.slug" /></el-form-item>
        <el-form-item label="摘要"><el-input v-model="form.summary" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="正文"><el-input v-model="form.contentBody" type="textarea" :rows="8" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="作者"><el-input v-model="form.authorName" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="栏目"><el-select v-model="form.columnId" class="w-full"><el-option v-for="item in columns" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="标签（名称或 ID，逗号分隔）"><el-input v-model="form.tagInput" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="状态"><el-select v-model="form.status" class="w-full"><el-option label="draft" value="draft" /><el-option label="published" value="published" /><el-option label="archived" value="archived" /></el-select></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
