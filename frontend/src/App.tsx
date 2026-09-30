
import { BrowserRouter } from "react-router-dom";

import AppLayout from "./components/layout/AppLayout";
import AppRoutes from "./routes/AppRoutes";
import { ToastProvider } from "./components/toast/ToastProvider";

function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <AppLayout>
          <AppRoutes />
        </AppLayout>
      </ToastProvider>
    </BrowserRouter>
  );
}

export default App;
