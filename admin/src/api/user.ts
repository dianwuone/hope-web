import { http } from "@/utils/http";
import { getToken } from "@/utils/auth";

export type UserResult = {
  success: boolean;
  data: {
    /** 头像 */
    avatar: string;
    /** 用户名 */
    username: string;
    /** 昵称 */
    nickname: string;
    /** 当前登录用户的角色 */
    roles: Array<string>;
    /** 按钮级别权限 */
    permissions: Array<string>;
    /** `token` */
    accessToken: string;
    /** 用于调用刷新`accessToken`的接口时所需的`token` */
    refreshToken: string;
    /** `accessToken`的过期时间（格式'xxxx/xx/xx xx:xx:xx'） */
    expires: Date;
  };
};

export type CaptchaResult = {
  captchaKey: string;
  captchaSvg: string;
  expiresIn: number;
};

export type RefreshTokenResult = {
  success: boolean;
  data: {
    /** `token` */
    accessToken: string;
    /** 用于调用刷新`accessToken`的接口时所需的`token` */
    refreshToken: string;
    /** `accessToken`的过期时间（格式'xxxx/xx/xx xx:xx:xx'） */
    expires: Date;
  };
};

/** 登录 */
export const getLogin = (data?: object) => {
  return http
    .request<any>("post", "/api/admin/login", { data })
    .then(res => {
      const expires = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);
      return {
        success: true,
        data: {
          avatar: "",
          username: res.user.username,
          nickname: res.user.displayName,
          roles: ["admin"],
          permissions: ["*:*:*"],
          accessToken: res.token,
          refreshToken: res.token,
          expires
        }
      } as UserResult;
    });
};

export const getCaptcha = (scope: "admin" | "frontend" = "admin") => {
  return http.get<CaptchaResult, Record<string, string>>("/api/security/captcha", {
    params: { scope }
  });
};

/** 刷新`token` */
export const refreshTokenApi = (data?: object) => {
  const token = getToken();
  return Promise.resolve({
    success: true,
    data: {
      accessToken: token?.accessToken ?? "",
      refreshToken: token?.refreshToken ?? "",
      expires: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)
    }
  } as RefreshTokenResult);
};
