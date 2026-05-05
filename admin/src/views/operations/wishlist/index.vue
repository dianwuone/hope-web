<script setup lang="ts">
import { ElMessage } from "element-plus";
import { onMounted, reactive, ref } from "vue";
import { fetchWishlistItems, updateWishlistItem } from "@/api/admin";

defineOptions({ name: "AdminWishlistPage" });

const loading = ref(false);
const dialogVisible = ref(false);
const items = ref<any[]>([]);
const editingId = ref<number | null>(null);
const form = reactive({
  wishState: "want_try",
  isActive: true,
  contactType: "",
  contactValue: "",
  note: ""
});

function resetForm() {
  editingId.value = null;
  Object.assign(form, {
    wishState: "want_try",
    isActive: true,
    contactType: "",
    contactValue: "",
    note: ""
  });
}

async function loadData() {
  loading.value = true;
  try {
    const res = await fetchWishlistItems();
    items.value = res.items;
  } catch (error: any) {
    ElMessage.error(error?.message || "加载心愿单失败");
  } finally {
    loading.value = false;
  }
}

function openEdit(row: any) {
  editingId.value = row.id;
  Object.assign(form, {
    wishState: row.wishState || "want_try",
    isActive: row.isActive === 1,
    contactType: row.contactType || "",
    contactValue: row.contactValue || "",
    note: row.note || ""
  });
  dialogVisible.value = true;
}

async function submit() {
  if (!editingId.value) return;
  try {
    await updateWishlistItem(editingId.value, form);
    ElMessage.success("心愿单已更新");
    dialogVisible.value = false;
    resetForm();
    await loadData();
  } catch (error: any) {
    ElMessage.error(error?.message || "保存心愿单失败");
  }
}

onMounted(loadData);
</script>

<template>
  <div class="p-4">
    <div class="mb-4">
      <h2 class="text-xl font-semibold">心愿单管理</h2>
      <p class="text-sm text-gray-500">查看项目期待状态、来源页和访客联系方式。</p>
    </div>

    <el-card shadow="never">
      <el-table :data="items" v-loading="loading">
        <el-table-column prop="projectName" label="项目名称" min-width="180">
          <template #default="{ row }">
            {{ row.projectName || row.projectSlug || "未命名项目" }}
          </template>
        </el-table-column>
        <el-table-column prop="category" label="类型" width="110" />
        <el-table-column prop="wishState" label="心愿状态" width="140" />
        <el-table-column prop="sourcePage" label="来源页" width="120" />
        <el-table-column prop="visitorId" label="访客标识" min-width="180" />
        <el-table-column prop="contactValue" label="联系方式" min-width="180" />
        <el-table-column label="是否有效" width="100">
          <template #default="{ row }">
            <el-tag :type="row.isActive === 1 ? 'success' : 'info'">{{ row.isActive === 1 ? "有效" : "关闭" }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updatedAt" label="更新时间" min-width="180" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="编辑心愿单" width="720px" destroy-on-close>
      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="心愿状态">
              <el-select v-model="form.wishState" class="w-full">
                <el-option label="want_try" value="want_try" />
                <el-option label="want_download" value="want_download" />
                <el-option label="want_beta" value="want_beta" />
                <el-option label="want_buy" value="want_buy" />
                <el-option label="realized" value="realized" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="是否有效">
              <el-switch v-model="form.isActive" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="联系方式类型"><el-input v-model="form.contactType" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="联系方式"><el-input v-model="form.contactValue" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="备注"><el-input v-model="form.note" type="textarea" :rows="5" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
