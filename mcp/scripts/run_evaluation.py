#!/usr/bin/env python3
"""
MCP Server Evaluation Runner

Per MCP Builder best practices (Phase 4), this script:
1. Loads evaluation questions from XML file
2. Runs questions against the MCP server
3. Compares answers and reports accuracy

Usage:
    python run_evaluation.py [--eval-file PATH] [--transport stdio|http]
"""
import argparse
import asyncio
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class QAPair:
    """Question-answer pair for evaluation"""
    question: str
    expected_answer: str
    tools_needed: str
    complexity: str
    actual_answer: Optional[str] = None
    correct: Optional[bool] = None
    error: Optional[str] = None


def load_evaluations(xml_path: str) -> list[QAPair]:
    """Load evaluation Q&A pairs from XML file"""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    qa_pairs = []
    for qa in root.findall('qa_pair'):
        question = qa.find('question').text.strip()
        answer = qa.find('answer').text.strip()
        tools = qa.find('tools_needed').text.strip() if qa.find('tools_needed') is not None else ""
        complexity = qa.find('complexity').text.strip() if qa.find('complexity') is not None else "unknown"

        qa_pairs.append(QAPair(
            question=question,
            expected_answer=answer,
            tools_needed=tools,
            complexity=complexity
        ))

    return qa_pairs


def check_answer(expected: str, actual: str) -> bool:
    """Compare expected and actual answers (case-insensitive, whitespace-normalized)"""
    if not actual:
        return False

    # Normalize for comparison
    expected_norm = expected.lower().strip()
    actual_norm = actual.lower().strip()

    # Direct match
    if expected_norm == actual_norm:
        return True

    # Check if actual contains expected (for partial matches)
    if expected_norm in actual_norm:
        return True

    # Try numeric comparison if both are numbers
    try:
        if float(expected_norm) == float(actual_norm):
            return True
    except ValueError:
        pass

    return False


def print_results(qa_pairs: list[QAPair]) -> dict:
    """Print evaluation results and return summary"""
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)

    correct = 0
    total = len(qa_pairs)

    for i, qa in enumerate(qa_pairs, 1):
        status = "PASS" if qa.correct else "FAIL"
        status_emoji = "✅" if qa.correct else "❌"

        print(f"\n{i}. [{status}] {status_emoji}")
        print(f"   Question: {qa.question[:60]}...")
        print(f"   Expected: {qa.expected_answer}")
        print(f"   Actual:   {qa.actual_answer or 'N/A'}")
        if qa.error:
            print(f"   Error:    {qa.error}")

        if qa.correct:
            correct += 1

    # Summary
    accuracy = (correct / total * 100) if total > 0 else 0
    print("\n" + "=" * 60)
    print(f"SUMMARY: {correct}/{total} correct ({accuracy:.1f}% accuracy)")
    print("=" * 60)

    # MCP Builder target: 80% accuracy
    if accuracy >= 80:
        print("✅ PASSED: Meets MCP Builder 80% accuracy target")
    else:
        print("❌ FAILED: Below MCP Builder 80% accuracy target")

    return {
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "passed": accuracy >= 80
    }


async def run_stdio_evaluation(qa_pairs: list[QAPair], server_cmd: str) -> list[QAPair]:
    """Run evaluation using stdio transport (not implemented - requires MCP client)"""
    print("⚠️  Stdio evaluation requires an MCP client to interact with the server.")
    print("    This script provides the framework - integrate with your MCP client.")
    print("")
    print("    For manual testing, use Claude Code CLI:")
    print(f"    claude mcp add databricks-mcp python {server_cmd}")
    print("")
    return qa_pairs


def main():
    parser = argparse.ArgumentParser(description="Run MCP server evaluations")
    parser.add_argument(
        "--eval-file",
        default="evaluations/databricks_mcp_eval.xml",
        help="Path to evaluation XML file"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport method for MCP communication"
    )
    parser.add_argument(
        "--server-cmd",
        default="server/main.py",
        help="Server command for stdio transport"
    )
    parser.add_argument(
        "--output",
        help="Output file for JSON results"
    )

    args = parser.parse_args()

    # Resolve paths relative to mcp directory
    mcp_dir = Path(__file__).parent.parent
    eval_file = mcp_dir / args.eval_file

    if not eval_file.exists():
        print(f"Error: Evaluation file not found: {eval_file}")
        print("")
        print("To create evaluations:")
        print("1. Copy evaluations/databricks_mcp_eval.xml")
        print("2. Update placeholder values with actual workspace resources")
        print("3. Run this script again")
        sys.exit(1)

    # Load evaluations
    print(f"Loading evaluations from: {eval_file}")
    qa_pairs = load_evaluations(str(eval_file))
    print(f"Loaded {len(qa_pairs)} evaluation questions")

    # Check for placeholder values
    placeholders = [qa for qa in qa_pairs if "UPDATE_WITH" in qa.expected_answer]
    if placeholders:
        print(f"\n⚠️  WARNING: {len(placeholders)} questions have placeholder answers")
        print("   Update these before running full evaluation:")
        for qa in placeholders[:3]:
            print(f"   - {qa.question[:50]}...")
        if len(placeholders) > 3:
            print(f"   ... and {len(placeholders) - 3} more")
        print("")

    # Run evaluation
    if args.transport == "stdio":
        qa_pairs = asyncio.run(run_stdio_evaluation(qa_pairs, args.server_cmd))
    else:
        print("HTTP transport not yet implemented")

    # Print results
    summary = print_results(qa_pairs)

    # Save results if output specified
    if args.output:
        output_data = {
            "summary": summary,
            "questions": [
                {
                    "question": qa.question,
                    "expected": qa.expected_answer,
                    "actual": qa.actual_answer,
                    "correct": qa.correct,
                    "tools_needed": qa.tools_needed,
                    "complexity": qa.complexity
                }
                for qa in qa_pairs
            ]
        }
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2)
        print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()
