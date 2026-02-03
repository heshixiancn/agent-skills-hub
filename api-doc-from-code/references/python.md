# Python FastAPI/Flask Extraction Notes

## FastAPI

### Decorators
- `@app.get("/path")`, `@router.post("/path")`, etc.
- `@app.api_route("/path", methods=["GET", "POST"])`

### Parameter hints
- Function parameters with type hints map to query/path/body depending on FastAPI rules.
- `Path(...)`, `Query(...)`, `Body(...)`, `Header(...)` provide explicit sources.
- Pydantic models in parameters typically represent request bodies.

### Response hints
- Return type hints: `-> Model`
- `response_model=Model` in decorator
- `responses={...}` for status and schema mapping

## Flask

### Decorators
- `@app.route("/path", methods=["GET", "POST"])`
- `@bp.route("/path")` for blueprints

### Parameter hints
- `request.args` -> query parameters
- `request.json` or `request.get_json()` -> JSON body
- `request.form` -> form fields
- URL converters in route: `/user/<int:id>` -> path param

### Response hints
- `return jsonify(...)` or `(payload, status)`
- `make_response(...)` or explicit status codes

## Summary heuristics
- Use function docstring first line if present.
- Otherwise derive a short summary from function name.
