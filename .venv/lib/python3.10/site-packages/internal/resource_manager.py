import asyncio
import json
import logging
import multiprocessing
import os
import platform
import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from enum import Enum, auto
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class CoreType(Enum):
    """Enum for different CPU core types."""
    PERFORMANCE = auto()
    EFFICIENCY = auto()


class M4MaxConfig:
    """Configuration class for M4 Max resource management."""
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.performance_cores = max(1, multiprocessing.cpu_count() // 2)
        self.efficiency_cores = max(1, multiprocessing.cpu_count() - self.performance_cores)
        self.cache_limit_bytes = 1024 * 1024 * 1024  # 1GB default
        
        # Cross-platform memory detection
        try:
            import psutil
            self.memory_limit_bytes = psutil.virtual_memory().total
            self.memory_available = psutil.virtual_memory().available
        except ImportError:
            # Fallback for systems without psutil
            if platform.system() == "Windows":
                import ctypes
                kernel32 = ctypes.windll.kernel32
                self.memory_limit_bytes = kernel32.GetPhysicallyInstalledSystemMemory() * 1024 * 1024
            else:
                # Linux/Mac fallback
                self.memory_limit_bytes = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
            self.memory_available = int(self.memory_limit_bytes * 0.8)


class PerformanceOptimizer:
    """Handles performance optimization and workload distribution"""

    def __init__(self, config: M4MaxConfig):
        self.config = config
        self._perf_executor = ThreadPoolExecutor(
            max_workers=self.config.performance_cores, thread_name_prefix="perf"
        )
        self._eff_executor = ThreadPoolExecutor(
            max_workers=self.config.efficiency_cores, thread_name_prefix="eff"
        )
        self._process_pool = ProcessPoolExecutor(
            max_workers=self.config.performance_cores // 2
        )
        self._io_pool = ThreadPoolExecutor(
            max_workers=self.config.efficiency_cores * 2, thread_name_prefix="io"
        )

    async def run_cpu_bound(
        self, func: Callable, *args, core_type: CoreType = CoreType.PERFORMANCE
    ):
        """Run CPU-bound tasks on appropriate cores"""
        loop = asyncio.get_event_loop()
        executor = (
            self._perf_executor
            if core_type == CoreType.PERFORMANCE
            else self._eff_executor
        )
        return await loop.run_in_executor(executor, func, *args)

    async def run_io_bound(self, func: Callable, *args):
        """Run IO-bound tasks on efficiency cores"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._io_pool, func, *args)

    async def run_parallel_compute(self, func: Callable, *args):
        """Run heavy compute tasks using process pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._process_pool, func, *args)

    def cleanup(self):
        """Cleanup executors"""
        self._perf_executor.shutdown(wait=True)
        self._eff_executor.shutdown(wait=True)
        self._process_pool.shutdown(wait=True)
        self._io_pool.shutdown(wait=True)


class MemoryManager:
    """Manages memory allocation and optimization"""

    def __init__(self, config: M4MaxConfig):
        self.config = config
        self.memory_threshold = 0.8  # 80% memory usage threshold
        self._cached_data: Dict[str, Any] = {}
        self._current_size = 0

    @lru_cache(maxsize=1000)
    def get_cached_data(self, key: str) -> Optional[Any]:
        """Get cached data with LRU caching"""
        return self._cached_data.get(key)

    def _calculate_size(self, value: Any) -> int:
        """Calculate approximate size of value in bytes"""
        if isinstance(value, (str, bytes)):
            return len(value)
        elif isinstance(value, dict):
            return sum(
                self._calculate_size(k) + self._calculate_size(v)
                for k, v in value.items()
            )
        elif isinstance(value, (list, tuple, set)):
            return sum(self._calculate_size(item) for item in value)
        else:
            return 1024  # Default size for other types

    def set_cached_data(self, key: str, value: Any):
        """Set cached data with memory checks"""
        value_size = self._calculate_size(value)

        # If adding this value would exceed cache limit, clear cache first
        if self._current_size + value_size > self.config.cache_limit_bytes:
            self._cached_data.clear()
            self._current_size = 0

        # Remove old value if key exists
        if key in self._cached_data:
            old_size = self._calculate_size(self._cached_data[key])
            self._current_size -= old_size

        # Add new value
        self._cached_data[key] = value
        self._current_size += value_size


