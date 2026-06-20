import { useEffect, useState } from "react";
import { Card, Form, InputNumber, Button, Divider, Typography, message, Spin } from "antd";
import { api } from "../services/api";

const { Title, Text } = Typography;

interface ScoringWeights {
  demographics: number;
  competitors: number;
  accessibility: number;
  visibility: number;
  location: number;
}

interface HuffParams {
  beta: number;
  cannibalization_radius_m: number;
}

const WEIGHT_LABELS: Record<string, string> = {
  demographics: "Демография",
  competitors: "Конкуренты",
  accessibility: "Доступность",
  visibility: "Видимость",
  location: "Локация (ТКП-45)",
};

export default function Settings() {
  const [weightsForm] = Form.useForm();
  const [huffForm] = Form.useForm();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get("/config/scoring-weights")
      .then((r) => {
        const data = r.data;
        const w = data.scoring_weights;
        weightsForm.setFieldsValue({
          demographics: Math.round(w.demographics * 100),
          competitors: Math.round(w.competitors * 100),
          accessibility: Math.round(w.accessibility * 100),
          visibility: Math.round(w.visibility * 100),
          location: Math.round(w.location * 100),
        });
        huffForm.setFieldsValue(data.huff_params);
      })
      .catch(() => {
        weightsForm.setFieldsValue({ demographics: 30, competitors: 25, accessibility: 20, visibility: 15, location: 10 });
        huffForm.setFieldsValue({ beta: 2.0, cannibalization_radius_m: 800 });
      })
      .finally(() => setLoading(false));
  }, []);

  const onSaveWeights = async (values: Record<string, number>) => {
    const total = Object.values(values).reduce((a, b) => a + b, 0);
    if (Math.abs(total - 100) > 1) {
      message.error("Сумма весов должна быть равна 100%");
      return;
    }
    setSaving(true);
    try {
      await api.patch("/config/scoring-weights", {
        scoring_weights: {
          demographics: values.demographics / 100,
          competitors: values.competitors / 100,
          accessibility: values.accessibility / 100,
          visibility: values.visibility / 100,
          location: values.location / 100,
        },
      });
      message.success("Веса скоринга сохранены");
    } catch {
      message.error("Не удалось сохранить веса");
    } finally {
      setSaving(false);
    }
  };

  const onSaveHuff = async (values: HuffParams) => {
    setSaving(true);
    try {
      await api.patch("/config/scoring-weights", { huff_params: values });
      message.success("Параметры Хаффа сохранены");
    } catch {
      message.error("Не удалось сохранить параметры");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div style={{ padding: 24, textAlign: "center" }}><Spin size="large" /></div>;

  return (
    <div style={{ padding: 24, maxWidth: 640 }}>
      <Title level={3}>Настройки</Title>

      <Card title="Веса скоринговой модели" style={{ marginBottom: 24 }}>
        <Text type="secondary" style={{ display: "block", marginBottom: 16 }}>
          Сумма весов должна составлять 100%. Изменения влияют на все новые расчёты.
        </Text>
        <Form form={weightsForm} onFinish={onSaveWeights} layout="vertical">
          {Object.keys(WEIGHT_LABELS).map((key) => (
            <Form.Item key={key} name={key} label={`${WEIGHT_LABELS[key]} (%)`}>
              <InputNumber min={0} max={100} style={{ width: 120 }} />
            </Form.Item>
          ))}
          <Button type="primary" htmlType="submit" loading={saving}>Сохранить веса</Button>
        </Form>
      </Card>

      <Card title="Параметры модели Хаффа">
        <Form form={huffForm} onFinish={onSaveHuff} layout="vertical">
          <Form.Item name="beta" label="Параметр затухания β">
            <InputNumber min={0.5} max={5} step={0.1} style={{ width: 120 }} />
          </Form.Item>
          <Form.Item name="cannibalization_radius_m" label="Радиус каннибализации (м)">
            <InputNumber min={100} max={5000} step={50} style={{ width: 120 }} />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={saving}>Сохранить</Button>
        </Form>
      </Card>
    </div>
  );
}
