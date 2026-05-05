<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";
import { createProject, deleteProject, fetchProjects, updateProject } from "@/api/admin";

defineOptions({ name: "AdminProjectsPage" });

const loading = ref(false);
const dialogVisible = ref(false);
const activeType = ref("all");
const items = ref<any[]>([]);
const editingId = ref<number | null>(null);
const form = reactive({
  slug: "",
  name: "",
  projectType: "product",
  title: "",
  subtitle: "",
  shortDesc: "",
  summary: "",
  description: "",
  coverImage: "",
  bannerImage: "",
  status: "draft",
  stage: "",
  supportStatus: "",
  price: "",
  originalPrice: "",
  tagsText: "",
  featuresText: "",
  highlightsText: "",
  faqText: "",
  testimonialsText: "",
  route: "",
  age: "",
  category: "",
  labProjectsText: ""
});

const filteredItems = computed(() => activeType.value === "all" ? items.value : items.value.filter(item => item.projectType === activeType.value));

function parseCommaList(value: string) {
  return value.split(",").map(item => item.trim()).filter(Boolean);
}
function formatCommaList(items: string[] = []) {
  return items.join(", ");
}
function parseLinePairs(value: string, keys: string[]) {
  return value.split("\n").map(line => line.trim()).filter(Boolean).map(line => {
    const parts = line.split("|").map(item => item.trim());
    const result = {};
    keys.forEach((key, index) => (result[key] = parts[index] || ""));
    return result;
  });
}
function formatLinePairs(items = [], keys: string[]) {
  return items.map((item: any) => keys.map(key => item[key] || "").join(" | ")).join("\n");
}

function resetForm() {
  editingId.value = null;
  Object.assign(form, {
    slug: "",
    name: "",
    projectType: "product",
    title: "",
    subtitle: "",
    shortDesc: "",
    summary: "",
    description: "",
    coverImage: "",
    bannerImage: "",
    status: "draft",
    stage: "",
    supportStatus: "",
    price: "",
    originalPrice: "",
    tagsText: "",
    featuresText: "",
    highlightsText: "",
    faqText: "",
    testimonialsText: "",
    route: "",
    age: "",
    category: "",
    labProjectsText: ""
  });
}

async function loadData() {
  loading.value = true;
  try {
    const res = await fetchProjects();
    items.value = res.items;
  } catch (error: any) {
    ElMessage.error(error?.message || "加载项目失败");
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
    name: row.name,
    projectType: row.projectType,
    title: row.title || "",
    subtitle: row.subtitle || "",
    shortDesc: row.shortDesc || "",
    summary: row.summary || "",
    description: row.description || "",
    coverImage: row.coverImage || "",
    bannerImage: row.bannerImage || "",
    status: row.status || "draft",
    stage: row.stage || "",
    supportStatus: row.supportStatus || "",
    price: row.price || "",
    originalPrice: row.originalPrice || "",
    tagsText: formatCommaList(row.tags || []),
    featuresText: formatLinePairs(row.features || [], ["title", "description"]),
    highlightsText: formatCommaList(row.highlights || []),
    faqText: formatLinePairs(row.faq || [], ["q", "a"]),
    testimonialsText: formatLinePairs(row.testimonials || [], ["author", "content"]),
    route: row.extra?.route || "",
    age: row.extra?.age || "",
    category: row.extra?.category || "",
    labProjectsText: formatLinePairs(row.extra?.projects || [], ["name", "status"])
  });
  dialogVisible.value = true;
}

async function submit() {
  const payload = {
    slug: form.slug,
    name: form.name,
    projectType: form.projectType,
    title: form.title,
    subtitle: form.subtitle,
    shortDesc: form.shortDesc,
    summary: form.summary,
    description: form.description,
    coverImage: form.coverImage,
    bannerImage: form.bannerImage,
    status: form.status,
    stage: form.stage,
    supportStatus: form.supportStatus,
    price: form.price,
    originalPrice: form.originalPrice,
    tags: parseCommaList(form.tagsText),
    features: parseLinePairs(form.featuresText, ["title", "description"]),
    highlights: parseCommaList(form.highlightsText),
    faq: parseLinePairs(form.faqText, ["q", "a"]),
    testimonials: parseLinePairs(form.testimonialsText, ["author", "content"]),
    extra: {
      ...(form.route ? { route: form.route } : {}),
      ...(form.age ? { age: form.age } : {}),
      ...(form.category ? { category: form.category } : {}),
      ...(form.labProjectsText ? { projects: parseLinePairs(form.labProjectsText, ["name", "status"]) } : {})
    }
  };
  try {
    if (editingId.value) {
      await updateProject(editingId.value, payload);
      ElMessage.success("项目已更新");
    } else {
      await createProject(payload);
      ElMessage.success("项目已创建");
    }
    dialogVisible.value = false;
    await loadData();
  } catch (error: any) {
    ElMessage.error(error?.message || "保存项目失败");
  }
}

