"""
AURA AI Deep Research Engine V2
Publication-grade research with 10-step pipeline.
Uses dedicated research LLM client — NEVER touches Chat/Agent providers.

Pipeline:
1. Query Understanding
2. Research Planning
3. Source Discovery
4. Source Collection
5. Cross Verification
6. Fact Extraction
7. Analysis
8. Report Generation
9. Citation Generation
10. Quality Control → Final Report
"""

import asyncio
import logging
import time
import json
import uuid
import re
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator
import httpx
from docx import Document
from docx.shared import Inches

from app.config import settings
from app.database.database import db
from app.search.search_manager import search_manager
from app.core.bedrock_research_client import research_llm_client
from app.database.schemas import ChatEventType

logger = logging.getLogger(__name__)

# Global registry for cancellation tracking
active_research_tasks: dict[str, asyncio.Task] = {}

# Research depth configurations
DEPTH_CONFIG = {
    "quick": {"sources": 3, "subtasks": 2, "verification": False, "pages_per_query": 1},
    "standard": {"sources": 5, "subtasks": 3, "verification": True, "pages_per_query": 2},
    "deep": {"sources": 8, "subtasks": 5, "verification": True, "pages_per_query": 3},
    "expert": {"sources": 12, "subtasks": 7, "verification": True, "pages_per_query": 3},
}

# Domain trust scores for source quality assessment
TRUSTED_DOMAINS = {
    # Tier 1: Academic/Government (95-100)
    "arxiv.org": 98, "scholar.google.com": 97, "pubmed.ncbi.nlm.nih.gov": 98,
    "nature.com": 98, "science.org": 98, "ieee.org": 97, "acm.org": 97,
    "gov": 95, "edu": 93, "who.int": 96, "un.org": 95,
    # Tier 2: Quality Journalism (80-94)
    "reuters.com": 92, "apnews.com": 92, "bbc.com": 90, "bbc.co.uk": 90,
    "nytimes.com": 88, "washingtonpost.com": 87, "theguardian.com": 87,
    "economist.com": 90, "ft.com": 89, "bloomberg.com": 88,
    # Tier 3: Tech/Industry (70-85)
    "techcrunch.com": 80, "wired.com": 82, "arstechnica.com": 83,
    "stackoverflow.com": 78, "github.com": 75, "medium.com": 65,
    "wikipedia.org": 80, "britannica.com": 88,
    # Tier 4: General (50-69)
    "reddit.com": 55, "quora.com": 50,
}


def get_workspace_root() -> Path:
    """Gets absolute path to user workspace."""
    return Path(__file__).resolve().parent.parent.parent.parent


def get_domain_trust_score(url: str) -> int:
    """Calculate trust score based on domain authority."""
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        domain = domain.replace("www.", "")

        # Exact match
        if domain in TRUSTED_DOMAINS:
            return TRUSTED_DOMAINS[domain]

        # TLD match (.gov, .edu)
        tld = domain.split(".")[-1]
        if tld in TRUSTED_DOMAINS:
            return TRUSTED_DOMAINS[tld]

        # Partial domain match
        for trusted, score in TRUSTED_DOMAINS.items():
            if trusted in domain:
                return score

        return 60  # Default trust score for unknown domains
    except Exception:
        return 50


