<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, reactive, ref } from "vue";
import { publishAiContent, syncDatabase, uploadDatabaseFile } from "@/api/admin";

defineOptions({ name: "AdminContentPublishPage" });

const syncing = ref(false);
const uploadingDatabase = ref(false);
const publishing = ref(false);
const syncResult = ref<any | null>(null);
const uploadResult = ref<any | null>(null);
const publishResult = ref<any | null>(null);
const selectedDatabaseFile = ref<File | null>(null);

const syncForm = reactive({
  apply: true,
  seedDefaults: true
});

const publishForm = reactive({
  contentType: "article",
  mode: "upsert",
  autoPublish: true,
  payloadText: `{
  "slug": "ai-demo-article",
  "title": "AI 新文章标题",
  "summary": "这里填写摘要",
  "contentBody": "这里填写正文",
  "authorName": "AI 助手",
  "columnSlug": "kunting",
  "tagNames": ["AI"]
}`
});

const payloadTemplateMap: Record<string, string> = {
  article: `{
  "slug": "ai-demo-article",
  "title": "AI 新文章标题",
  "summary": "这里填写摘要",
  "contentBody": "这里填写正文",
  "authorName": "AI 助手",
  "columnSlug": "kunting",
  "tagNames": ["AI", "内容运营"]
}`,
  project: `{
  "slug": "ai-demo-product",
  "name": "AI 新产品",
  "projectType": "product",
  "title": "AI 新产品标题",
  "summary": "一句话概述产品",
  "description": "详细介绍",
  "price": "¥29",
  "tags": ["AI 工具", "效率"]
}`,
  offer: `{
  "slug": "ai-demo-offer",
  "title": "AI 限时内容",
  "subtitle": "副标题说明",
  "price": "¥19",
  "summary": "售卖内容简介",
  "benefits": ["权益一", "权益二"]
}`
};

const publishHint = computed(() => {
  return publishForm.contentType === "article"
    ? "文章支持 columnSlug / columnName、tagSlugs / tagNames，AI 不一定要先查 ID。"
    : publishForm.contentType === "project"
      ? "项目支持 product / game / lab 三种 projectType。"
      : "商品适合资料包、尝鲜内容、活动权益等可售内容。";
});

function getErrorMessage(error: any, fallback: string) {
  return error?.response?.data?.detail || error?.message || fallback;
}

function fillTemplate() {
  publishForm.payloadText = payloadTemplateMap[publishForm.contentType];
}

function onDatabaseFileChange(file: any) {
  selectedDatabaseFile.value = file?.raw || null;
}

function onDatabaseFileRemove() {
  selectedDatabaseFile.value = null;
}

async function submitSync() {
  syncing.value = true;
  syncResult.value = null;
  try {
    const res = await syncDatabase({
      apply: syncForm.apply,
      seedDefaults: syncForm.seedDefaults
    });
    syncResult.value = res;
    ElMessage.success(syncForm.apply ? "数据库同步完成" : "数据库差异检查完成");
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, "数据库同步失败"));
  } finally {
    syncing.value = false;
  }
}

async function submitDatabaseUpload() {
  if (!selectedDatabaseFile.value) {
    ElMessage.error("请先选择本地 SQLite 数据库文件");
    return;
  }

  uploadingDatabase.value = true;
  uploadResult.value = null;
  try {
    const res = await uploadDatabaseFile(selectedDatabaseFile.value);
    uploadResult.value = res;
    ElMessage.success("数据库文件已上传并切换");
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, "数据库上传失败"));
  } finally {
    uploadingDatabase.value = false;
  }
}

async function submitPublish() {
  let payload: Record<string, any>;
  try {
    payload = JSON.parse(publishForm.payloadText);
  } catch (error) {
    ElMessage.error("发布内容 JSON 格式不正确");
    return;
  }

  publishing.value = true;
  publishResult.value = null;
  try {
    const res = await publishAiContent({
      contentType: publishForm.contentType,
      mode: publishForm.mode,
      autoPublish: publishForm.autoPublish,
      payload
    });
    publishResult.value = res;
    ElMessage.success(`内容已${res.action === "created" ? "创建" : "更新"}`);
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, "AI 发布失败"));
  } finally {
    publishing.value = false;
  }
}
</script>

