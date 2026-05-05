<script setup lang="ts">
import { ElMessage } from "element-plus";
import { onMounted, reactive, ref } from "vue";
import { createPageConfig, deletePageConfig, fetchPageConfigs, updatePageConfig } from "@/api/admin";

defineOptions({ name: "AdminPageConfigsPage" });

const loading = ref(false);
const dialogVisible = ref(false);
const items = ref<any[]>([]);
const editingId = ref<number | null>(null);
const form = reactive({ pageKey: "", title: "", status: "active", remark: "", configJson: '{ "title": "", "subtitle": "" }' });

function resetForm() {
  editingId.value = null;
  Object.assign(form, { pageKey: "", title: "", status: "active", remark: "", configJson: '{ "title": "", "subtitle": "" }' });
}

async function loadData() {
  loading.value = true;
  try {
    const res = await fetchPageConfigs();
    items.value = res.items;
  } catch (error: any) {
    ElMessage.error(error?.message || "加载页面配置失败");
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
  Object.assign(form, row);
  dialogVisible.value = true;
}

async function submit() {
  try {
    if (editingId.value) {
      await updatePageConfig(editingId.value, form);
      ElMessage.success("页面配置已更新");
    } else {
      await createPageConfig(form);
      ElMessage.success("页面配置已创建");
    }
    dialogVisible.value = false;
    await loadData();
  } catch (error: any) {
    ElMessage.error(error?.message || "保存页面配置失败");
  }
}

async function remove(row: any) {
  try {
    await deletePageConfig(row.id);
    ElMessage.success("页面配置已删除");
    await loadData();
  } catch (error: any) {
    ElMessage.error(error?.message || "删除页面配置失败");
  }
}

onMounted(loadData);
</script>

<template>
  <div class="p-4">
    <div class="mb-4 flex items-center justify-between">
      <div>
        <h2 class="text-xl font-semibold">页面配置</h2>
        <p class="text-sm text-gray-500">管理首页、文章中心、关于页等页面配置。</p>
      </div>
      <el-button type="primary" @click="openCreate">新建页面配置</el-button>
    </div>
    <el-card shadow="never">
      <el-table :data="items" v-loading="loading">
        <el-table-column prop="pageKey" label="页面键" min-width="160" />
        <el-table-column prop="title" label="标题" min-width="200" />
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column prop="remark" label="备注" min-width="180" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-popconfirm title="确认删除该页面配置？" @confirm="remove(row)">
              <template #reference>
                <el-button link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑页面配置' : '新建页面配置'" width="760px">
      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="页面键"><el-input v-model="form.pageKey" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="标题"><el-input v-model="form.title" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="状态"><el-select v-model="form.status" class="w-full"><el-option label="active" value="active" /><el-option label="draft" value="draft" /><el-option label="disabled" value="disabled" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="备注"><el-input v-model="form.remark" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="配置 JSON"><el-input v-model="form.configJson" type="textarea" :rows="12" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
