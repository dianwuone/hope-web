<script setup lang="ts">
import { ElMessage } from "element-plus";
import { onMounted, reactive, ref } from "vue";
import { fetchFrontendUsers, updateFrontendUser } from "@/api/admin";

defineOptions({ name: "AdminFrontendUsersPage" });

const loading = ref(false);
const dialogVisible = ref(false);
const items = ref<any[]>([]);
const editingId = ref<number | null>(null);
const form = reactive({
  nickname: "",
  email: "",
  avatar: "",
  bio: "",
  status: "active"
});

async function loadData() {
  loading.value = true;
  try {
    const res = await fetchFrontendUsers();
    items.value = res.items;
  } catch (error: any) {
    ElMessage.error(error?.message || "加载前台用户失败");
  } finally {
    loading.value = false;
  }
}

function openEdit(row: any) {
  editingId.value = row.id;
  Object.assign(form, {
    nickname: row.nickname || "",
    email: row.email || "",
    avatar: row.avatar || "",
    bio: row.bio || "",
    status: row.status || "active"
  });
  dialogVisible.value = true;
}

async function submit() {
  if (!editingId.value) return;
  try {
    await updateFrontendUser(editingId.value, form);
    ElMessage.success("用户信息已更新");
    dialogVisible.value = false;
    await loadData();
  } catch (error: any) {
    ElMessage.error(error?.message || "保存用户信息失败");
  }
}

onMounted(loadData);
</script>

<template>
  <div class="p-4">
    <div class="mb-4">
      <h2 class="text-xl font-semibold">前台用户管理</h2>
      <p class="text-sm text-gray-500">查看注册用户，以及点赞、评论、收藏、心愿单等关联行为。</p>
    </div>

    <el-card shadow="never">
      <el-table :data="items" v-loading="loading">
        <el-table-column prop="username" label="用户名" min-width="140" />
        <el-table-column prop="nickname" label="昵称" min-width="140" />
        <el-table-column prop="email" label="邮箱" min-width="200" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column prop="wishlistCount" label="心愿单" width="90" />
        <el-table-column prop="likeCount" label="点赞" width="80" />
        <el-table-column prop="favoriteCount" label="收藏" width="80" />
        <el-table-column prop="commentCount" label="评论" width="80" />
        <el-table-column prop="betaApplicationCount" label="内测申请" width="100" />
        <el-table-column prop="communityLeadCount" label="线索" width="80" />
        <el-table-column prop="lastLoginAt" label="最近登录" min-width="180" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="编辑前台用户" width="720px" destroy-on-close>
      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="昵称"><el-input v-model="form.nickname" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="邮箱"><el-input v-model="form.email" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="头像地址"><el-input v-model="form.avatar" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" class="w-full">
            <el-option label="active" value="active" />
            <el-option label="disabled" value="disabled" />
          </el-select>
        </el-form-item>
        <el-form-item label="简介"><el-input v-model="form.bio" type="textarea" :rows="4" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
