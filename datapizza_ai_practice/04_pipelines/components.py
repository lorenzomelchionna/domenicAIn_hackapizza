"""Pipeline components: reusable PipelineComponent subclasses for data processing.

Defines DataLoader, DataValidator, DataTransformer, and DataSaver.
Used by branching.py and loops.py examples.
"""
import pandas as pd

from datapizza.core.models import PipelineComponent

class DataLoader(PipelineComponent):
    def _run(self, filepath: str):
        """Load data from a CSV file."""
        df = pd.read_csv(filepath)
        print(f"Loaded {len(df)} rows from {filepath}")
        return df

class DataValidator(PipelineComponent):
    def _run(self, data: pd.DataFrame):
        """Validate data quality."""
        is_valid = not data.isnull().any().any()
        print(f"Data validation: {'passed' if is_valid else 'failed'}")
        return {"is_valid": is_valid, data: data}

class DataTransformer(PipelineComponent):
    def _run(self, data: pd.DataFrame):
        """Transform data."""
        # Example: normalize numerical columns
        numeric_cols = data.select_dtypes(include=['number']).columns
        data[numeric_cols] = data[numeric_cols].apply(lambda x: (x - x.mean()) / x.std())
        print("Data transformed successfully")
        return data

class DataSaver(PipelineComponent):
    def _run(self, data: pd.DataFrame, output_path: str):
        """Save data to a CSV file."""
        data.to_csv(output_path, index=False)
        print(f"Data saved to {output_path}")
        return {"success": True, "path": output_path}
