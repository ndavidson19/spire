# LLM Schema Toolkit

A powerful toolkit for dynamic schema generation and structured data processing with Large Language Models. This library provides high-level abstractions for generating synthetic datasets, parsing documents, and creating structured outputs from LLMs.

## Features

- 🔄 Dynamic schema generation based on content types
- 📄 Document parsing and structure extraction
- 🤖 Synthetic data generation for LLM training
- 🔗 Integration with popular LLM preprocessing tools
- 🎯 Type-safe data handling with Pydantic

## Installation

```bash
uv venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install llm-schema-toolkit
```

## Quick Start

```python
from llm_schema_toolkit import SchemaGenerator, DocumentProcessor
from llm_schema_toolkit.synthetic_data import DataGenerator

# Define a base schema for your data
schema = SchemaGenerator.from_template("customer_interaction")

# Process documents and generate matching schemas
doc_processor = DocumentProcessor(schema)
structured_data = await doc_processor.process_document("path/to/document.txt")

# Generate synthetic data matching your schema
data_gen = DataGenerator(schema)
synthetic_dataset = data_gen.generate(
    num_samples=100,
    constraints={
        "length": "medium",
        "style": "formal",
        "domain": "customer_service"
    }
)

# Use with your favorite LLM
response = await llm.generate(
    prompt=synthetic_dataset.to_prompt(),
    schema=schema.to_json_schema()
)
```

## Advanced Usage

### Custom Schema Rules

```python
from llm_schema_toolkit import SchemaRule, ContentType

# Define custom rules for schema generation
rules = [
    SchemaRule(
        content_type=ContentType.CONVERSATION,
        extractors=[
            "sentiment",
            "key_topics",
            "action_items"
        ],
        validation_rules={
            "min_length": 50,
            "required_fields": ["speaker", "timestamp"]
        }
    )
]

# Create schema generator with custom rules
schema_gen = SchemaGenerator(rules=rules)
dynamic_schema = schema_gen.generate_for_content("customer_chat_log.txt")
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.