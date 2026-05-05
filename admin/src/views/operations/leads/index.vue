<script setup lang="ts">
import { ElMessage } from "element-plus";
import { onMounted, reactive, ref } from "vue";
import { fetchCommunityLeads, updateCommunityLead } from "@/api/admin";

defineOptions({ name: "AdminLeadsPage" });

const loading = ref(false);
const dialogVisible = ref(false);
const items = ref<any[]>([]);
const editingId = ref<number | null>(null);
const form = reactive({
  status: "new",
  message: ""
});

async function loadData() {
  loading.value = true;
  try {
    const res = await fetchCommunityLeads();
    items.value = res.items;
  } catch (error: any) {
    ElMessage.error(error?.message || "加载用户线索失败");
  } finally {
    loading.value = false;
  }
}

function openEdit(row: any) {
  editingId.value = row.id;
  form.status = row.status || "new";
  form.message = row.message || "";
  dialogVisible.value = true;
}

async function submit() {
  if (!editingId.value) return;
  try {
    await updateCommunityLead(editingId.value, form);
    ElMessage.success("用户线索已更新");
    dialogVisible.value = false;
    await loadData();
  } catch (error: any) {
    ElMessage.error(error?.message || "保存用户线索失败");
  }
}

onMounted(loadData);
</script>

<template>
  <div class="p-4">
    <div class="mb-4">
      <h2 class="text-xl font-semibold">用户线索管理</h2>
      <p class="text-sm text-gray-500">统一查看社区加入、合作联系和留言线索。</p>
    </div>

    <el-card shadow="never">
      <el-table :data="items" v-loading="loading">
        <el-table-column prop="leadType" label="线索类型" width="120" />
        <el-table-column prop="intentReason" label="来意" width="140" />
        <el-table-column prop="name" label="姓名 / 昵称" min-width="140" />
        <el-table-column prop="contactType" label="联系方式类型" width="120" />
        <el-table-column prop="contactValue" label="联系方式" min-width="180" />
        <el-table-column prop="status" label="跟进状态" width="120" />
        <el-table-column prop="createdAt" label="提交时间" min-width="180" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="编辑用户线索" width="680px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="跟进状态">
          <el-select v-model="form.status" class="w-full">
            <el-option label="new" value="new" />
            <el-option label="processing" value="processing" />
            <el-option label="done" value="done" />
          </el-select>
        </el-form-item>
        <el-form-item label="留言 / 跟进记录">
          <el-input v-model="form.message" type="textarea" :rows="6" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
