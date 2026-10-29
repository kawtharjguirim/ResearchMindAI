import type { IconName } from "@/components/icons";

export type DemoType = "pdf" | "web" | "figure" | "video" | "notes" | "personal";

export const FEATURES: [IconName, string, string][] = [
  ["layers", "Multimodal import", "PDFs, web pages, images, YouTube videos and personal documents gathered in a single project."],
  ["shield", "Evidence-backed answers", "Every answer cites its source: page, figure or video timestamp."],
  ["search", "Hybrid search", "BM25, semantic search and reranking to retrieve the most relevant passages."],
  ["target", "Research Twin", "A structured, evolving view of your project: question, hypotheses, methods, results."],
  ["network", "Knowledge Graph", "Papers, methods, datasets and results linked in a navigable graph."],
  ["bar", "A model that is measured, not assumed", "The search engine is chosen through experiments: baselines, ML, Deep Learning, fine-tuning."],
];

export type SourceTab = {
  label: string;
  icon: IconName;
  title: string;
  description: string;
  cta: string;
  question: string;
  answer: string;
  pill: [DemoType, string];
};

export const SOURCE_TABS: Record<"pdf" | "web" | "figure" | "video" | "personal", SourceTab> = {
  pdf: {
    label: "PDF documents",
    icon: "pdf",
    title: "Query your papers",
    description: "Text and structure are extracted (abstract, methods, results). Every answer points to the exact page.",
    cta: "Import a source",
    question: "What data is the model trained on?",
    answer: "On EyePACS, with five severity levels.",
    pill: ["pdf", "Benali et al. · p. 4"],
  },
  web: {
    label: "Web pages",
    icon: "web",
    title: "Add a page with a single link",
    description: "Paste a URL: the useful content is extracted cleanly, and the source and date stay attached to every passage.",
    cta: "Add a URL",
    question: "What are the criteria for the moderate grade?",
    answer: "Microaneurysms combined with other lesions, without signs of the severe form.",
    pill: ["web", "Grading criteria · §2"],
  },
  figure: {
    label: "Figures",
    icon: "figure",
    title: "Make your charts talk",
    description: "OCR and visual analysis of figures and tables: a question about a curve gets an answer that cites the figure.",
    cta: "Import a figure",
    question: "What does figure 3 show?",
    answer: "AUC is lower on APTOS 2019 than on EyePACS: the model generalizes less well.",
    pill: ["figure", "Fig. 3 · ROC curves"],
  },
  video: {
    label: "Videos",
    icon: "video",
    title: "Find the right moment in a talk",
    description: "Timestamped transcription: every answer points to the second where the speaker covers the topic.",
    cta: "Add a video",
    question: "When is the method explained?",
    answer: "From 12:20, in the Methodology part of the talk.",
    pill: ["video", "Talk · 12:20"],
  },
  personal: {
    label: "Personal documents",
    icon: "notes",
    title: "Your notes, isolated and protected",
    description: "Private indexing: your notes and protocols are visible and searchable only by you.",
    cta: "Import a document",
    question: "What did we decide about external validation?",
    answer: "Use APTOS 2019 as an external test set, without retraining.",
    pill: ["personal", "Meeting notes · March 12"],
  },
};

export const PROFILES: [string, string, string, string][] = [
  ["PhD", "PhD student", "Follow a thesis over three years", "Link every new paper to your hypotheses, without losing what you read in your first year."],
  ["MS", "Master's student", "Structure a thesis", "Go from a pile of PDFs to a clear research question and a fully sourced literature review."],
  ["LR", "Lecturer-researcher", "Compare work quickly", "Put methods, datasets and results from several papers side by side before a committee."],
  ["RD", "R&D engineer", "Map the state of the art of a technology", "Cross-check papers, video talks and web documentation around a technical problem."],
];

export type Plan = {
  name: string;
  monthly: number | null;
  yearly: number | null;
  description: string;
  cta: string;
  style: "outline" | "gradient" | "dark";
  popular?: boolean;
  features: string[];
};

