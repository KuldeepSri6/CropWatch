export type Crop = "tomato" | "potato" | "maize" | "rice";

export type RiskLevel = "low" | "moderate" | "high" | "unknown";

export interface Candidate {
  disease: string;
  confidence: number;
  description: string;
}

export interface Risk {
  level: RiskLevel;
  favorable_days: number;
  window_days: number;
  reason: string;
}

export interface Advice {
  message: string;
  steps: string[];
  low_confidence: boolean;
  expert_referral: string;
}

export interface WeatherSummary {
  avg_temp_c: number;
  avg_humidity_pct: number;
  total_rain_mm: number;
}

export interface DiagnosisResult {
  id: string;
  created_at: string;
  crop: string;
  candidates: Candidate[];
  risk: Risk;
  advice: Advice;
  weather_summary: WeatherSummary;
}

export interface HistoryResponse {
  items: DiagnosisResult[];
}
