"""Foreach loops: iterate over a list of items with FunctionalPipeline.foreach().

Demonstrates scraping multiple URLs in a fan-out pattern.
Usage: python 04_pipelines/loops.py
"""
from datapizza.core.models import PipelineComponent
from datapizza.pipeline import Dependency, FunctionalPipeline

class URLScraper(PipelineComponent):
    def _run(self, num_urls: int = 5):
        """Simulate fetching URLs."""
        urls = [f"https://example.com/page{i}" for i in range(num_urls)]
        print(f"Found {len(urls)} URLs")
        return urls

class PageProcessor(PipelineComponent):
    def _run(self, item: str):
        """Process a single URL"""
        print(f"Processing {item}")
        # Simulate processing 
        return {"url": item, "content": f"Content from {item}"}

pipeline = (
    FunctionalPipeline()
    .run("get_urls", URLScraper(), kwargs={"num_urls": 3})
    .foreach(
        name="process_url",
        dependencies=[Dependency(node_name="get_urls")],
        do=PageProcessor(),
    )
)

result = pipeline.execute()
print(f"Processed {len(result['process_url'])} pages")
