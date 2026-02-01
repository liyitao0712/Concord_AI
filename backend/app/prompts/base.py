# app/prompts/base.py
# Prompt 基础模块
#
# 功能说明：
# 1. 定义 Prompt 模板的基类
# 2. 提供模板渲染功能
# 3. 统一管理 Prompt 格式
#
# Prompt 工程最佳实践：
# 1. 结构清晰：使用 XML 标签或 Markdown 分隔内容
# 2. 角色明确：开头说明 AI 的角色和任务
# 3. 示例驱动：提供具体的输入输出示例
# 4. 约束明确：说明输出格式要求
#
# 使用方法：
#   from app.prompts.base import PromptTemplate
#
#   template = PromptTemplate(
#       name="greet",
#       template="你好，{name}！",
#   )
#   prompt = template.render(name="张三")
#   # 输出：你好，张三！

from typing import Dict, Any, Optional
from string import Template


class PromptTemplate:
    """
    Prompt 模板类

    用于管理和渲染 Prompt 模板

    属性：
        name: 模板名称（用于日志和调试）
        template: 模板内容，使用 {变量名} 作为占位符
        description: 模板描述（可选）

    占位符语法：
        - {variable}: 基本变量替换
        - 支持多个变量

    示例：
        template = PromptTemplate(
            name="email_analysis",
            template=\"\"\"
            请分析以下邮件内容：

            <email>
            {email_content}
            </email>

            请识别邮件的意图类型。
            \"\"\",
            description="Email analysis template"
        )

        prompt = template.render(
            email_content="您好，请问产品A的价格是多少？"
        )
    """

    def __init__(
        self,
        name: str,
        template: str,
        description: Optional[str] = None
    ):
        """
        初始化 Prompt 模板

        Args:
            name: 模板名称
            template: 模板内容
            description: 模板描述
        """
        self.name = name
        self.template = template
        self.description = description

    def render(self, **kwargs: Any) -> str:
        """
        渲染模板

        将模板中的占位符替换为实际值

        Args:
            **kwargs: 变量名和值的键值对

        Returns:
            str: 渲染后的 Prompt

        Raises:
            KeyError: 缺少必需的变量时抛出

        示例：
            prompt = template.render(
                email_content="邮件内容",
                customer_name="张三"
            )
        """
        try:
            # 使用 str.format() 进行变量替换
            return self.template.format(**kwargs)
        except KeyError as e:
            raise KeyError(f"模板 '{self.name}' 缺少必需的变量: {e}")

    def render_safe(self, **kwargs: Any) -> str:
        """
        安全渲染模板

        与 render() 类似，但缺少变量时不会报错
        而是保留原始占位符

        Args:
            **kwargs: 变量名和值的键值对

        Returns:
            str: 渲染后的 Prompt

        示例：
            # 即使缺少某些变量也不会报错
            prompt = template.render_safe(email_content="内容")
        """
        # 使用 Template 的 safe_substitute 方法
        t = Template(self.template.replace("{", "${").replace("}", "}"))
        return t.safe_substitute(**kwargs)

    def get_variables(self) -> list:
        """
        获取模板中的所有变量名

        Returns:
            list: 变量名列表

        示例：
            vars = template.get_variables()
            # 返回：['email_content', 'customer_name']
        """
        import re
        # 匹配 {variable_name} 格式
        pattern = r'\{(\w+)\}'
        return list(set(re.findall(pattern, self.template)))

    def __repr__(self) -> str:
        """返回模板的字符串表示"""
        return f"PromptTemplate(name='{self.name}', variables={self.get_variables()})"


class SystemPrompt:
    """
    系统提示词管理类

    用于定义和管理 AI 的角色设定

    系统提示词的作用：
    - 设定 AI 的角色和身份
    - 定义行为规范和约束
    - 指定输出格式和风格

    示例：
        system = SystemPrompt(
            role="邮件分析助手",
            instructions=[
                "你是一个专业的邮件分析助手",
                "你擅长识别邮件的意图和提取关键信息",
            ],
            constraints=[
                "只输出 JSON 格式",
                "不要添加额外的解释",
            ]
        )

        prompt = system.render()
    """

    def __init__(
        self,
        role: str,
        instructions: Optional[list] = None,
        constraints: Optional[list] = None,
        examples: Optional[list] = None,
    ):
        """
        初始化系统提示词

        Args:
            role: AI 的角色描述
            instructions: 行为指令列表
            constraints: 约束条件列表
            examples: 示例列表
        """
        self.role = role
        self.instructions = instructions or []
        self.constraints = constraints or []
        self.examples = examples or []

    def render(self) -> str:
        """
        渲染系统提示词

        Returns:
            str: 完整的系统提示词
        """
        parts = []

        # 角色定义
        parts.append(f"# 角色\n{self.role}")

        # 行为指令
        if self.instructions:
            instructions_text = "\n".join(f"- {i}" for i in self.instructions)
            parts.append(f"\n# 指令\n{instructions_text}")

        # 约束条件
        if self.constraints:
            constraints_text = "\n".join(f"- {c}" for c in self.constraints)
            parts.append(f"\n# 约束\n{constraints_text}")

        # 示例
        if self.examples:
            examples_text = "\n\n".join(self.examples)
            parts.append(f"\n# 示例\n{examples_text}")

        return "\n".join(parts)


# ==================== 常用的系统提示词 ====================

# 通用助手
ASSISTANT_SYSTEM = SystemPrompt(
    role="你是 Concord AI 智能助手，一个专业、友好的 AI 助手。",
    instructions=[
        "用简洁清晰的语言回答问题",
        "如果不确定，诚实地表示不知道",
        "在适当的时候提供相关的建议",
    ],
    constraints=[
        "使用中文回答",
        "保持专业和礼貌",
    ]
)

# JSON 输出格式
JSON_OUTPUT_SYSTEM = SystemPrompt(
    role="你是一个数据提取助手，专门将文本转换为结构化的 JSON 数据。",
    instructions=[
        "仔细阅读输入内容",
        "按照指定的格式提取信息",
        "只输出 JSON，不要添加任何解释",
    ],
    constraints=[
        "输出必须是有效的 JSON 格式",
        "字段值为空时使用 null",
        "不要添加 markdown 代码块标记",
    ]
)
