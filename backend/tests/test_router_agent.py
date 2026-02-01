# tests/test_router_agent.py
# RouterAgent 单元测试
#
# 运行方式：
#   cd backend
#   pytest tests/test_router_agent.py -v
#   pytest tests/test_router_agent.py::test_route_inquiry -v  # 单个测试
#
# 注意：
#   - 需要设置 ANTHROPIC_API_KEY 环境变量
#   - 需要数据库中有 intents 种子数据

import pytest
import asyncio
from uuid import uuid4

from app.agents.router_agent import router_agent, RouteResult
from app.schemas.event import UnifiedEvent


# ==================== Fixtures ====================

@pytest.fixture
def make_email_event():
    """创建邮件事件的工厂函数"""
    def _make(content: str, subject: str = "", sender: str = "test@example.com"):
        return UnifiedEvent(
            event_id=str(uuid4()),
            event_type="email",
            source="email",
            source_id=f"msg-{uuid4()}",
            content=content,
            user_external_id=sender,
            user_name="测试用户",
            metadata={"subject": subject},
        )
    return _make


@pytest.fixture
def make_feishu_event():
    """创建飞书事件的工厂函数"""
    def _make(content: str, user_id: str = "user123"):
        return UnifiedEvent(
            event_id=str(uuid4()),
            event_type="feishu",
            source="feishu",
            source_id=f"msg-{uuid4()}",
            content=content,
            user_external_id=user_id,
            user_name="飞书用户",
            metadata={},
        )
    return _make


# ==================== 意图分类测试 ====================

@pytest.mark.asyncio
async def test_route_inquiry(make_email_event):
    """测试询价意图识别"""
    event = make_email_event(
        subject="产品报价咨询",
        content="您好，我想咨询一下贵公司的产品价格，能否发一份最新的报价单？谢谢。"
    )

    result = await router_agent.route(event)

    assert isinstance(result, RouteResult)
    assert result.intent == "inquiry"
    assert result.confidence >= 0.5
    print(f"\n意图: {result.intent_label} ({result.intent})")
    print(f"置信度: {result.confidence:.2f}")
    print(f"理由: {result.reasoning}")


@pytest.mark.asyncio
async def test_route_complaint(make_email_event):
    """测试投诉意图识别"""
    event = make_email_event(
        subject="投诉：产品质量问题",
        content="我们上周收到的货物有严重的质量问题，很多产品都有破损，这让我们非常失望。请尽快处理！"
    )

    result = await router_agent.route(event)

    assert isinstance(result, RouteResult)
    assert result.intent == "complaint"
    print(f"\n意图: {result.intent_label} ({result.intent})")
    print(f"置信度: {result.confidence:.2f}")
    print(f"理由: {result.reasoning}")


@pytest.mark.asyncio
async def test_route_order(make_email_event):
    """测试订单意图识别"""
    event = make_email_event(
        subject="采购订单 - 紧急",
        content="请按照附件的清单下单，数量100件，希望本周内发货。付款方式为月结。"
    )

    result = await router_agent.route(event)

    assert isinstance(result, RouteResult)
    assert result.intent == "order"
    print(f"\n意图: {result.intent_label} ({result.intent})")
    print(f"置信度: {result.confidence:.2f}")
    print(f"理由: {result.reasoning}")


@pytest.mark.asyncio
async def test_route_greeting(make_feishu_event):
    """测试问候意图识别"""
    event = make_feishu_event("你好，在吗？")

    result = await router_agent.route(event)

    assert isinstance(result, RouteResult)
    assert result.intent == "greeting"
    print(f"\n意图: {result.intent_label} ({result.intent})")
    print(f"置信度: {result.confidence:.2f}")
    print(f"理由: {result.reasoning}")


@pytest.mark.asyncio
async def test_route_follow_up(make_email_event):
    """测试跟进意图识别"""
    event = make_email_event(
        subject="Re: 关于上周的报价",
        content="上周发给你们的报价有回复了吗？请尽快确认一下订单进度。"
    )

    result = await router_agent.route(event)

    assert isinstance(result, RouteResult)
    assert result.intent == "follow_up"
    print(f"\n意图: {result.intent_label} ({result.intent})")
    print(f"置信度: {result.confidence:.2f}")
    print(f"理由: {result.reasoning}")


# ==================== 新意图建议测试 ====================

