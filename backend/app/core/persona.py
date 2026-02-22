"""
app.core.persona
~~~~~~~~~~~~~~~~

多物理主播角色包（Persona Bundle）的解析与管理器。
每个角色拥有一套独立的配置（Prompt、TTS设定）和专享的知识库（FAISS）。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

import yaml
from pydantic import BaseModel, Field

from app.core.settings import settings, PROJECT_ROOT
from app.core.logging import get_logger
from app.rag.faiss_adapter import FAISSAdapter
from app.llm.client import create_gemini_client

logger = get_logger(__name__)

# 定义数据层根目录
PERSONA_DIR = PROJECT_ROOT / "data" / "personas"


class TTSConfig(BaseModel):
    voice: str = Field(..., description="Edge TTS 语音声线名称")
    rate: str = Field(default="+0%", description="语速调整")
    pitch: str = Field(default="+0Hz", description="音调调整")


class RAGConfig(BaseModel):
    chunk_size: int = Field(default=200, description="知识库文本分段大小")
    chunk_overlap: int = Field(default=50, description="知识库分段重叠字数")
    search_top_k: int = Field(default=2, description="每次检索返回的知识块数量")


class PersonaConfig(BaseModel):
    name: str = Field(..., description="虚拟主播显示名称")
    description: str = Field(..., description="该角色的简要描述")
    system_prompt: str = Field(..., description="发送给大语言模型的系统级别 Prompt")
    is_default: bool = Field(default=False, description="是否为默认使用的角色。如果存在多个 default，使用第一个找到的。")
    tts: TTSConfig = Field(..., description="TTS 相关设定")
    rag: RAGConfig = Field(..., description="RAG 检索相关设定")
    fallback_responses: list[str] = Field(
        default=[
            "主播正在思考中...",
            "哎呀，直播间线路好像卡了一下，等我一下~",
            "稍等片刻，主播整理一下思绪~",
            "这个嘛... 让我想想看！"
        ],
        description="大模型调用失败时的兜底回复",
    )


class PersonaBundle:
    """包装已解析的角色配置及其专用的知识库引擎。"""

    def __init__(self, config: PersonaConfig, rag_engine: FAISSAdapter):
        self.config = config
        self.rag = rag_engine


class PersonaManager:
    """全局单例，加载并维护所有的可选主播。"""

    def __init__(self) -> None:
        self._personas: Dict[str, PersonaBundle] = {}
        # 为了节约资源，全局共享同一个 embedding 客户端（也可以拆分）
        self._shared_client = create_gemini_client()

    async def load_all(self) -> None:
        """扫描 data/personas 目录并加载所有有效角色。"""
        if not PERSONA_DIR.exists():
            logger.warning(f"Persona 目录不存在: {PERSONA_DIR}, 已自动创建。")
            PERSONA_DIR.mkdir(parents=True, exist_ok=True)
            return

        for p_dir in PERSONA_DIR.iterdir():
            if p_dir.is_dir():
                config_path = p_dir / "config.yaml"
                if config_path.exists():
                    try:
                        persona_id = p_dir.name
                        bundle = await self._load_persona(persona_id, config_path, p_dir)
                        self._personas[persona_id] = bundle
                        logger.info(f"成功加载角色包: {persona_id} ({bundle.config.name})")
                    except Exception as e:
                        logger.error(f"加载角色包 {p_dir.name} 失败: {e}", exc_info=True)

    async def _load_persona(self, persona_id: str, config_path: Path, p_dir: Path) -> PersonaBundle:
        # 解析 YAML 到 Dict 然后转成 BaseModel
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        config = PersonaConfig(**data)

        # 初始化独立的 QA 向量引擎
        faiss = FAISSAdapter(
            client=self._shared_client,
            chunk_size=config.rag.chunk_size,
            chunk_overlap=config.rag.chunk_overlap,
        )
        
        # 加载专属知识库文件
        knowledge_dir = p_dir / "knowledge"
        if knowledge_dir.exists():
            await faiss.load_directory(str(knowledge_dir))
        else:
            knowledge_dir.mkdir()
            
        return PersonaBundle(config, faiss)

    def get_bundle(self, persona_id: str) -> PersonaBundle:
        """获取指定角色的配置及知识引擎，找不到则报错。"""
        if persona_id not in self._personas:
            raise ValueError(f"无效的 persona_id: {persona_id}")
        return self._personas[persona_id]

    @property
    def default_persona_id(self) -> str:
        """如果没有指定，优先返回标记为 is_default 的角色。如果都没有，返回加载的第一个。"""
        for pid, bundle in self._personas.items():
            if bundle.config.is_default:
                return pid
        if self._personas:
            return next(iter(self._personas.keys()))
        raise ValueError("系统中没有加载任何角色，请检查 data/personas/")