class DeepResearchEngine:
    """
    Executes publication-grade deep research with a 10-step pipeline.
    Uses research_llm_client (Bedrock) — NEVER uses Chat/Agent providers.
    """

    STEPS = [
        ("understanding", "🔍 Understanding Topic", "Analyzing query scope and intent"),
        ("planning", "📋 Research Planning", "Decomposing into research subtasks"),
        ("discovery", "🌐 Searching Sources", "Discovering relevant sources"),
        ("collection", "📚 Reading Documents", "Extracting content from sources"),
        ("verification", "✅ Verifying Facts", "Cross-referencing claims"),
        ("extraction", "🧬 Extracting Facts", "Isolating atomic claims"),
        ("analysis", "🧠 Analyzing Findings", "Synthesizing patterns and insights"),
        ("report", "📝 Writing Report", "Generating publication-grade report"),
        ("citations", "📎 Adding Citations", "Building bibliography"),
        ("finalizing", "🎯 Finalizing", "Quality checks and export"),
    ]

    async def conduct_research(
        self, topic: str, conversation_id: str, depth: str = "standard"
    ) -> AsyncGenerator[tuple[ChatEventType, str, dict | None], None]:
        """
        Full deep research pipeline. Yields SSE events for live progress.
        Uses research_llm_client exclusively — never Chat/Agent providers.
        """
        start_time = time.time()

        # Register for cancellation
        current_task = asyncio.current_task()
        if current_task:
            active_research_tasks[conversation_id] = current_task

        # Validate depth
        if depth not in DEPTH_CONFIG:
            depth = "standard"
        depth_cfg = DEPTH_CONFIG[depth]

        # Init workspace
        workspace_root = get_workspace_root()
        dest_folder = workspace_root / "backend" / ".research_cache"
        dest_folder.mkdir(parents=True, exist_ok=True)

        # Metrics tracked in real-time
        metrics = {
            "current_step": "understanding",
            "current_source": "",
            "pages_read": 0,
            "sources_found": 0,
            "facts_extracted": 0,
            "facts_verified": 0,
            "depth": depth,
            "elapsed_time": 0,
        }

        def make_progress_meta(step_id: str, step_label: str, detail: str) -> dict:
            metrics["current_step"] = step_id
            metrics["elapsed_time"] = round(time.time() - start_time, 1)
            return {
                "status": "searching",
                "step": step_id,
                "step_label": step_label,
                "detail": detail,
                "metrics": {**metrics},
                "steps": [
                    {"id": s[0], "label": s[1], "status":
                        "completed" if self.STEPS.index(s) < [i for i, x in enumerate(self.STEPS) if x[0] == step_id][0]
                        else "running" if s[0] == step_id
                        else "pending"
                    }
                    for s in self.STEPS
                ],
            }

        try:
            # ═══════════════════════════════════════════════════
            # STEP 1: Query Understanding
            # ═══════════════════════════════════════════════════
            yield (ChatEventType.SEARCH, "Understanding your research topic...",
                   make_progress_meta("understanding", "🔍 Understanding Topic", "Analyzing query scope and entities"))

            query_analysis = await self._understand_query(topic)
            refined_topic = query_analysis.get("refined_topic", topic)
            key_entities = query_analysis.get("key_entities", [])
            scope = query_analysis.get("scope", "general")

            # ═══════════════════════════════════════════════════
            # STEP 2: Research Planning
            # ═══════════════════════════════════════════════════
            yield (ChatEventType.SEARCH, "Planning research strategy...",
                   make_progress_meta("planning", "📋 Research Planning", f"Decomposing into {depth_cfg['subtasks']} subtasks"))

            subtasks = await self._plan_research(refined_topic, key_entities, scope, depth_cfg["subtasks"])

            # ═══════════════════════════════════════════════════
            # STEP 3: Source Discovery
            # ═══════════════════════════════════════════════════
            yield (ChatEventType.SEARCH, "Discovering relevant sources...",
                   make_progress_meta("discovery", "🌐 Searching Sources", "Querying search providers"))

            all_search_results = []
            visited_urls = set()

            for idx, sub in enumerate(subtasks):
                metrics["current_source"] = f"Query {idx + 1}: {sub['query'][:50]}"
                yield (ChatEventType.SEARCH, f"Searching: {sub['query'][:60]}...",
                       make_progress_meta("discovery", "🌐 Searching Sources", f"Query {idx + 1}/{len(subtasks)}"))

                try:
                    results = await search_manager.search(
                        query=sub["query"], cascade=False,
                        max_results=depth_cfg["pages_per_query"] + 1
                    )
                    for r in results.get("results", []):
                        url = r.get("url", "")
                        if url and url not in visited_urls:
                            visited_urls.add(url)
                            all_search_results.append({
                                "url": url,
                                "title": r.get("title", "Untitled"),
                                "snippet": r.get("snippet", ""),
                                "domain": self._extract_domain(url),
                                "trust_score": get_domain_trust_score(url),
                                "subtask": sub["query"],
                            })
                except Exception as e:
                    logger.warning(f"Search failed for subtask '{sub['query']}': {e}")

            metrics["sources_found"] = len(all_search_results)
            # Sort by trust score
            all_search_results.sort(key=lambda x: x["trust_score"], reverse=True)
            # Limit to depth config
            sources_to_read = all_search_results[:depth_cfg["sources"]]

            # ═══════════════════════════════════════════════════
            # STEP 4: Source Collection
            # ═══════════════════════════════════════════════════
            harvested_docs = []

            for idx, source in enumerate(sources_to_read):
                metrics["current_source"] = source["url"]
                metrics["pages_read"] = idx + 1
                yield (ChatEventType.SEARCH, f"Reading source {idx + 1}/{len(sources_to_read)}...",
                       make_progress_meta("collection", "📚 Reading Documents", f"Extracting: {source['domain']}"))

                content = await self._extract_url_content(source["url"])
                if content and len(content.strip()) > 150:
                    harvested_docs.append({
                        "url": source["url"],
                        "title": source["title"],
                        "domain": source["domain"],
                        "trust_score": source["trust_score"],
                        "content": content[:8000],  # Cap per-source content
                        "publication_date": self._extract_date_hint(content),
                    })

            if not harvested_docs:
                # Fallback: use search snippets
                yield (ChatEventType.SEARCH, "Using search snippets as fallback...",
                       make_progress_meta("collection", "📚 Reading Documents", "Fallback to snippets"))
                for sr in all_search_results[:5]:
                    if sr.get("snippet"):
                        harvested_docs.append({
                            "url": sr["url"],
                            "title": sr["title"],
                            "domain": sr["domain"],
                            "trust_score": sr["trust_score"],
                            "content": sr["snippet"],
                            "publication_date": None,
                        })

            # ═══════════════════════════════════════════════════
            # STEP 5: Fact Extraction
            # ═══════════════════════════════════════════════════
            yield (ChatEventType.SEARCH, "Extracting facts from sources...",
                   make_progress_meta("extraction", "🧬 Extracting Facts", "Processing documents"))

            raw_facts = []
            for idx, doc in enumerate(harvested_docs):
                metrics["current_source"] = doc["url"]
                yield (ChatEventType.SEARCH, f"Extracting facts from source {idx + 1}...",
                       make_progress_meta("extraction", "🧬 Extracting Facts", f"Document {idx + 1}/{len(harvested_docs)}"))

                facts = await self._extract_facts(doc["content"], refined_topic)
                for f in facts:
                    raw_facts.append({
                        "fact": f,
                        "url": doc["url"],
                        "title": doc["title"],
                        "domain": doc["domain"],
                        "trust_score": doc["trust_score"],
                    })

            metrics["facts_extracted"] = len(raw_facts)

            # ═══════════════════════════════════════════════════
            # STEP 6: Cross Verification
            # ═══════════════════════════════════════════════════
            verified_facts = raw_facts  # Default: pass through

            if depth_cfg["verification"] and len(raw_facts) > 0:
                yield (ChatEventType.SEARCH, "Cross-verifying facts across sources...",
                       make_progress_meta("verification", "✅ Verifying Facts", "Checking consistency"))

                verified_facts = await self._verify_facts(raw_facts, refined_topic)
                metrics["facts_verified"] = len(verified_facts)
            else:
                # Quick mode: skip verification, mark all as single-source
                verified_facts = [{
                    "fact": rf["fact"],
                    "sources": [rf["url"]],
                    "source_titles": [rf["title"]],
                    "status": "Single Source",
                    "trust_score": rf["trust_score"],
                    "notes": "",
                } for rf in raw_facts]
                metrics["facts_verified"] = len(verified_facts)

            yield (ChatEventType.SEARCH, f"Verified {metrics['facts_verified']} facts",
                   make_progress_meta("verification", "✅ Verifying Facts", "Verification complete"))

            # ═══════════════════════════════════════════════════
            # STEP 7: Analysis
            # ═══════════════════════════════════════════════════
            yield (ChatEventType.SEARCH, "Analyzing findings and synthesizing insights...",
                   make_progress_meta("analysis", "🧠 Analyzing Findings", "Pattern recognition & synthesis"))

            analysis = await self._analyze_findings(verified_facts, refined_topic, key_entities)

            # ═══════════════════════════════════════════════════
            # STEP 8 & 9: Report Generation + Citations
            # ═══════════════════════════════════════════════════
            yield (ChatEventType.SEARCH, "Writing publication-grade report...",
                   make_progress_meta("report", "📝 Writing Report", "Generating with citations"))

            # Build sources metadata for sidebar
            sources_for_panel = []
            for doc in harvested_docs:
                sources_for_panel.append({
                    "url": doc["url"],
                    "title": doc["title"],
                    "domain": doc["domain"],
                    "trust_score": doc["trust_score"],
                    "publication_date": doc.get("publication_date"),
                    "category": self._categorize_source(doc["url"]),
                })

            # Stream the report
            report_md = ""
            bibliography_urls = []
            async for chunk in self._stream_report(verified_facts, analysis, refined_topic, harvested_docs):
                if isinstance(chunk, list):
                    bibliography_urls = chunk
                else:
                    report_md += chunk
                    yield (ChatEventType.TOKEN, chunk,
                           make_progress_meta("report", "📝 Writing Report", "Streaming report"))

            yield (ChatEventType.SEARCH, "Adding citations...",
                   make_progress_meta("citations", "📎 Adding Citations", "Building bibliography"))

            # ═══════════════════════════════════════════════════
            # STEP 10: Quality Control & Export
            # ═══════════════════════════════════════════════════
            yield (ChatEventType.SEARCH, "Running quality checks...",
                   make_progress_meta("finalizing", "🎯 Finalizing", "Quality validation"))

            quality_result = await self._quality_check(report_md, verified_facts)

            # Export files
            timestamp = int(time.time())
            safe_topic = re.sub(r"[^a-zA-Z0-9_-]", "_", topic.replace(" ", "_"))[:40]

            md_filename = f"Research_Report_{safe_topic}_{timestamp}.md"
            docx_filename = f"Research_Report_{safe_topic}_{timestamp}.docx"
            pdf_filename = f"Research_Report_{safe_topic}_{timestamp}.pdf"

            md_path = dest_folder / md_filename
            docx_path = dest_folder / docx_filename
            pdf_path = dest_folder / pdf_filename

            # Save Markdown
            md_path.write_text(report_md, encoding="utf-8")

            # Save DOCX
            self._export_docx(report_md, str(docx_path))

            # Save PDF
            await self._export_pdf(report_md, str(pdf_path), topic)

            yield (ChatEventType.SEARCH, "Research complete!",
                   make_progress_meta("finalizing", "🎯 Finalizing", "Export complete"))

            # Persist to database
            report_id = str(uuid.uuid4())
            rel_md = str(md_path.relative_to(workspace_root))
            rel_docx = str(docx_path.relative_to(workspace_root))
            rel_pdf = str(pdf_path.relative_to(workspace_root))

            await db.db.research_reports.insert_one({
                "id": report_id,
                "conversation_id": conversation_id,
                "topic": topic,
                "depth": depth,
                "markdown_path": rel_md,
                "pdf_path": rel_pdf,
                "docx_path": rel_docx,
                "report_content": report_md,
                "facts_json": json.dumps(verified_facts),
                "sources_json": json.dumps(sources_for_panel),
                "quality_check": json.dumps(quality_result),
                "metrics": json.dumps(metrics),
                "created_at": datetime.utcnow().isoformat(),
                "elapsed_seconds": round(time.time() - start_time, 1),
            })

            # Final metadata with export links and sources
            yield (ChatEventType.TOKEN, "", {
                "research_report": {
                    "id": report_id,
                    "topic": topic,
                    "depth": depth,
                    "markdown": rel_md,
                    "pdf": rel_pdf,
                    "docx": rel_docx,
                    "sources": sources_for_panel,
                    "quality": quality_result,
                    "elapsed_seconds": round(time.time() - start_time, 1),
                    "facts_count": len(verified_facts),
                    "sources_count": len(harvested_docs),
                }
            })

        except asyncio.CancelledError:
            logger.info(f"Research task cancelled for conversation {conversation_id}")
            yield (ChatEventType.ERROR, "Research process aborted by the user.", None)
            raise
        except Exception as e:
            logger.error(f"Deep research failed: {e}", exc_info=True)
            yield (ChatEventType.ERROR, f"Deep research task failed: {str(e)}", None)
        finally:
            active_research_tasks.pop(conversation_id, None)

    # ══════════════════════════════════════════════════
    # PIPELINE STAGE IMPLEMENTATIONS
    # ══════════════════════════════════════════════════

    async def _understand_query(self, topic: str) -> dict:
        """Step 1: Deep query understanding using research LLM."""
        system_prompt = (
            "You are AURA's Query Analysis Engine. Analyze the research topic to understand:\n"
            "1. The refined, search-optimized version of the topic\n"
            "2. Key entities, concepts, and names mentioned\n"
            "3. The scope (narrow/specific, general/broad, comparative, historical, technical)\n"
            "4. What type of information the user likely needs\n"
            "Return JSON: {\"refined_topic\": str, \"key_entities\": [str], \"scope\": str, \"info_needs\": [str]}"
        )
        prompt = f"Analyze this research request: \"{topic}\""
        try:
            result = await research_llm_client.generate_json(prompt, system_prompt=system_prompt)
            return result
        except Exception as e:
            logger.warning(f"Query understanding failed: {e}")
            return {"refined_topic": topic, "key_entities": [], "scope": "general", "info_needs": []}

    async def _plan_research(self, topic: str, entities: list, scope: str, num_subtasks: int) -> list[dict]:
        """Step 2: Research planning — decompose into search subtasks."""
        system_prompt = (
            "You are AURA's Deep Research Planner. Create a search strategy.\n"
            f"Generate exactly {num_subtasks} search subtasks. Each subtask should cover a different aspect.\n"
            "For each subtask, provide:\n"
            "- 'query': A search-engine-optimized query string\n"
            "- 'focus': What type of information to harvest\n"
            "- 'priority': 1 (most important) to 5 (supplementary)\n"
            "Return JSON: {\"subtasks\": [{\"query\": str, \"focus\": str, \"priority\": int}]}"
        )
        prompt = (
            f"Research Topic: \"{topic}\"\n"
            f"Key Entities: {', '.join(entities) if entities else 'None identified'}\n"
            f"Scope: {scope}\n"
            f"Create {num_subtasks} diverse search subtasks."
        )
        try:
            result = await research_llm_client.generate_json(prompt, system_prompt=system_prompt)
            subtasks = result.get("subtasks", [{"query": topic, "focus": "General", "priority": 1}])
            subtasks.sort(key=lambda x: x.get("priority", 3))
            return subtasks
        except Exception as e:
            logger.warning(f"Research planning failed: {e}")
            return [{"query": topic, "focus": "General search", "priority": 1}]

    async def _extract_url_content(self, url: str) -> str:
        """Step 4: Extract content from a URL."""
        # PDF handling
        if url.lower().endswith(".pdf") or "/pdf/" in url.lower():
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, timeout=12.0)
                    if resp.status_code == 200:
                        from app.knowledge.file_processors import file_processor
                        txt, _ = file_processor.extract_text("paper.pdf", resp.content)
                        return txt
            except Exception as e:
                logger.warning(f"PDF extraction failed for {url}: {e}")

        # Web page extraction
        context = None
        page = None
        try:
            context, page = await search_manager.google.get_page_for_extraction()
            extracted = await search_manager.extractor.extract(page, url)
            if extracted.success:
                return extracted.content
        except Exception as e:
            logger.warning(f"Page extraction failed for {url}: {e}")
        finally:
            if page:
                await page.close()
            if context:
                await context.close()
        return ""

    async def _extract_facts(self, content: str, topic: str) -> list[str]:
        """Step 5: Extract atomic facts from content using research LLM."""
        system_prompt = (
            "You are AURA's Factual Extraction Engine.\n"
            "Extract all important facts, statistics, claims, and key findings related to the topic.\n"
            "Requirements:\n"
            "- Each fact must be a single, self-contained sentence\n"
            "- Only extract facts actually supported by the source text\n"
            "- Include specific numbers, dates, statistics when available\n"
            "- DO NOT fabricate or hallucinate any information\n"
            "Return JSON: {\"facts\": [\"fact1\", \"fact2\", ...]}"
        )
        prompt = f"Research Topic: {topic}\n\nSource Content:\n{content[:6000]}"
        try:
            result = await research_llm_client.generate_json(prompt, system_prompt=system_prompt)
            return result.get("facts", [])
        except Exception as e:
            logger.warning(f"Fact extraction failed: {e}")
            return []

    async def _verify_facts(self, raw_facts: list[dict], topic: str) -> list[dict]:
        """Step 6: Cross-verify facts, merge duplicates, assess reliability."""
        if not raw_facts:
            return []

        facts_list = []
        for i, item in enumerate(raw_facts[:30], 1):  # Cap to avoid token overflow
            facts_list.append(f"[{i}] Claim: {item['fact']} | Source: {item['url']} | Trust: {item['trust_score']}")

        system_prompt = (
            "You are AURA's Claims Verification & Deduplication Engine.\n"
            "Tasks:\n"
            "1. Merge duplicate or near-identical claims, combining their source URLs\n"
            "2. Evaluate claim truth across sources. Mark verification status:\n"
            "   - 'Verified': aligned across multiple independent sources\n"
            "   - 'Single Source': mentioned in only one source\n"
            "   - 'Conflicting': contradicting assertions across sources\n"
            "3. Assign an aggregated trust_score (0-100) based on source quality\n"
            "Return JSON: {\"verified_facts\": [{\"fact\": str, \"sources\": [urls], \"source_titles\": [titles], "
            "\"status\": str, \"trust_score\": int, \"notes\": str}]}"
        )
        prompt = f"Research Topic: {topic}\n\nRetrieved Claims:\n" + "\n".join(facts_list)

        try:
            result = await research_llm_client.generate_json(prompt, system_prompt=system_prompt)
            return result.get("verified_facts", [])
        except Exception as e:
            logger.warning(f"Verification failed: {e}")
            return [{
                "fact": rf["fact"],
                "sources": [rf["url"]],
                "source_titles": [rf["title"]],
                "status": "Single Source",
                "trust_score": rf["trust_score"],
                "notes": "",
            } for rf in raw_facts]

    async def _analyze_findings(self, facts: list[dict], topic: str, entities: list) -> dict:
        """Step 7: Deep analysis — patterns, counter-arguments, insights."""
        facts_text = "\n".join([f"- {f.get('fact', f) if isinstance(f, dict) else f}" for f in facts[:20]]) if facts else "No external facts extracted. Use foundational intelligence."

        system_prompt = (
            "You are AURA's Research Analyst. Perform deep strategic analysis on the topic and any verified facts.\n"
            "If external web facts are limited, synthesize thoroughly from your comprehensive pre-trained domain knowledge.\n"
            "Provide:\n"
            "1. Executive summary (2-3 sentences)\n"
            "2. Key patterns, strengths, weaknesses, and industry trends identified\n"
            "3. Counter-arguments, threats, or alternative market perspectives\n"
            "4. Strategic analysis or knowledge gaps\n"
            "5. Confidence assessment\n"
            "Return JSON: {\"summary\": str, \"patterns\": [str], \"counter_arguments\": [str], "
            "\"gaps\": [str], \"confidence\": str}"
        )
        prompt = f"Topic: {topic}\nEntities: {', '.join(entities) if entities else topic}\n\nVerified Facts:\n{facts_text}"

        try:
            return await research_llm_client.generate_json(prompt, system_prompt=system_prompt)
        except Exception as e:
            logger.warning(f"Analysis failed: {e}")
            return {"summary": f"Comprehensive strategic synthesis for {topic}.", "patterns": [], "counter_arguments": [], "gaps": []}

    async def _stream_report(
        self, facts: list[dict], analysis: dict, topic: str, sources: list[dict]
    ) -> AsyncGenerator[str | list[str], None]:
        """Step 8-9: Stream publication-grade report with inline citations."""
        # Normalize facts
        normalized = []
        for f in facts:
            if isinstance(f, str):
                normalized.append({"fact": f, "sources": [], "status": "Verified", "notes": ""})
            elif isinstance(f, dict):
                normalized.append({
                    "fact": f.get("fact", ""),
                    "sources": f.get("sources", []) if isinstance(f.get("sources"), list) else [],
                    "status": f.get("status", "Verified"),
                    "notes": f.get("notes", ""),
                })
        facts = normalized

        # Build numbered bibliography
        urls_map = {}
        idx = 1
        for f in facts:
            for s in f.get("sources", []):
                if s not in urls_map:
                    urls_map[s] = idx
                    idx += 1

        # Build facts context with citation indices
        facts_ctx = ""
        for i, f in enumerate(facts, 1):
            src_indices = [str(urls_map[s]) for s in f.get("sources", []) if s in urls_map]
            facts_ctx += f"Fact {i}: {f['fact']} | Citations: [{', '.join(src_indices)}] | Status: {f['status']}\n"

        # Analysis context
        analysis_ctx = ""
        if analysis:
            analysis_ctx = f"\nExecutive Summary: {analysis.get('summary', '')}\n"
            if analysis.get("patterns"):
                analysis_ctx += "Patterns: " + "; ".join(analysis["patterns"]) + "\n"
            if analysis.get("counter_arguments"):
                analysis_ctx += "Counter Arguments: " + "; ".join(analysis["counter_arguments"]) + "\n"
            if analysis.get("gaps"):
                analysis_ctx += "Knowledge Gaps: " + "; ".join(analysis["gaps"]) + "\n"

        system_prompt = (
            "You are AURA's Lead Research Scientist. Compile a PUBLICATION-GRADE research report.\n\n"
            "MANDATORY REPORT STRUCTURE (follow exactly):\n"
            "# [Research Title]\n\n"
            "## Executive Summary\n"
            "[2-3 paragraph overview]\n\n"
            "## Background\n"
            "[Context and importance of the topic]\n\n"
            "## Key Findings\n"
            "[Numbered list of the most important discoveries]\n\n"
            "## Detailed Analysis\n"
            "[In-depth discussion with subsections as needed]\n\n"
            "## Evidence\n"
            "[Specific data, statistics, and supporting evidence]\n\n"
            "## Counter Arguments\n"
            "[Alternative perspectives and criticisms]\n\n"
            "## Statistics\n"
            "[Key numbers and data points in a markdown table if applicable]\n\n"
            "## Sources\n"
            "[Numbered bibliography matching inline citations]\n\n"
            "## Conclusion\n"
            "[Final synthesis and implications]\n\n"
            "CITATION RULES:\n"
            "- When source citations are available, include inline references like [[1]](url)\n"
            "- Include markdown tables where strategic or data comparison is useful (e.g. SWOT Matrix: Strengths, Weaknesses, Opportunities, Threats)\n"
            "- Use **bold** for key terms, metrics, and strategic pillars\n"
            "- Output pure Markdown, no JSON wrapper or code fences\n\n"
            "INTELLIGENCE SYNTHESIS DIRECTIVES:\n"
            "- Deliver a thorough, comprehensive, publication-grade research analysis addressing all user questions\n"
            "- If the topic asks for a SWOT analysis, provide a detailed SWOT section with Strengths, Weaknesses, Opportunities, Threats, and Strategic Implications\n"
            "- Incorporate verified web facts where available, and synthesize with your deep foundational knowledge to provide actionable, exhaustive insights rather than refusing or stating data gaps\n"
            "- Maintain rigorous objectivity, clarity, and depth throughout"
        )

        prompt = (
            f"Research Topic: {topic}\n\n"
            f"Analysis Context:\n{analysis_ctx}\n\n"
            f"Verified Web Facts (if any):\n{facts_ctx if facts_ctx else 'Synthesize with foundational industry and company knowledge.'}\n\n"
            f"Bibliography Map:\n" + ("\n".join([f"[{v}] {k}" for k, v in urls_map.items()]) if urls_map else "Foundational Domain Intelligence")
        )

        try:
            yield list(urls_map.keys())  # Yield source URLs for backend tracking

            async for chunk in research_llm_client.stream_chat(
                [{"role": "user", "content": prompt}],
                system_prompt=system_prompt,
            ):
                yield chunk
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            yield f"# Research Report: {topic}\n\n## Findings\n\n"
            for f in facts:
                yield f"- {f.get('fact', '')}\n"

    async def _quality_check(self, report: str, facts: list[dict]) -> dict:
        """Step 10: Quality validation before final output."""
        checks = {
            "has_title": report.strip().startswith("#"),
            "has_executive_summary": "## Executive Summary" in report or "## executive summary" in report.lower(),
            "has_conclusion": "## Conclusion" in report or "## conclusion" in report.lower(),
            "has_sources": "## Sources" in report or "## sources" in report.lower() or "## References" in report,
            "has_citations": bool(re.search(r'\[\d+\]', report)),
            "citation_count": len(re.findall(r'\[\d+\]', report)),
            "word_count": len(report.split()),
            "facts_count": len(facts),
            "has_tables": "|" in report and "---" in report,
            "sections_count": report.count("## "),
        }

        # Overall quality score
        quality_score = 0
        if checks["has_title"]: quality_score += 10
        if checks["has_executive_summary"]: quality_score += 15
        if checks["has_conclusion"]: quality_score += 10
        if checks["has_sources"]: quality_score += 15
        if checks["has_citations"]: quality_score += 20
        if checks["citation_count"] >= 3: quality_score += 10
        if checks["word_count"] >= 500: quality_score += 10
        if checks["has_tables"]: quality_score += 5
        if checks["sections_count"] >= 5: quality_score += 5

        checks["quality_score"] = quality_score
        checks["passed"] = quality_score >= 50

        return checks

    # ══════════════════════════════════════════════════
    # EXPORT UTILITIES
    # ══════════════════════════════════════════════════

    def _export_docx(self, markdown_text: str, output_path: str):
        """Export report as structured Word document."""
        try:
            doc = Document()
            for section in doc.sections:
                section.top_margin = Inches(1)
                section.bottom_margin = Inches(1)
                section.left_margin = Inches(1)
                section.right_margin = Inches(1)

            lines = markdown_text.split("\n")
            for line in lines:
                line_strip = line.strip()
                if not line_strip:
                    continue
                if line_strip.startswith("# "):
                    doc.add_heading(line_strip[2:], level=1)
                elif line_strip.startswith("## "):
                    doc.add_heading(line_strip[3:], level=2)
                elif line_strip.startswith("### "):
                    doc.add_heading(line_strip[4:], level=3)
                elif line_strip.startswith("- ") or line_strip.startswith("* "):
                    doc.add_paragraph(line_strip[2:], style="List Bullet")
                elif line_strip.startswith("|") and line_strip.endswith("|"):
                    pass  # Skip table formatting in DOCX
                else:
                    p = doc.add_paragraph()
                    parts = re.split(r"(\*\*.*?\*\*)", line_strip)
                    for part in parts:
                        if part.startswith("**") and part.endswith("**"):
                            p.add_run(part[2:-2]).bold = True
                        else:
                            p.add_run(part)

            doc.save(output_path)
            logger.info(f"DOCX exported: {output_path}")
        except Exception as e:
            logger.error(f"DOCX export failed: {e}")

    async def _export_pdf(self, markdown_text: str, output_path: str, topic: str):
        """Export report as styled PDF using Playwright with a strict non-blocking timeout."""
        try:
            html_body = ""
            lines = markdown_text.split("\n")
            in_list = False

            for line in lines:
                ls = line.strip()
                if not ls:
                    if in_list:
                        html_body += "</ul>\n"
                        in_list = False
                    continue
                if ls.startswith("# "):
                    html_body += f"<h1>{ls[2:]}</h1>\n"
                elif ls.startswith("## "):
                    html_body += f"<h2>{ls[3:]}</h2>\n"
                elif ls.startswith("### "):
                    html_body += f"<h3>{ls[4:]}</h3>\n"
                elif ls.startswith("- ") or ls.startswith("* "):
                    if not in_list:
                        html_body += "<ul>\n"
                        in_list = True
                    html_body += f"<li>{ls[2:]}</li>\n"
                else:
                    if in_list:
                        html_body += "</ul>\n"
                        in_list = False
                    formatted = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", ls)
                    formatted = re.sub(r'\[\[(\d+)\]\]\((.*?)\)', r'<a href="\2">[\1]</a>', formatted)
                    html_body += f"<p>{formatted}</p>\n"

            if in_list:
                html_body += "</ul>\n"

            html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
            <title>Research: {topic}</title>
            <style>
                body {{ font-family: 'Georgia', serif; color: #1a1a1a; line-height: 1.7; padding: 40px; max-width: 800px; margin: 0 auto; }}
                h1 {{ font-size: 26px; color: #0f172a; border-bottom: 2px solid #3b82f6; padding-bottom: 8px; margin-top: 32px; }}
                h2 {{ font-size: 20px; color: #1e293b; margin-top: 28px; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; }}
                h3 {{ font-size: 16px; color: #334155; margin-top: 20px; }}
                p {{ margin-bottom: 14px; font-size: 14px; }}
                ul {{ margin-bottom: 14px; padding-left: 24px; }}
                li {{ font-size: 14px; margin-bottom: 5px; }}
                a {{ color: #3b82f6; text-decoration: none; }}
                strong {{ color: #0f172a; }}
                table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
                th, td {{ border: 1px solid #e2e8f0; padding: 8px 12px; font-size: 13px; }}
                th {{ background: #f8fafc; font-weight: 600; }}
            </style></head><body>{html_body}</body></html>"""

            async def do_pdf_export():
                context, page = await search_manager.google.get_page_for_extraction()
                try:
                    await page.set_content(html, timeout=3000)
                    await page.pdf(
                        path=output_path,
                        format="A4",
                        margin={"top": "20mm", "bottom": "20mm", "left": "20mm", "right": "20mm"}
                    )
                finally:
                    try:
                        await page.close()
                    except Exception:
                        pass
                    try:
                        await context.close()
                    except Exception:
                        pass

            # Strict 5.0 second timeout for the entire Playwright operation
            await asyncio.wait_for(do_pdf_export(), timeout=5.0)
            logger.info(f"PDF exported: {output_path}")
        except Exception as e:
            logger.warning(f"PDF export failed or timed out (bypassing to prevent hang): {e}")

    # ══════════════════════════════════════════════════
    # HELPER UTILITIES
    # ══════════════════════════════════════════════════

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract clean domain from URL."""
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.lower()
            return domain.replace("www.", "")
        except Exception:
            return url

    @staticmethod
    def _extract_date_hint(content: str) -> str | None:
        """Try to extract a publication date from content."""
        patterns = [
            r'(\d{4}-\d{2}-\d{2})',
            r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s+\d{4})',
            r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4})',
        ]
        for pattern in patterns:
            match = re.search(pattern, content[:2000])
            if match:
                return match.group(1)
        return None

    @staticmethod
    def _categorize_source(url: str) -> str:
        """Categorize source type based on URL."""
        url_lower = url.lower()
        if any(x in url_lower for x in ["arxiv.org", "pubmed", "scholar", "ieee", "acm.org", "nature.com"]):
            return "Research Paper"
        if any(x in url_lower for x in [".pdf"]):
            return "Document"
        if any(x in url_lower for x in [".gov", ".edu", "who.int", "un.org"]):
            return "Official Source"
        if any(x in url_lower for x in ["reuters", "bbc", "nytimes", "guardian", "bloomberg"]):
            return "News Article"
        return "Web Article"


# Global instance
research_engine = DeepResearchEngine()
