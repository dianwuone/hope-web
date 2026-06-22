from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from .models import AdminUser, Article, ContentCategory, ContentTag, Offer, PageConfig, Project, SiteConfig


DEFAULT_SITE_CONFIGS = [
    {
        "configKey": "hero_title",
        "configValue": json.dumps({"value": "QUENTIN WINDOW"}, ensure_ascii=False),
        "groupName": "home",
        "remark": "首页主标题",
    },
    {
        "configKey": "hero_subtitle",
        "configValue": json.dumps({"value": "产品、内容与实验的窗口"}, ensure_ascii=False),
        "groupName": "home",
        "remark": "首页主副标题",
    },
    {
        "configKey": "contact_email",
        "configValue": json.dumps({"value": ""}, ensure_ascii=False),
        "groupName": "contact",
        "remark": "联系邮箱",
    },
    {
        "configKey": "community_wechat",
        "configValue": json.dumps({"value": ""}, ensure_ascii=False),
        "groupName": "community",
        "remark": "社区微信号",
    },
    {
        "configKey": "site_meta",
        "configValue": json.dumps(
            {
                "name": "QUENTIN WINDOW",
                "titleSuffix": "QUENTIN WINDOW",
                "tagline": "连接内容、App 与交流的网站窗口",
                "description": "围绕内容展示 App、收集线索、承接前置销售，并持续维护后续交流。",
                "copyright": "QUENTIN WINDOW. All rights reserved.",
                "beian": {"label": "蜀ICP备19016117号-1", "href": "https://beian.miit.gov.cn/"},
            },
            ensure_ascii=False,
        ),
        "groupName": "site",
        "remark": "站点基础信息",
    },
    {
        "configKey": "main_nav",
        "configValue": json.dumps(
            [
                {"name": "首页", "path": "/"},
                {"name": "昆廷笔记", "path": "/columns/kunting"},
                {"name": "启鸣宝宝", "path": "/columns/qiming"},
                {"name": "产品中心", "path": "/products"},
                {"name": "游戏中心", "path": "/games"},
                {"name": "快来尝鲜", "path": "/try"},
                {"name": "实验室", "path": "/lab"},
                {"name": "关于", "path": "/about"},
            ],
            ensure_ascii=False,
        ),
        "groupName": "site",
        "remark": "主导航",
    },
    {
        "configKey": "footer_sections",
        "configValue": json.dumps(
            [
                {"title": "内容", "links": [{"name": "昆廷笔记", "path": "/columns/kunting"}, {"name": "启鸣宝宝", "path": "/columns/qiming"}, {"name": "文章中心", "path": "/articles"}]},
                {"title": "产品", "links": [{"name": "产品中心", "path": "/products"}, {"name": "个人助手", "path": "/products/personal-assistant"}, {"name": "育儿助手", "path": "/products/parenting-assistant"}, {"name": "AI 工具助手", "path": "/products/ai-tools"}]},
                {"title": "游戏", "links": [{"name": "游戏中心", "path": "/games"}, {"name": "拼音大冒险", "path": "/games/pinyin-adventure"}]},
                {"title": "互动", "links": [{"name": "在线轻试玩", "path": "/play"}, {"name": "下载动态墙", "path": "/download-wall"}, {"name": "快来尝鲜", "path": "/try"}]},
            ],
            ensure_ascii=False,
        ),
        "groupName": "site",
        "remark": "页脚导航",
    },
    {
        "configKey": "social_links",
        "configValue": json.dumps(
            [
                {"name": "GitHub", "href": "#"},
                {"name": "微信", "href": "#"},
                {"name": "Email", "href": ""},
            ],
            ensure_ascii=False,
        ),
        "groupName": "site",
        "remark": "社交链接",
    },
    {
        "configKey": "article_categories",
        "configValue": json.dumps(["全部", "AI 提效", "App 开发", "幼小衔接", "亲子游戏", "产品思考"], ensure_ascii=False),
        "groupName": "content",
        "remark": "文章分类筛选项",
    },
    {
        "configKey": "article_hot_topics",
        "configValue": json.dumps(["AI 提效", "独立开发", "育儿启蒙", "亲子游戏", "产品思考", "阅读成长"], ensure_ascii=False),
        "groupName": "content",
        "remark": "文章热门话题",
    },
]

