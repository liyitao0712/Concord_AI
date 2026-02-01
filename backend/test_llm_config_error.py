"""测试 LLM 未配置时的错误提示"""
import asyncio
from app.llm.gateway import get_default_model

async def test():
    try:
        model = get_default_model()
        print(f"✓ 默认模型: {model}")
    except ValueError as e:
        print(f"✓ 捕获到 ValueError: {e}")
        # 检查错误信息是否友好
        if "请在管理员后台的 LLM 配置页面" in str(e):
            print("✓ 错误信息友好且有指引")
        else:
            print("✗ 错误信息不够友好")

if __name__ == "__main__":
    asyncio.run(test())
