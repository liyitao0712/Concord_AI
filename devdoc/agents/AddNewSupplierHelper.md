# AddNewSupplierHelper Agent

## 概述

AddNewSupplierHelper 是新供应商信息自动填充 Agent，负责：
- 根据公司名称通过 LLM + Web Search 搜索供应商信息
- 返回结构化数据，用于自动填充供应商表单
- 减少人工录入供应商信息的工作量

此 Agent 是 AddNewClientHelper 的供应商版镜像实现，适配供应商特有字段（如 `main_products`）。同样**直接使用 Anthropic SDK**（而非 LiteLLM），因为 LiteLLM 不支持 Anthropic 的 `web_search_20250305` 服务端工具类型。

## 基本信息

| 属性 | 值 |
|------|-----|
| name | add_new_supplier_helper |
| display_name | 新供应商信息助手 |
| description | 根据公司名称自动搜索并填充供应商信息 |
| prompt_name | add_new_supplier_helper |
| tools | web_search（Anthropic 服务端工具，最多 5 次搜索） |
| max_iterations | 1 |

## 执行流程

```
输入（公司名称）
    ↓
[search] 搜索节点
    ├─ 渲染 Prompt（注入公司名称）
    ├─ 获取系统提示 + 模型配置
    ├─ 调用 Anthropic SDK + web_search 服务端工具
    └─ 提取文本内容（过滤 web_search_tool_result）
    ↓
[output] 输出节点
    ├─ 解析 JSON（三级回退策略）
    └─ 映射到 Supplier 模型字段
    ↓
返回结构化供应商数据
```

## 输入格式

通过 `input_data` 传递：

```python
{
    "company_name": "公司全称",
}
```

或直接使用便捷方法：

```python
result = await add_new_supplier_helper.lookup("Shenzhen ABC Electronics Co., Ltd.")
```

## 输出格式

```json
{
    "short_name": "ABC Electronics",
    "country": "China",
    "region": "Asia",
    "industry": "Electronics Manufacturing",
    "company_size": "large",
    "main_products": "LED displays, PCB assemblies, power supplies",
    "website": "https://abc-electronics.cn",
    "email": "sales@abc-electronics.cn",
    "phone": "+86-755-12345678",
    "address": "深圳市宝安区工业园 A 栋",
    "tags": ["electronics", "manufacturer", "led"],
    "notes": "Founded in 2010, ISO9001 certified...",
    "confidence": 0.90,
    "company_name": "Shenzhen ABC Electronics Co., Ltd.",
    "llm_model": "claude-sonnet-4-20250514",
    "token_used": 1456
}
```

### 与 AddNewClientHelper 输出的区别

| 字段 | ClientHelper | SupplierHelper | 说明 |
|------|-------------|----------------|------|
| `main_products` | 无 | 有 | 供应商特有：主营产品 |

### 错误降级

搜索失败时返回空结果：

```json
{
    "short_name": null,
    "country": null,
    "region": null,
    "industry": null,
    "company_size": null,
    "main_products": null,
    "website": null,
    "email": null,
    "phone": null,
    "address": null,
    "tags": [],
    "notes": null,
    "confidence": 0,
    "error": "错误信息"
}
```

## 核心方法

### lookup()

```python
async def lookup(self, company_name: str) -> dict:
    """
    搜索供应商信息（便捷方法）

    Args:
        company_name: 公司全称

    Returns:
        dict: 可直接用于 SupplierCreate 的结构化数据
    """
```

## JSON 解析策略

LLM 返回的内容通过三级回退策略解析：

1. **直接 `json.loads`** - 标准 JSON 格式
2. **Markdown 代码块提取** - 从 ` ```json ``` ` 中提取
3. **花括号定位** - 找第一个 `{` 到最后一个 `}`

## 技术细节

### 为什么使用 Anthropic SDK 而非 LiteLLM

与 AddNewClientHelper 相同，Anthropic 的 `web_search_20250305` 是服务端工具（Server-side Tool），LiteLLM 不支持此类工具类型，因此直接使用 `anthropic.AsyncAnthropic` 客户端。

### 模型名称转换

LiteLLM 格式的模型名（如 `anthropic/claude-sonnet-4-20250514`）会通过 `_resolve_anthropic_model()` 方法自动转换为 Anthropic SDK 格式（如 `claude-sonnet-4-20250514`）。

### 超时配置

- Anthropic SDK 超时：120 秒（web_search 可能较慢）
- web_search 最大调用次数：5 次

## Prompt 配置

| Prompt Key | 用途 | 文件 |
|------------|------|------|
| `add_new_supplier_helper_system` | 系统提示 | `backend/app/llm/prompts/defaults.py` |
| `add_new_supplier_helper` | 用户提示模板 | `backend/app/llm/prompts/defaults.py` |

用户提示模板支持以下变量：
- `{{company_name}}` - 公司全称

## 相关文件

- Agent: `backend/app/agents/add_new_supplier_helper.py`
- API 集成: `backend/app/api/suppliers.py`
- Prompt 默认值: `backend/app/llm/prompts/defaults.py`
- 镜像实现参考: `backend/app/agents/add_new_client_helper.py`

## 使用示例

```python
from app.agents.add_new_supplier_helper import add_new_supplier_helper

# 方式一：使用便捷方法
result = await add_new_supplier_helper.lookup("Shenzhen ABC Electronics Co., Ltd.")

if result.get("confidence", 0) > 0.5:
    print(f"公司简称: {result['short_name']}")
    print(f"国家: {result['country']}")
    print(f"主营产品: {result['main_products']}")
    print(f"网站: {result['website']}")
else:
    print(f"搜索失败或置信度不足: {result.get('error')}")

# 方式二：使用 run() 方法
result = await add_new_supplier_helper.run(
    "搜索供应商信息: Shenzhen ABC Electronics Co., Ltd.",
    input_data={"company_name": "Shenzhen ABC Electronics Co., Ltd."},
)

if result.success:
    print(result.data)
```
