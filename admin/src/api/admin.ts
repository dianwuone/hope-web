import { http } from "@/utils/http";

export interface ListResult<T> {
  items: T[];
  total: number;
}

export interface ArticleItem {
  id: number;
  title: string;
  slug: string;
  summary: string;
  contentBody: string;
  authorName: string;
  columnId: number;
  tagIds: number[];
  status: string;
}

export interface ProjectItem {
  id: number;
  slug: string;
  name: string;
  projectType: string;
  title?: string;
  subtitle?: string;
  shortDesc?: string;
  summary?: string;
  description?: string;
  coverImage: string;
  bannerImage: string;
  status: string;
  stage?: string;
  supportStatus?: string;
  price?: string;
  originalPrice?: string;
  tags: string[];
  features: Array<{ title: string; description: string }>;
  highlights: string[];
  faq: Array<{ q: string; a: string }>;
  testimonials: Array<{ author: string; content: string }>;
  extra: Record<string, any>;
}

export interface OfferItem {
  id: number;
  slug: string;
  title: string;
  subtitle: string;
  category?: string;
  status?: string;
  statusTone?: string;
  price: string;
  originalPrice?: string;
  bannerImage: string;
  summary?: string;
  ctaLabel?: string;
  benefits: string[];
  meta: string[];
  extra: Record<string, any>;
}

export interface AdItem {
  id: number;
  slotKey: string;
  title: string;
  pageKey?: string;
  imageUrl: string;
  targetUrl: string;
  description?: string;
  ctaLabel?: string;
  status: string;
  sortOrder: number;
  startAt?: string;
  endAt?: string;
  payload: Record<string, any>;
  createdAt: string;
  updatedAt: string;
}

export interface ConfigItem {
  id: number;
  configKey?: string;
  configValue?: string;
  groupName?: string;
  pageKey?: string;
  title?: string;
  configJson?: string;
  status?: string;
  remark?: string;
}

export interface WishlistItem {
  id: number;
  visitorId: string;
  projectSlug?: string;
  projectName?: string;
  category?: string;
  wishState: string;
  sourcePage?: string;
  contactType?: string;
  contactValue?: string;
  note?: string;
  isActive: number;
  createdAt: string;
  updatedAt: string;
}

