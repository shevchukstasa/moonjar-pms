import { Routes, Route, Navigate } from "react-router-dom";
import { ScanPage } from "./pages/ScanPage";
import { ReceivePage } from "./pages/ReceivePage";
import { InventoryPage } from "./pages/InventoryPage";
import { LoginPage } from "./pages/LoginPage";

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/scan" element={<ScanPage />} />
      <Route path="/receive" element={<ReceivePage />} />
      <Route path="/inventory" element={<InventoryPage />} />
      <Route path="*" element={<Navigate to="/scan" replace />} />
    </Routes>
  );
}
