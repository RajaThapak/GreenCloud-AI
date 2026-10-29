// src/data/fakeData.js
// ─────────────────────────────────────────────────────────
// All fake/static data that powers the UI without a backend
// ─────────────────────────────────────────────────────────

export const REGIONS = [
  "us-east-1", "us-east-2", "eu-north-1",
  "eu-west-1", "ca-central-1", "ap-south-1",
];

export const INSTANCE_TYPES = [
  "t3.large", "m5.xlarge", "c5.2xlarge", "r5.xlarge", "g5.xlarge",
];

export const GPU_OPTIONS = [
  "1x A10G", "2x A10G", "1x A100", "2x A100", "4x A100",
];

export const carbonIntensity = [
  { region: "eu-north-1",   value: 28,  label: "eu-north-1",   pct: 4  },
  { region: "ca-central-1", value: 120, label: "ca-central-1", pct: 19 },
  { region: "eu-west-1",    value: 290, label: "eu-west-1",    pct: 45 },
  { region: "us-east-1",    value: 380, label: "us-east-1",    pct: 59 },
  { region: "ap-south-1",   value: 640, label: "ap-south-1",   pct: 100 },
];

export const costOverTime = [
  { month: "May", onDemand: 3200, withGC: 1900 },
  { month: "Jun", onDemand: 3800, withGC: 2200 },
  { month: "Jul", onDemand: 3500, withGC: 2000 },
  { month: "Aug", onDemand: 4100, withGC: 2400 },
  { month: "Sep", onDemand: 4600, withGC: 2700 },
  { month: "Oct", onDemand: 4900, withGC: 2481 },
];

export const recentWorkloads = [
  {
    id: 1,
    name: "BERT fine-tune",
    mode: "Balanced",
    status: "running",
    region: "eu-north-1",
    estCost: 7.20,
    actCost: null,
    gpu: "1x A10G",
    duration: 6,
    startTime: "2026-10-26T02:00:00Z",
    deadline: "2026-10-26T18:00:00Z",
  },
  {
    id: 2,
    name: "Nightly ETL",
    mode: "Cost",
    status: "awaiting",
    region: "us-east-2",
    estCost: 3.10,
    actCost: null,
    gpu: "t3.large",
    duration: 2,
    startTime: null,
    deadline: "2026-10-27T06:00:00Z",
  },
  {
    id: 3,
    name: "Render batch 14",
    mode: "Carbon",
    status: "completed",
    region: "ca-central-1",
    estCost: 12.10,
    actCost: 12.40,
    gpu: "1x A100",
    duration: 4,
    startTime: "2026-10-25T22:00:00Z",
    deadline: "2026-10-26T10:00:00Z",
  },
  {
    id: 4,
    name: "Genome align",
    mode: "Cost",
    status: "recovered",
    region: "us-west-2",
    estCost: 5.80,
    actCost: 6.35,
    gpu: "c5.2xlarge",
    duration: 8,
    startTime: "2026-10-25T18:00:00Z",
    deadline: "2026-10-26T04:00:00Z",
  },
  {
    id: 5,
    name: "ResNet training",
    mode: "Balanced",
    status: "running",
    region: "eu-north-1",
    estCost: 9.40,
    actCost: null,
    gpu: "2x A10G",
    duration: 10,
    startTime: "2026-10-26T00:00:00Z",
    deadline: "2026-10-26T14:00:00Z",
  },
  {
    id: 6,
    name: "Log aggregation",
    mode: "Cost",
    status: "completed",
    region: "us-east-1",
    estCost: 1.80,
    actCost: 1.72,
    gpu: "t3.large",
    duration: 1,
    startTime: "2026-10-25T10:00:00Z",
    deadline: "2026-10-25T14:00:00Z",
  },
];

export const dashboardStats = {
  costSaved: 2418,
  costSavedPct: 34,
  carbonAvoided: 182,
  carbonAvoidedPct: 41,
  deadlineCompliance: 98.6,
  complianceOf: "142 of 144 jobs",
  activeWorkloads: 7,
  awaitingApproval: 2,
};

// Spot price comparison for recommended plan
export const recommendedPlan = {
  region: "eu-north-1",
  instance: "g5.xlarge Spot",
  startTime: "Tue 02:00",
  interruptionRisk: "Low",
  estCost: 7.20,
  onDemandCost: 11.80,
  estCarbon: 6.1,
  runNowCarbon: 14.3,
  finishBy: "Tue 08:30",
  deadline: "Tue 18:00",
  sparehours: 9,
  reasons: [
    "Spot prices in eu-north-1 usually dip overnight, about 62% below on-demand.",
    "Grid carbon there is the lowest of the regions that can fit your GPU.",
    "Starting at 02:00 leaves time for one retry if the instance is interrupted.",
  ],
  alternatives: [
    { label: "us-east-2 · Tue 03:00", cost: 6.40, carbon: 11.9 },
    { label: "ca-central-1 · Mon 23:00", cost: 8.10, carbon: 7.4 },
  ],
};

export const spotPriceHistory = [
  { time: "00:00", "eu-north-1": 1.82, "us-east-1": 2.10, "ca-central-1": 2.05 },
  { time: "02:00", "eu-north-1": 1.65, "us-east-1": 2.08, "ca-central-1": 2.10 },
  { time: "04:00", "eu-north-1": 1.55, "us-east-1": 1.95, "ca-central-1": 2.00 },
  { time: "06:00", "eu-north-1": 1.60, "us-east-1": 2.00, "ca-central-1": 2.12 },
  { time: "08:00", "eu-north-1": 1.90, "us-east-1": 2.20, "ca-central-1": 2.30 },
  { time: "10:00", "eu-north-1": 2.10, "us-east-1": 2.40, "ca-central-1": 2.50 },
  { time: "12:00", "eu-north-1": 2.20, "us-east-1": 2.50, "ca-central-1": 2.60 },
];

export const carbonTrend = [
  { time: "Mon", "eu-north-1": 22, "ca-central-1": 115, "eu-west-1": 310 },
  { time: "Tue", "eu-north-1": 28, "ca-central-1": 120, "eu-west-1": 290 },
  { time: "Wed", "eu-north-1": 18, "ca-central-1": 108, "eu-west-1": 275 },
  { time: "Thu", "eu-north-1": 30, "ca-central-1": 130, "eu-west-1": 320 },
  { time: "Fri", "eu-north-1": 25, "ca-central-1": 122, "eu-west-1": 300 },
  { time: "Sat", "eu-north-1": 20, "ca-central-1": 110, "eu-west-1": 280 },
  { time: "Sun", "eu-north-1": 15, "ca-central-1": 105, "eu-west-1": 265 },
];
