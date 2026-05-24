export type DashboardStats = {
  applications: {
    total: number;
    applied: number;
    in_progress: number;
    offers: number;
    response_rate: number;
  };
  referrals: {
    total: number;
    in_progress: number;
    referred: number;
    conversion_rate: number;
  };
  nudges: {
    today: number;
    overdue: number;
  };
};

export type ActivityItem = {
  id: number;
  event_type: string;
  payload: Record<string, unknown>;
  occurred_at: string;
};
