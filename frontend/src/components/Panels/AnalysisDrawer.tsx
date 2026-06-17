import { Drawer, Tabs, Spin, Alert, Typography, Statistic, Row, Col, Table, Button, Progress, Tag, Divider } from "antd";
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer } from "recharts";
import { useAppDispatch, useAppSelector } from "../../hooks/redux";
import { setAnalysisPanelOpen } from "../../store/uiSlice";
import { clearAnalysis } from "../../store/mapSlice";
import { generateReport, downloadReportUrl } from "../../services/api";
import { useState } from "react";

const { Title, Text } = Typography;

function scoreColor(score: number) {
  if (score >= 70) return "#27ae60";
  if (score >= 45) return "#f39c12";
  return "#e74c3c";
}

function scoreLabel(score: number) {
  if (score >= 70) return "Высокий";
  if (score >= 45) return "Средний";
  return "Низкий";
}

export default function AnalysisDrawer() {
  const dispatch = useAppDispatch();
  const open = useAppSelector((s) => s.ui.analysisPanelOpen);
  const { analysisResult, analysisLoading, analysisError } = useAppSelector((s) => s.map);
  const [reportLoading, setReportLoading] = useState(false);

  const handleClose = () => {
    dispatch(setAnalysisPanelOpen(false));
    dispatch(clearAnalysis());
  };

  const radarData = analysisResult?.scoring
    ? [
        { label: "Демография",      value: analysisResult.scoring.score_demographics },
        { label: "Конкуренты",       value: analysisResult.scoring.score_competitors },
        { label: "Доступность",      value: analysisResult.scoring.score_accessibility },
        { label: "Видимость",        value: analysisResult.scoring.score_visibility },
        { label: "Локация",          value: analysisResult.scoring.score_location },
      ]
    : [];

  const competitorColumns = [
    { title: "Бренд",     dataIndex: "brand_name",  key: "brand" },
    { title: "Расст., м", dataIndex: "distance_m",  key: "dist", render: (v: number) => v ? Math.round(v) : "—" },
  ];

  return (
    <Drawer
      title={analysisResult ? "Анализ локации" : "Выберите точку на карте"}
      placement="right"
      width={420}
      open={open}
      onClose={handleClose}
      className="analysis-drawer"
      extra={
        analysisResult && (
          <Button
            size="small"
            loading={reportLoading}
            onClick={async () => {
              // requires saved location; demo only
              setReportLoading(true);
              setTimeout(() => setReportLoading(false), 2000);
            }}
          >
            PDF-отчёт
          </Button>
        )
      }
    >
      {analysisLoading && (
        <div style={{ textAlign: "center", paddingTop: 60 }}>
          <Spin size="large" />
          <p style={{ marginTop: 16, color: "#888" }}>Выполняем анализ…</p>
        </div>
      )}

      {analysisError && !analysisLoading && (
        <Alert type="error" message={analysisError} showIcon style={{ marginBottom: 16 }} />
      )}

      {analysisResult && !analysisLoading && (
        <Tabs
          defaultActiveKey="data"
          items={[
            {
              key: "data",
              label: "Данные",
              children: (
                <>
                  <Text type="secondary">{analysisResult.address}</Text>
                  <Divider />

                  {/* Score */}
                  <div style={{ textAlign: "center", marginBottom: 24 }}>
                    <Progress
                      type="circle"
                      percent={analysisResult.scoring?.total_score || 0}
                      format={(p) => <span style={{ color: scoreColor(p!), fontSize: 22, fontWeight: 700 }}>{p}</span>}
                      strokeColor={scoreColor(analysisResult.scoring?.total_score || 0)}
                      size={120}
                    />
                    <div style={{ marginTop: 8 }}>
                      <Tag color={scoreColor(analysisResult.scoring?.total_score || 0)}>
                        {scoreLabel(analysisResult.scoring?.total_score || 0)}
                      </Tag>
                    </div>
                  </div>

                  <Row gutter={12}>
                    <Col span={12}>
                      <Statistic
                        title="Нас. в 10 мин"
                        value={analysisResult.population_in_isochrone?.["10min"] || "—"}
                        suffix="чел."
                      />
                    </Col>
                    <Col span={12}>
                      <Statistic
                        title="Доля рынка (Хафф)"
                        value={analysisResult.huff_market_share != null
                          ? (analysisResult.huff_market_share * 100).toFixed(1)
                          : "—"}
                        suffix="%"
                      />
                    </Col>
                  </Row>
                </>
              ),
            },
            {
              key: "analytics",
              label: "Аналитика",
              children: (
                <>
                  <Title level={5}>Компонентная оценка</Title>
                  <ResponsiveContainer width="100%" height={220}>
                    <RadarChart data={radarData}>
                      <PolarGrid />
                      <PolarAngleAxis dataKey="label" tick={{ fontSize: 11 }} />
                      <Radar dataKey="value" stroke="#1a5276" fill="#1a5276" fillOpacity={0.3} />
                    </RadarChart>
                  </ResponsiveContainer>

                  <Divider />
                  <Title level={5}>Конкуренты поблизости ({analysisResult.competitors_nearby?.length || 0})</Title>
                  <Table
                    dataSource={analysisResult.competitors_nearby?.slice(0, 10) || []}
                    columns={competitorColumns}
                    size="small"
                    pagination={false}
                    rowKey="id"
                    scroll={{ y: 200 }}
                  />
                </>
              ),
            },
          ]}
        />
      )}
    </Drawer>
  );
}
