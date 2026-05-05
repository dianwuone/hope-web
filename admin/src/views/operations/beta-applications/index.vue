<script setup lang="ts">
import { ElMessage } from "element-plus";
import { onMounted, reactive, ref } from "vue";
import { fetchBetaApplications, updateBetaApplication } from "@/api/admin";

defineOptions({ name: "AdminBetaApplicationsPage" });

const loading = ref(false);
const dialogVisible = ref(false);
const items = ref<any[]>([]);
const editingId = ref<number | null>(null);
const form = reactive({
  status: "pending",
  followUpNote: ""
});

async function loadData() {
  loading.value = true;
  try {
    const res = await fetchBetaApplications();
    items.value = res.items;
  } catch (error: any) {
    ElMessage.error(error?.message || "加载内测申请失败");
  } finally {
    loading.value = false;
  }
}

function openEdit(row: any) {
  editingId.value = row.id;
  form.status = row.status || "pending";
  form.followUpNote = row.followUpNote || "";
  dialogVisible.value = true;
}

async function submit() {
  if (!editingId.value) return;
  try {
    await updateBetaApplication(editingId.value, form);
    ElMessage.success("内测申请已更新");
    dialogVisible.value = false;
    await loadData();
  } catch (error: any) {
    ElMessage.error(error?.message || "保存内测申请失败");
  }
}

onMounted(loadData);
</script>

<template>
  <div class="p-4">
    <div class="mb-4">
      <h2 class="text-xl font-semibold">内测申请管理</h2>
      <p class="text-sm text-gray-500">集中处理实验室和产品的体验申请与跟进状态。</p>
    </div>

    <el-card shadow="never">
      <el-table :data="items" v-loading="loading">
        <el-table-column prop="projectSlug" label="项目" min-width="160" />
        <el-table-column prop="sourcePage" label="来源页" width="120" />
        <el-table-column prop="roleType" label="申请角色" width="140" />
        <el-table-column prop="name" label="姓名 / 昵称" min-width="140" />
        <el-table-column prop="contactValue" label="联系方式" min-width="180" />
        <el-table-column prop="city" label="城市" width="120" />
        <el-table-column prop="status" label="处理状态" width="120" />
        <el-table-column prop="createdAt" label="提交时间" min-width="180" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="编辑内测申请" width="720px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="处理状态">
          <el-select v-model="form.status" class="w-full">
            <el-option label="pending" value="pending" />
            <el-option label="contacted" value="contacted" />
            <el-option label="approved" value="approved" />
            <el-option label="rejected" value="rejected" />
          </el-select>
        </el-form-item>
        <el-form-item label="跟进备注">
          <el-input v-model="form.followUpNote" type="textarea" :rows="6" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
