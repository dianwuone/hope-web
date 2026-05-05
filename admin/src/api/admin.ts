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

export const fetchSiteConfigs = () => http.get<ListResult<ConfigItem>, any>("/api/admin/site-configs");
export const createSiteConfig = (data: any) => http.post<ConfigItem, any>("/api/admin/site-configs", { data });
export const updateSiteConfig = (id: number, data: any) => http.request<ConfigItem>("put", `/api/admin/site-configs/${id}`, { data });
export const deleteSiteConfig = (id: number) => http.request<any>("delete", `/api/admin/site-configs/${id}`);

export const fetchPageConfigs = () => http.get<ListResult<ConfigItem>, any>("/api/admin/page-configs");
export const createPageConfig = (data: any) => http.post<ConfigItem, any>("/api/admin/page-configs", { data });
export const updatePageConfig = (id: number, data: any) => http.request<ConfigItem>("put", `/api/admin/page-configs/${id}`, { data });
export const deletePageConfig = (id: number) => http.request<any>("delete", `/api/admin/page-configs/${id}`);
