import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Card, Tabs, Descriptions, Tag, Button, Space, Spin, Empty, message,
  Typography, Table, Modal, Input,
} from "antd";
import {
  CheckOutlined, CloseOutlined, ReloadOutlined, ArrowLeftOutlined, ThunderboltOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import {
  getLocation, updateLocationStatus, listAnalysisJobs, startAnalysis,
} from "../services/api";
import { useJobProgress } from "../hooks/useJobProgress";
import JobProgress from "../components/Analysis/JobProgress";
import AnalysisResultView from "../components/Analysis/AnalysisResultView";

const { Title } = Typography;

const STATUS_COLOR: Record<string, string> = {
  draft: "default", in_review: "processing", approved: "success", rejected: "error", opened: "success",
};
const STATUS_LABEL: Record<string, string> = {
  draft: "Черновик", in_review: "На рассмотрении", approved: "Одобрен", rejected: "Отклонён", opened: "Открыт",
};

export default function LocationDetail() {
  const { id } = useParams();
  const locId = Number(id);
  const navigate = useNavigate();

  const [loc, setLoc] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [jobs, setJobs] = useState<any[]>([]);
  const [jobId, setJobId] = useState<number | null>(null);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectComment, setRejectComment] = useState("");

  const { job } = useJobProgress(jobId);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [l, j] = await Promise.all([
        getLocation(locId),
        listAnalysisJobs({ location_id: locId }).catch(() => ({ items: [] })),
      ]);
      setLoc(l);
      setJobs(j.items || []);
    } catch {
      message.error("Не удалось загрузить объект");
    } finally {
      setLoading(false);
    }
  }, [locId]);

  useEffect(() => { load(); }, [load]);

  const changeStatus = async (status: string, comment?: string) => {
    try {
      const updated = await updateLocationStatus(locId, status, comment);
      setLoc(updated);
      message.success(`Статус изменён: ${STATUS_LABEL[status] || status}`);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Не удалось изменить статус");
    }
  };

  const runAnalysis = async () => {
    if (!loc?.address) return;
    try {
      const created = await startAnalysis({ address: loc.address, location_id: locId, include_huff: true });
      setJobId(created.id);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Не удалось запустить анализ");
    }
  };

  if (loading) return <div style={{ padding: 48, textAlign: "center" }}><Spin size="large" /></div>;
  if (!loc) return <Empty description="Объект не найден" style={{ marginTop: 80 }} />;

  const status = loc.status as string;
  const latestResult = job?.result || jobs.find((j) => j.result)?.result;

  const statusActions = (
    <Space>
      {status === "draft" && (
        <Button icon={<CheckOutlined />} onClick={() => changeStatus("in_review")}>На рассмотрение</Button>
      )}
      {status === "in_review" && (
        <>
          <Button type="primary" icon={<CheckOutlined />} onClick={() => changeStatus("approved")}>Одобрить</Button>
          <Button danger icon={<CloseOutlined />} onClick={() => setRejectOpen(true)}>Отклонить</Button>
        </>
      )}
      {status === "rejected" && (
        <Button icon={<ReloadOutlined />} onClick={() => changeStatus("draft")}>Вернуть в черновик</Button>
      )}
    </Space>
  );

  return (
    <div style={{ padding: 24 }}>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/locations")}>Назад</Button>
      </Space>

      <Card
        title={<Space><Title level={4} style={{ margin: 0 }}>{loc.name || loc.address}</Title><Tag color={STATUS_COLOR[status]}>{STATUS_LABEL[status] || status}</Tag></Space>}
        extra={statusActions}
      >
        <Tabs
          defaultActiveKey="overview"
          items={[
            {
              key: "overview",
              label: "Обзор",
              children: (
                <Descriptions bordered column={2} size="small">
                  <Descriptions.Item label="Адрес" span={2}>{loc.address}</Descriptions.Item>
                  <Descriptions.Item label="Название">{loc.name || "—"}</Descriptions.Item>
                  <Descriptions.Item label="Площадь">{loc.area_sqm ? `${loc.area_sqm} м²` : "—"}</Descriptions.Item>
                  <Descriptions.Item label="Парковка">{loc.parking_spaces ?? "—"}</Descriptions.Item>
                  <Descriptions.Item label="Этаж">{loc.floor_number ?? "—"}</Descriptions.Item>
                  <Descriptions.Item label="Видимость">{loc.visibility_score ?? "—"}</Descriptions.Item>
                  <Descriptions.Item label="Создан">{loc.created_at ? dayjs(loc.created_at).format("DD.MM.YYYY") : "—"}</Descriptions.Item>
                  <Descriptions.Item label="Заметки" span={2}>{loc.notes || "—"}</Descriptions.Item>
                </Descriptions>
              ),
            },
            {
              key: "analysis",
              label: "Анализ",
              children: (
                <div>
                  <Space style={{ marginBottom: 16 }}>
                    <Button type="primary" icon={<ThunderboltOutlined />} onClick={runAnalysis} disabled={!!jobId && job?.status !== "completed" && job?.status !== "failed"}>
                      Запустить анализ
                    </Button>
                  </Space>
                  {jobId && <div style={{ marginBottom: 16 }}><JobProgress job={job} /></div>}
                  {latestResult ? (
                    <AnalysisResultView result={latestResult} />
                  ) : (
                    <Empty description="Анализ ещё не выполнялся" />
                  )}
                </div>
              ),
            },
            {
              key: "history",
              label: `История (${jobs.length})`,
              children: (
                <Table
                  dataSource={jobs}
                  rowKey="id"
                  size="small"
                  pagination={{ pageSize: 10 }}
                  columns={[
                    { title: "#", dataIndex: "id", width: 60 },
                    { title: "Статус", dataIndex: "status", render: (v) => <Tag>{v}</Tag> },
                    { title: "Этап", dataIndex: "current_stage", render: (v) => v || "—" },
                    { title: "Балл", key: "score", render: (_, r: any) => r.result?.scoring?.total_score?.toFixed(0) ?? "—" },
                    { title: "Создан", dataIndex: "created_at", render: (v) => v ? dayjs(v).format("DD.MM HH:mm") : "—" },
                  ]}
                  locale={{ emptyText: <Empty description="Нет запусков анализа" /> }}
                />
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title="Отклонить объект"
        open={rejectOpen}
        onOk={() => { changeStatus("rejected", rejectComment); setRejectOpen(false); setRejectComment(""); }}
        onCancel={() => setRejectOpen(false)}
        okText="Отклонить"
        okButtonProps={{ danger: true }}
        cancelText="Отмена"
      >
        <Input.TextArea
          rows={3}
          placeholder="Причина отклонения (необязательно)"
          value={rejectComment}
          onChange={(e) => setRejectComment(e.target.value)}
        />
      </Modal>
    </div>
  );
}
