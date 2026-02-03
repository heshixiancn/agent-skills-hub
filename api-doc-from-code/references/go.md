# Go Gin Extraction Notes

## Router patterns
- `router.GET("/path", handler)`
- `group := router.Group("/v1")` then `group.POST("/path", handler)`
- Chained groups: `router.Group("/v1").GET("/path", handler)`

## Parameter hints
- `c.Param("id")` -> path parameter `id`
- `c.Query("q")` -> query parameter `q`
- `c.ShouldBindJSON(&req)` -> JSON body model
- `c.Bind(...)` or `c.ShouldBind(...)` -> body/form model

## Response hints
- `c.JSON(status, payload)` -> response status and model
- `c.String(status, ...)` -> text response

## Model hints
- Struct tags: `json:"field"` or `form:"field"` indicate names
- Embedded structs indicate nested response models

## Summary heuristics
- Use handler comment if present.
- Otherwise infer from handler name.
