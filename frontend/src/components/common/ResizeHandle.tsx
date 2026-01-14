import { PanelResizeHandle } from "react-resizable-panels";
import { GripVertical, GripHorizontal } from "lucide-react";

interface ResizeHandleProps {
  className?: string;
  id?: string;
  direction?: "horizontal" | "vertical";
}

export default function ResizeHandle({ className = "", id, direction = "horizontal" }: ResizeHandleProps) {
  return (
    <PanelResizeHandle
      className={`relative flex items-center justify-center bg-gray-800 transition-all duration-300 outline-none group hover:z-10 ${
        direction === "horizontal" 
          ? "w-2 h-full cursor-col-resize hover:bg-blue-500/50" 
          : "h-2 w-full cursor-row-resize hover:bg-blue-500/50"
      } ${className}`}
      id={id}
    >
      <div className={`absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex items-center justify-center text-gray-600 group-hover:text-blue-200 transition-colors duration-300`}>
        {direction === "horizontal" ? (
           <GripVertical size={12} />
        ) : (
           <GripHorizontal size={12} />
        )}
      </div>
      {/* 视觉反馈条 - 拖拽时显示高亮线 */}
      <div className={`absolute bg-blue-500 opacity-0 group-active:opacity-100 transition-opacity duration-200 ${
         direction === "horizontal" ? "w-[1px] h-full" : "h-[1px] w-full"
      }`} />
    </PanelResizeHandle>
  );
}
