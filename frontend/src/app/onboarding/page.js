"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { fetchEarnings } from "@/services/api";
import Loader from "@/components/Loader";
import Card from "@/components/Card";
import { FaMotorcycle, FaRupeeSign, FaClock } from "react-icons/fa";

export default function Onboarding() {
  const { riderId } = useAuth();
  const router = useRouter();
  const [earnings, setEarnings] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!riderId) {
      router.push("/");
      return;
    }

    const loadEarnings = async () => {
      try {
        const data = await fetchEarnings(riderId);
        setEarnings(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    loadEarnings();
  }, [riderId, router]);

  if (loading) return <Loader fullScreen text="Syncing partner data..." />;
  if (!earnings) return <Loader text="Failed to load your earnings profile. Please try refreshing." />;

  const { summary } = earnings;

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <div className="text-center mb-10">
        <h1 className="text-4xl font-extrabold text-gray-900 mb-4">Profile Synced!</h1>
        <p className="text-xl text-gray-600">We've connected to your partner account. Here is your current earning profile used to calculate coverage.</p>
      </div>

      <div className="grid md:grid-cols-3 gap-6 mb-10">
        <Card className="text-center relative overflow-hidden group">
          <div className="absolute top-0 right-0 -mt-4 -mr-4 w-24 h-24 bg-green-50 rounded-full z-0 group-hover:scale-150 transition-transform duration-500"></div>
          <div className="relative z-10 flex flex-col items-center">
            <FaRupeeSign className="text-green-500 text-4xl mb-4" />
            <p className="text-sm font-medium text-gray-500 uppercase tracking-wide">Avg. Weekly Income</p>
            <p className="text-3xl font-bold text-gray-900 mt-2">₹{summary.avg_weekly_earnings}</p>
          </div>
        </Card>

        <Card className="text-center relative overflow-hidden group">
          <div className="absolute top-0 right-0 -mt-4 -mr-4 w-24 h-24 bg-blue-50 rounded-full z-0 group-hover:scale-150 transition-transform duration-500"></div>
          <div className="relative z-10 flex flex-col items-center">
            <FaClock className="text-blue-500 text-4xl mb-4" />
            <p className="text-sm font-medium text-gray-500 uppercase tracking-wide">Calculated Hourly</p>
            <p className="text-3xl font-bold text-gray-900 mt-2">₹{summary.avg_hourly_income}/hr</p>
          </div>
        </Card>

        <Card className="text-center relative overflow-hidden group">
          <div className="absolute top-0 right-0 -mt-4 -mr-4 w-24 h-24 bg-orange-50 rounded-full z-0 group-hover:scale-150 transition-transform duration-500"></div>
          <div className="relative z-10 flex flex-col items-center">
            <FaMotorcycle className="text-orange-500 text-4xl mb-4" />
            <p className="text-sm font-medium text-gray-500 uppercase tracking-wide">Active Days / Week</p>
            <p className="text-3xl font-bold text-gray-900 mt-2">{summary.avg_active_days}</p>
          </div>
        </Card>
      </div>

      <div className="text-center">
        <button
          onClick={() => router.push("/policy")}
          className="px-10 py-4 text-lg font-bold rounded-xl text-white bg-green-600 hover:bg-green-700 shadow-lg shadow-green-600/30 transition-all hover:scale-105"
        >
          Continue to Policy Selection
        </button>
      </div>
    </div>
  );
}
