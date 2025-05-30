/**
 * The main React application component that handles routing and layout.
 * It sets up the main layout with a sidebar and a content area, and defines the routes for the different pages of the application.
 * The component also manages the state of the dark theme and the collapsed state of the sidebar.
 */
import { useState } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Provider } from "react-redux";
import { Button, Layout, theme } from "antd";
import { MenuFoldOutlined, MenuUnfoldOutlined } from "@ant-design/icons";
import HomePage from "./pages/HomePage";
import FourOFourPage from "./pages/404Page";
import BotControlPage from "./pages/BotControlPage";
import Logo from "./components/Logo";
import MenuList from "./components/MenuList";
import ToggleThemeButton from "./components/ToggleThemeButton";
const { Header, Sider } = Layout;

const App = () => {
  const [darkTheme, setDarkTheme] = useState(true);
  const [collapsed, setCollapsed] = useState(false);

  const toggleTheme = () => {
    setDarkTheme(!darkTheme);
  };

  const {
    token: { colorBgContainer },
  } = theme.useToken();

  return (
      <Router>
        <Layout>
          <Sider
            collapsed={collapsed}
            collapsible
            trigger={null}
            theme={darkTheme ? "dark" : "light"}
            className="sidebar"
            style={{height: "100%"}}
          >
            <Logo />
            <MenuList darkTheme={darkTheme} />
            <ToggleThemeButton
              darkTheme={darkTheme}
              toggleTheme={toggleTheme}
            />
          </Sider>
          <Layout>
            <Header style={{ padding: 0, background: colorBgContainer, borderBottom: "none" }}>
              <Button
                type="text"
                className="toggle"
                onClick={() => setCollapsed(!collapsed)}
                icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              />
            </Header>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/*" element={<FourOFourPage />} />
              <Route path="/bot-control" element={<BotControlPage />} />
            </Routes>
          </Layout>
        </Layout>
      </Router>
  );
};

export default App;
