// frontend/src/components/Auth/PersistenceWrapper/PersistenceWrapper.tsx
import React, { useEffect, useState } from 'react';
import { useAppDispatch } from '../../store/hooks';
import { checkAuthStatus } from '../../store/slices/authSlice';
import { initializeCsrf } from '../../utils/csrf';

interface PersistenceWrapperProps {
  children: React.ReactNode;
}

const PersistenceWrapper: React.FC<PersistenceWrapperProps> = (props) => {
  const { children } = props;
  const [isInitialized, setIsInitialized] = useState(false);
  const [initError, setInitError] = useState<Error | null>(null);
  const dispatch = useAppDispatch();

  useEffect(() => {
    const initialize = async () => {
      console.log('🦔 Sir Hawkington: Initializing authentication persistence...');
      
      try {
        // Step 1: Initialize CSRF token (critical for any authenticated requests)
        console.log('🐌 The Meth Snail: Initializing CSRF protection...');
        const csrfInitialized = await initializeCsrf();
        
        if (!csrfInitialized) {
          throw new Error('Failed to initialize CSRF protection');
        }
        
        // Step 2: Check for existing tokens in localStorage
        const token = localStorage.getItem('token');
        const refreshToken = localStorage.getItem('refresh_token');
        
        if (token && refreshToken) {
          console.log('🐹 Hamsters: Found existing tokens, validating...');
          
          // Step 3: Validate tokens by checking auth status
          await dispatch(checkAuthStatus()).unwrap()
            .then(user => {
              if (user) {
                console.log('✅ Authentication restored successfully!');
              } else {
                console.warn('⚠️ Token validation failed despite tokens being present');
                // Clear invalid tokens
                localStorage.removeItem('token');
                localStorage.removeItem('refresh_token');
              }
            })
            .catch(error => {
              console.error('🚨 Token validation failed:', error);
              // Clear invalid tokens
              localStorage.removeItem('token');
              localStorage.removeItem('refresh_token');
            });
        } else {
          console.log('🧙‍♂️ The Stick: No authentication tokens found');
        }
        
        setIsInitialized(true);
      } catch (error) {
        console.error('🚨 Initialization error:', error);
        setInitError(error instanceof Error ? error : new Error('Unknown initialization error'));
        // Still mark as initialized so the app doesn't get stuck
        setIsInitialized(true);
      }
    };

    initialize();
  }, [dispatch]);

  // Loading state
  if (!isInitialized) {
    return (
      <div className="persistence-loading" style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        backgroundColor: '#120258',
        color: 'white',
        fontSize: '1.2rem',
        textAlign: 'center',
        padding: '2rem'
      }}>
        <div style={{
          width: '50px',
          height: '50px',
          border: '5px solid #f3f3f3',
          borderTop: '5px solid #3498db',
          borderRadius: '50%',
          animation: 'spin 2s linear infinite',
          marginBottom: '1rem'
        }}></div>
        <h2>Initializing System Rebellion...</h2>
        <p>Sir Hawkington is validating your authentication credentials</p>
        <style>{
          `@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`
        }</style>
      </div>
    );
  }

  // Error state
  if (initError) {
    return (
      <div className="persistence-error" style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        backgroundColor: '#120258',
        color: 'white',
        fontSize: '1.2rem',
        textAlign: 'center',
        padding: '2rem'
      }}>
        <h2>Authentication Error</h2>
        <p>{initError.message}</p>
        <button 
          onClick={() => window.location.reload()}
          style={{
            padding: '10px 20px',
            backgroundColor: '#3498db',
            color: 'white',
            border: 'none',
            borderRadius: '5px',
            cursor: 'pointer',
            fontSize: '1rem',
            marginTop: '1rem'
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  // Return children when initialized
  return <>{children}</>;
};

export default PersistenceWrapper;