class MetadataManager:
    """Manages cache metadata operations with optimizations"""

    def __init__(self, cache_dir: Path, memory_manager: MemoryManager):
        self.cache_dir = cache_dir
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        self.memory_manager = memory_manager
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> dict:
        """Load cache metadata from json file with caching"""
        cached = self.memory_manager.get_cached_data("metadata")
        if cached:
            return cached

        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r") as f:
                    data = json.load(f)
                    self.memory_manager.set_cached_data("metadata", data)
                    return data
            except json.JSONDecodeError:
                return {}
        return {}

    async def save_metadata_async(self):
        """Save metadata asynchronously"""
        try:
            async with asyncio.Lock():
                with open(self.metadata_file, "w") as f:
                    json.dump(self.metadata, f)
        except Exception as e:
            print(f"Error saving cache metadata: {e}")

    def remove_entry(self, filename: str):
        """Remove an entry from metadata"""
        if filename in self.metadata:
            del self.metadata[filename]
            self.memory_manager.set_cached_data("metadata", self.metadata)


class FileOperator:
    """Handles optimized file operations"""

    def __init__(self, perf_optimizer: PerformanceOptimizer):
        self.perf_optimizer = perf_optimizer
        self.chunk_size = 1024 * 1024  # 1MB chunks for file operations

    async def parallel_operation(self, files: List[Path], operation: Callable):
        """Execute file operations in parallel with optimal core distribution"""
        if not files:
            return

        async def run_operation(file: Path):
            if file.is_file():  # Check if file still exists
                try:
                    if file.stat().st_size > self.chunk_size:
                        # Ensure operation is awaited if it's a coroutine
                        result = await self.perf_optimizer.run_cpu_bound(
                            operation, file
                        )
                        if asyncio.iscoroutine(result):
                            await result
                    else:
                        result = await self.perf_optimizer.run_io_bound(operation, file)
                        if asyncio.iscoroutine(result):
                            await result
                except Exception as e:
                    print(f"Error in operation for {file}: {e}")

        tasks = [asyncio.create_task(run_operation(file)) for file in files]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    async def get_file_size(file: Path) -> int:
        """Get size of a single file asynchronously"""
        try:
            return file.stat().st_size if file.exists() else 0
        except (OSError, IOError):
            return 0

    async def calculate_directory_size(self, files: List[Path]) -> int:
        """Calculate directory size with parallel processing"""
        if not files:
            return 0

        if len(files) > 1000:
            sizes = await asyncio.gather(
                *[
                    self.perf_optimizer.run_parallel_compute(self.get_file_size, f)
                    for f in files
                    if f.is_file()
                ],
                return_exceptions=True,
            )
            return sum(s for s in sizes if not isinstance(s, Exception))

        # For smaller directories, use gather to run all size calculations concurrently
        sizes = await asyncio.gather(
            *[self.get_file_size(f) for f in files if f.is_file()]
        )
        return sum(sizes)