export interface CommunityLeadItem {
  id: number;
  leadType: string;
  intentReason: string;
  name?: string;
  contactType: string;
  contactValue: string;
  message?: string;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface BetaApplicationItem {
  id: number;
  projectSlug?: string;
  sourcePage: string;
  roleType: string;
  name: string;
  contactType: string;
  contactValue: string;
  city?: string;
  experienceNote?: string;
  status: string;
  followUpNote?: string;
  createdAt: string;
  updatedAt: string;
}

export interface DashboardData {
  overview: Record<string, number>;
  wishlist: {
    byState: Record<string, number>;
    bySource: Record<string, number>;
    topProjects: Array<{ name: string; count: number }>;
  };
  leads: {
    byStatus: Record<string, number>;
    byType: Record<string, number>;
  };
  beta: {
    byStatus: Record<string, number>;
    byRole: Record<string, number>;
  };
}

export interface FrontendUserItem {
  id: number;
  username: string;
  email: string;
  nickname: string;
  avatar: string;
  bio?: string;
  status: string;
  lastLoginAt?: string;
  createdAt: string;
  updatedAt: string;
  wishlistCount: number;
  likeCount: number;
  favoriteCount: number;
  commentCount: number;
  betaApplicationCount: number;
  communityLeadCount: number;
}

export interface DatabaseSyncResult {
  ok: boolean;
  applied: boolean;
  seeded: boolean;
  missingTables: string[];
  addedColumns: string[];
  executedSql: string[];
}

export interface DatabaseUploadResult {
  ok: boolean;
  databasePath: string;
  backupPath: string;
  backupWalPath?: string;
  backupShmPath?: string;
  uploadedAt: string;
  appliedSync: boolean;
  seeded: boolean;
  missingTables: string[];
  addedColumns: string[];
  executedSql: string[];
}

export interface AiPublishResult {
  ok: boolean;
  contentType: string;
  action: string;
  itemId: number;
  slug: string;
  item: Record<string, any>;
}

export const fetchColumns = () => http.get<ListResult<any>, any>("/api/columns");
export const fetchTags = () => http.get<ListResult<any>, any>("/api/tags");
export const fetchArticles = () => http.get<ListResult<ArticleItem>, any>("/api/admin/articles");
export const createArticle = (data: any) => http.post<ArticleItem, any>("/api/admin/articles", { data });
export const updateArticle = (id: number, data: any) => http.request<ArticleItem>("put", `/api/admin/articles/${id}`, { data });
export const deleteArticle = (id: number) => http.request<any>("delete", `/api/admin/articles/${id}`);

export const fetchProjects = (projectType = "") => http.get<ListResult<ProjectItem>, any>("/api/admin/projects", { params: projectType ? { projectType } : {} });
export const createProject = (data: any) => http.post<ProjectItem, any>("/api/admin/projects", { data });
export const updateProject = (id: number, data: any) => http.request<ProjectItem>("put", `/api/admin/projects/${id}`, { data });
export const deleteProject = (id: number) => http.request<any>("delete", `/api/admin/projects/${id}`);

export const fetchOffers = () => http.get<ListResult<OfferItem>, any>("/api/admin/offers");
export const createOffer = (data: any) => http.post<OfferItem, any>("/api/admin/offers", { data });
export const updateOffer = (id: number, data: any) => http.request<OfferItem>("put", `/api/admin/offers/${id}`, { data });
export const deleteOffer = (id: number) => http.request<any>("delete", `/api/admin/offers/${id}`);

export const fetchAds = () => http.get<ListResult<AdItem>, any>("/api/admin/ads");
export const createAd = (data: any) => http.post<AdItem, any>("/api/admin/ads", { data });
export const updateAd = (id: number, data: any) => http.request<AdItem>("put", `/api/admin/ads/${id}`, { data });
export const deleteAd = (id: number) => http.request<any>("delete", `/api/admin/ads/${id}`);

export const fetchSiteConfigs = () => http.get<ListResult<ConfigItem>, any>("/api/admin/site-configs");
export const createSiteConfig = (data: any) => http.post<ConfigItem, any>("/api/admin/site-configs", { data });
export const updateSiteConfig = (id: number, data: any) => http.request<ConfigItem>("put", `/api/admin/site-configs/${id}`, { data });
export const deleteSiteConfig = (id: number) => http.request<any>("delete", `/api/admin/site-configs/${id}`);

export const fetchPageConfigs = () => http.get<ListResult<ConfigItem>, any>("/api/admin/page-configs");
export const createPageConfig = (data: any) => http.post<ConfigItem, any>("/api/admin/page-configs", { data });
export const updatePageConfig = (id: number, data: any) => http.request<ConfigItem>("put", `/api/admin/page-configs/${id}`, { data });
export const deletePageConfig = (id: number) => http.request<any>("delete", `/api/admin/page-configs/${id}`);

export const fetchDashboard = () => http.get<DashboardData, any>("/api/admin/dashboard");
export const fetchFrontendUsers = () => http.get<ListResult<FrontendUserItem>, any>("/api/admin/frontend-users");
export const updateFrontendUser = (id: number, data: any) => http.request<FrontendUserItem>("put", `/api/admin/frontend-users/${id}`, { data });

export const fetchWishlistItems = () => http.get<ListResult<WishlistItem>, any>("/api/admin/wishlist-items");
export const updateWishlistItem = (id: number, data: any) => http.request<WishlistItem>("put", `/api/admin/wishlist-items/${id}`, { data });

export const fetchCommunityLeads = () => http.get<ListResult<CommunityLeadItem>, any>("/api/admin/community-leads");
export const updateCommunityLead = (id: number, data: any) => http.request<CommunityLeadItem>("put", `/api/admin/community-leads/${id}`, { data });

export const fetchBetaApplications = () => http.get<ListResult<BetaApplicationItem>, any>("/api/admin/beta-applications");
export const updateBetaApplication = (id: number, data: any) => http.request<BetaApplicationItem>("put", `/api/admin/beta-applications/${id}`, { data });

export const syncDatabase = (data: { apply: boolean; seedDefaults: boolean }) =>
  http.post<DatabaseSyncResult, any>("/api/admin/database/sync", { data });

export const uploadDatabaseFile = (file: File) => {
  const formData = new FormData();
  formData.append("file", file);
  return http.request<DatabaseUploadResult>("post", "/api/admin/database/upload", {
    data: formData,
    headers: {
      "Content-Type": "multipart/form-data"
    }
  });
};

export const publishAiContent = (data: {
  contentType: string;
  mode: string;
  autoPublish: boolean;
  payload: Record<string, any>;
}) => http.post<AiPublishResult, any>("/api/admin/content/publish", { data });
