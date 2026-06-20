import { Steps, Progress, Alert, Button, Space } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import type { AnalysisJob } from "../../services/api";

const STAGES = [
  { key: "geocoding", title: "Геокодирование" },
  { key: "routing", title: "Изохроны" },
  { key: "collecting", title: "Сбор данных" },
  { key: "scoring", title: "Скоринг" },
  { key: "completed", title: "Готово" },
];

function currentStep(status: string): number {
  const idx = STAGES.findIndex((s) => s.key === status);
  if (status === "queued") return 0;
  if (status === "completed") return STAGES.length - 1;
  return idx >= 0 ? idx : 0;
}

interface Props {
  job: AnalysisJob | null;
  error?: string | null;
  onRetry?: () => void;
}

export default function JobProgress({ job, error, onRetry }: Props) {
  if (error) {
    return (
      <Alert
        type="error"
        message="Ошибка анализа"
        description={error}
        action={onRetry && <Button size="small" icon={<ReloadOutlined />} onClick={onRetry}>Повторить</Button>}
        showIcon
      />
    );
  }
  if (!job) return <Progress percent={0} status="active" />;

  if (job.status === "failed") {
    return (
      <Alert
        type="error"
        message="Анализ не удался"
        description={job.error_message || "Неизвестная ошибка"}
        action={onRetry && <Button size="small" icon={<ReloadOutlined />} onClick={onRetry}>Повторить</Button>}
        showIcon
      />
    );
  }

  const failed = job.status === "failed";
  return (
    <Space direction="vertical" style={{ width: "100%" }} size="middle">
      <Steps
        size="small"
        current={currentStep(job.status)}
        status={failed ? "error" : job.status === "completed" ? "finish" : "process"}
        items={STAGES.map((s) => ({ title: s.title }))}
      />
      <Progress
        percent={job.progress_pct}
        status={job.status === "completed" ? "success" : "active"}
      />
    </Space>
  );
}
