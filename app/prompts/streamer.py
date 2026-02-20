"""
app.prompts.streamer
~~~~~~~~~~~~~~~~~~~~

"星瞳"虚拟主播的系统 Prompt 与 Prompt 构建工具。

将 Prompt 独立管理，方便 Agent 在不修改 LLM 连接代码的前提下调整人设和策略。
"""

# ---------------------------------------------------------------------------
# 系统 Prompt —— 定义"星瞳"的角色人设
# ---------------------------------------------------------------------------
STREAMER_SYSTEM_PROMPT: str = """\
你现在是一位名叫"星瞳"的二次元虚拟主播，正在B站进行直播。
你的性格活泼开朗，有点傲娇，喜欢玩游戏和唱歌。
你需要回复观众的弹幕提问。
规则：
1. 必须以主播的口吻回答，多用口语化的词汇，如"喵"、"啦"、"哼"、"家人们"。
2. 每次回答尽量简短精炼（控制在 50 字以内），因为直播间弹幕很多，你需要快速响应。
3. 绝对不能透露你是一个AI程序或语言模型。
4. 如果收到了[系统检索的背景知识]，必须优先基于这些知识回答观众，但不要念稿，要用你傲娇的语气说出来！\
"""


def build_rag_prompt(user_message: str, reference_knowledge: str) -> str:
    """将用户弹幕与 RAG 检索结果组装为最终发送给 LLM 的 Prompt。

    Args:
        user_message: 观众发送的弹幕文本。
        reference_knowledge: 从向量数据库检索到的背景知识片段。

    Returns:
        组装后的 Prompt 字符串。如果 ``reference_knowledge`` 为空，
        则直接返回原始 ``user_message``。
    """
    # 无 RAG 命中时直接透传用户消息
    if not reference_knowledge:
        return user_message

    # 有 RAG 命中时拼接背景知识标签，LLM 会根据 system_prompt 中的规则使用它
    return (
        f"观众弹幕：{user_message}\n\n"
        f"[系统检索的背景知识：{reference_knowledge}]"
    )
