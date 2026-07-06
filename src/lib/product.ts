export type ModuleEntry = {
  slug: string;
  title: string;
  eyebrow: string;
  href: string;
  description: string;
  tags: string[];
  metric: string;
  action: string;
};

export const moduleEntries: ModuleEntry[] = [
  {
    slug: 'live',
    title: 'AI 直播中控',
    eyebrow: 'Control Room',
    href: '/app/live',
    description: '一个界面完成开播、播报、弹幕、AI 回复、场景切换和人工接管。',
    tags: ['实时预览', '弹幕问答', '一键接管'],
    metric: '端到端链路可观测',
    action: '进入直播中控',
  },
  {
    slug: 'avatars',
    title: '数字人定制',
    eyebrow: 'Avatar Studio',
    href: '/app/avatars',
    description: '管理形象、声线、服装、动作、表情和检测报告，支持 2D 到 3D 扩展。',
    tags: ['形象管理', '声线克隆', '服装切换'],
    metric: '2D/3D 双路线',
    action: '进入数字人资产',
  },
  {
    slug: 'scripts',
    title: '脚本编排',
    eyebrow: 'Script Studio',
    href: '/app/scripts',
    description: '上传 PPT、Word、Excel，自动解析为直播流程、讲解话术和场景时间线。',
    tags: ['文档解析', '时间线', '场景联动'],
    metric: '文件到流程自动化',
    action: '创建直播脚本',
  },
  {
    slug: 'knowledge',
    title: '知识库问答',
    eyebrow: 'Knowledge RAG',
    href: '/app/knowledge',
    description: '行业知识、商品信息和 FAQ 自动召回，驱动数字人实时回答观众问题。',
    tags: ['RAG 检索', '商品库', '答案溯源'],
    metric: '知识驱动回复',
    action: '管理知识库',
  },
  {
    slug: 'platforms',
    title: '多平台推流',
    eyebrow: 'Multi Stream',
    href: '/app/platforms',
    description: '统一管理抖音、快手、淘宝、视频号等平台推流地址和直播状态。',
    tags: ['RTMP', 'SRT', 'WebRTC'],
    metric: '平台故障隔离',
    action: '配置推流平台',
  },
  {
    slug: 'moderation',
    title: '场控与风控',
    eyebrow: 'Safety Desk',
    href: '/app/moderation',
    description: '过滤广告、刷屏和高风险内容，敏感回复进入人工确认队列。',
    tags: ['敏感词', '风险审核', '人工确认'],
    metric: '风险先审后播',
    action: '查看风险队列',
  },
  {
    slug: 'reports',
    title: '数据报表',
    eyebrow: 'Analytics',
    href: '/app/reports',
    description: '自动生成直播复盘、互动数据、AI 回复质量和系统运行月报。',
    tags: ['直播复盘', 'SLA', '月报导出'],
    metric: '服务材料沉淀',
    action: '查看报表',
  },
  {
    slug: 'services',
    title: '年度服务',
    eyebrow: 'Service Hub',
    href: '/app/services',
    description: '管理授权、算法更新、故障工单、技术培训和季度优化记录。',
    tags: ['7x24 支持', '更新记录', '培训服务'],
    metric: '交付可追踪',
    action: '查看服务中心',
  },
];

export const workflowSteps = [
  {
    title: '创建数字人',
    text: '选择 2D 视频数字人、3D 形象或商业 API 形象，并绑定声线与服装。',
  },
  {
    title: '导入脚本',
    text: '上传 PPT、Word、Excel 和商品表，自动生成直播流程和知识库。',
  },
  {
    title: '连接平台',
    text: '配置抖音、快手、淘宝、视频号推流地址和弹幕事件来源。',
  },
  {
    title: 'AI 自动直播',
    text: '数字人按脚本讲解，根据弹幕和知识库实时回答问题。',
  },
  {
    title: '复盘交付',
    text: '生成直播数据、问答质量、风险记录、SLA 和月度服务报告。',
  },
];

export const solutionCards = [
  {
    title: '电商直播',
    description: '卖点讲解、优惠提醒、售后问答。',
    accent: 'commerce',
  },
  {
    title: '教育培训',
    description: '课件解析、在线讲解、学员问答。',
    accent: 'education',
  },
  {
    title: '金融服务',
    description: '合规话术、风险提示、人工审核。',
    accent: 'finance',
  },
  {
    title: '政企宣传',
    description: '政策宣讲、展厅导览、服务报告。',
    accent: 'gov',
  },
];

export const capabilityTiers = [
  {
    title: 'MVP 验证版',
    scope: '内部演示、单直播间试点',
    items: ['2D 数字人播报', '知识库问答', '单平台推流', '弹幕模拟器'],
  },
  {
    title: '商用直播版',
    scope: '客户上线、多平台运营',
    items: ['声线克隆', '真实弹幕接入', '多平台转推', '报表与 SLA'],
  },
  {
    title: '投标级 3D 版',
    scope: '高质量形象定制和招投标',
    items: ['高精度 3D', '52+ 微表情', '全身动捕', '4K HDR 与检测报告'],
  },
];

export const faqs = [
  {
    question: '是否可以私有化部署？',
    answer: '可以。业务服务、AI 推理、媒体网关和数字人渲染节点都可以按客户环境拆分部署。',
  },
  {
    question: '是否支持抖音、快手、淘宝、视频号？',
    answer: '系统预留统一平台 Adapter。真实弹幕和互动能力需要按平台官方开放能力或服务商能力接入。',
  },
  {
    question: 'AI 说错了怎么办？',
    answer: '中控内置风险过滤、人工确认、打断、静音和人工接管，高风险回复默认不直接播报。',
  },
  {
    question: '能否扩展投标级 3D 数字人？',
    answer: '可以。MVP 先跑通直播闭环，后续可接 UE5、MetaHuman、动捕和第三方检测报告流程。',
  },
];

export const statusCards = [
  { label: '当前直播', value: '0', detail: '暂无进行中直播', tone: 'neutral' },
  { label: '平台连接', value: '3/4', detail: '视频号待授权', tone: 'good' },
  { label: 'AI 服务', value: '正常', detail: 'ASR / LLM / TTS 在线', tone: 'good' },
  { label: '风险待审', value: '7', detail: '建议开播前处理', tone: 'warn' },
];

export const recentTasks = [
  { title: '电商新品专场脚本', meta: 'PPT 解析完成，生成 18 个节点', state: '待预演' },
  { title: '数字人「晓岚」声线绑定', meta: '声线样本已入库', state: '可测试' },
  { title: '抖音平台推流配置', meta: 'RTMP 地址已保存，弹幕权限待确认', state: '待检查' },
  { title: '7 月运行月报', meta: '模板已生成，等待真实数据填充', state: '草稿' },
];

export const moduleDetails = Object.fromEntries(
  moduleEntries.map((entry) => [
    entry.slug,
    {
      ...entry,
      headline: `${entry.title}工作区`,
      sections: [
        `围绕「${entry.tags[0]}」建立核心操作流程，后续接入真实 API 后即可从占位页升级为生产模块。`,
        `当前阶段先完成导航、信息架构和关键状态位，便于后续逐步接入后端和实时数据。`,
        `模块将与直播 Session、数字人资产、知识库、平台 Adapter 和审计日志保持统一数据协议。`,
      ],
    },
  ]),
) as Record<string, ModuleEntry & { headline: string; sections: string[] }>;
