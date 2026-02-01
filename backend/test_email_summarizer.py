#!/usr/bin/env python3
"""
测试 EmailSummarizer 的 LLM 响应解析
"""
import asyncio
import sys
sys.path.insert(0, '/Users/alexli/Concord_AI/backend')

from app.agents.email_summarizer import email_summarizer
from datetime import datetime

async def test():
    result = await email_summarizer.analyze(
        email_id="test-001",
        sender="hrcours2000@gmail.com",
        sender_name="Training Center",
        subject="مهارات المستقبل المالي",
        body_text="""
برنامج تدريبي تنفيذي احترافي
المحاسب الذكي
The Smart Accountant Program
التاريخ: من 8 إلى 12 فبراير 2026
المدة: 5 أيام تدريبية مكثفة
المكان: القاهرة – جمهورية مصر العربية
""",
        received_at=datetime.now(),
    )

    print("=" * 60)
    print("分析结果:")
    print("=" * 60)
    for key, value in result.items():
        if key != "cleaned_content":
            print(f"{key:20}: {value}")
    print("=" * 60)

    if not result.get("summary"):
        print("\n❌ 问题：summary 为空！")
        if result.get("parse_error"):
            print(f"原始响应: {result.get('raw_response')}")
    else:
        print("\n✅ 分析成功")

if __name__ == "__main__":
    asyncio.run(test())
