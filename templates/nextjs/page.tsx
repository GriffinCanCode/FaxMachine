import { GetServerSideProps, NextPage } from 'next';
import Head from 'next/head';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';

// Import components
import Layout from '@/components/Layout';
import LoadingSpinner from '@/components/LoadingSpinner';
import ErrorMessage from '@/components/ErrorMessage';

// Import types
import { DataType } from '@/types';

// Import API and utilities
import { fetchData } from '@/lib/api';

interface PageProps {
  initialData: DataType[];
  error?: string;
}

const Page: NextPage<PageProps> = ({ initialData, error: initialError }) => {
  const router = useRouter();
  const { id } = router.query;
  
  // State management
  const [data, setData] = useState<DataType[]>(initialData);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(initialError || null);
  
  // Fetch additional data client-side if needed
  useEffect(() => {
    if (id) {
      const fetchAdditionalData = async () => {
        setLoading(true);
        
        try {
          const result = await fetchData(id as string);
          setData(result);
        } catch (err) {
          setError('Failed to load data');
          console.error(err);
        } finally {
          setLoading(false);
        }
      };
      
      fetchAdditionalData();
    }
  }, [id]);
  
  // Handle user interaction
  const handleAction = async () => {
    // Handle user action
  };
  
  return (
    <>
      <Head>
        <title>Page Title | My App</title>
        <meta name="description" content="Page description" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      
      <Layout>
        <div className="container mx-auto px-4 py-8">
          <h1 className="text-3xl font-bold mb-6">Page Title</h1>
          
          {loading ? (
            <LoadingSpinner />
          ) : error ? (
            <ErrorMessage message={error} />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {data.map((item) => (
                <div 
                  key={item.id} 
                  className="bg-white p-6 rounded-lg shadow-md"
                >
                  <h2 className="text-xl font-semibold mb-2">{item.title}</h2>
                  <p className="text-gray-700">{item.description}</p>
                  <button
                    onClick={handleAction}
                    className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition"
                  >
                    View Details
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </Layout>
    </>
  );
};

export const getServerSideProps: GetServerSideProps = async (context) => {
  try {
    // Fetch initial data from API
    const data = await fetchData();
    
    return {
      props: {
        initialData: data,
      },
    };
  } catch (error) {
    console.error('Error fetching data:', error);
    
    return {
      props: {
        initialData: [],
        error: 'Failed to load initial data',
      },
    };
  }
};

export default Page; 