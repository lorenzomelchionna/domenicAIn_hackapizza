"""Branching pipelines: conditional execution with FunctionalPipeline.branch().

Runs different sub-pipelines depending on data validation results.
Usage: python 04_pipelines/branching.py
"""
from datapizza.pipeline import FunctionalPipeline, Dependency

from components import DataLoader, DataValidator, DataTransformer, DataSaver, DataCleaner

# pipeline = (
#     FunctionalPipeline()
#     .run("load_data", DataLoader(), kwargs={"filepath": "input.csv"})
#     .then("validate", DataValidator(), target_key="data")
#     .then("transform", DataTransformer(), target_key="data")
#     .then("save", DataSaver(), kwargs={"output_path": "output.csv"})
# )

valid_data_pipeline = (
    FunctionalPipeline()
    .run("transform", DataTransformer())
    .then("save_clean", DataSaver(), target_key="data", kwargs={"output_path": "cleaned_data.csv"})
)

invalid_data_pipeline = (
    FunctionalPipeline()
    .run("clean", DataCleaner())
    .then("save_dirty", DataSaver(), target_key="data", kwargs={"output_path": "invalid_data.csv"})
)

pipeline = (
    FunctionalPipeline()
    .run("load_data", DataLoader(), kwargs={"filepath": "input.csv"})
    .then("validate", DataValidator(), target_key="data")
    .branch(
        condition=lambda ctx : ctx.get("validate")["is_valid"],
        dependencies=[Dependency(node_name="validate")],
        if_true=valid_data_pipeline,
        if_false=invalid_data_pipeline,
    )
)

result = valid_data_pipeline.execute(
    initial_data={
        "transform": {"data": "valid_data.csv"}
    }
)
print(f"Pipeline completed: {result}")
# # Execute the pipeline
# result = pipeline.execute(
#     initial_data={
#         "load_data": {"filepath": "different_file.csv"},
#         "save": {"output_path": "different_output.csv"}
#     }
# )
# print(f"Pipeline completed: {result}")