<template>
  <div class="p-4 space-y-4">
    <div>
      <h2 class="text-xl font-semibold">同步与 AI 发布</h2>
      <p class="text-sm text-gray-500">支持上传本地 SQLite 覆盖服务器数据库、补齐结构差异，并通过统一入口让 AI 直接发布文章、产品或商品内容。</p>
    </div>

    <el-row :gutter="16">
      <el-col :xs="24" :lg="8">
        <el-card shadow="never" class="h-full">
          <template #header>
            <div>
              <div class="text-base font-semibold">上传本地数据库</div>
              <div class="text-sm text-gray-500">把本地最新的 SQLite 文件上传到服务器，自动备份旧库后再切换。</div>
            </div>
          </template>

          <el-form label-position="top">
            <el-form-item label="选择数据库文件">
              <el-upload
                :auto-upload="false"
                :limit="1"
                accept=".db,.sqlite,.sqlite3"
                :show-file-list="true"
                :on-change="onDatabaseFileChange"
                :on-remove="onDatabaseFileRemove"
              >
                <el-button>选择本地 app.db</el-button>
              </el-upload>
            </el-form-item>

            <el-alert
              type="warning"
              :closable="false"
              title="这个操作会用上传的数据库替换当前服务端库，适合本地数据库就是最新权威数据的场景。"
            />
            <div class="mt-4">
              <el-button type="primary" :loading="uploadingDatabase" @click="submitDatabaseUpload">
                上传并切换数据库
              </el-button>
            </div>
          </el-form>

          <div v-if="uploadResult" class="mt-4">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="执行结果">{{ uploadResult.ok ? "成功" : "失败" }}</el-descriptions-item>
              <el-descriptions-item label="当前数据库">{{ uploadResult.databasePath }}</el-descriptions-item>
              <el-descriptions-item label="备份文件">{{ uploadResult.backupPath || "无旧库可备份" }}</el-descriptions-item>
              <el-descriptions-item label="上传时间">{{ uploadResult.uploadedAt }}</el-descriptions-item>
              <el-descriptions-item label="补结构同步">{{ uploadResult.appliedSync ? "是" : "否" }}</el-descriptions-item>
              <el-descriptions-item label="新增字段">{{ uploadResult.addedColumns?.length ? uploadResult.addedColumns.join("、") : "无" }}</el-descriptions-item>
            </el-descriptions>

            <el-form-item class="mt-4" label="执行 SQL">
              <el-input :model-value="(uploadResult.executedSql || []).join('\n')" type="textarea" :rows="6" readonly />
            </el-form-item>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card shadow="never" class="h-full">
          <template #header>
            <div>
              <div class="text-base font-semibold">数据库同步</div>
              <div class="text-sm text-gray-500">补齐缺失表、缺失字段，也可以只做检查不落库。</div>
            </div>
          </template>

          <el-form label-position="top">
            <el-form-item label="执行模式">
              <el-switch v-model="syncForm.apply" inline-prompt active-text="应用变更" inactive-text="仅检查" />
            </el-form-item>
            <el-form-item label="补默认数据">
              <el-switch v-model="syncForm.seedDefaults" inline-prompt active-text="开启" inactive-text="关闭" />
            </el-form-item>
            <el-alert
              type="info"
              :closable="false"
              title="建议上线新版本代码后，先执行一次“应用变更”，让服务端 SQLite 跟当前代码模型对齐。"
            />
            <div class="mt-4">
              <el-button type="primary" :loading="syncing" @click="submitSync">
                {{ syncForm.apply ? "立即同步数据库" : "检查数据库差异" }}
              </el-button>
            </div>
          </el-form>

          <div v-if="syncResult" class="mt-4">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="执行结果">{{ syncResult.ok ? "成功" : "失败" }}</el-descriptions-item>
              <el-descriptions-item label="是否应用">{{ syncResult.applied ? "是" : "否" }}</el-descriptions-item>
              <el-descriptions-item label="补默认数据">{{ syncResult.seeded ? "是" : "否" }}</el-descriptions-item>
              <el-descriptions-item label="缺失表">{{ syncResult.missingTables?.length ? syncResult.missingTables.join("、") : "无" }}</el-descriptions-item>
              <el-descriptions-item label="新增字段">{{ syncResult.addedColumns?.length ? syncResult.addedColumns.join("、") : "无" }}</el-descriptions-item>
            </el-descriptions>

            <el-form-item class="mt-4" label="执行 SQL">
              <el-input :model-value="(syncResult.executedSql || []).join('\n')" type="textarea" :rows="8" readonly />
            </el-form-item>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card shadow="never" class="h-full">
          <template #header>
            <div class="flex items-center justify-between gap-4">
              <div>
                <div class="text-base font-semibold">AI 发布内容</div>
                <div class="text-sm text-gray-500">统一入口，按 slug 创建或更新内容。</div>
              </div>
              <el-button @click="fillTemplate">填入示例</el-button>
            </div>
          </template>

          <el-form label-position="top">
            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item label="内容类型">
                  <el-select v-model="publishForm.contentType" class="w-full" @change="fillTemplate">
                    <el-option label="文章 article" value="article" />
                    <el-option label="项目 project" value="project" />
                    <el-option label="商品 offer" value="offer" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="写入模式">
                  <el-select v-model="publishForm.mode" class="w-full">
                    <el-option label="upsert" value="upsert" />
                    <el-option label="create" value="create" />
                    <el-option label="update" value="update" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="自动发布">
                  <el-switch v-model="publishForm.autoPublish" inline-prompt active-text="发布" inactive-text="草稿" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-alert :title="publishHint" type="info" :closable="false" class="mb-4" />

            <el-form-item label="Payload JSON">
              <el-input v-model="publishForm.payloadText" type="textarea" :rows="18" />
            </el-form-item>

            <el-button type="primary" :loading="publishing" @click="submitPublish">提交 AI 发布</el-button>
          </el-form>

          <div v-if="publishResult" class="mt-4">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="结果">{{ publishResult.ok ? "成功" : "失败" }}</el-descriptions-item>
              <el-descriptions-item label="动作">{{ publishResult.action }}</el-descriptions-item>
              <el-descriptions-item label="内容类型">{{ publishResult.contentType }}</el-descriptions-item>
              <el-descriptions-item label="ID">{{ publishResult.itemId }}</el-descriptions-item>
              <el-descriptions-item label="Slug" :span="2">{{ publishResult.slug }}</el-descriptions-item>
            </el-descriptions>

            <el-form-item class="mt-4" label="返回内容">
              <el-input :model-value="JSON.stringify(publishResult.item || {}, null, 2)" type="textarea" :rows="12" readonly />
            </el-form-item>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>
