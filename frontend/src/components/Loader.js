import { FaSpinner } from 'react-icons/fa';

export default function Loader({ fullScreen = false, text = "Loading..." }) {
  if (fullScreen) {
    return (
      <div className="fixed inset-0 bg-white/80 backdrop-blur-sm z-50 flex flex-col items-center justify-center">
        <FaSpinner className="animate-spin text-green-600 text-4xl mb-4" />
        <p className="text-gray-600 font-medium">{text}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center p-8">
      <FaSpinner className="animate-spin text-green-600 text-3xl mb-3" />
      <p className="text-gray-500 text-sm">{text}</p>
    </div>
  );
}