export const PLANS: Plan[] = [
  {
    name: "Student",
    monthly: 0,
    yearly: 0,
    description: "Discover the platform on a first project.",
    cta: "Start for free",
    style: "outline",
    features: ["1 project", "Limited sources", "Q&A with citations", "Hybrid search"],
  },
  {
    name: "Researcher",
    monthly: 15,
    yearly: 144,
    description: "Run your research day to day.",
    cta: "Choose Researcher",
    style: "gradient",
    popular: true,
    features: ["Unlimited projects", "Every multimodal source", "Research Twin", "Project Knowledge Graph"],
  },
  {
    name: "Lab",
    monthly: 40,
    yearly: 384,
    description: "For a team that shares its literature.",
    cta: "Choose Lab",
    style: "dark",
    features: ["Team workspace", "Shared Knowledge Graph", "Priority processing", "Everything in Researcher"],
  },
  {
    name: "Institution",
    monthly: null,
    yearly: null,
    description: "For a university or a research center.",
    cta: "Contact us",
    style: "dark",
    features: ["Dedicated deployment", "Access management", "Onboarding support", "Custom quote"],
  },
];

export const FAQ: [string, string][] = [
  [
    "What types of sources can I import?",
    "Scientific papers and PDF documents, web pages, images and scientific figures, YouTube videos (talks, lectures, webinars) and your personal documents. Audio sources are planned for a later version.",
  ],
  [
    "How are answers verified?",
    "Every answer is built only from passages retrieved in your sources. A verification step checks that each claim is linked to a passage, and the interface shows how many claims are sourced. Without evidence, the assistant says so instead of making things up.",
  ],
  [
    "Are my personal documents private?",
    "Yes. Each user's data is isolated: nobody else can see it or find it in their searches. Your documents are never used to train a model without your consent.",
  ],
  [
    "What is the Research Twin?",
    "A structured, evolving view of your project: question, problem statement, objectives, hypotheses, methods, results, limitations and research gaps. The AI suggests updates from your sources, and you decide whether to accept them.",
  ],
  [
    "How is it different from a chatbot or NotebookLM?",
    "ResearchMind AI cites the figure or the video timestamp, not just text. Its search engine is chosen through measured experiments, and it links your reading to your own project through the Research Twin and the Knowledge Graph.",
  ],
  [
    "Which languages can I ask questions in?",
    "English or French, including on sources written in the other language. The assistant answers in the language of the question.",
  ],
];

export const DEMO_SOURCES: [DemoType, string][] = [
  ["pdf", "Benali et al. (2023)"],
  ["pdf", "Ortega & Lin (2022)"],
  ["video", "Conference talk"],
  ["figure", "Fig. 3"],
  ["web", "ICDR grading criteria"],
  ["notes", "Team meeting notes"],
];

export const DEMO_QUESTION = "Which dataset is used, and does the model generalize?";

const sup = (n: number) => `<sup class="ml-px text-[11px] font-semibold text-primary-500">[${n}]</sup>`;
const strong = (t: string) => `<b class="font-semibold text-gray-800 dark:text-white">${t}</b>`;

// Static, trusted HTML fragments typed word by word into the demo answer.
export const DEMO_TOKENS = [
  "The", "model", "is", "trained", "on", `${strong("EyePACS")}${sup(1)},`, "then", "evaluated", "without",
  "retraining", "on", `${strong("APTOS 2019")}${sup(2)}.`, "Performance", "drops", "on", "this", "external", `set${sup(3)}.`,
];

export const DEMO_PILLS: [DemoType, string][] = [
  ["pdf", "Benali et al. · p. 4"],
  ["pdf", "p. 6"],
  ["figure", "Fig. 3"],
];

export const TYPE_COLOR: Record<DemoType, string> = {
  pdf: "text-error-500 bg-error-50 dark:bg-error-500/15",
  web: "text-[#4E6EFF] bg-[#EEF2FF] dark:bg-[#4E6EFF]/15",
  figure: "text-success-600 bg-success-50 dark:bg-success-600/15",
  video: "text-error-500 bg-error-50 dark:bg-error-500/15",
  notes: "text-primary-600 bg-primary-50 dark:bg-primary-500/15 dark:text-primary-300",
  personal: "text-primary-600 bg-primary-50 dark:bg-primary-500/15 dark:text-primary-300",
};

export const typeIcon = (t: DemoType): IconName => (t === "personal" ? "notes" : t);
