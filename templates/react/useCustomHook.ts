import { useState, useEffect } from 'react';

/**
 * Custom hook description
 * 
 * @param param - Description of parameter
 * @returns Description of return value
 * 
 * @example
 * ```tsx
 * const { data, loading, error } = useCustomHook('param');
 * ```
 */
const useCustomHook = (param: string) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let isMounted = true;
    
    const fetchData = async () => {
      if (!param) return;
      
      setLoading(true);
      setError(null);
      
      try {
        // Fetch or process data here
        const result = await Promise.resolve(param);
        
        if (isMounted) {
          setData(result);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err : new Error('Unknown error'));
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };
    
    fetchData();
    
    // Cleanup function
    return () => {
      isMounted = false;
    };
  }, [param]);
  
  return { data, loading, error };
};

export default useCustomHook; 