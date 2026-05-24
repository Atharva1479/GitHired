export type ConnectionStatus =
  | "Request Sent"
  | "Accepted"
  | "Msg Sent"
  | "Replied"
  | "Referred"
  | "Dropped";

export type Outcome = "Referred" | "NoResponse" | "Declined";

export const CONNECTION_STATUSES: ConnectionStatus[] = [
  "Request Sent",
  "Accepted",
  "Msg Sent",
  "Replied",
  "Referred",
  "Dropped",
];

export const CONN_STATUS_META: Record<
  ConnectionStatus,
  { label: string; chip: string; dot: string; columnAccent: string }
> = {
  "Request Sent": {
    label: "Request Sent",
    chip: "bg-blue-50 text-blue-700 ring-1 ring-blue-200",
    dot: "bg-blue-500",
    columnAccent: "bg-blue-500",
  },
  Accepted: {
    label: "Accepted",
    chip: "bg-violet-50 text-violet-700 ring-1 ring-violet-200",
    dot: "bg-violet-500",
    columnAccent: "bg-violet-500",
  },
  "Msg Sent": {
    label: "Msg Sent",
    chip: "bg-amber-50 text-amber-800 ring-1 ring-amber-200",
    dot: "bg-amber-500",
    columnAccent: "bg-amber-500",
  },
  Replied: {
    label: "Replied",
    chip: "bg-cyan-50 text-cyan-700 ring-1 ring-cyan-200",
    dot: "bg-cyan-500",
    columnAccent: "bg-cyan-500",
  },
  Referred: {
    label: "Referred",
    chip: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200",
    dot: "bg-emerald-500",
    columnAccent: "bg-emerald-500",
  },
  Dropped: {
    label: "Dropped",
    chip: "bg-gray-100 text-gray-700 ring-1 ring-gray-300",
    dot: "bg-gray-400",
    columnAccent: "bg-gray-400",
  },
};

export type Referral = {
  id: number;
  name: string;
  company: string;
  target_role: string;
  role_at_company: string | null;
  linkedin_url: string | null;
  mutual_context: string | null;
  connection_sent_date: string;
  connection_status: ConnectionStatus;
  referral_msg_sent_date: string | null;
  reply_date: string | null;
  outcome: Outcome | null;
  notes: string | null;
  last_updated: string;
  created_at: string;
};

export type ReferralCreate = {
  name: string;
  company: string;
  target_role: string;
  connection_sent_date: string;
  role_at_company?: string | null;
  linkedin_url?: string | null;
  mutual_context?: string | null;
  notes?: string | null;
};

export type ReferralUpdate = Partial<{
  name: string;
  company: string;
  target_role: string;
  role_at_company: string | null;
  linkedin_url: string | null;
  mutual_context: string | null;
  connection_status: ConnectionStatus;
  referral_msg_sent_date: string | null;
  reply_date: string | null;
  outcome: Outcome | null;
  notes: string | null;
}>;
