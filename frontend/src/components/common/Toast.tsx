import { createContext, useContext, useState, useCallback, ReactNode, useEffect } from 'react';
import './Toast.css';

type ToastType = 'success' | 'error' | 'warning' | 'info';

interface ToastMessage {
  id: string;
  type: ToastType;
  message: string;
  duration?: number;
}

interface ToastContextType {
  showToast: (message: string, type?: ToastType, duration?: number) => void;
  success: (message: string, duration?: number) => void;
  error: (message: string, duration?: number) => void;
  warning: (message: string, duration?: number) => void;
  info: (message: string, duration?: number) => void;
  removeToast: (id: string) => void;
  toasts: ToastMessage[];
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider = (props: { children: ReactNode }) => {
  const { children } = props;
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [isMounted, setIsMounted] = useState(false);

  // Set mounted state to prevent memory leaks
  useEffect(() => {
    setIsMounted(true);
    return () => setIsMounted(false);
  }, []);

  const removeToast = useCallback((id: string) => {
    if (!isMounted) return;
    setToasts((currentToasts) => currentToasts.filter((toast) => toast.id !== id));
  }, [isMounted]); 

  const showToast = useCallback((message: string, type: ToastType = 'info', duration = 5000) => {
    if (!isMounted) return '';
    const id = Math.random().toString(36).substr(2, 9);
    
    setToasts((currentToasts) => [...currentToasts, { id, type, message, duration }]);

    if (duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, duration);
    }
  }, [removeToast, isMounted]);

  const toastFunctions = {
    success: (message: string, duration?: number) => showToast(message, 'success', duration),
    error: (message: string, duration?: number) => showToast(message, 'error', duration),
    warning: (message: string, duration?: number) => showToast(message, 'warning', duration),
    info: (message: string, duration?: number) => showToast(message, 'info', duration),
  };

  return (
    <ToastContext.Provider value={{ showToast, ...toastFunctions, removeToast, toasts }}>
      {children}
      <div className="toast-container">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast toast-${toast.type}`}>
            <div className="toast-message">{toast.message}</div>
            <button 
              className="toast-close" 
              onClick={() => removeToast(toast.id)}
              aria-label="Close"
            >
              &times;
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

// Export the hook as a named export
const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};
// Export the ToastProvider as default and include useToast in the exports
export { useToast };
export default ToastProvider;
