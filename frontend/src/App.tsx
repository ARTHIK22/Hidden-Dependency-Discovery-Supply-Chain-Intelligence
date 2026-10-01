
import { BrowserRouter } from "react-router-dom";

import AppRoutes from "./routes/AppRoutes";
import { ToastProvider } from "./components/toast/ToastProvider";

function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <AppRoutes />
      </ToastProvider>
    </BrowserRouter>
  );
}

export default App;
