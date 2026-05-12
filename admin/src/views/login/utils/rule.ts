import { reactive } from "vue";
import type { FormRules } from "element-plus";

/** 登录校验 */
const loginRules = reactive<FormRules>({
  username: [
    {
      required: true,
      message: "请输入账号",
      trigger: "blur"
    }
  ],
  password: [
    {
      validator: (rule, value, callback) => {
        if (value === "") {
          callback(new Error("请输入密码"));
        } else if (String(value).trim().length < 6) {
          callback(new Error("密码至少 6 位"));
        } else {
          callback();
        }
      },
      trigger: "blur"
    }
  ],
  captchaCode: [
    {
      validator: (rule, value, callback) => {
        const text = String(value || "").trim();
        if (text && text.length < 4) {
          callback(new Error("验证码至少 4 位"));
        } else {
          callback();
        }
      },
      trigger: "blur"
    }
  ]
});

export { loginRules };