class CacheManager:
    """Manages cache operations with M4 optimizations"""

    def __init__(
        self,
        cache_dir: Path,
        max_cache_age: int,
        config: M4MaxConfig,
        metadata_manager: MetadataManager,
        file_operator: FileOperator,
        memory_manager: MemoryManager,
    ):
        self.cache_dir = cache_dir
        self.max_cache_age = max_cache_age
        self.config = config
        self.metadata_manager = metadata_manager
        self.file_operator = file_operator
        self.memory_manager = memory_manager
        self.ensure_cache_dir()

    def ensure_cache_dir(self):
        """Ensure cache directory exists with optimal permissions"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.cache_dir, 0o700)

    async def clear_old_caches(self):
        """Clear old caches asynchronously"""
        current_time = time.time()
        try:
            files_to_remove = []
            for item in self.cache_dir.glob("*"):  # Changed to sync for reliability
                if item.is_file() and item.name != "cache_metadata.json":
                    try:
                        age = current_time - item.stat().st_mtime
                        if age > self.max_cache_age:
                            files_to_remove.append(item)
                            self.metadata_manager.remove_entry(item.name)
                    except (OSError, IOError) as e:
                        print(f"Error checking file age: {e}")

            if files_to_remove:

                async def remove_file(file: Path):
                    try:
                        if file.exists():
                            file.unlink()
                            return True
                    except Exception as e:
                        print(f"Error removing {file}: {e}")
                        return False

                # Use parallel_operation to handle file deletion
                await self.file_operator.parallel_operation(
                    files_to_remove, remove_file
                )
                await self.metadata_manager.save_metadata_async()

                # Verify deletions
                for file in files_to_remove:
                    if file.exists():
                        print(f"Warning: Failed to delete {file}")
        except Exception as e:
            print(f"Error clearing old caches: {e}")

    async def clear_current_caches(self):
        """Clear current caches asynchronously"""
        try:
            preserve_files = {"last_summary", "cache_metadata.json"}
            files_to_remove = [
                item
                for item in self.cache_dir.glob("*")
                if item.is_file() and item.name not in preserve_files
            ]

            if files_to_remove:

                async def remove_file(file: Path):
                    try:
                        if file.exists():
                            file.unlink()
                            self.metadata_manager.remove_entry(file.name)
                            return True
                    except Exception as e:
                        print(f"Error removing {file}: {e}")
                        return False

                await self.file_operator.parallel_operation(
                    files_to_remove, remove_file
                )
                await self.metadata_manager.save_metadata_async()

                # Verify deletions
                for file in files_to_remove:
                    if file.exists():
                        print(f"Warning: Failed to delete {file}")
        except Exception as e:
            print(f"Error clearing current caches: {e}")

    async def get_cache_size(self) -> int:
        """Get cache size asynchronously"""
        try:
            files = [f for f in self.cache_dir.glob("**/*") if f.is_file()]
            return await self.file_operator.calculate_directory_size(files)
        except Exception as e:
            print(f"Error calculating cache size: {e}")
            return 0

    async def optimize_cache(self):
        """Optimize cache with improved algorithms"""
        current_size = await self.get_cache_size()

        if current_size > self.config.cache_limit_bytes:
            try:
                files = []
                for item in self.cache_dir.glob("*"):
                    if item.is_file() and item.name not in {
                        "last_summary",
                        "cache_metadata.json",
                    }:
                        try:
                            files.append((item, item.stat().st_atime))
                        except Exception:
                            continue

                if files:
                    files.sort(key=lambda x: x[1])
                    size_to_remove = current_size - self.config.cache_limit_bytes
                    current_removed = 0

                    for file, _ in files:
                        if current_removed >= size_to_remove:
                            break
                        try:
                            if file.exists():
                                size = file.stat().st_size
                                file.unlink()
                                self.metadata_manager.remove_entry(file.name)
                                current_removed += size
                        except Exception as e:
                            print(f"Error removing file during optimization: {e}")
                            continue

                    await self.metadata_manager.save_metadata_async()

                    # Wait for file operations to complete
                    await asyncio.sleep(0.1)
            except Exception as e:
                print(f"Error during cache optimization: {e}")


class ResourceConfig(M4MaxConfig):
    """Resource configuration with M4 Max optimizations."""
    def __init__(self, cache_dir: Path):
        super().__init__(cache_dir)

    def _get_available_memory(self) -> int:
        """Get available system memory in bytes."""
        try:
            import psutil
            return psutil.virtual_memory().available
        except ImportError:
            # Fallback to a conservative estimate of 80% of total memory
            return int(self.memory_limit_bytes * 0.8)


class ResourceManager:
    """Enhanced resource manager for M4 Max"""

    def __init__(self, cache_dir: Path):
        self.config = ResourceConfig(cache_dir)
        self.perf_optimizer = PerformanceOptimizer(self.config)
        self.memory_manager = MemoryManager(self.config)
        self.metadata_manager = MetadataManager(
            self.config.cache_dir, self.memory_manager
        )
        self.file_operator = FileOperator(self.perf_optimizer)
        self.cache_manager = CacheManager(
            self.config.cache_dir,
            86400,  # Default max_cache_age
            self.config,
            self.metadata_manager,
            self.file_operator,
            self.memory_manager,
        )
        self._setup_cache_dir()

    def _setup_cache_dir(self):
        """Setup cache directory with proper permissions."""
        try:
            self.config.cache_dir.mkdir(parents=True, exist_ok=True)
            self.config.cache_dir.chmod(0o700)  # Secure permissions
        except Exception as e:
            print(f"Warning: Could not setup cache directory: {e}", file=sys.stderr)

    def get_core_allocation(self, core_type: CoreType) -> int:
        """Get number of cores to allocate based on type."""
        if core_type == CoreType.PERFORMANCE:
            return self.config.performance_cores
        return self.config.efficiency_cores

    def get_memory_allocation(self, percentage: float = 0.8) -> int:
        """Get memory allocation in bytes."""
        return int(
            min(
                self.config.memory_available * percentage,
                self.config.memory_limit_bytes * percentage,
            )
        )

    def get_cache_allocation(self) -> int:
        """Get cache allocation in bytes."""
        return self.config.cache_limit_bytes

    async def process_batch(
        self,
        items: List[Any],
        processor: Callable,
        batch_size: int = 100,
        core_type: CoreType = CoreType.PERFORMANCE,
    ) -> List[Any]:
        """Process items in optimized batches using available cores.

        Args:
            items: List of items to process
            processor: Callable that processes a single item (can be sync or async)
            batch_size: Size of each batch (default 100)
            core_type: Type of cores to use (default PERFORMANCE)

        Returns:
            List of processed results
        """
        results = []

        async def process_batch(batch: List[Any]) -> List[Any]:
            try:
                if core_type == CoreType.PERFORMANCE:
                    batch_results = await asyncio.gather(
                        *[
                            self.perf_optimizer.run_cpu_bound(processor, item)
                            for item in batch
                        ],
                        return_exceptions=True,
                    )
                else:
                    batch_results = await asyncio.gather(
                        *[
                            self.perf_optimizer.run_io_bound(processor, item)
                            for item in batch
                        ],
                        return_exceptions=True,
                    )

                # Filter out exceptions and log them
                filtered_results = []
                for i, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        logging.error(f"Error processing item {batch[i]}: {result}")
                    else:
                        filtered_results.append(result)
                return filtered_results
            except Exception as e:
                logging.error(f"Error processing batch: {e}")
                return []

        try:
            # Process items in batches
            for i in range(0, len(items), batch_size):
                batch = items[i : i + batch_size]
                batch_results = await process_batch(batch)
                results.extend(batch_results)

                # Allow other tasks to run between batches
                await asyncio.sleep(0)
        except Exception as e:
            logging.error(f"Error in batch processing: {e}")

        return results

    async def cleanup(self):
        """Asynchronous cleanup operations"""
        try:
            # Clear old caches first
            await self.cache_manager.clear_old_caches()

            # Check cache size and optimize if needed
            cache_size = await self.cache_manager.get_cache_size()
            if cache_size > self.config.cache_limit_bytes:
                await self.cache_manager.optimize_cache()

            # Update metadata
            await self.metadata_manager.save_metadata_async()

            # Ensure cache directory permissions are correct
            os.chmod(self.config.cache_dir, 0o700)

            # Wait for all operations to complete
            await asyncio.sleep(0.1)
        finally:
            self.perf_optimizer.cleanup()


def get_resource_manager(cache_dir: Optional[Path] = None) -> ResourceManager:
    """Get or create resource manager instance."""
    if cache_dir is None:
        # Use platform-specific cache directory
        if platform.system() == "Windows":
            cache_dir = Path(os.getenv("LOCALAPPDATA", "")) / "safespace"
        else:
            cache_dir = Path.home() / ".cache" / "safespace"
    return ResourceManager(cache_dir)
