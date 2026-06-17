import { useState, useEffect, useCallback } from "react";
import {
  Typography, Card, Table, Button, Tag, Space, Tooltip,
  message, Spin, Empty,
} from "antd";
import {
  FileTextOutlined, DownloadOutlined, ReloadOutlined, FilePdfOutlined,
} from "@ant-design/icons";
import { getLocations, generateReport, downloadReportUrl } from "../services/api";

const { Title } = Typography;

interface LocationRow {
  id: number;
  address: string;
  name: string | null;
  status: string;
  reportStatus?: "idle" | "generating" | "ready" | "error";
}

const STATUS_LABEL: Record<string, { text: string; color: string }> = {
  draft:     { text: "Черновик",   color: "default"  },
  in_review: { text: "На проверке", color: "processing" },
  approved:  { text: "Одобрен",    color: "success"  },
  rejected:  { text: "Отклонён",   color: "error"    },
};

export default function Reports() {
  const [locations, setLocations] = useState<LocationRow[]>([]);
  const [loading, setLoading]     = useState(false);
  const [genStatus, setGenStatus] = useState<Record<number, "idle" | "generating" | "ready" | "error">>({});

  const fetchLocations = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getLocations({ page_size: 100 });
      setLocations((data.items || data) as LocationRow[]);
    } catch {
      message.error("Не удалось загрузить список объектов");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchLocations(); }, [fetchLocations]);

  const handleGenerate = async (id: number) => {
    setGenStatus((s) => ({ ...s, [id]: "generating" }));
    try {
      await generateReport(id);
      // In stub mode the report is instantly "ready"
      setGenStatus((s) => ({ ...s, [id]: "ready" }));
      message.success("PDF-отчёт сформирован");
    } catch {
      setGenStatus((s) => ({ ...s, [id]: "error" }));
      message.error("Ошибка генерации отчёта");
    }
  };

  const handleDownload = (id: number) => {
    const url = downloadReportUrl(id);
    window.open(url, "_blank");
  };

  const columns = [
    {
      title: "ID",
      dataIndex: "id",
      width: 60,
    },
    {
      title: "Адрес / Название",
      dataIndex: "address",
      render: (addr: string, row: LocationRow) => (
        <div>
          <div style={{ fontWeight: 500 }}>{row.name || addr}</div>
          {row.name && <div style={{ color: "#888", fontSize: 12 }}>{addr}</div>}
        </div>
      ),
    },
    {
      title: "Статус объекта",
      dataIndex: "status",
      width: 140,
      render: (s: string) => {
        const info = STATUS_LABEL[s] || { text: s, color: "default" };
        return <Tag color={info.color}>{info.text}</Tag>;
      },
    },
    {
      title: "PDF-отчёт",
      width: 220,
      render: (_: any, row: LocationRow) => {
        const st = genStatus[row.id] || "idle";
        return (
          <Space>
            {st === "generating" ? (
              <Button icon={<Spin size="small" />} disabled>
                Генерируется…
              </Button>
            ) : (
              <Tooltip title="Сгенерировать PDF-отчёт по объекту">
                <Button
                  icon={<FilePdfOutlined />}
                  onClick={() => handleGenerate(row.id)}
                  type={st === "ready" ? "default" : "primary"}
                  ghost={st === "ready"}
                >
                  {st === "ready" ? "Обновить" : "Сформировать"}
                </Button>
              </Tooltip>
            )}
            {st === "ready" && (
              <Tooltip title="Скачать PDF">
                <Button
                  icon={<DownloadOutlined />}
                  type="link"
                  onClick={() => handleDownload(row.id)}
                >
                  Скачать
                </Button>
              </Tooltip>
            )}
            {st === "error" && (
              <Tag color="error">Ошибка</Tag>
            )}
          </Space>
        );
      },
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>
          <FileTextOutlined style={{ marginRight: 8 }} />
          Отчёты
        </Title>
        <Button icon={<ReloadOutlined />} onClick={fetchLocations} loading={loading}>
          Обновить
        </Button>
      </div>

      <Card>
        {loading ? (
          <div style={{ textAlign: "center", padding: 48 }}><Spin size="large" /></div>
        ) : locations.length === 0 ? (
          <Empty description="Нет объектов для генерации отчётов" />
        ) : (
          <Table
            dataSource={locations}
            columns={columns}
            rowKey="id"
            pagination={{ pageSize: 20 }}
            size="middle"
          />
        )}
      </Card>
    </div>
  );
}
