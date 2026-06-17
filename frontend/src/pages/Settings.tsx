import { Card, Form, InputNumber, Button, Divider, Typography, message, Switch } from "antd";

const { Title, Text } = Typography;

const DEFAULT_WEIGHTS = {
  demographics: 30,
  competitors: 25,
  accessibility: 20,
  visibility: 15,
  location: 10,
};

export default function Settings() {
  const [form] = Form.useForm();

  const onSave = (values: any) => {
    const total = Object.values(values).reduce((a: any, b: any) => a + b, 0);
    if (Math.abs(total - 100) > 1) {
      message.error("Сумма весов должна быть равна 100%");
      return;
    }
    // In production: PATCH /api/v1/config/scoring-weights
    message.success("Веса сохранены (демо)");
  };

  return (
    <div style={{ padding: 24, maxWidth: 640 }}>
      <Title level={3}>Настройки</Title>

      <Card title="Веса скоринговой модели" style={{ marginBottom: 24 }}>
        <Text type="secondary" style={{ display: "block", marginBottom: 16 }}>
          Сумма весов должна составлять 100%. Изменения влияют на все новые расчёты.
        </Text>
        <Form form={form} initialValues={DEFAULT_WEIGHTS} onFinish={onSave} layout="vertical">
          {Object.entries(DEFAULT_WEIGHTS).map(([key, val]) => {
            const labels: Record<string, string> = {
              demographics: "Демография",
              competitors: "Конкуренты",
              accessibility: "Доступность",
              visibility: "Видимость",
              location: "Локация (ТКП-45)",
            };
            return (
              <Form.Item key={key} name={key} label={`${labels[key]} (%)`}>
                <InputNumber min={0} max={100} style={{ width: 120 }} />
              </Form.Item>
            );
          })}
          <Button type="primary" htmlType="submit">Сохранить веса</Button>
        </Form>
      </Card>

      <Card title="Параметры модели Хаффа">
        <Form layout="vertical">
          <Form.Item label="Параметр затухания β (по умолчанию 2.0)">
            <InputNumber min={0.5} max={5} step={0.1} defaultValue={2.0} style={{ width: 120 }} />
          </Form.Item>
          <Form.Item label="Радиус каннибализации (м)">
            <InputNumber min={100} max={5000} step={50} defaultValue={800} style={{ width: 120 }} />
          </Form.Item>
          <Button type="primary">Сохранить</Button>
        </Form>
      </Card>
    </div>
  );
}
