import { useEffect, useState } from "react";
import { Card, Row, Col, Statistic, Typography, List, Tag, Spin } from "antd";
import {
  EnvironmentOutlined, CheckCircleOutlined,
  ClockCircleOutlined, RiseOutlined,
} from "@ant-design/icons";
import { useAppDispatch, useAppSelector } from "../hooks/redux";
import { fetchLocations } from "../store/locationSlice";
import { useNavigate } from "react-router-dom";

const { Title } = Typography;

function statusColor(status: string) {
  const map: Record<string, string> = {
    draft: "default", in_review: "processing", approved: "success", rejected: "error", opened: "success",
  };
  return map[status] || "default";
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    draft: "Черновик", in_review: "На рассмотрении", approved: "Одобрен",
    rejected: "Отклонён", opened: "Открыт",
  };
  return map[status] || status;
}

export default function Dashboard() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { items, total, loading } = useAppSelector((s) => s.locations);

  useEffect(() => { dispatch(fetchLocations({})); }, [dispatch]);

  const approved = items.filter((l) => l.status === "approved").length;
  const inReview = items.filter((l) => l.status === "in_review").length;

  return (
    <div style={{ padding: 24 }}>
      <Title level={3} style={{ marginBottom: 24 }}>Дашборд</Title>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="Всего объектов" value={total} prefix={<EnvironmentOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="Одобрено" value={approved} prefix={<CheckCircleOutlined style={{ color: "#27ae60" }} />} valueStyle={{ color: "#27ae60" }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="На рассмотрении" value={inReview} prefix={<ClockCircleOutlined style={{ color: "#f39c12" }} />} valueStyle={{ color: "#f39c12" }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="Ср. скоринг" value={
              items.length
                ? Math.round(items.reduce((a, b) => a + (b.total_score || 0), 0) / items.length)
                : "—"
            } suffix="/100" prefix={<RiseOutlined />} />
          </Card>
        </Col>
      </Row>

      <Card title="Последние объекты" extra={<a onClick={() => navigate("/locations")}>Все объекты</a>}>
        {loading ? <Spin /> : (
          <List
            dataSource={items.slice(0, 8)}
            renderItem={(item) => (
              <List.Item
                style={{ cursor: "pointer" }}
                onClick={() => navigate("/locations")}
                extra={<Tag color={statusColor(item.status)}>{statusLabel(item.status)}</Tag>}
              >
                <List.Item.Meta
                  title={item.name || item.address}
                  description={item.area_sqm ? `${item.area_sqm} м²` : "Площадь не указана"}
                />
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  );
}
