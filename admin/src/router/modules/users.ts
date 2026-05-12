const Layout = () => import("@/layout/index.vue");

export default {
  path: "/users",
  name: "Users",
  component: Layout,
  redirect: "/users/index",
  meta: {
    icon: "ri/user-settings-line",
    title: "用户管理",
    rank: 3
  },
  children: [
    {
      path: "/users/index",
      name: "UsersIndex",
      component: () => import("@/views/users/index.vue"),
      meta: {
        title: "前台用户"
      }
    }
  ]
} satisfies RouteConfigsTable;
