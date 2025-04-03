import React from 'react';
import { FC } from 'react';

interface ComponentProps {
  /** Description of prop */
  propName?: string;
}

/**
 * Component description
 * 
 * @example
 * ```tsx
 * <Component propName="value" />
 * ```
 */
const Component: FC<ComponentProps> = ({ propName = '' }) => {
  // State hooks
  // const [state, setState] = useState(initialState);
  
  // Effect hooks
  // useEffect(() => {
  //   // Effect logic
  //   return () => {
  //     // Cleanup logic
  //   };
  // }, [dependencies]);
  
  // Event handlers
  const handleEvent = () => {
    // Handle event
  };
  
  return (
    <div className="component">
      {propName}
    </div>
  );
};

export default Component; 