import { useState } from 'react';
import { Star, Heart, Zap, Shield, Crown, Anchor, Ghost } from 'lucide-react';

interface JojolandMascotProps {
  inline?: boolean;
}

export default function JojolandMascot({ inline = false }: JojolandMascotProps) {
  const mascots = [
    { id: 1, name: 'Star', color: 'text-purple-400', bg: 'bg-purple-500/20', icon: Star },
    { id: 2, name: 'Magician', color: 'text-red-400', bg: 'bg-red-500/20', icon: Zap },
    { id: 3, name: 'Hierophant', color: 'text-green-400', bg: 'bg-green-500/20', icon: Ghost },
    { id: 4, name: 'Chariot', color: 'text-gray-300', bg: 'bg-gray-500/20', icon: Shield },
    { id: 5, name: 'World', color: 'text-yellow-400', bg: 'bg-yellow-500/20', icon: Crown },
    { id: 6, name: 'Ocean', color: 'text-blue-400', bg: 'bg-blue-500/20', icon: Anchor },
    { id: 7, name: 'Crazy', color: 'text-pink-400', bg: 'bg-pink-500/20', icon: Heart },
  ];

  const [selectedId, setSelectedId] = useState<number | null>(null);

  const containerClass = inline
    ? 'flex items-center gap-2 px-3 py-1 rounded border border-jojo-gold bg-jojo-blue-light min-w-0'
    : 'jojo-card p-2';

  const headerClass = inline
    ? 'flex items-center gap-2 flex-shrink-0'
    : 'flex items-center justify-between mb-2';

  return (
    <div className={containerClass}>
      <div className={headerClass}>
        <h3 className="jojo-title text-xs md:text-sm whitespace-nowrap">JOJO LAND 萌宠</h3>
        <span className="hidden sm:inline text-[10px] md:text-xs text-jojo-gold/70 whitespace-nowrap">Stand Power</span>
      </div>
      
      <div className="flex justify-between items-center gap-1 overflow-x-auto custom-scrollbar pb-1 flex-1 min-w-0">
        {mascots.map((mascot) => {
          const Icon = mascot.icon;
          const isSelected = selectedId === mascot.id;
          
          return (
            <button
              key={mascot.id}
              onClick={() => setSelectedId(mascot.id)}
              className={`
                flex flex-col items-center justify-center p-1.5 rounded-lg transition-all duration-300
                flex-shrink-0 w-12 h-14
                ${isSelected ? 'bg-jojo-gold/20 border-jojo-gold scale-110' : 'hover:bg-white/5 border-transparent'}
                border border-opacity-50
              `}
            >
              <div className={`
                p-1.5 rounded-full mb-1 transition-transform duration-500
                ${mascot.bg} ${mascot.color}
                ${isSelected ? 'rotate-12' : ''}
              `}>
                <Icon size={16} />
              </div>
              <span className={`text-[10px] transform scale-90 whitespace-nowrap ${isSelected ? 'text-jojo-gold font-bold' : 'text-gray-400'}`}>
                {mascot.name}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
