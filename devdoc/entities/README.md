# Entities 数据实体

本目录包含系统中所有数据实体的详细说明文档。

## 实体列表

### 客户与供应商

| 实体 | 说明 | 文档 |
|------|------|------|
| Customer / Contact | 客户 + 联系人 | [Customer.md](./Customer.md) |
| CustomerSuggestion | AI 客户建议（待审批） | [Customer.md](./Customer.md) |
| Supplier / SupplierContact | 供应商 + 联系人 | [Supplier.md](./Supplier.md) |

### 产品与库存

| 实体 | 说明 | 文档 |
|------|------|------|
| Category | 品类（层级结构） | [Category.md](./Category.md) |
| Product / ProductSupplier | 产品 + 供应商关联 | [Product.md](./Product.md) |
| Warehouse | 仓库 | [Warehouse.md](./Warehouse.md) |
| Inventory | 库存 | [Inventory.md](./Inventory.md) |

### 询价与报价

| 实体 | 说明 | 文档 |
|------|------|------|
| ClientRFQ / ClientRFQLine | 客户询价单 + 明细行 | [ClientRfq.md](./ClientRfq.md) |
| Quotation / QuotationLine | 报价单（给客户） + 明细行 | [Quotation.md](./Quotation.md) |
| SupplierRFQ / SupplierRFQLine | 供应商询价单 + 明细行 | [SupplierRfq.md](./SupplierRfq.md) |
| SupplierQuotation / SupplierQuotationLine | 供应商报价单 + 明细行 | [SupplierQuotation.md](./SupplierQuotation.md) |

### 合同与单据

| 实体 | 说明 | 文档 |
|------|------|------|
| SalesContract / SalesLine | 销售合同 + 明细行 | [SalesContract.md](./SalesContract.md) |
| PurchaseContract / PurchaseLine | 采购合同 + 明细行 | [PurchaseContract.md](./PurchaseContract.md) |
| InboundOrder / InboundLine | 入库单 + 明细行 | [InboundOrder.md](./InboundOrder.md) |
| OutboundOrder / OutboundLine | 出库单 + 明细行 | [OutboundOrder.md](./OutboundOrder.md) |
| ContractNumberRule | 合同编号规则 | [ContractNumberRule.md](./ContractNumberRule.md) |

### 项目管理

| 实体 | 说明 | 文档 |
|------|------|------|
| Project / ProjectAssociation | 项目 + 多态关联 | [Project.md](./Project.md) |
| ProjectSuggestion | AI 项目建议（待审批） | [ProjectSuggestion.md](./ProjectSuggestion.md) |
| Task | 任务/里程碑（支持子任务树） | [Task.md](./Task.md) |
| Progress | 进度记录/时间线 | [Progress.md](./Progress.md) |

### 邮件处理

| 实体 | 说明 | 文档 |
|------|------|------|
| EmailAccount | 邮箱账户 | [EmailAccount.md](./EmailAccount.md) |
| EmailRawMessage / EmailAttachment | 原始邮件 + 附件 | [EmailRawMessage.md](./EmailRawMessage.md) |
| EmailAnalysis | AI 邮件分析结果 | [EmailAnalysis.md](./EmailAnalysis.md) |
| Event | 统一事件 | [Event.md](./Event.md) |

### 工作流与分类

| 实体 | 说明 | 文档 |
|------|------|------|
| WorkType / WorkTypeSuggestion | 工作类型 + AI 建议 | [WorkType.md](./WorkType.md) |
| Intent | 意图定义 | [Intent.md](./Intent.md) |

### 基础数据（只读预设）

| 实体 | 说明 | 文档 |
|------|------|------|
| Country | 国家/地区 | [Country.md](./Country.md) |
| TradeTerm | 贸易术语 (Incoterms) | [TradeTerm.md](./TradeTerm.md) |
| PaymentMethod | 付款方式 | [PaymentMethod.md](./PaymentMethod.md) |

### 组织与权限

| 实体 | 说明 | 文档 |
|------|------|------|
| Organization | 组织/公司（多租户顶层） | [Organization.md](./Organization.md) |
| Department / UserDepartment | 部门（树形） + 用户-部门关联 | [Department.md](./Department.md) |
| Role / Permission / RolePermission / RoleDataScope | 角色 + 功能权限 + 数据范围 | [Role.md](./Role.md) |
| User | 用户 | [User.md](./User.md) |

