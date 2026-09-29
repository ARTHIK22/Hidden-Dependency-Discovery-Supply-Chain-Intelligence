import { BrowserRouter } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";
import AppRoutes from "./routes/AppRoutes";

function App() {
  return <BrowserRouter><AppLayout><AppRoutes /></AppLayout></BrowserRouter>;
}

export default App;