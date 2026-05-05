type Result = {
  success: boolean;
  data: Array<any>;
};

export const getAsyncRoutes = () => {
  return Promise.resolve({
    success: true,
    data: [
      {
        path: "/content",
        name: "Content",
        component: "content/index",
        redirect: "/content/articles",
        meta: {
          icon: "ep:Document",
          title: "内容管理",
          rank: 1
        },
        children: [
          {
            path: "/content/articles",
            name: "AdminArticles",
            component: "content/articles/index",
            meta: {
              title: "文章管理"
            }
          },
          {
            path: "/content/projects",
            name: "AdminProjects",
            component: "content/projects/index",
            meta: {
              title: "项目管理"
            }
          },
          {
            path: "/content/offers",
            name: "AdminOffers",
            component: "content/offers/index",
            meta: {
              title: "商品管理"
            }
          }
        ]
      },
      {
        path: "/system",
        name: "System",
        component: "system/index",
        redirect: "/system/site-configs",
        meta: {
          icon: "ep:Setting",
          title: "系统配置",
          rank: 2
        },
        children: [
          {
            path: "/system/site-configs",
            name: "AdminSiteConfigs",
            component: "system/site-configs/index",
            meta: {
              title: "全站配置"
            }
          },
          {
            path: "/system/page-configs",
            name: "AdminPageConfigs",
            component: "system/page-configs/index",
            meta: {
              title: "页面配置"
            }
          }
        ]
      }
    ]
  } as Result);
};
