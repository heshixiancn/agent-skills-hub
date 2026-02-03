# Java Spring 提取说明

## 常见控制器标识
- `@RestController`, `@Controller`
- 类级 `@RequestMapping("/base")`

## 方法注解
- `@GetMapping("/path")`, `@PostMapping`, `@PutMapping`, `@DeleteMapping`, `@PatchMapping`
- `@RequestMapping(value = "/path", method = RequestMethod.GET)`

## 路径拼接
- 组合类级 `@RequestMapping` 与方法级映射。
- 规范化斜杠，避免出现双斜杠 `//`。

## 参数提示
- `@PathVariable("id") Long id` -> 路径参数 `id`
- `@RequestParam("q") String q` -> 查询参数 `q`
- `@RequestHeader("X-Id")` -> Header 参数
- `@RequestBody` -> 请求体模型
- `@ModelAttribute` -> 表单或查询绑定

## 响应提示
- 方法返回类型：`ResponseEntity<T>` 或 `T`
- `@ResponseStatus` 表示非 200 的默认状态码
- 异常可能映射为错误响应（不明确时标记 TODO）

## 摘要规则
- 优先使用方法名或 Javadoc 摘要。
- 若存在 Javadoc，抽取首句作为摘要。