DEFAULT_PAGE_CONFIGS = [
    {
        "pageKey": "home",
        "title": "首页配置",
        "configJson": json.dumps(
            {
                "hero": {
                    "badge": "AI x 产品 x 游戏",
                    "title": "用 AI 提升工作与生活，用产品与游戏解决真实问题",
                    "subtitle": "我是 Quentin，一名产品探索者。",
                },
                "community": {
                    "title": "加入我的私域联系圈",
                    "subtitle": "获取内容更新、产品动态、体验通知与后续交流入口。",
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        "status": "active",
        "remark": "首页 Hero 与社区配置",
    },
    {
        "pageKey": "community",
        "title": "社区页配置",
        "configJson": json.dumps(
            {
                "title": "加入我的私域联系圈",
                "subtitle": "围绕内容、产品和后续合作交流，继续保持联系。",
                "benefits": ["获取内容更新", "产品动态通知", "体验资格提醒", "持续交流联系"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        "status": "active",
        "remark": "加入社区页基础配置",
    },
    {
        "pageKey": "article_center",
        "title": "文章中心页配置",
        "configJson": json.dumps(
            {
                "title": "文章中心",
                "subtitle": "汇聚全部内容，从 AI 提效到育儿启蒙，从独立开发到亲子成长。",
                "banner": "/src/assets/images/shucai/banners/banner-articles.jpg",
            },
            ensure_ascii=False,
            indent=2,
        ),
        "status": "active",
        "remark": "文章中心页静态配置",
    },
    {
        "pageKey": "games",
        "title": "游戏中心页配置",
        "configJson": json.dumps(
            {
                "title": "游戏中心",
                "subtitle": "把学习与互动放进更轻松的体验里，让探索更愿意持续。",
                "banner": "/src/assets/images/shucai/banners/banner-games.jpg",
            },
            ensure_ascii=False,
            indent=2,
        ),
        "status": "active",
        "remark": "游戏中心页静态配置",
    },
    {
        "pageKey": "downloads",
        "title": "下载中心页配置",
        "configJson": json.dumps(
            {
                "title": "下载中心",
                "subtitle": "统一查看可用产品、体验状态、下载方式和设备说明。",
                "banner": "/src/assets/images/shucai/banners/banner-downloads.jpg",
                "requirements": [
                    "首批版本优先支持 Web 体验与报名收集",
                    "移动端与桌面端能力将随产品迭代逐步开放",
                    "部分产品当前仅提供内测或心愿单登记",
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        "status": "active",
        "remark": "下载中心页静态配置",
    },
    {
        "pageKey": "try",
        "title": "快来尝鲜页配置",
        "configJson": json.dumps(
            {
                "title": "快来尝鲜",
                "subtitle": "新想法的验证场，限定内容的首发站。",
                "banner": "/src/assets/images/shucai/banners/banner-try.jpg",
                "filters": ["全部", "文档/资料包", "方法模板", "软件小工具", "游戏体验资格", "资源体验包", "内测资格"],
                "heroOfferSlug": "founding-pass",
                "validatingOfferSlugs": ["智能写作伴侣内测", "家庭时间管理器"],
                "limitedOfferSlugs": ["拼音大冒险完整版", "ai-toolkit", "创意灵感卡片"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        "status": "active",
        "remark": "快来尝鲜页基础配置",
    },
    {
        "pageKey": "about",
        "title": "关于页配置",
        "configJson": json.dumps(
            {
                "title": "一个连接内容、App 与交流的网站",
                "subtitle": "这里既有内容记录，也承接我正在做的 App 展示、线索收集、前置销售和后续交流。",
                "eyebrow": "欢迎来到昆廷的窗口",
                "authorName": "Quentin",
                "qrLabel": "",
            },
            ensure_ascii=False,
            indent=2,
        ),
        "status": "active",
        "remark": "关于页基础配置",
    },
    {
        "pageKey": "legal_privacy",
        "title": "隐私政策页配置",
        "configJson": json.dumps(
            {
                "title": "隐私政策",
                "intro": "我们尊重并保护访问者的个人信息。",
            },
            ensure_ascii=False,
            indent=2,
        ),
        "status": "active",
        "remark": "隐私政策页基础配置",
    },
    {
        "pageKey": "legal_terms",
        "title": "服务条款页配置",
        "configJson": json.dumps(
            {
                "title": "服务条款",
                "intro": "访问和使用本网站，即表示你同意遵守当前站点规则。",
            },
            ensure_ascii=False,
            indent=2,
        ),
        "status": "active",
        "remark": "服务条款页基础配置",
    },
    {
        "pageKey": "open_source",
        "title": "开源页配置",
        "configJson": json.dumps(
            {
                "title": "开源项目",
                "subtitle": "把一部分能力、方法和实验开放出来，让更多人复用与延展。",
                "projects": [
                    {"name": "Hope Site", "desc": "当前网站的前端工程骨架。", "tags": ["Vue", "Vite", "网站"]},
                    {"name": "Prompt Fragments", "desc": "围绕常用 AI 工作场景整理的提示模板集合。", "tags": ["AI", "工作流"]},
                    {"name": "Learning Toybox", "desc": "面向亲子互动和启蒙练习的轻量游戏原型。", "tags": ["教育", "互动体验"]},
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        "status": "active",
        "remark": "开源页基础配置",
    },
    {
        "pageKey": "subscribe",
        "title": "订阅页配置",
        "configJson": json.dumps(
            {
                "title": "订阅更新",
                "subtitle": "输入你的邮箱，获取最新产品动态、内测信息和内容更新。",
                "highlights": ["产品新进展", "优先体验资格", "深度内容更新"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        "status": "active",
        "remark": "订阅页基础配置",
    },
    {
        "pageKey": "play",
        "title": "在线轻试玩页配置",
        "configJson": json.dumps(
            {
                "title": "在线轻试玩",
                "subtitle": "无需下载，直接在浏览器里体验核心玩法与互动节奏。",
                "banner": "/src/assets/images/shucai/banners/banner-arcade.jpg",
            },
            ensure_ascii=False,
            indent=2,
        ),
        "status": "active",
        "remark": "在线试玩页基础配置",
    },
]

DEFAULT_PROJECTS = [
    {
        "slug": "personal-assistant",
        "name": "个人助手",
        "projectType": "product",
        "shortDesc": "你的全能生活管理助手，让每一天都井然有序、高效从容。",
        "summary": "整合日程、待办、习惯、笔记和 AI 整理能力的个人效率中枢。",
        "coverImage": "/src/assets/images/shucai/products/app-personal-assistant.jpg",
        "bannerImage": "/src/assets/images/shucai/banners/banner-products.jpg",
        "status": "new",
        "stage": "beta",
        "supportStatus": "beta_apply",
        "price": "¥29",
        "originalPrice": "¥99",
        "tagsJson": json.dumps(["个人管理", "效率工具", "习惯养成"], ensure_ascii=False),
        "featuresJson": json.dumps([{"title": "日程与任务联动", "description": "把待办、提醒、时间块和目标放在同一工作流里。"}, {"title": "AI 整理与复盘", "description": "自动总结当天重点，让记录真正可回顾、可行动。"}, {"title": "成长型仪表盘", "description": "用稳定指标追踪习惯、专注和阶段成果。"}], ensure_ascii=False),
        "highlightsJson": json.dumps(["效率提升", "日程管理", "习惯养成"], ensure_ascii=False),
        "faqJson": json.dumps([{"q": "适合什么样的用户？", "a": "适合希望把事务管理、复盘和 AI 辅助整合在一起的个人用户。"}, {"q": "是否支持多端？", "a": "第一阶段以 Web 体验和轻量表单收集为主，后续会扩展更多端。"}], ensure_ascii=False),
        "testimonialsJson": json.dumps([{"author": "自由职业者 Lin", "content": "比单独用待办工具更顺，复盘和提醒结合后明显更容易坚持。"}], ensure_ascii=False),
        "extraJson": json.dumps({}, ensure_ascii=False),
    },
    {
        "slug": "parenting-assistant",
        "name": "育儿助手",
        "projectType": "product",
        "shortDesc": "科学育儿的好帮手，记录成长点滴，陪伴宝宝健康快乐成长。",
        "summary": "围绕成长记录、启蒙建议、亲子互动和日常提醒设计的家庭型助手。",
        "coverImage": "/src/assets/images/shucai/products/app-parenting-assistant.jpg",
        "bannerImage": "/src/assets/images/shucai/banners/banner-products.jpg",
        "status": "new",
        "stage": "beta",
        "supportStatus": "beta_apply",
        "price": "¥39",
        "originalPrice": "¥129",
        "tagsJson": json.dumps(["育儿陪伴", "成长记录", "亲子教育"], ensure_ascii=False),
        "featuresJson": json.dumps([{"title": "成长记录轻量化", "description": "把睡眠、饮食、身高体重和关键事件都沉淀成可回看的轨迹。"}, {"title": "启蒙内容建议", "description": "围绕年龄阶段给出亲子互动、阅读和学习建议。"}, {"title": "家庭共管视角", "description": "让照护者协同更顺畅，减少信息割裂。"}], ensure_ascii=False),
        "highlightsJson": json.dumps(["育儿记录", "启蒙教育", "亲子互动"], ensure_ascii=False),
        "faqJson": json.dumps([{"q": "适合什么年龄段？", "a": "目前更偏向 0-8 岁家庭，后续会逐步扩展使用场景。"}, {"q": "会替代医生建议吗？", "a": "不会，产品提供的是记录、提醒和内容参考，不替代专业诊疗意见。"}], ensure_ascii=False),
        "testimonialsJson": json.dumps([{"author": "二孩妈妈 Zoe", "content": "最有价值的是把零散记录变成体系，回看孩子成长特别直观。"}], ensure_ascii=False),
        "extraJson": json.dumps({}, ensure_ascii=False),
    },
    {
        "slug": "ai-tools",
        "name": "AI 工具助手",
        "projectType": "product",
        "shortDesc": "你的 AI 工具中枢，更好用的提示词与工作流管理器。",
        "summary": "把提示词、模板、工具流和知识库统一整理，让常用 AI 能力真正形成稳定工作台。",
        "coverImage": "/src/assets/images/shucai/products/app-ai-tools.jpg",
        "bannerImage": "/src/assets/images/shucai/banners/banner-products.jpg",
        "status": "new",
        "stage": "coming_soon",
        "supportStatus": "wishlist",
        "price": "¥49",
        "originalPrice": "¥149",
        "tagsJson": json.dumps(["AI 提效", "创作工具", "效率应用"], ensure_ascii=False),
        "featuresJson": json.dumps([{"title": "常用场景模板化", "description": "把写作、总结、提纲、拆解等高频场景收纳成工具集。"}, {"title": "结果可编辑可再生", "description": "不是一次性输出，而是支持继续改、继续提问。"}, {"title": "低门槛 AI 工作流", "description": "让不懂提示词的人也能快速用起来。"}], ensure_ascii=False),
        "highlightsJson": json.dumps(["AI 写作", "内容总结", "灵感生成"], ensure_ascii=False),
        "faqJson": json.dumps([{"q": "什么时候上线？", "a": "当前处于规划与原型阶段，优先对外开放心愿单和早期体验名单。"}, {"q": "适合什么职业？", "a": "创作者、自由职业者、小团队运营和知识工作者都会受益。"}], ensure_ascii=False),
        "testimonialsJson": json.dumps([{"author": "内容运营 Amy", "content": "如果把常用 AI 能力统一收纳，日常效率会稳定很多。"}], ensure_ascii=False),
        "extraJson": json.dumps({"detailPage": {"eyebrow": "AI 工具助手", "heroTitle": "你的 AI 工具中枢\n更好用的提示词与工作流管理器", "heroDescription": "AI 工具助手帮你收集、整理与提炼提示词，构建高效工作流。把杂乱管理用 AI 工具与模板，让你的创作、学习与工作更快、更稳、更可积累。", "heroPrimaryLabel": "立即体验 Beta", "heroPrimaryTo": "/community", "heroSecondaryLabel": "进入网页版", "heroSecondaryTo": "/play", "heroCaption": "支持多模型 / 多端协作，持续迭代中", "stats": [{"value": "1,300+", "label": "精选提示词"}, {"value": "120+", "label": "工作流模板"}, {"value": "23+", "label": "内置 AI 工具"}, {"value": "9,800+", "label": "用户正在使用"}], "ecosystemTitle": "兼容主流模型与工具", "ecosystem": ["ChatGPT", "Claude", "Gemini", "通义千问", "智谱清言", "Midjourney", "Stable Diffusion"], "abilitiesTitle": "核心能力", "abilitiesSubtitle": "提词、提示词、工作流、工具三位一体，让 AI 真正成为你的生产力。", "stepsTitle": "从灵感到结果，只需 4 步", "stepsSubtitle": "用工作流把隐性经验拆成行动，让 AI 帮你一步步完成。", "templatesTitle": "精选模板 / 提示词", "templatesSubtitle": "开箱即用，持续更新。", "ctaTitle": "立即体验 AI 工具助手", "ctaPoints": ["Beta 版本抢先体验", "云端同步，支持多端", "提词更新，不断进化"], "ctaPrimaryLabel": "下载桌面版", "ctaPrimaryTo": "/downloads", "ctaSecondaryLabel": "进入网页版", "ctaSecondaryTo": "/play", "ctaCaption": "支持 Windows 10+ / macOS 11+ / Web", "articlesTitle": "相关文章", "articlesCtaLabel": "进入文章中心", "articlesCtaTo": "/articles", "articles": ["ai-workflow-output", "first-app-in-90-days", "shipping-small-products-fast", "pinyin-learning-at-home"], "moreTitle": "更多产品", "moreItems": [{"title": "个人助手", "desc": "任务、习惯、复盘，打造个人效率系统", "to": "/products/personal-assistant", "icon": "◌", "tone": "green"}, {"title": "育儿助手", "desc": "成长记录、提醒、早教陪伴，陪伴孩子快乐成长", "to": "/products/parenting-assistant", "icon": "◉", "tone": "coral"}, {"title": "拼音大冒险", "desc": "趣味拼音学习游戏，边玩边学更轻松", "to": "/games/pinyin-adventure", "icon": "✦", "tone": "blue"}, {"title": "下载动态墙", "desc": "看看大家都在下载什么，实时感受热度", "to": "/download-wall", "icon": "▣", "tone": "blue"}], "wishlistTitle": "喜欢 AI 工具助手？", "wishlistDescription": "加入心愿单，获取更新提醒与专属资料，不错过每一次进化。", "wishlistLabel": "加入心愿单", "wishlistTo": "/wishlist", "heroMockImage": "/src/assets/images/shucai/banners/banner-arcade.jpg"}}, ensure_ascii=False),
    },
    {
        "slug": "pinyin-adventure",
        "name": "拼音大冒险",
        "projectType": "game",
        "title": "拼音大冒险",
        "subtitle": "趣味拼音闯关，轻松掌握声母韵母",
        "shortDesc": "专为 4-7 岁孩子设计的拼音学习游戏。",
        "summary": "在冒险中认识声母、韵母和整体认读音节，边玩边学，轻松启蒙。",
        "description": "通过闯关、互动探索和即时反馈，让孩子在轻松氛围中完成拼音启蒙。",
        "coverImage": "/src/assets/images/shucai/products/app-pinyin-game.jpg",
        "bannerImage": "/src/assets/images/shucai/banners/banner-arcade.jpg",
        "status": "published",
        "stage": "beta",
        "supportStatus": "download",
        "price": "",
        "originalPrice": "",
        "tagsJson": json.dumps(["教育益智", "语言学习", "4-7岁"], ensure_ascii=False),
        "featuresJson": json.dumps(
            [
                {"title": "科学分级", "description": "循序渐进，系统学习"},
                {"title": "互动探索", "description": "丰富场景，激发兴趣"},
                {"title": "即时反馈", "description": "智能反馈，巩固记忆"},
            ],
            ensure_ascii=False,
        ),
        "highlightsJson": json.dumps(["拼音启蒙", "互动探索", "趣味学习"], ensure_ascii=False),
        "faqJson": json.dumps([], ensure_ascii=False),
        "testimonialsJson": json.dumps([], ensure_ascii=False),
        "extraJson": json.dumps(
            {
                "route": "/games/pinyin-adventure",
                "age": "4-7岁",
                "category": "教育益智",
            },
            ensure_ascii=False,
        ),
    },
    {
        "slug": "tools",
        "name": "工具实验室",
        "projectType": "lab",
        "title": "工具实验室",
        "subtitle": "探索下一代 AI 工具与效率应用原型，体验更顺手的工作方式。",
        "description": "聚焦 AI 辅助写作、整理、计划和工作流自动化的实验场。",
        "coverImage": "/src/assets/images/shucai/lab/lab-tools.jpg",
        "bannerImage": "/src/assets/images/shucai/banners/banner-lab.jpg",
        "status": "published",
        "tagsJson": json.dumps(["AI 工具", "效率应用", "智能交互"], ensure_ascii=False),
        "extraJson": json.dumps({"projects": [{"name": "AI 写作助手", "status": "开发中"}, {"name": "智能日程管理", "status": "规划中"}, {"name": "轻量知识整理台", "status": "内测中"}]}, ensure_ascii=False),
        "featuresJson": "[]",
        "highlightsJson": "[]",
        "faqJson": "[]",
        "testimonialsJson": "[]",
    },
    {
        "slug": "games",
        "name": "游戏实验室",
        "projectType": "lab",
        "title": "游戏实验室",
        "subtitle": "教育游戏与互动体验的试验场，用游戏化思维重新定义学习方式。",
        "description": "探索亲子互动、拼音启蒙和轻量试玩产品的原型方向。",
        "coverImage": "/src/assets/images/shucai/lab/lab-games.jpg",
        "bannerImage": "/src/assets/images/shucai/banners/banner-lab.jpg",
        "status": "published",
        "tagsJson": json.dumps(["教育游戏", "互动体验", "寓教于乐"], ensure_ascii=False),
        "extraJson": json.dumps({"projects": [{"name": "拼音大冒险扩展关卡", "status": "开发中"}, {"name": "儿童互动问答", "status": "规划中"}, {"name": "亲子桌游数字化助手", "status": "内测中"}]}, ensure_ascii=False),
        "featuresJson": "[]",
        "highlightsJson": "[]",
        "faqJson": "[]",
        "testimonialsJson": "[]",
    },
]

DEFAULT_OFFERS = [
    {"slug": "founding-pass", "title": "独立开发支持手册", "subtitle": "从零到一的完整开发经验，包含项目规划、技术选型、产品设计、上线运营全流程。", "price": "¥29", "originalPrice": "¥99", "bannerImage": "/src/assets/images/shucai/banners/banner-try.jpg", "benefitsJson": json.dumps(["文档资料包", "可下载 PDF", "适合刚起步的独立开发者"], ensure_ascii=False), "metaJson": "[]", "extraJson": "{}", "category": "文档/资料包", "status": "早鸟尝鲜中", "statusTone": "green", "summary": "从零到一的完整开发经验，涵盖项目规划、技术选型、产品设计与上线运营全流程。", "ctaLabel": "立即购买"},
    {"slug": "ai-toolkit", "title": "AI 效率工具包", "subtitle": "精选 AI 工具使用方法与落地工作流，让内容生产和信息整理更快进入状态。", "price": "¥19", "originalPrice": "¥59", "bannerImage": "/src/assets/images/shucai/banners/banner-try.jpg", "benefitsJson": json.dumps(["方法模板", "内容创作参考", "持续迭代更新"], ensure_ascii=False), "metaJson": json.dumps(["人", "内容创作者", "在线查阅"], ensure_ascii=False), "extraJson": "{}", "category": "方法模板", "status": "限量首发", "statusTone": "amber", "summary": "精选 AI 工具使用方法与高频工作流清单，让内容生产和信息整理效率提升。", "ctaLabel": "立即购买"},
    {"slug": "育儿时间管理模板", "title": "育儿时间管理模板", "subtitle": "针对家长时间与陪伴节奏整理的实践型资料，帮助家庭安排更清晰。", "price": "¥9", "originalPrice": "¥29", "bannerImage": "/src/assets/images/shucai/banners/banner-try.jpg", "benefitsJson": json.dumps(["时间规划模板", "可下载 PDF", "适合新手爸妈"], ensure_ascii=False), "metaJson": json.dumps(["人", "新手爸妈", "PDF 下载"], ensure_ascii=False), "extraJson": "{}", "category": "方法模板", "status": "早鸟尝鲜中", "statusTone": "green", "summary": "科学规划育儿日程，帮助新手爸妈高效安排日常，减少混乱，提升陪伴质量。", "ctaLabel": "立即购买"},
    {"slug": "拼音大冒险完整版", "title": "拼音大冒险完整版", "subtitle": "完整拼音学习游戏包，更多关卡、更多陪练，让孩子在趣味中掌握拼音。", "price": "¥15", "originalPrice": "¥39", "bannerImage": "/src/assets/images/shucai/banners/banner-try.jpg", "benefitsJson": json.dumps(["游戏资料包", "适龄指南", "家长陪练建议"], ensure_ascii=False), "metaJson": json.dumps(["人", "4-8 岁儿童", "游戏版"], ensure_ascii=False), "extraJson": "{}", "category": "游戏体验资格", "status": "首发测试", "statusTone": "coral", "summary": "完整拼音学习游戏包，更多关卡、更多陪练，让孩子在趣味中掌握拼音。", "ctaLabel": "立即购买"},
    {"slug": "智能写作伴侣内测", "title": "智能写作伴侣内测", "subtitle": "基于上下文理解的写作辅助工具，优先进入更高自由度的内测阶段。", "price": "¥1", "originalPrice": "¥29", "bannerImage": "/src/assets/images/shucai/banners/banner-try.jpg", "benefitsJson": json.dumps(["内测资格", "早期反馈通道", "阶段权益保留"], ensure_ascii=False), "metaJson": json.dumps(["人", "写作爱好者", "会员资格"], ensure_ascii=False), "extraJson": "{}", "category": "内测资格", "status": "限时验证中", "statusTone": "purple", "summary": "基于上下文理解的写作辅助工具，让内容表达更流畅，抢先体验连贯写作链路。", "ctaLabel": "特别验证"},
    {"slug": "产品设计检查清单", "title": "产品设计检查清单", "subtitle": "系统化的产品设计自查工具，覆盖需求分析到上线前验收的关键节点。", "price": "¥5", "originalPrice": "¥19", "bannerImage": "/src/assets/images/shucai/banners/banner-try.jpg", "benefitsJson": json.dumps(["文档资料包", "可下载 PDF", "适合独立开发者"], ensure_ascii=False), "metaJson": json.dumps(["人", "产品经理", "PDF 下载"], ensure_ascii=False), "extraJson": "{}", "category": "文档/资料包", "status": "早鸟尝鲜中", "statusTone": "green", "summary": "系统化的产品设计自查工具，覆盖需求分析到上线前验收的关键节点。", "ctaLabel": "立即购买"},
    {"slug": "家庭时间管理器", "title": "家庭时间管理器", "subtitle": "为家庭协同而设计的可视化时间管理工具，帮助全家人规划日程与任务。", "price": "¥1", "originalPrice": "¥19", "bannerImage": "/src/assets/images/shucai/banners/banner-try.jpg", "benefitsJson": json.dumps(["软件小工具", "预付验证中", "后续优先获得内测资格"], ensure_ascii=False), "metaJson": "[]", "extraJson": "{}", "category": "软件小工具", "status": "特别验证中", "statusTone": "purple", "summary": "为家庭协同规划日程与任务而生，帮助全家人规划日程，预付验证后会优先同步后续动态。", "ctaLabel": "特别验证"},
    {"slug": "创意灵感卡片", "title": "创意灵感卡片", "subtitle": "帮助记录灵感、激发思路的数字卡片包，适合创作者与头脑风暴场景。", "price": "¥3", "originalPrice": "¥12", "bannerImage": "/src/assets/images/shucai/banners/banner-try.jpg", "benefitsJson": json.dumps(["数字资料", "限时首发", "创作辅助"], ensure_ascii=False), "metaJson": "[]", "extraJson": "{}", "category": "资源体验包", "status": "首发测试", "statusTone": "coral", "summary": "帮助记录灵感、激发思路的数字卡片包，适合创作者和头脑风暴场景。", "ctaLabel": "立即购买"},
]


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def seed_if_empty(db: Session, seed_file: Path) -> None:
    has_data = db.query(ContentCategory).first()
    if not has_data:
        payload = json.loads(seed_file.read_text(encoding="utf-8"))

        for item in payload.get("adminUsers", []):
            db.add(AdminUser(**item))

        columns_by_id: dict[int, ContentCategory] = {}
        for item in payload.get("columns", []):
            model = ContentCategory(**item)
            columns_by_id[item["id"]] = model
            db.add(model)

        tags_by_id: dict[int, ContentTag] = {}
        for item in payload.get("tags", []):
            model = ContentTag(**item)
            tags_by_id[item["id"]] = model
            db.add(model)

        db.flush()

        for source in payload.get("articles", []):
            item = dict(source)
            tag_ids = item.pop("tagIds", [])
            item.pop("publishedAt", None)
            item.pop("createdAt", None)
            item.pop("updatedAt", None)
            article = Article(
                **item,
                publishedAt=parse_datetime(source.get("publishedAt")),
                createdAt=parse_datetime(source["createdAt"]),
                updatedAt=parse_datetime(source["updatedAt"]),
            )
            article.tags = [tags_by_id[tag_id] for tag_id in tag_ids if tag_id in tags_by_id]
            article.column = columns_by_id[item["columnId"]]
            db.add(article)

    now = datetime.utcnow()
    existing_site_keys = {item.configKey for item in db.query(SiteConfig).all()}
    for item in DEFAULT_SITE_CONFIGS:
        if item["configKey"] not in existing_site_keys:
            db.add(SiteConfig(**item, updatedAt=now))

    existing_page_keys = {item.pageKey for item in db.query(PageConfig).all()}
    for item in DEFAULT_PAGE_CONFIGS:
        if item["pageKey"] not in existing_page_keys:
            db.add(PageConfig(**item, updatedAt=now))

    existing_project_slugs = {item.slug for item in db.query(Project).all()}
    for item in DEFAULT_PROJECTS:
        if item["slug"] not in existing_project_slugs:
            db.add(Project(**item, createdAt=now, updatedAt=now))

    existing_offer_slugs = {item.slug for item in db.query(Offer).all()}
    for item in DEFAULT_OFFERS:
        if item["slug"] not in existing_offer_slugs:
            db.add(Offer(**item, createdAt=now, updatedAt=now))

    db.commit()