### 系统配置

| 实体 | 说明 | 文档 |
|------|------|------|
| LLMModelConfig | LLM 模型配置 | [LLMModelConfig.md](./LLMModelConfig.md) |
| Prompt / PromptHistory | Prompt 模板 + 修改历史 | [Prompt.md](./Prompt.md) |
| SystemSetting | 系统设置 | [SystemSetting.md](./SystemSetting.md) |
| WorkerConfig | Worker 配置 | [WorkerConfig.md](./WorkerConfig.md) |

### 聊天与执行记录

| 实体 | 说明 | 文档 |
|------|------|------|
| ChatSession / ChatMessage | 聊天会话 + 消息 | [ChatSession.md](./ChatSession.md) |
| WorkflowExecution / AgentExecution | 工作流 + Agent 执行记录 | [Execution.md](./Execution.md) |

## 实体关系图

```
┌──────────────────────────────────────────────────────────────┐
│                        邮件处理链路                            │
│                                                              │
│  EmailAccount ──→ EmailRawMessage ──→ Event                  │
│                       │                  │                   │
│                       ↓                  ↓                   │
│                  EmailAnalysis      WorkType                 │
│                       │                ↑                     │
│                       ↓                │                     │
│              CustomerSuggestion  WorkTypeSuggestion          │
│              ProjectSuggestion                               │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                   询价 → 报价 → 合同 流转链                    │
│                                                              │
│  客户侧:                                                     │
│  ClientRFQ ──→ Quotation ──→ SalesContract ──→ OutboundOrder │
│    │               │               │                │        │
│    └── Lines       └── Lines       └── Lines        └── Lines│
│                                                              │
│  供应商侧:                                                    │
│  SupplierRFQ ──→ SupplierQuotation ──→ PurchaseContract      │
│    │                    │                    │                │
│    └── Lines            └── Lines            └── Lines       │
│                                              ↓               │
│                                          InboundOrder        │
│                                              └── Lines       │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                        业务主数据                              │
│                                                              │
│  Customer ←──→ Contact          Category ──→ Product         │
│      │                                         │             │
│      │                          Supplier ←──→ SupplierContact│
│      │                              │          │             │
│      │                              └──── ProductSupplier ───┘
│      │                                                       │
│      └──→ SalesContract           PurchaseContract            │
│               │                        │                     │
│               ↓                        ↓                     │
│          OutboundOrder            InboundOrder                │
│               │                        │                     │
│               └───────→ Warehouse ←────┘                     │
│                             │                                │
│                             ↓                                │
│                         Inventory ←── Product                │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                        项目管理                               │
│                                                              │
│  ProjectSuggestion ──(审批)──→ Project                       │
│                                   │                          │
│                        ProjectAssociation ──→ 多种业务实体    │
│                                   │          (Customer,      │
│                                   │           Supplier,      │
│                                   │           Contract, ...) │
│                                   ↓                          │
│                                 Task ←──→ Task (子任务树)     │
│                                   │                          │
│                                   ↓                          │
│                               Progress ←── EmailRawMessage   │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                     组织与权限体系                              │
│                                                              │
│  Organization ──→ Department (树形自引用)                      │
│       │               │                                      │
│       │               ↓                                      │
│       │          UserDepartment ←── User                     │
│       │                              │                       │
│       └──→ Role ──→ RolePermission ──→ Permission            │
│                 └──→ RoleDataScope                            │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  基础数据: Country | TradeTerm | PaymentMethod               │
│  编号规则: ContractNumberRule                                 │
│  系统配置: LLMModelConfig | Prompt | SystemSetting           │
│           WorkerConfig | ChatSession | ChatMessage           │
└──────────────────────────────────────────────────────────────┘
```

## 数据库迁移

所有实体对应的数据库表通过 Alembic 管理：

```bash
# 生成迁移
cd backend
alembic revision --autogenerate -m "description"

# 执行迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

## 文件位置

- Models: `backend/app/models/`
- Schemas: `backend/app/schemas/`
- Migrations: `backend/alembic/versions/`
