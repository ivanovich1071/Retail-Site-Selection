import { Layout, Menu, Avatar, Dropdown, Button, Typography } from "antd";
import {
  DashboardOutlined, EnvironmentOutlined, UnorderedListOutlined,
  UploadOutlined, FileTextOutlined, SettingOutlined, ThunderboltOutlined,
  MenuFoldOutlined, MenuUnfoldOutlined, UserOutlined, LogoutOutlined,
} from "@ant-design/icons";
import { useNavigate, useLocation } from "react-router-dom";
import { useAppDispatch, useAppSelector } from "../../hooks/redux";
import { toggleSidebar } from "../../store/uiSlice";
import { logout } from "../../store/authSlice";
import AIChat from "../AI/AIChat";
import type { ReactNode } from "react";

const { Sider, Header, Content } = Layout;
const { Text } = Typography;

const menuItems = [
  { key: "/dashboard",  icon: <DashboardOutlined />,      label: "Дашборд" },
  { key: "/analysis",   icon: <ThunderboltOutlined />,    label: "Новый анализ" },
  { key: "/map",        icon: <EnvironmentOutlined />,    label: "Карта" },
  { key: "/locations",  icon: <UnorderedListOutlined />,  label: "Объекты" },
  { key: "/batch",      icon: <UploadOutlined />,         label: "Пакетная загрузка" },
  { key: "/reports",    icon: <FileTextOutlined />,       label: "Отчёты" },
  { key: "/settings",   icon: <SettingOutlined />,        label: "Настройки" },
];

export default function AppLayout({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useAppDispatch();
  const collapsed = useAppSelector((s) => s.ui.sidebarCollapsed);
  const user = useAppSelector((s) => s.auth.user);

  const handleLogout = () => {
    dispatch(logout());
    navigate("/login");
  };

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider
        collapsible
        collapsed={collapsed}
        trigger={null}
        width={220}
        style={{ background: "#1a5276" }}
      >
        <div style={{
          height: 56, display: "flex", alignItems: "center", justifyContent: "center",
          color: "#fff", fontWeight: 700, fontSize: collapsed ? 14 : 16,
          borderBottom: "1px solid rgba(255,255,255,0.15)", padding: "0 12px",
        }}>
          {collapsed ? "RSS" : "Retail Site Selection"}
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          onClick={({ key }) => navigate(key)}
          items={menuItems}
          style={{ background: "#1a5276", border: "none", color: "#d6eaf8" }}
          theme="dark"
        />
      </Sider>

      <Layout>
        <Header style={{
          background: "#fff", padding: "0 16px", display: "flex",
          alignItems: "center", justifyContent: "space-between",
          boxShadow: "0 1px 4px rgba(0,0,0,0.12)", height: 56,
        }}>
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => dispatch(toggleSidebar())}
          />
          <Dropdown
            menu={{
              items: [
                { key: "logout", icon: <LogoutOutlined />, label: "Выйти", onClick: handleLogout },
              ],
            }}
          >
            <div style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: 8 }}>
              <Avatar icon={<UserOutlined />} size="small" />
              <Text style={{ maxWidth: 160 }} ellipsis>{user?.email || "Пользователь"}</Text>
            </div>
          </Dropdown>
        </Header>

        <Content style={{
          margin: 0, flex: 1, display: "flex", flexDirection: "column",
          overflow: location.pathname === "/map" ? "hidden" : "auto",
        }}>
          {children}
        </Content>
      </Layout>

      <AIChat />
    </Layout>
  );
}
