<script setup lang="ts">
import Motion from "./utils/motion";
import { useRouter } from "vue-router";
import { message } from "@/utils/message";
import { loginRules } from "./utils/rule";
import { computed, onMounted, ref, reactive, toRaw } from "vue";
import { debounce } from "@pureadmin/utils";
import { useNav } from "@/layout/hooks/useNav";
import { useEventListener } from "@vueuse/core";
import type { FormInstance } from "element-plus";
import { useLayout } from "@/layout/hooks/useLayout";
import { useUserStoreHook } from "@/store/modules/user";
import { initRouter, getTopMenu } from "@/router/utils";
import { bg, avatar, illustration } from "./utils/static";
import { useRenderIcon } from "@/components/ReIcon/src/hooks";
import { useDataThemeChange } from "@/layout/hooks/useDataThemeChange";

import dayIcon from "@/assets/svg/day.svg?component";
import darkIcon from "@/assets/svg/dark.svg?component";
import Lock from "~icons/ri/lock-fill";
import User from "~icons/ri/user-3-fill";

defineOptions({
  name: "Login"
});

const router = useRouter();
const loading = ref(false);
const disabled = ref(false);
const ruleFormRef = ref<FormInstance>();

const { initStorage } = useLayout();
initStorage();

const { dataTheme, overallStyle, dataThemeChange } = useDataThemeChange();
dataThemeChange(overallStyle.value);
const { title } = useNav();

const ruleForm = reactive({
  username: "admin",
  password: "admin123",
  captchaKey: "",
  captchaCode: ""
});

const captchaSvg = ref("");
const showCaptcha = ref(false);
const captchaLoading = ref(false);
const captchaImage = computed(() =>
  captchaSvg.value ? `data:image/svg+xml;utf8,${encodeURIComponent(captchaSvg.value)}` : ""
);

function getErrorPayload(error: any) {
  return error?.response?.data?.detail ?? null;
}

function getErrorMessage(error: any, fallback: string) {
  const detail = getErrorPayload(error);
  if (typeof detail === "string") return detail;
  return detail?.message || error?.message || fallback;
}

async function refreshCaptcha(forceShow = false) {
  captchaLoading.value = true;
  try {
    const result = await useUserStoreHook().fetchCaptcha("admin");
    ruleForm.captchaKey = result.captchaKey;
    ruleForm.captchaCode = "";
    captchaSvg.value = result.captchaSvg;
    if (forceShow) showCaptcha.value = true;
  } finally {
    captchaLoading.value = false;
  }
}

const onLogin = async (formEl: FormInstance | undefined) => {
  if (!formEl) return;
  await formEl.validate(valid => {
    if (valid) {
      loading.value = true;
      useUserStoreHook()
        .loginByUsername({
          username: ruleForm.username,
          password: ruleForm.password,
          captchaKey: ruleForm.captchaKey,
          captchaCode: ruleForm.captchaCode
        })
        .then(res => {
          if (res.success) {
            // 获取后端路由
            return initRouter().then(() => {
              disabled.value = true;
              router
                .push(getTopMenu(true).path)
                .then(() => {
                  message("登录成功", { type: "success" });
                })
                .finally(() => (disabled.value = false));
            });
          } else {
            message("登录失败", { type: "error" });
          }
        })
        .catch(async error => {
          const detail = getErrorPayload(error);
          if (detail?.captchaRequired || detail?.captcha) {
            showCaptcha.value = true;
          }
          if (detail?.captcha) {
            ruleForm.captchaKey = detail.captcha.captchaKey || "";
            captchaSvg.value = detail.captcha.captchaSvg || "";
            ruleForm.captchaCode = "";
          } else if (showCaptcha.value) {
            await refreshCaptcha(true);
          }
          message(getErrorMessage(error, "登录失败"), { type: "error", duration: 3500 });
        })
        .finally(() => (loading.value = false));
    }
  });
};

const immediateDebounce: any = debounce(
  formRef => onLogin(formRef),
  1000,
  true
);

useEventListener(document, "keydown", ({ code }) => {
  if (
    ["Enter", "NumpadEnter"].includes(code) &&
    !disabled.value &&
    !loading.value
  )
    immediateDebounce(ruleFormRef.value);
});

onMounted(() => {
  refreshCaptcha(false);
});
</script>

<template>
  <div class="select-none">
    <img :src="bg" class="wave" />
    <div class="flex-c absolute right-5 top-3">
      <!-- 主题 -->
      <el-switch
        v-model="dataTheme"
        inline-prompt
        :active-icon="dayIcon"
        :inactive-icon="darkIcon"
        @change="dataThemeChange"
      />
    </div>
    <div class="login-container">
      <div class="img">
        <component :is="toRaw(illustration)" />
      </div>
      <div class="login-box">
        <div class="login-form">
          <avatar class="avatar" />
          <Motion>
            <h2 class="outline-hidden">{{ title }}</h2>
          </Motion>

          <el-form
            ref="ruleFormRef"
            :model="ruleForm"
            :rules="loginRules"
            size="large"
          >
            <Motion :delay="100">
              <el-form-item
                prop="username"
              >
                <el-input
                  v-model="ruleForm.username"
                  clearable
                  placeholder="账号"
                  :prefix-icon="useRenderIcon(User)"
                />
              </el-form-item>
            </Motion>

            <Motion :delay="150">
              <el-form-item prop="password">
                <el-input
                  v-model="ruleForm.password"
                  clearable
                  show-password
                  placeholder="密码"
                  :prefix-icon="useRenderIcon(Lock)"
                />
              </el-form-item>
            </Motion>

            <Motion :delay="250">
              <el-form-item v-if="showCaptcha" prop="captchaCode">
                <div class="flex w-full gap-3">
                  <el-input
                    v-model="ruleForm.captchaCode"
                    clearable
                    maxlength="8"
                    placeholder="请输入验证码"
                  />
                  <button
                    type="button"
                    class="h-[40px] min-w-[124px] overflow-hidden rounded-[10px] border border-[var(--el-border-color)] bg-white px-2"
                    :disabled="captchaLoading"
                    @click="refreshCaptcha(true)"
                  >
                    <img
                      v-if="captchaImage"
                      :src="captchaImage"
                      alt="验证码"
                      class="h-full w-full object-cover"
                    />
                    <span v-else class="text-xs text-[#909399]">加载中</span>
                  </button>
                </div>
              </el-form-item>
            </Motion>

            <Motion :delay="300">
              <el-button
                class="w-full mt-4!"
                size="default"
                type="primary"
                :loading="loading"
                :disabled="disabled"
                @click="onLogin(ruleFormRef)"
              >
                登录
              </el-button>
            </Motion>
          </el-form>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import url("@/style/login.css");
</style>

<style lang="scss" scoped>
:deep(.el-input-group__append, .el-input-group__prepend) {
  padding: 0;
}
</style>
