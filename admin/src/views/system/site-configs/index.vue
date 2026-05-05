<script setup lang="ts">
import { ElMessage } from "element-plus";
import { onMounted, reactive, ref } from "vue";
import { createSiteConfig, deleteSiteConfig, fetchSiteConfigs, updateSiteConfig } from "@/api/admin";

defineOptions({ name: "AdminSiteConfigsPage" });

const loading = ref(false);
const dialogVisible = ref(false);
const items = ref<any[]>([]);
const editingId = ref<number | null>(null);
const form = reactive({ configKey: "", groupName: "general", remark: "", configValue: '{ "value": "" }' });

function resetForm() {
  editingId.value = null;
  Object.assign(form, { configKey: "", groupName: "general", remark: "", configValue: '{ "value": "" }' });
}

async function loadData() {
  loading.value = true;
  try {
    const res = await fetchSiteConfigs();
    items.value = res.items;
  } catch (error: any) {
    ElMessage.error(error?.message || "加载全站配置失败");
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
      await updateSiteConfig(editingId.value, form);
      ElMessage.success("全站配置已更新");
    } else {
      await createSiteConfig(form);
      ElMessage.success("全站配置已创建");
    }
    dialogVisible.value = false;
    await loadData();
  } catch (error: any) {
    ElMessage.error(error?.message || "保存全站配置失败");
  }
}

async function remove(row: any) {
  try {
    await deleteSiteConfig(row.id);
    ElMessage.success("全站配置已删除");
    await loadData();
  } catch (error: any) {
    ElMessage.error(error?.message || "删除全站配置失败");
  }
}

onMounted(loadData);
</script>

<template>
  <div class="p-4">
    <div class="mb-4 flex items-center justify-between">
      <div>
        <h2 class="text-xl font-semibold">全站配置</h2>
        <p class="text-sm text-gray-500">管理站点信息、导航、热点标签等全局配置。</p>
      </div>
      <el-button type="primary" @click="openCreate">新建配置</el-button>
    </div>
    <el-card shadow="never">
      <el-table :data="items" v-loading="loading">
        <el-table-column prop="configKey" label="配置键" min-width="180" />
        <el-table-column prop="groupName" label="分组" width="120" />
        <el-table-column prop="remark" label="备注" min-width="180" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-popconfirm title="确认删除该配置？" @confirm="remove(row)">
              <template #reference>
                <el-button link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑全站配置' : '新建全站配置'" width="760px">
      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="配置键"><el-input v-model="form.configKey" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="分组"><el-input v-model="form.groupName" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="备注"><el-input v-model="form.remark" /></el-form-item>
        <el-form-item label="配置值"><el-input v-model="form.configValue" type="textarea" :rows="10" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
