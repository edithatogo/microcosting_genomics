"""Performance optimization tools for microcosting analysis."""

import pandas as pd
import time
from typing import Dict, Any, Callable, Optional
from .logging_config import get_logger
import numpy as np
from functools import wraps


logger = get_logger(__name__)


class PerformanceProfiler:
    """Profiles performance of operations and provides optimization suggestions."""
    
    def __init__(self):
        """Initialize the performance profiler."""
        self.metrics: Dict[str, Dict[str, Any]] = {}
        self.call_counts: Dict[str, int] = {}
        
    def profile(self, operation_name: str):
        """Decorator to profile a function."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                start_memory = self._get_memory_usage()
                
                error_occurred = None
                try:
                    result = func(*args, **kwargs)
                    success = True
                except Exception as e:
                    result = None
                    success = False
                    error_occurred = e
                
                end_time = time.time()
                end_memory = self._get_memory_usage()
                
                # Record metrics
                if operation_name not in self.metrics:
                    self.metrics[operation_name] = {
                        "call_count": 0,
                        "total_time": 0,
                        "avg_time": 0,
                        "max_time": 0,
                        "min_time": float('inf'),
                        "total_memory": 0,
                        "avg_memory": 0,
                        "max_memory": 0,
                        "errors": 0
                    }
                
                execution_time = end_time - start_time
                memory_used = end_memory - start_memory
                
                metrics = self.metrics[operation_name]
                metrics["call_count"] += 1
                metrics["total_time"] += execution_time
                metrics["avg_time"] = metrics["total_time"] / metrics["call_count"]
                metrics["max_time"] = max(metrics["max_time"], execution_time)
                metrics["min_time"] = min(metrics["min_time"], execution_time)
                
                metrics["total_memory"] += memory_used
                metrics["avg_memory"] = metrics["total_memory"] / metrics["call_count"]
                metrics["max_memory"] = max(metrics["max_memory"], memory_used)
                
                if not success:
                    metrics["errors"] += 1
                
                logger.info(f"Profiled {operation_name}: {execution_time:.4f}s, {memory_used:.2f}MB")
                
                if error_occurred:
                    raise error_occurred
                    
                return result
            return wrapper
        return decorator
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            return 0.0
    
    def get_report(self) -> Dict[str, Dict[str, Any]]:
        """Get performance report.
        
        Returns:
            Dict[str, Dict[str, Any]]: Performance metrics for all operations
        """
        return self.metrics
    
    def print_report(self) -> None:
        """Print formatted performance report."""
        if not self.metrics:
            print("No performance data collected.")
            return
        
        print("\nPerformance Report")
        print("=" * 80)
        print(f"{'Operation':<30} {'Calls':<8} {'Avg Time':<12} {'Max Time':<12} {'Avg Memory':<12} {'Errors':<8}")
        print("-" * 80)
        
        for operation, metrics in self.metrics.items():
            print(f"{operation:<30} {metrics['call_count']:<8} {metrics['avg_time']:<12.4f} "
                  f"{metrics['max_time']:<12.4f} {metrics['avg_memory']:<12.2f} {metrics['errors']:<8}")


class DataOptimizer:
    """Optimizes data handling for better performance."""
    
    @staticmethod
    def optimize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Optimize DataFrame memory usage.
        
        Args:
            df (pd.DataFrame): DataFrame to optimize
            
        Returns:
            pd.DataFrame: Optimized DataFrame
        """
        logger.info(f"Optimizing DataFrame with shape {df.shape}")
        start_memory = df.memory_usage(deep=True).sum() / 1024 / 1024  # MB
        
        optimized_df = df.copy()
        
        # Optimize numeric columns
        for col in optimized_df.columns:
            if optimized_df[col].dtype == 'object':
                # Try to convert to numeric
                try:
                    numeric_series = pd.to_numeric(optimized_df[col], errors='coerce')
                    if not numeric_series.isna().all():
                        optimized_df[col] = numeric_series
                        logger.debug(f"Converted column {col} to numeric")
                except Exception:
                    pass
            elif optimized_df[col].dtype == 'float64':
                # Downcast floats
                optimized_df[col] = pd.to_numeric(optimized_df[col], downcast='float')
                logger.debug(f"Downcasted float column {col}")
            elif optimized_df[col].dtype == 'int64':
                # Downcast integers
                optimized_df[col] = pd.to_numeric(optimized_df[col], downcast='integer')
                logger.debug(f"Downcasted integer column {col}")
        
        end_memory = optimized_df.memory_usage(deep=True).sum() / 1024 / 1024  # MB
        savings = start_memory - end_memory
        logger.info(f"Memory optimization: {start_memory:.2f}MB -> {end_memory:.2f}MB (saved {savings:.2f}MB)")
        
        return optimized_df
    
    @staticmethod
    def chunked_processing(df: pd.DataFrame, chunk_size: int = 1000) -> pd.DataFrame:
        """Process DataFrame in chunks to reduce memory usage.
        
        Args:
            df (pd.DataFrame): DataFrame to process
            chunk_size (int): Size of each chunk
            
        Returns:
            pd.DataFrame: Processed DataFrame
        """
        logger.info(f"Processing DataFrame in chunks of size {chunk_size}")
        
        # This is a placeholder - in a real implementation, this would
        # apply some processing to each chunk and combine results
        chunks = np.array_split(df, max(1, len(df) // chunk_size))
        processed_chunks = []
        
        for i, chunk in enumerate(chunks):
            logger.debug(f"Processing chunk {i+1}/{len(chunks)} with {len(chunk)} rows")
            # In a real implementation, we would do some processing here
            processed_chunks.append(chunk)
        
        return pd.concat(processed_chunks, ignore_index=True) if processed_chunks else df


class ParallelProcessor:
    """Handles parallel processing for better performance."""
    
    @staticmethod
    def parallel_apply(df: pd.DataFrame, func: Callable, column: str, 
                      n_cores: int = 4) -> pd.Series:
        """Apply function to column in parallel.
        
        Args:
            df (pd.DataFrame): DataFrame to process
            func (Callable): Function to apply
            column (str): Column to apply function to
            n_cores (int): Number of cores to use
            
        Returns:
            pd.Series: Result of applying function
        """
        try:
            import multiprocessing as mp
            from functools import partial
            
            logger.info(f"Applying function in parallel to column {column} using {n_cores} cores")
            
            # Split data into chunks
            chunks = np.array_split(df[column], n_cores)
            
            # Create partial function with fixed arguments
            partial_func = partial(func)
            
            # Process in parallel
            with mp.Pool(n_cores) as pool:
                results = pool.map(partial_func, chunks)
            
            # Combine results
            combined_result = pd.concat(results, ignore_index=True)
            return combined_result
        except ImportError:
            logger.warning("Multiprocessing not available, falling back to sequential processing")
            return df[column].apply(func)
        except Exception as e:
            logger.error(f"Error in parallel processing: {e}")
            return df[column].apply(func)


class CachingOptimizer:
    """Implements caching strategies for performance optimization."""
    
    def __init__(self):
        """Initialize the caching optimizer."""
        self.cache: Dict[str, Any] = {}
        self.access_counts: Dict[str, int] = {}
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.
        
        Args:
            key (str): Cache key
            
        Returns:
            Any: Cached value or None if not found
        """
        if key in self.cache:
            self.access_counts[key] = self.access_counts.get(key, 0) + 1
            logger.debug(f"Cache hit for key {key}")
            return self.cache[key]
        logger.debug(f"Cache miss for key {key}")
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Set value in cache.
        
        Args:
            key (str): Cache key
            value (Any): Value to cache
        """
        self.cache[key] = value
        self.access_counts[key] = self.access_counts.get(key, 0) + 1
        logger.debug(f"Set cache for key {key}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dict[str, Any]: Cache statistics
        """
        total_accesses = sum(self.access_counts.values())
        return {
            "cache_size": len(self.cache),
            "total_accesses": total_accesses,
            "hit_rate": total_accesses / max(1, len(self.access_counts)),
            "most_accessed": sorted(self.access_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        }


# Example usage function
def example_usage():
    """Example of how to use the performance optimization tools."""
    print("Performance Optimization Tools Example")
    
    # Create profiler
    profiler = PerformanceProfiler()
    
    # Profile a function
    @profiler.profile("data_processing")
    def process_data():
        # Simulate some data processing
        df = pd.DataFrame({
            "A": range(10000),
            "B": range(10000, 20000),
            "C": [f"item_{i}" for i in range(10000)]
        })
        
        # Optimize the DataFrame
        optimizer = DataOptimizer()
        optimized_df = optimizer.optimize_dataframe(df)
        
        # Process in chunks
        chunked_df = optimizer.chunked_processing(optimized_df, chunk_size=1000)
        
        return chunked_df
    
    # Run the function
    result = process_data()
    print(f"Processed DataFrame with shape {result.shape}")
    
    # Print performance report
    profiler.print_report()
    
    # Test caching
    cache = CachingOptimizer()
    cache.set("test_key", "test_value")
    value = cache.get("test_key")
    print(f"Retrieved from cache: {value}")
    
    stats = cache.get_stats()
    print(f"Cache stats: {stats}")


if __name__ == "__main__":
    example_usage()