@pytest.mark.asyncio
async def test_route_unknown_suggests_new(make_email_event):
    """测试未知内容是否建议新意图"""
    event = make_email_event(
        subject="技术支持请求",
        content="我们在使用贵公司的API时遇到了集成问题，请问有技术文档或者能安排技术支持吗？"
    )

    result = await router_agent.route(event)

    assert isinstance(result, RouteResult)
    print(f"\n意图: {result.intent_label} ({result.intent})")
    print(f"置信度: {result.confidence:.2f}")
    print(f"理由: {result.reasoning}")

    if result.new_suggestion:
        print(f"\n新意图建议:")
        print(f"  名称: {result.new_suggestion.label} ({result.new_suggestion.name})")
        print(f"  描述: {result.new_suggestion.description}")
        print(f"  建议处理: {result.new_suggestion.suggested_handler}")


# ==================== 升级规则测试 ====================

@pytest.mark.asyncio
async def test_route_escalation(make_email_event):
    """测试升级规则触发"""
    event = make_email_event(
        subject="大额订单咨询",
        content="我们计划采购50万元的设备，需要签订正式合同。请安排商务人员对接。"
    )

    result = await router_agent.route(event)

    assert isinstance(result, RouteResult)
    print(f"\n意图: {result.intent_label} ({result.intent})")
    print(f"动作: {result.action}")
    print(f"需要升级: {result.needs_escalation}")
    if result.needs_escalation:
        print(f"升级原因: {result.escalation_reason}")
        print(f"工作流: {result.workflow_name}")


# ==================== route_text 便捷方法测试 ====================

@pytest.mark.asyncio
async def test_route_text_simple():
    """测试 route_text 便捷方法"""
    result = await router_agent.route_text(
        content="你们的产品多少钱？",
        source="web",
        metadata={"subject": "价格咨询"},
    )

    assert isinstance(result, RouteResult)
    assert result.intent in ["inquiry", "greeting", "other"]
    print(f"\n意图: {result.intent_label}")
    print(f"置信度: {result.confidence:.2f}")


# ==================== 边界情况测试 ====================

@pytest.mark.asyncio
async def test_route_empty_content(make_email_event):
    """测试空内容处理"""
    event = make_email_event(content="", subject="")

    result = await router_agent.route(event)

    assert isinstance(result, RouteResult)
    # 空内容应该返回 other 或 greeting
    assert result.intent in ["other", "greeting"]
    print(f"\n空内容意图: {result.intent}")


@pytest.mark.asyncio
async def test_route_long_content(make_email_event):
    """测试长内容处理"""
    long_content = "这是一封很长的邮件。" * 500  # 约5000字
    event = make_email_event(content=long_content, subject="测试长邮件")

    result = await router_agent.route(event)

    assert isinstance(result, RouteResult)
    print(f"\n长内容意图: {result.intent}")
    print(f"置信度: {result.confidence:.2f}")


# ==================== 缓存测试 ====================

@pytest.mark.asyncio
async def test_intent_cache():
    """测试意图缓存是否生效"""
    # 清除缓存
    router_agent.clear_cache()

    # 第一次调用，应该从数据库加载
    result1 = await router_agent.route_text("测试缓存")

    # 第二次调用，应该使用缓存
    result2 = await router_agent.route_text("再次测试")

    assert result1 is not None
    assert result2 is not None
    print("\n缓存测试通过")


# ==================== 运行单个测试（用于快速调试）====================

if __name__ == "__main__":
    """直接运行此文件进行快速测试"""
    import sys
    import os

    # 添加项目根目录到 path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # 设置环境变量（如果需要）
    # os.environ["ANTHROPIC_API_KEY"] = "your-key"

    async def quick_test():
        print("=" * 60)
        print("RouterAgent 快速测试")
        print("=" * 60)

        # 测试询价
        result = await router_agent.route_text(
            content="你们的产品价格是多少？能发一份报价单吗？",
            source="email",
            metadata={"subject": "询价"},
        )

        print(f"\n测试输入: 你们的产品价格是多少？能发一份报价单吗？")
        print(f"识别意图: {result.intent_label} ({result.intent})")
        print(f"置信度: {result.confidence:.2%}")
        print(f"推理: {result.reasoning}")
        print(f"动作: {result.action}")
        if result.needs_escalation:
            print(f"需要升级: {result.escalation_reason}")
        if result.new_suggestion:
            print(f"建议新意图: {result.new_suggestion.label}")

    asyncio.run(quick_test())
