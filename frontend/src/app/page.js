import Link from "next/link";
import { FaBolt, FaShieldAlt, FaUmbrella, FaWater, FaSun, FaSmog, FaCheckCircle } from "react-icons/fa";

export default function LandingPage() {
  return (
    <div className="bg-white">
      {/* Hero Section */}
      <div className="relative bg-gradient-to-br from-green-50 via-white to-green-50 overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-24 text-center">
          <h1 className="text-5xl md:text-6xl font-extrabold text-gray-900 tracking-tight mb-8">
            Weather disruptions shouldn't <br className="hidden md:block" />
            cost you <span className="text-transparent bg-clip-text bg-gradient-to-r from-green-600 to-emerald-500">your income.</span>
          </h1>
          <p className="mt-4 max-w-2xl mx-auto text-xl text-gray-600 mb-10">
            RideGuard is an AI-powered parametric insurance platform for delivery partners. Instant automated payouts when extreme weather hits your zone. No claims, no waiting.
          </p>
          <div className="flex justify-center gap-4">
            <Link 
              href="/register" 
              className="px-8 py-4 text-lg font-bold rounded-xl text-white bg-green-600 hover:bg-green-700 shadow-lg shadow-green-600/30 transition-all hover:scale-105"
            >
              Get Started Now
            </Link>
            <Link 
              href="/login" 
              className="px-8 py-4 text-lg font-bold rounded-xl text-gray-700 bg-white border-2 border-gray-200 hover:border-green-600 hover:text-green-600 transition-all"
            >
              Login
            </Link>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900">How RideGuard Works</h2>
          </div>

          <div className="grid md:grid-cols-3 gap-10">
            <div className="bg-gray-50 rounded-2xl p-8 border border-gray-100">
              <div className="w-14 h-14 bg-green-100 rounded-xl flex items-center justify-center mb-6">
                <FaShieldAlt className="text-green-600 text-2xl" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">Modular Coverage</h3>
              <p className="text-gray-600">Choose protection only for the risks you face: Rain, Floods, Heatwaves, or Hazardous AQI.</p>
            </div>

            <div className="bg-gray-50 rounded-2xl p-8 border border-gray-100">
              <div className="w-14 h-14 bg-blue-100 rounded-xl flex items-center justify-center mb-6">
                <FaBolt className="text-blue-600 text-2xl" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">Zero Manual Claims</h3>
              <p className="text-gray-600">Our AI monitors environmental triggers in real-time. If conditions are met, a claim is auto-generated.</p>
            </div>

            <div className="bg-gray-50 rounded-2xl p-8 border border-gray-100">
              <div className="w-14 h-14 bg-emerald-100 rounded-xl flex items-center justify-center mb-6">
                <FaCheckCircle className="text-emerald-600 text-2xl" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">Instant UPI Payouts</h3>
              <p className="text-gray-600">Receive compensation for lost income directly to your bank account via UPI within minutes.</p>
            </div>
          </div>
        </div>
      </div>

      {/* Coverage Types */}
      <div className="py-20 bg-gray-900 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold">Comprehensive Protection</h2>
            <p className="mt-4 text-gray-400">Parametric triggers designed specifically for Bangalore's climate.</p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div className="bg-gray-800 rounded-xl p-6 text-center border border-gray-700">
              <FaUmbrella className="text-blue-400 text-4xl mx-auto mb-4" />
              <h4 className="font-bold mb-2">Heavy Rain</h4>
              <p className="text-sm text-gray-400">&ge; 15mm/hr</p>
            </div>
            <div className="bg-gray-800 rounded-xl p-6 text-center border border-gray-700">
              <FaWater className="text-cyan-400 text-4xl mx-auto mb-4" />
              <h4 className="font-bold mb-2">Flooding</h4>
              <p className="text-sm text-gray-400">Traffic &lt; 5km/h</p>
            </div>
            <div className="bg-gray-800 rounded-xl p-6 text-center border border-gray-700">
              <FaSun className="text-orange-400 text-4xl mx-auto mb-4" />
              <h4 className="font-bold mb-2">Extreme Heat</h4>
              <p className="text-sm text-gray-400">&ge; 42&deg;C</p>
            </div>
            <div className="bg-gray-800 rounded-xl p-6 text-center border border-gray-700">
              <FaSmog className="text-gray-400 text-4xl mx-auto mb-4" />
              <h4 className="font-bold mb-2">Toxic AQI</h4>
              <p className="text-sm text-gray-400">&ge; 300 AQI</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
