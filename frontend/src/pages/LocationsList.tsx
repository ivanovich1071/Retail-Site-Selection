import { useEffect } from "react";
import { Table, Tag, Button, Select, Space, Typography, Popconfirm, message, Tooltip } from "antd";
import { DeleteOutlined, EyeOutlined, FileTextOutlined } from "@ant-design/icons";
import { useAppDispatch, useAppSelector } from "../hooks/redux";
import { fetchLocations, deleteLocation, setPage } from "../store/locationSlice";
import { generateReport } from "../services/api";
import dayjs from "dayjs";

const { Title } = Typography;

const STATUS_OPTIONS = [
  { label: "Все", value: "" },
  { label: "Черновик", value: "draft" },
  { label: "На рассмотрении", value: "in_review" },
  { label: "Одобрен", value: "approved" },
  { label: "Отклонён", value: "rejected" },
];

const STATUS_COLOR: Record<string, string> = {
  draft: "default", in_review: "processing", approved: "success",
  rejected: "error", opened: "success",
};

export default function LocationsList() {
  const dispatch = useAppDispatch();
  const { items, total, page, loading } = useAppSelector((s) => s.locations);

  useEffect(() => { dispatch(fetchLocations({ page })); }, [dispatch, page]);

  const handleDelete = async (id: number) => {
    await dispatch(deleteLocation(id));
    message.success("Объект удалён");
  };

  const handleReport = async (id: number) => {
    try {
      await generateReport(id);
      message.success("Генерация отчёта запущена, перейдите в раздел Отчёты");
    } catch {
      message.error("Ошибка запуска генерации");
    }
  };

  const columns = [
    { title: "ID",     dataIndex: "id",      width: 60 },
    { title: "Адрес",  dataIndex: "address", ellipsis: true },
    { title: "Название", dataIndex: "name",  ellipsis: true, render: (v: string) => v || "—" },
    { title: "Площадь", dataIndex: "area_sqm", render: (v: number) => v ? `${v} м²` : "—" },
    {
      title: "Статус", dataIndex: "status",
      render: (v: string) => <Tag color={STATUS_COLOR[v] || "default"}>{v}</Tag>,
    },
    {
      title: "Создан", dataIndex: "created_at",
      render: (v: string) => dayjs(v).format("DD.MM.YYYY"),
    },
    {
      title: "Действия", key: "actions",
      render: (_: any, record: any) => (
        <Space>
          <Tooltip title="Генерировать отчёт">
            <Button icon={<FileTextOutlined />} size="small" onClick={() => handleReport(record.id)} />
          </Tooltip>
          <Popconfirm title="Удалить объект?" onConfirm={() => handleDelete(record.id)} okText="Да" cancelText="Нет">
            <Button icon={<DeleteOutlined />} size="small" danger />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>Объекты</Title>
        <Select
          defaultValue=""
          options={STATUS_OPTIONS}
          style={{ width: 180 }}
          onChange={(v) => dispatch(fetchLocations({ status: v || undefined }))}
        />
      </div>

      <Table
        columns={columns}
        dataSource={items}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          pageSize: 20,
          total,
          onChange: (p) => dispatch(setPage(p)),
        }}
        size="middle"
        scroll={{ x: 900 }}
      />
    </div>
  );
}
