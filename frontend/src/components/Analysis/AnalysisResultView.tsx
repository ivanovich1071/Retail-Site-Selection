import { Row, Col, Statistic, Progress, Tag, Table, Typography, Divider } from "antd";
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer } from "recharts";

const { Title, Text } = Typography;

export function scoreColor(score: number) {
  if (score >= 70) return "#27ae60";
  if (score >= 45) return "#f39c12";
  return "#e74c3c";
}

export function scoreLabel(score: number) {
  if (score >= 70) return "Высокий";
  if (score >= 45) return "Средний";
  return "Низкий";
}

const competitorColumns = [
  { title: "Бренд", dataIndex: "brand_name", key: "brand" },
  { title: "Расст., м", dataIndex: "distance_m", key: "dist", render: (v: number) => (v ? Math.round(v) : "—") },
];

export default function AnalysisResultView({ result }: { result: any }) {
  if (!result) return null;
  const s = result.scoring || {};
  const total = s.total_score || 0;

  const radarData = [
    { label: "Демография", value: s.score_demographics },
    { label: "Конкуренты", value: s.score_competitors },
    { label: "Доступность", value: s.score_accessibility },
    { label: "Видимость", value: s.score_visibility },
    { label: "Локация", value: s.score_location },
  ];

  return (
    <div>
      <Text type="secondary">{result.address}</Text>
      <Divider />

      <Row gutter={24} align="middle">
        <Col xs={24} sm={8} style={{ textAlign: "center" }}>
          <Progress
            type="circle"
            percent={Math.round(total)}
            format={(p) => <span style={{ color: scoreColor(p!), fontSize: 22, fontWeight: 700 }}>{p}</span>}
            strokeColor={scoreColor(total)}
            size={120}
          />
          <div style={{ marginTop: 8 }}>
            <Tag color={scoreColor(total)}>{scoreLabel(total)}</Tag>
          </div>
        </Col>
        <Col xs={24} sm={16}>
          <Row gutter={12}>
            <Col span={12}>
              <Statistic title="Население в 10 мин" value={result.population_10min || result.population_in_isochrone?.["10min"] || "—"} suffix="чел." />
            </Col>
            <Col span={12}>
              <Statistic
                title="Доля рынка (Хафф)"
                value={result.huff_market_share != null ? (result.huff_market_share * 100).toFixed(1) : "—"}
                suffix="%"
              />
            </Col>
            <Col span={12} style={{ marginTop: 12 }}>
              <Statistic title="Ср. зарплата" value={result.avg_salary || "—"} suffix="BYN" />
            </Col>
            <Col span={12} style={{ marginTop: 12 }}>
              <Statistic title="Конкурентов" value={result.competitors_nearby?.length || 0} />
            </Col>
          </Row>
        </Col>
      </Row>

      <Divider />
      <Title level={5}>Компонентная оценка</Title>
      <ResponsiveContainer width="100%" height={240}>
        <RadarChart data={radarData}>
          <PolarGrid />
          <PolarAngleAxis dataKey="label" tick={{ fontSize: 11 }} />
          <Radar dataKey="value" stroke="#1a5276" fill="#1a5276" fillOpacity={0.3} />
        </RadarChart>
      </ResponsiveContainer>

      <Divider />
      <Title level={5}>Конкуренты поблизости ({result.competitors_nearby?.length || 0})</Title>
      <Table
        dataSource={result.competitors_nearby?.slice(0, 15) || []}
        columns={competitorColumns}
        size="small"
        pagination={false}
        rowKey="id"
        scroll={{ y: 240 }}
      />
    </div>
  );
}
