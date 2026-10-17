import { Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import CustomerList from './pages/customer/CustomerList'
import CustomerOrder from './pages/customer/CustomerOrder'
import CustomerRestaurant from './pages/customer/CustomerRestaurant'
import InspectorRanking from './pages/inspector/InspectorRanking'
import InspectorRestaurant from './pages/inspector/InspectorRestaurant'
import InspectorReview from './pages/inspector/InspectorReview'
import Landing from './pages/Landing'
import NotFound from './pages/NotFound'
import OwnerDashboard from './pages/owner/OwnerDashboard'
import LiveAudit from './pages/owner/LiveAudit'
import AuditReport from './pages/owner/AuditReport'
import Tour from './pages/Tour'

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Landing />} />
        <Route path="tour" element={<Tour />} />
        <Route path="owner" element={<OwnerDashboard />} />
        <Route path="owner/audit/:auditId" element={<LiveAudit />} />
        <Route path="owner/report/:auditId" element={<AuditReport />} />
        <Route path="customer" element={<CustomerList />} />
        <Route path="customer/restaurant/:id" element={<CustomerRestaurant />} />
        <Route path="customer/order/:orderId" element={<CustomerOrder />} />
        <Route path="inspector" element={<InspectorRanking />} />
        <Route path="inspector/restaurant/:id" element={<InspectorRestaurant />} />
        <Route path="inspector/review" element={<InspectorReview />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
