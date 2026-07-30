"""
eval/run_eval.py — Chạy TOÀN BỘ eval/golden_set.json qua AGENT THẬT (gọi
Gemini thật qua src/llm_handler.run_agent_with_trace, KHÔNG mock) rồi tự
chấm pass/fail theo đúng tiêu chí đã khai trong spec.md §7:
  - Case có "expected_output_keywords": PASS nếu câu trả lời cuối cùng chứa
    đủ tất cả từ khoá kỳ vọng (không phân biệt hoa/thường).
  - Case có "expected_intent": PASS nếu agent có gọi đúng tool tương ứng
    với action kỳ vọng (create/update/cancel/list_events/notify_missing).

Mỗi lần chạy được LƯU LẠI có version (v1, v2, v3...) trong eval/runs/, để so
sánh qua các lần chỉnh sửa prompts.py/tools.py — không cần giữ nhiều bản sao
song song của prompt (git đã lưu lịch sử đó rồi), chỉ cần lưu lại KẾT QUẢ mỗi
lần chạy để biết lần chỉnh sửa nào làm % pass tăng/giảm.

Cách chạy:
    python eval/run_eval.py
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from match_manager import MatchManager  # noqa: E402
from llm_handler import run_agent_with_trace  # noqa: E402

GOLDEN_SET_PATH = BASE_DIR / "eval" / "golden_set.json"
RUNS_DIR = BASE_DIR / "eval" / "runs"

# action (trong golden_set.json) -> tên tool tương ứng phải được agent gọi
EXPECTED_TOOL_FOR_ACTION = {
    "create": "create_match",
    "update": "update_match",
    "cancel": "cancel_match",
    "list_events": "list_open_matches",
    # "notify_missing": không có tool riêng — đây là side-effect của
    # leave_match khi 1 trận đang đủ người rớt xuống thiếu. Case này được
    # đánh dấu SKIP (cần soát tay) thay vì auto pass/fail — xem README bên
    # dưới phần in kết quả.
}


def _seed_matches(mgr: MatchManager) -> None:
    """Seed vài trận cố định để các case cần dữ liệu (list/find/cancel/update) có gì để thao tác."""
    mgr.create_match(
        sport="bóng đá", time="17h", location="sân nội khu",
        creator_name="Duong", creator_id=800001, level="vui là chính",
    )
    mgr.create_match(
        sport="cầu lông", time="8h sáng chủ nhật", location="sân indoor",
        creator_name="Lan", creator_id=800002, level="trung bình",
    )


def _check_keywords(reply_text: str, keywords: list[str]) -> tuple[bool, list[str]]:
    t = reply_text.lower()
    hits = [k for k in keywords if k.lower() in t]
    return len(hits) == len(keywords), hits


def _check_intent(tool_calls: list[dict], expected_intent: dict):
    expected_action = expected_intent.get("action")
    expected_tool = EXPECTED_TOOL_FOR_ACTION.get(expected_action)
    called_names = [c["name"] for c in tool_calls]
    if expected_tool is None:
        return None, called_names, f"action '{expected_action}' không có tool ánh xạ trực tiếp — cần soát tay"
    return (expected_tool in called_names), called_names, f"kỳ vọng gọi '{expected_tool}'"


def _next_version() -> int:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    nums = [int(m.group(1)) for f in RUNS_DIR.glob("v*_*.json") if (m := re.match(r"v(\d+)_", f.name))]
    return max(nums, default=0) + 1


def run() -> None:
    cases = json.loads(GOLDEN_SET_PATH.read_text(encoding="utf-8"))

    matches_path = RUNS_DIR / "_eval_matches_scratch.json"
    if matches_path.exists():
        matches_path.unlink()
    mgr = MatchManager(data_path=matches_path)
    _seed_matches(mgr)

    results = []
    for i, case in enumerate(cases):
        # user_id riêng cho mỗi case -> mỗi case là 1 phiên chat độc lập,
        # không bị lẫn ngữ cảnh/tool xác nhận của case trước.
        uid = 900000 + i

        # Case dạng "sửa/huỷ trận" (cancel_event/update_event) cần CÓ SẴN 1
        # trận do CHÍNH user_id này tạo, nếu không agent sẽ (đúng theo thiết
        # kế) từ chối vì không tìm thấy trận nào để thao tác -> seed riêng.
        expected = case.get("expected_intent", {})
        if case.get("type") in ("cancel_event", "update_event") and expected.get("sport"):
            mgr.create_match(
                sport=expected["sport"],
                time="17h",
                location="sân nội khu",
                creator_name=f"EvalUser{i}",
                creator_id=uid,
            )

        reply_text, tool_calls = run_agent_with_trace(
            user_id=uid, user_name=f"EvalUser{i}", user_text=case["input"], match_manager=mgr
        )

        passed = None
        detail = ""
        if "expected_output_keywords" in case:
            passed, hits = _check_keywords(reply_text, case["expected_output_keywords"])
            detail = f"khớp {len(hits)}/{len(case['expected_output_keywords'])} từ khoá: {hits}"
        elif "expected_intent" in case:
            passed, called_names, note = _check_intent(tool_calls, case["expected_intent"])
            detail = f"{note} | tool thực tế đã gọi: {called_names}"
        else:
            detail = "(case không có expected_output_keywords/expected_intent — cần soát tay)"

        results.append(
            {
                "id": case["id"],
                "layer": case.get("layer", ""),
                "type": case.get("type", ""),
                "input": case["input"],
                "reply": reply_text,
                "tool_calls": tool_calls,
                "passed": passed,
                "detail": detail,
            }
        )
        status = "PASS" if passed is True else ("FAIL" if passed is False else "SKIP")
        print(f"[{case['id']:8}] {status:4} — {detail}")

    total = len(results)
    passed_n = sum(1 for r in results if r["passed"] is True)
    failed_n = sum(1 for r in results if r["passed"] is False)
    skipped_n = sum(1 for r in results if r["passed"] is None)
    graded = passed_n + failed_n
    pct = round(100 * passed_n / graded, 1) if graded else 0.0

    version = _next_version()
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    out_path = RUNS_DIR / f"v{version}_{ts}.json"
    out_path.write_text(
        json.dumps(
            {
                "version": version,
                "timestamp": ts,
                "model": __import__("llm_handler").GEMINI_MODEL,
                "total_cases": total,
                "passed": passed_n,
                "failed": failed_n,
                "skipped_needs_manual_review": skipped_n,
                "pass_rate_percent_of_graded": pct,
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    if matches_path.exists():
        matches_path.unlink()

    print()
    print(f"=== KẾT QUẢ v{version} ({ts}) — model {__import__('llm_handler').GEMINI_MODEL} ===")
    print(f"Pass: {passed_n}/{graded} case đã chấm được ({pct}%) | Fail: {failed_n} | Cần soát tay: {skipped_n}")
    print(f"Quality bar spec.md §7: ≥85% pass, 0% hallucination — {'ĐẠT' if pct >= 85 else 'CHƯA ĐẠT'} theo pass rate.")
    print(f"Đã lưu chi tiết đầy đủ vào {out_path.relative_to(BASE_DIR)}")
    print("Log toàn bộ lời gọi AI thật (bằng chứng cho R5): logs/agent_calls.jsonl")


if __name__ == "__main__":
    run()
