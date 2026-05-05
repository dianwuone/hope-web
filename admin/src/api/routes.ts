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
          },
          {
            path: "/content/ads",
            name: "AdminAds",
            component: "content/ads/index",
            meta: {
              title: "广告管理"
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
      },
      {
        path: "/operations",
        name: "Operations",
        component: "content/index",
        redirect: "/operations/wishlist",
        meta: {
          icon: "ep:DataAnalysis",
          title: "运营管理",
          rank: 3
        },
        children: [
          {
            path: "/operations/wishlist",
            name: "AdminWishlist",
            component: "operations/wishlist/index",
            meta: {
              title: "心愿单管理"
            }
          },
          {
            path: "/operations/leads",
            name: "AdminLeads",
            component: "operations/leads/index",
            meta: {
              title: "用户线索管理"
            }
          },
          {
            path: "/operations/beta-applications",
            name: "AdminBetaApplications",
            component: "operations/beta-applications/index",
            meta: {
              title: "内测申请管理"
            }
          }
        ]
      }
    ]
  } as Result);
};
