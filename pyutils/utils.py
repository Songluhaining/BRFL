import os
from pathlib import Path
from typing import List, Dict, Any, Tuple
import json
import textwrap
from collections import defaultdict
from http import HTTPStatus
import dashscope
from dashscope import Generation

def load_test_file_source(variant_root: Path, estest_class: str) -> str:
    """
    根据 estest_class 找到对应测试 Java 文件源码。
    形如: ElevatorSystem.Elevator_ESTest -> test/ElevatorSystem/Elevator_ESTest.java
    """
    rel = estest_class.replace(".", "/") + ".java"
    candidate = variant_root / "test" / rel
    if not candidate.exists():
        # 这里打个 warning；模型那边可以看到注释，也知道缺失
        return f"// TEST SOURCE NOT FOUND for {estest_class}\n"

    return candidate.read_text(encoding="utf-8", errors="ignore")

def group_items_by_class(
    failed_items: List[Dict[str, Any]],
    passed_items: List[Dict[str, Any]],
) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, List[Dict[str, Any]]]]:
    """
    按 estest_class（测试类）分组 failed / passed 测试项。
    """
    failed_by_class: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    passed_by_class: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for it in failed_items:
        est = it.get("estest_class")
        if est:
            failed_by_class[est].append(it)

    for it in passed_items:
        est = it.get("estest_class")
        if est:
            passed_by_class[est].append(it)

    return failed_by_class, passed_by_class


def llm_match_passed_for_failed_in_class(
    estest_class: str,
    test_source: str,
    failed_items_in_class: List[Dict[str, Any]],
    passed_items_in_class: List[Dict[str, Any]],
    model_name: str = "qwen-plus",
    temperature: float = 0.1,
    top_k: int = 5,
    api_key: str | None = None,
) -> Dict[str, List[str]]:
    """
    使用 Qwen，为单个测试类 estest_class 中的每个 failing 测试方法，
    选出若干最相近的 passing 测试方法（反事实候选）。

    返回:
        mapping: {failed_method_name: [passed_method_name1, ...]}
    """
    # 1) 提取方法名列表，方便做合法性检查
    failed_methods = [it["test_method"] for it in failed_items_in_class]
    passed_methods = [it["test_method"] for it in passed_items_in_class]

    meta = {
        "test_class": estest_class,
        "failed_methods": failed_methods,
        "passed_methods": passed_methods,
    }

    # 2) 构造 prompt
    system_prompt = (
        "You are an assistant for software testing.\n"
        "You will receive:\n"
        "  (1) The source code of a Java test class.\n"
        "  (2) A list of failing test method names.\n"
        "  (3) A list of passing test method names.\n\n"
        "For each failing test method, you must select a small number of most similar\n"
        "passing test methods that can serve as counterfactual test cases\n"
        "(similar intention or scenario but passing).\n\n"
        "IMPORTANT CONSTRAINTS:\n"
        "- Only use the provided method names; do not invent new method names.\n"
        "- If no suitable passing candidate exists for a failing method, you may return an empty list.\n"
        "- The output MUST be a single JSON object with the structure:\n"
        "{\n"
        "  \"matches\": [\n"
        "    {\"failed\": \"<failed_method>\", \"candidates\": [\"<passed1>\", \"<passed2>\"]},\n"
        "    ...\n"
        "  ]\n"
        "}\n"
        "- Do NOT output any explanation or extra text outside this JSON.\n"
    )

    user_prompt = (
        "Here is the Java test class source code:\n"
        "<<<TEST_FILE_BEGIN>>>\n"
        f"{test_source}\n"
        "<<<TEST_FILE_END>>>\n\n"
        "Here is the metadata (in JSON):\n"
        f"{json.dumps(meta, indent=2)}\n\n"
        f"For each failing method, select up to {top_k} most similar passing methods.\n"
        "Return ONLY the JSON object described above."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_prompt},
    ]

    # 3) 调用 Qwen
    raw = call_qwen(
        messages,
        model=model_name,
        temperature=temperature,
        api_key="sk-f57b1660c96d4810a354314d2b7d1e80",
    ).strip()

    # 4) 处理可能出现的 ```json ... ``` 或额外说明，尽量只保留 JSON 部分
    def _extract_json(text: str) -> str:
        # 去掉 ```json / ``` 包裹
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        # 从第一个 '{' 到最后一个 '}' 截取
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and start < end:
            return text[start : end + 1]
        return text  # 尝试原文

    json_str = _extract_json(raw)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        # 方便调试：你可以在这里打印 raw 或写到日志
        raise RuntimeError(
            f"[LLM] JSON 解析失败: {e}\nRaw response was:\n{raw}"
        ) from e

    # 5) 构造 {failed_method -> [passed_method,...]} 映射
    mapping: Dict[str, List[str]] = {}
    for entry in data.get("matches", []):
        f = entry.get("failed")
        cands = entry.get("candidates") or []
        if not isinstance(f, str):
            continue
        # 只保留真实存在的 passing 方法，并限制 top_k
        valid_cands = [m for m in cands if m in passed_methods]
        if valid_cands:
            mapping[f] = valid_cands[:top_k]

    return mapping

def call_qwen(messages, model="qwen-plus", temperature=0.1, api_key: str | None = None) -> str:
    """
    仅使用 dashscope.Generation 调用千问对话模型。
    messages: [{"role":"system/user/assistant", "content":"..."}]
    """
    # 可选：显式设置 API Key（如果你已在外层设置了环境变量，这里可省略）
    # 1) 统一确定要用的 key
    key = api_key or os.getenv("DASHSCOPE_API_KEY")
    if not key:
        raise RuntimeError("未提供 DASHSCOPE_API_KEY 或 api_key")

    # 2) 同步给 dashscope 模块本身
    # dashscope.api_key = key

    # 使用 Generation，结果格式指定为 message，便于统一解析
    resp = Generation.call(
        model=model,
        messages=messages,
        temperature=temperature,
        result_format="message",
        api_key=key,
    )

    status = getattr(resp, "status_code", HTTPStatus.OK)
    if status != HTTPStatus.OK:
        code = getattr(resp, "code", None)
        msg = getattr(resp, "message", None)
        raise RuntimeError(f"DashScope Generation 调用失败: code={code}, message={msg}")

    try:
        return resp.output["choices"][0]["message"]["content"]
    except Exception:
        text = getattr(resp, "output", {}).get("text")
        if text:
            return text
        return json.dumps(getattr(resp, "output", {}), ensure_ascii=False)