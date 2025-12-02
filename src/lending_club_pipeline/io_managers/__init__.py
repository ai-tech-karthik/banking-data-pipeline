"""
IO Managers for the LendingClub data pipeline.

This module provides IO managers for different storage formats and backends.
"""

from .parquet_manager import ParquetIOManager

__all__ = ["ParquetIOManager"]
