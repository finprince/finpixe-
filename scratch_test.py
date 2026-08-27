from ast_rim.llm_pipeline import process_llm_response

text = """```python
def test(data):
    return sum([x for x in data])
```"""

print(process_llm_response(text))
