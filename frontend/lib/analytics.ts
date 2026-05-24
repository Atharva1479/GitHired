export type FunnelStats = {
  applied: number;
  screened: number;
  interviewed: number;
  offered: number;
  /** Integer percentage 0–100 */
  response_rate: number;
  /** Integer percentage 0–100 */
  offer_rate: number;
};

export type SourceStat = {
  source: string;
  count: number;
  /** Integer percentage 0–100 */
  response_rate: number;
};

export type WeekPoint = {
  /** ISO date string "YYYY-MM-DD", Monday-anchored week start */
  week_start: string;
  count: number;
};

export type StatusStat = {
  status: string;
  count: number;
};

export type AnalyticsStats = {
  funnel: FunnelStats;
  by_source: SourceStat[];
  weekly_trend: WeekPoint[];
  by_status: StatusStat[];
};
