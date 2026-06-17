import { Typography, Card, Empty, Button } from "antd";
import { FileTextOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";

const { Title, Text } = Typography;

export default function Reports() {
  const navigate = useNavigate();
  return (
    <div style={{ padding: 24 }}>
      <Title level={3}>Отчёты</Title>
      <Card>
        <Empty
          image={<FileTextOutlined style={{ fontSize: 64, color: "#ccc" }} />}
          description={
            <>
              <Text>Отчёты генерируются на странице объектов.</Text><br />
              <Text type="secondary">После генерации файлы появятся здесь.</Text>
            </>
          }
        >
          <Button type="primary" onClick={() => navigate("/locations")}>
            Перейти к объектам
          </Button>
        </Empty>
      </Card>
    </div>
  );
}
