import { useEffect, useState } from "react";
import {
  Upload, Button, Table, Tag, Progress, Card, Typography,
  Space, message, Alert, Tooltip,
} from "antd";
import { InboxOutlined, ReloadOutlined, DownloadOutlined } from "@ant-design/icons";
import { uploadBatchFile, getBatchJobs, getBatchResults } from "../services/api";
import type { UploadFile } from "antd";
import dayjs from "dayjs";

const { Dragger } = Upload;
const { Title, Text } = Typography;

const STATUS_COLOR: Record<string, string> = {
  pending: "default", running: "processing", completed: "success",
  failed: "error", cancelled: "warning",
};

export default function BatchUpload() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedJob, setSelectedJob] = useState<any>(null);
  const [results, setResults] = useState<any[]>([]);

  const loadJobs = async () => {
    setJobsLoading(true);
    try {
      const data = await getBatchJobs();
      setJobs(data);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || "Не удалось загрузить задачи");
    } finally {
      setJobsLoading(false);
    }
  };

  useEffect(() => { loadJobs(); }, []);

  // Poll running jobs
  useEffect(() => {
    const running = jobs.some((j) => j.status === "running" || j.status === "pending");
    if (!running) return;
    const timer = setInterval(loadJobs, 3000);
    return () => clearInterval(timer);
  }, [jobs]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      await uploadBatchFile(file);
      message.success("Файл загружен, обработка начата");
      loadJobs();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || "Ошибка загрузки");
    } finally {
      setUploading(false);
    }
    return false; // prevent default antd upload
  };

  const handleSelectJob = async (job: any) => {
    setSelectedJob(job);
    try {
      const data = await getBatchResults(job.id);
      setResults(data.results);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || "Не удалось загрузить результаты");
      setResults([]);
    }
  };

  const jobColumns = [
    { title: "Файл",     dataIndex: "file_name", ellipsis: true },
    {
      title: "Статус", dataIndex: "status",
      render: (v: string) => <Tag color={STATUS_COLOR[v]}>{v}</Tag>,
    },
    {
      title: "Прогресс", key: "progress",
      render: (_: any, r: any) => (
        <Progress
          percent={r.total_rows ? Math.round(r.processed_rows / r.total_rows * 100) : 0}
          size="small"
          style={{ width: 120 }}
        />
      ),
    },
    { title: "Строк",   dataIndex: "total_rows" },
    { title: "Создан",  dataIndex: "created_at", render: (v: string) => dayjs(v).format("DD.MM.YYYY HH:mm") },
    {
      title: "",        key: "actions",
      render: (_: any, r: any) => (
        <Button size="small" onClick={() => handleSelectJob(r)} disabled={r.status !== "completed"}>
          Результаты
        </Button>
      ),
    },
  ];

  const resultColumns = [
    { title: "Адрес",   dataIndex: "address",   ellipsis: true },
    { title: "Скоринг", dataIndex: "score",      render: (v: number) => v?.toFixed(0) || "—" },
    {
      title: "Приоритет", dataIndex: "priority",
      render: (v: string) => {
        const c = { high: "success", medium: "warning", low: "error" }[v] || "default";
        return <Tag color={c}>{v || "—"}</Tag>;
      },
    },
    { title: "Ошибка",  dataIndex: "error_message", ellipsis: true, render: (v: string) => v || "—" },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Title level={3}>Пакетная загрузка</Title>
      <Alert
        type="info"
        message="Загрузите Excel или CSV файл с колонкой «address» или «адрес». Каждая строка будет геокодирована и оценена."
        style={{ marginBottom: 16 }}
        showIcon
      />

      <Card style={{ marginBottom: 24 }}>
        <Dragger
          accept=".xlsx,.xls,.csv"
          beforeUpload={handleUpload}
          showUploadList={false}
          disabled={uploading}
        >
          <p className="ant-upload-drag-icon"><InboxOutlined /></p>
          <p className="ant-upload-text">Перетащите файл или кликните для выбора</p>
          <p className="ant-upload-hint">Поддерживаются .xlsx, .xls, .csv</p>
        </Dragger>
      </Card>

      <Card
        title="Задачи обработки"
        extra={
          <Button icon={<ReloadOutlined />} onClick={loadJobs} loading={jobsLoading} size="small">
            Обновить
          </Button>
        }
        style={{ marginBottom: 24 }}
      >
        <Table
          columns={jobColumns}
          dataSource={jobs}
          rowKey="id"
          loading={jobsLoading}
          size="small"
          pagination={false}
        />
      </Card>

      {selectedJob && (
        <Card title={`Результаты: ${selectedJob.file_name}`}>
          <Table
            columns={resultColumns}
            dataSource={results}
            rowKey="id"
            size="small"
            pagination={{ pageSize: 50 }}
            scroll={{ x: 700 }}
          />
        </Card>
      )}
    </div>
  );
}
