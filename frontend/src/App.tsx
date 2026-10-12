import { Navigate, Route, Routes } from "react-router-dom";
import { CustomerLayout } from "./layouts/CustomerLayout";
import { OpsLayout } from "./layouts/OpsLayout";
import { HomePage } from "./pages/HomePage";
import { CartPage } from "./pages/CartPage";
import { CheckoutPage } from "./pages/CheckoutPage";
import { ConfirmationPage } from "./pages/ConfirmationPage";
import { TrackingPage } from "./pages/TrackingPage";
import { OpsDashboard } from "./pages/OpsDashboard";
import { SimulationPage } from "./pages/SimulationPage";
import { PoolingSimulatorPage } from "./pages/PoolingSimulatorPage";
import { ModelEvaluationPage } from "./pages/ModelEvaluationPage";
import { PoolingImpactPage } from "./pages/PoolingImpactPage";
import { DatasetExplorerPage } from "./pages/DatasetExplorerPage";

export default function App() {
  return (
    <Routes>
      <Route element={<CustomerLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/cart" element={<CartPage />} />
        <Route path="/checkout" element={<CheckoutPage />} />
        <Route path="/orders/:id" element={<ConfirmationPage />} />
        <Route path="/orders/:id/track" element={<TrackingPage />} />
      </Route>
      <Route path="/operations" element={<OpsLayout />}>
        <Route index element={<OpsDashboard />} />
        <Route path="simulation" element={<SimulationPage />} />
        <Route path="simulator" element={<PoolingSimulatorPage />} />
        <Route path="evaluation" element={<ModelEvaluationPage />} />
        <Route path="impact" element={<PoolingImpactPage />} />
        <Route path="data" element={<DatasetExplorerPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
