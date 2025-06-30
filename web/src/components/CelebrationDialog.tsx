import React from 'react';
import Confetti from 'react-confetti';

export default function CelebrationDialog({ open, onClose, darkMode = false }: { open: boolean, onClose: () => void, darkMode?: boolean }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 flex items-center justify-center z-50 bg-black/60 dark:bg-black/80 backdrop-blur-sm p-4">
      <Confetti width={window.innerWidth} height={window.innerHeight} numberOfPieces={200} recycle={false} />
      <div className={`w-full max-w-md rounded-2xl shadow-2xl p-8 border-2 ${darkMode ? 'bg-gray-900 border-gray-700' : 'bg-white border-gray-200'}`}
        style={{ background: darkMode ? 'linear-gradient(135deg, #232946 0%, #1a1a2e 100%)' : 'linear-gradient(135deg, #fff1f7 0%, #e0e7ff 100%)' }}>
        <h2 className={`text-3xl font-extrabold mb-3 tracking-tight ${darkMode ? 'text-white' : 'text-gray-900'}`}>🎉 Welcome to RabbitReels! 🎉</h2>
        <p className={`mb-6 text-lg font-medium ${darkMode ? 'text-gray-200' : 'text-gray-700'}`}>You&apos;ve received <span className="font-bold text-pink-500">1 free credit</span> to get started!</p>
        <button
          className="w-full py-3 rounded-xl bg-gradient-to-r from-pink-500 to-purple-500 text-white font-bold text-lg shadow-lg hover:from-pink-600 hover:to-purple-600 transition-all focus:outline-none focus:ring-2 focus:ring-pink-400 focus:ring-offset-2"
          onClick={onClose}
        >
          Start Creating!
        </button>
      </div>
    </div>
  );
} 