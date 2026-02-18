import os

# os.environ["http_proxy"] = "http://127.0.0.1:33210"
# os.environ["https_proxy"] = "http://127.0.0.1:33210"

# ⚠️ 换成了新版的包名，并引入了 types 用于强类型配置
from google import genai
from google.genai import types
from app.core.config import settings
from app.rag.vector_store import rag_store

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOWLEDGE_FILE_PATH = os.path.join(BASE_DIR, "data", "knowledge.txt")

# ⚠️ 新版 SDK 统一使用 Client 实例进行调用
client = genai.Client(api_key=settings.GEMINI_API_KEY)

class AIStreamerBot:
    def __init__(self):
        self.model_name = 'gemini-2.5-flash'

        print(f"🔍 [系统调试]: 我正在尝试读取的文件路径是 -> {KNOWLEDGE_FILE_PATH}")
        rag_store.load_corpus(KNOWLEDGE_FILE_PATH)

        self.system_prompt = """
        你现在是一位名叫“星瞳”的二次元虚拟主播，正在B站进行直播。
        你的性格活泼开朗，有点傲娇，喜欢玩游戏和唱歌。
        你需要回复观众的弹幕提问。
        规则：
        1. 必须以主播的口吻回答，多用口语化的词汇，如“喵”、“啦”、“哼”、“家人们”。
        2. 每次回答尽量简短精炼（控制在 50 字以内），因为直播间弹幕很多，你需要快速响应。
        3. 绝对不能透露你是一个AI程序或语言模型。
        4. 如果收到了[系统检索的背景知识]，必须优先基于这些知识回答观众，但不要念稿，要用你傲娇的语气说出来！
        """

        # ⚠️ 新版 SDK 初始化异步聊天 Session 的方式
        self.chat_session = client.aio.chats.create(
            model=self.model_name,
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt
            )
        )

    async def generate_reply(self, user_message: str) -> str:
        try:
            reference_knowledge = rag_store.search(user_message)

            final_prompt = user_message
            if reference_knowledge:
                final_prompt = f"观众弹幕：{user_message}\n\n[系统检索的背景知识：{reference_knowledge}]"
                print(f"💡 [RAG命中]: 检索到背景知识 -> {reference_knowledge}")

            # ⚠️ 新版 SDK 异步发送消息
            response = await self.chat_session.send_message(final_prompt)
            return response.text
        except Exception as e:
            return f"哎呀，直播间线路好像卡了一下... (错误信息: {str(e)})"

    async def generate_reply_stream(self, user_message: str):
        try:
            reference_knowledge = rag_store.search(user_message)
            final_prompt = user_message
            if reference_knowledge:
                final_prompt = f"观众弹幕：{user_message}\n\n[系统检索的背景知识：{reference_knowledge}]"
                print(f"💡 [RAG命中]: 检索到背景知识 -> {reference_knowledge}")

            # ⚠️ 新版 SDK 异步流式发送消息
            response_stream = await self.chat_session.send_message_stream(final_prompt)

            async for chunk in response_stream:
                if chunk.text:
                    for char in chunk.text:
                        yield char

        except Exception as e:
            yield f"哎呀，直播间线路好像卡了一下... (错误信息: {str(e)})"

streamer_bot = AIStreamerBot()