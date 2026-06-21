import { useState } from "react";
import {
  Card, Segmented, Input, InputNumber, Button, Form, Typography,
  message, Space, Result, Row, Col,
} from "antd";
import {
  SearchOutlined, EnvironmentOutlined, EditOutlined, UploadOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { startAnalysis } from "../services/api";
import { useJobProgress } from "../hooks/useJobProgress";
import JobProgress from "../components/Analysis/JobProgress";
import AnalysisResultView from "../components/Analysis/AnalysisResultView";

const { Title, Paragraph } = Typography;

type Mode = "address" | "map" | "polygon" | "batch";

export default function AnalysisPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>("address");
  const [jobId, setJobId] = useState<number | null>(null);
  const [starting, setStarting] = useState(false);

  const { job, error } = useJobProgress(jobId);

  const handleStart = async (values: any) => {
    setStarting(true);
    try {
      const created = await startAnalysis({
        address: values.address,
        area_sqm: values.area_sqm,
        parking_spaces: values.parking_spaces,
        visibility_score: values.visibility_score,
        include_huff: true,
      });
      setJobId(created.id);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Не удалось запустить анализ");
    } finally {
      setStarting(false);
    }
  };

  const reset = () => {
    // The address Card unmounts while a job runs and remounts on reset,
    // so the form fields clear naturally — no shared form instance needed.
    setJobId(null);
  };

  return (
    <div style={{ padding: 24, maxWidth: 860, margin: "0 auto" }}>
      <Title level={3}>Новый анализ</Title>

      <Segmented
        value={mode}
        onChange={(v) => setMode(v as Mode)}
        options={[
          { label: "Адрес", value: "address", icon: <SearchOutlined /> },
          { label: "Точка на карте", value: "map", icon: <EnvironmentOutlined /> },
          { label: "Полигон", value: "polygon", icon: <EditOutlined /> },
          { label: "Пакет", value: "batch", icon: <UploadOutlined /> },
        ]}
        style={{ marginBottom: 20 }}
        block
      />

      {mode === "address" && !jobId && (
        <Card>
          <Form layout="vertical" onFinish={handleStart}>
            <Form.Item name="address" label="Адрес" rules={[{ required: true, message: "Введите адрес" }]}>
              <Input prefix={<SearchOutlined />} placeholder="пр. Независимости 95, Минск" />
            </Form.Item>
            <Row gutter={12}>
              <Col span={8}>
                <Form.Item name="area_sqm" label="Площадь, м²">
                  <InputNumber min={10} max={100000} style={{ width: "100%" }} placeholder="400" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="parking_spaces" label="Парковка, мест">
                  <InputNumber min={0} style={{ width: "100%" }} placeholder="40" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="visibility_score" label="Видимость (0–10)">
                  <InputNumber min={0} max={10} step={0.5} style={{ width: "100%" }} placeholder="7" />
                </Form.Item>
              </Col>
            </Row>
            <Button type="primary" htmlType="submit" loading={starting}>
              Запустить анализ
            </Button>
          </Form>
        </Card>
      )}

      {mode === "map" && (
        <Card>
          <Result
            icon={<EnvironmentOutlined />}
            title="Анализ по клику на карте"
            subTitle="Откройте карту и кликните по нужной точке — анализ запустится автоматически."
            extra={<Button type="primary" onClick={() => navigate("/map")}>Открыть карту</Button>}
          />
        </Card>
      )}

      {mode === "polygon" && (
        <Card>
          <Result
            icon={<EditOutlined />}
            title="Анализ по нарисованной зоне"
            subTitle="На карте включите режим «Нарисовать зону» и обведите участок."
            extra={<Button type="primary" onClick={() => navigate("/map")}>Открыть карту</Button>}
          />
        </Card>
      )}

      {mode === "batch" && (
        <Card>
          <Result
            icon={<UploadOutlined />}
            title="Пакетный анализ"
            subTitle="Загрузите Excel/CSV со списком адресов для массовой обработки."
            extra={<Button type="primary" onClick={() => navigate("/batch")}>Перейти к загрузке</Button>}
          />
        </Card>
      )}

      {jobId && (
        <Card style={{ marginTop: 16 }}>
          <Paragraph type="secondary">Задача #{jobId}</Paragraph>
          <JobProgress job={job} error={error} onRetry={reset} />
          {job?.status === "completed" && job.result && (
            <div style={{ marginTop: 24 }}>
              <AnalysisResultView result={job.result} />
              <Space style={{ marginTop: 16 }}>
                <Button onClick={reset}>Новый анализ</Button>
              </Space>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
