import { Component, type ReactNode, type ErrorInfo } from "react";
import { Result, Button } from "antd";
import { logger } from "../utils/logger";

interface Props { children: ReactNode }
interface State { hasError: boolean; message?: string }

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    logger.error(`React render error: ${error.message}`, {
      stack: error.stack?.split("\n").slice(0, 4).join(" | "),
      componentStack: info.componentStack?.split("\n").slice(0, 4).join(" | "),
    });
  }

  render() {
    if (this.state.hasError) {
      return (
        <Result
          status="error"
          title="Что-то пошло не так"
          subTitle={this.state.message || "Произошла ошибка интерфейса. Детали — в логах."}
          extra={
            <Button type="primary" onClick={() => window.location.reload()}>
              Перезагрузить
            </Button>
          }
        />
      );
    }
    return this.props.children;
  }
}