async function remove(row: any) {
  try {
    await deleteProject(row.id);
    ElMessage.success("项目已删除");
    await loadData();
  } catch (error: any) {
    ElMessage.error(error?.message || "删除项目失败");
  }
}

onMounted(loadData);
</script>

<template>
  <div class="p-4">
    <div class="mb-4 flex items-center justify-between">
      <div>
        <h2 class="text-xl font-semibold">项目管理</h2>
        <p class="text-sm text-gray-500">统一管理产品、游戏、实验室数据。</p>
      </div>
      <el-button type="primary" @click="openCreate">新建项目</el-button>
    </div>

    <el-card shadow="never" class="mb-4">
      <el-radio-group v-model="activeType">
        <el-radio-button label="all">全部</el-radio-button>
        <el-radio-button label="product">产品</el-radio-button>
        <el-radio-button label="game">游戏</el-radio-button>
        <el-radio-button label="lab">实验室</el-radio-button>
      </el-radio-group>
    </el-card>

    <el-card shadow="never">
      <el-table :data="filteredItems" v-loading="loading">
        <el-table-column prop="name" label="名称" min-width="180" />
        <el-table-column prop="slug" label="Slug" min-width="160" />
        <el-table-column prop="projectType" label="类型" width="110" />
        <el-table-column prop="status" label="状态" width="110" />
        <el-table-column prop="stage" label="阶段" width="120" />
        <el-table-column prop="supportStatus" label="支持状态" width="130" />
        <el-table-column label="标签" min-width="220">
          <template #default="{ row }">
            <el-space wrap>
              <el-tag v-for="tag in row.tags" :key="tag" size="small">{{ tag }}</el-tag>
            </el-space>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-popconfirm title="确认删除该项目？" @confirm="remove(row)">
              <template #reference>
                <el-button link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑项目' : '新建项目'" width="860px" destroy-on-close>
      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="Slug"><el-input v-model="form.slug" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="类型"><el-select v-model="form.projectType" class="w-full"><el-option label="product" value="product" /><el-option label="game" value="game" /><el-option label="lab" value="lab" /></el-select></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="名称"><el-input v-model="form.name" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="状态"><el-input v-model="form.status" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="标题"><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="副标题"><el-input v-model="form.subtitle" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="短描述"><el-input v-model="form.shortDesc" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="摘要"><el-input v-model="form.summary" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="详情描述"><el-input v-model="form.description" type="textarea" :rows="4" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="封面图路径"><el-input v-model="form.coverImage" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="横幅图路径"><el-input v-model="form.bannerImage" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="阶段"><el-input v-model="form.stage" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="支持状态"><el-input v-model="form.supportStatus" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="价格"><el-input v-model="form.price" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="原价"><el-input v-model="form.originalPrice" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="标签（逗号分隔）"><el-input v-model="form.tagsText" /></el-form-item>
        <el-form-item label="功能（每行：标题 | 描述）"><el-input v-model="form.featuresText" type="textarea" :rows="4" /></el-form-item>
        <el-form-item label="亮点（逗号分隔）"><el-input v-model="form.highlightsText" /></el-form-item>
        <el-form-item label="FAQ（每行：问题 | 答案）"><el-input v-model="form.faqText" type="textarea" :rows="4" /></el-form-item>
        <el-form-item label="评价（每行：作者 | 内容）"><el-input v-model="form.testimonialsText" type="textarea" :rows="3" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="8"><el-form-item label="路由"><el-input v-model="form.route" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="年龄"><el-input v-model="form.age" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="分类"><el-input v-model="form.category" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="实验室子项目（每行：名称 | 状态）"><el-input v-model="form.labProjectsText" type="textarea" :rows="4" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
