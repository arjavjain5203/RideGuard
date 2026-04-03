"use client";

import { useEffect, useState } from "react";
import { fetchAdminMetrics, fetchAdminClaims, fetchAdminFraudAlerts } from "@/services/api";
import Sidebar from "@/components/Sidebar";
import Card from "@/components/Card";
import Loader from "@/components/Loader";
import { FaChartLine, FaShieldAlt, FaFileContract, FaExclamationCircle } from "react-icons/fa";

export default function AdminDashboard() {
  const [data, setData] = useState({
    metrics: null,
    claims: [],
    fraudAlerts: []
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [metrics, claims, fraudAlerts] = await Promise.all([
          fetchAdminMetrics(),
          fetchAdminClaims(),
          fetchAdminFraudAlerts()
        ]);
        setData({ metrics, claims, fraudAlerts });
      } catch (err) {
        console.error("Admin data load failed", err);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  if (loading) return <Loader fullScreen text="Loading Admin Dashboard..." />;

  const { metrics, claims, fraudAlerts } = data;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex gap-8">
        <Sidebar />
        
        <div className="flex-1 space-y-6">
          <div className="mb-6">
            <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
            <p className="text-gray-600 mt-1">System observability and fraud monitoring</p>
          </div>

          {metrics && (
            <div className="grid md:grid-cols-4 gap-4 mb-8">
              <Card>
                <div className="flex items-center gap-2 mb-2 text-blue-600">
                  <FaFileContract />
                  <h3 className="font-semibold text-sm">Active Policies</h3>
                </div>
                <p className="text-2xl font-bold">{metrics.active_policies}</p>
              </Card>
              <Card>
                <div className="flex items-center gap-2 mb-2 text-green-600">
                  <FaChartLine />
                  <h3 className="font-semibold text-sm">Weekly Premiums</h3>
                </div>
                <p className="text-2xl font-bold">₹{metrics.total_premiums_weekly}</p>
              </Card>
              <Card>
                <div className="flex items-center gap-2 mb-2 text-orange-600">
                  <FaShieldAlt />
                  <h3 className="font-semibold text-sm">Loss Ratio</h3>
                </div>
                <p className="text-2xl font-bold">{metrics.loss_ratio.toFixed(2)}</p>
              </Card>
              <Card>
                <div className="flex items-center gap-2 mb-2 text-purple-600">
                  <FaShieldAlt />
                  <h3 className="font-semibold text-sm">Avg Trust Score</h3>
                </div>
                <p className="text-2xl font-bold">{metrics.avg_urts}</p>
              </Card>
            </div>
          )}

          <div className="grid md:grid-cols-2 gap-6">
            <Card>
              <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                <FaExclamationCircle className="text-red-500" /> Fraud Alerts
              </h3>
              {fraudAlerts.length === 0 ? (
                <p className="text-sm text-gray-500">No recent fraud alerts.</p>
              ) : (
                <div className="space-y-3">
                  {fraudAlerts.map(alert => (
                    <div key={alert.claim_id} className="p-3 bg-red-50 border border-red-100 rounded-lg text-sm">
                      <div className="flex justify-between font-bold text-red-800">
                        <span>Rider {alert.rider_id.substring(0,8)}</span>
                        <span>URTS: {alert.effective_urts}</span>
                      </div>
                      <p className="text-xs text-red-600 mt-1">{alert.behavioral_signals}</p>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            <Card>
              <h3 className="font-bold text-gray-900 mb-4">Recent Claims</h3>
              {claims.length === 0 ? (
                <p className="text-sm text-gray-500">No recent claims.</p>
              ) : (
                <div className="space-y-3">
                  {claims.map(claim => (
                    <div key={claim.id} className="flex justify-between items-center border-b pb-2 text-sm">
                      <div>
                        <p className="font-medium text-gray-800">Rider {claim.rider_id.substring(0,8)}</p>
                        <p className="text-xs text-gray-500">{new Date(claim.created_at).toLocaleString()}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-bold text-gray-900">₹{claim.loss_amount}</p>
                        <span className={`text-xs px-2 py-0.5 rounded uppercase font-bold ${
                          claim.status === 'paid' ? 'bg-green-100 text-green-700' : 
                          claim.status === 'capped' ? 'bg-orange-100 text-orange-700' : 
                          'bg-gray-100 text-gray-700'
                        }`}>
                          {claim.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
