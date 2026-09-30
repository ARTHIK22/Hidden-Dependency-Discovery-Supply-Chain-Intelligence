import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Info,
  X,
} from "lucide-react";
import "./toast.css";

export type ToastType = "success" | "warning" | "error" | "info";

type Toast = {
  id: number;
  type: ToastType;
  message: string;
};

type ToastContextType = {
  toast: {
    success: (message: string) => void;
    warning: (message: string) => void;
    error: (message: string) => void;
    info: (message: string) => void;
  };
};

const ToastContext = createContext<ToastContextType | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);

  const remove = useCallback((id: number) => {
    setItems((current) => current.filter((item) => item.id !== id));
  }, []);

  const show = useCallback(
    (type: ToastType, message: string) => {
      const id = Date.now() + Math.random();

      setItems((current) => [...current, { id, type, message }]);

      window.setTimeout(() => remove(id), 3500);
    },
    [remove]
  );

  const value = useMemo(
    () => ({
      toast: {
        success: (message: string) => show("success", message),
        warning: (message: string) => show("warning", message),
        error: (message: string) => show("error", message),
        info: (message: string) => show("info", message),
      },
    }),
    [show]
  );

  return (
    <ToastContext.Provider value={value}>
      {children}

      <div
        className="toast-container"
        aria-live="polite"
        aria-relevant="additions text"
      >
        {items.map((item) => {
          const Icon =
            item.type === "success"
              ? CheckCircle2
              : item.type === "warning"
              ? AlertTriangle
              : item.type === "error"
              ? XCircle
              : Info;

          return (
            <div
              key={item.id}
              className={`toast toast-${item.type}`}
              role={item.type === "error" ? "alert" : "status"}
            >
              <div className="toast-icon">
                <Icon size={18} />
              </div>

              <span>{item.message}</span>

              <button
                onClick={() => remove(item.id)}
                type="button"
                aria-label="Dismiss notification"
              >
                <X size={15} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);

  if (!context) {
    throw new Error("useToast must be used inside ToastProvider");
  }

  return context;
}
