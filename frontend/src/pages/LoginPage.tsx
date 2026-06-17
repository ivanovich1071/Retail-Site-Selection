import { Form, Input, Button, Card, Typography, Alert } from "antd";
import { UserOutlined, LockOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useAppDispatch, useAppSelector } from "../hooks/redux";
import { login } from "../store/authSlice";

const { Title, Text } = Typography;

export default function LoginPage() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { loading, error } = useAppSelector((s) => s.auth);

  const onFinish = async (values: { email: string; password: string }) => {
    const result = await dispatch(login(values));
    if (login.fulfilled.match(result)) navigate("/dashboard");
  };

  return (
    <div style={{
      minHeight: "100vh", display: "flex", alignItems: "center",
      justifyContent: "center", background: "linear-gradient(135deg, #1a5276 0%, #2471a3 100%)",
    }}>
      <Card style={{ width: 380, borderRadius: 12, boxShadow: "0 8px 32px rgba(0,0,0,0.2)" }}>
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <Title level={3} style={{ margin: 0, color: "#1a5276" }}>Retail Site Selection</Title>
          <Text type="secondary">Евроторг — система выбора локаций</Text>
        </div>

        {error && <Alert type="error" message={error} style={{ marginBottom: 16 }} showIcon />}

        <Form layout="vertical" onFinish={onFinish} size="large">
          <Form.Item name="email" rules={[{ required: true, type: "email", message: "Введите email" }]}>
            <Input prefix={<UserOutlined />} placeholder="Email" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: "Введите пароль" }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="Пароль" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading}>
              Войти
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
