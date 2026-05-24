import { AppShell } from "@/components/layout/AppShell";
import ReportView from "@/components/interview/ReportView";

export default async function InterviewReportPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <AppShell>
      <ReportView sessionId={Number(id)} />
    </AppShell>
  );
}
