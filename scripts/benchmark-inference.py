#!/usr/bin/env python3
"""
Hydra Inference Benchmark Script

Measures LLM inference performance across cluster endpoints.
Tracks tokens/second, latency, and throughput over time.

Usage:
    python benchmark-inference.py                    # Run default benchmark
    python benchmark-inference.py --endpoint tabby   # Test TabbyAPI only
    python benchmark-inference.py --compare          # Compare all endpoints
    python benchmark-inference.py --stress           # Stress test
    python benchmark-inference.py --save             # Save results to file
"""

import argparse
import json
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

import httpx
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich import box

console = Console()

# Endpoints
ENDPOINTS = {
    "tabby": {
        "url": "http://192.168.1.250:5000/v1/chat/completions",
        "name": "TabbyAPI (hydra-ai)",
        "node": "hydra-ai",
    },
    "ollama": {
        "url": "http://192.168.1.203:11434/v1/chat/completions",
        "name": "Ollama (hydra-compute)",
        "node": "hydra-compute",
    },
    "litellm": {
        "url": "http://192.168.1.244:4000/v1/chat/completions",
        "name": "LiteLLM Gateway",
        "node": "hydra-storage",
    },
}

# Benchmark prompts of varying complexity
PROMPTS = {
    "short": "What is 2+2?",
    "medium": "Explain the concept of recursion in programming with a simple example.",
    "long": """Write a detailed explanation of how neural networks learn,
including the concepts of forward propagation, backpropagation,
gradient descent, and the role of activation functions.
Include examples where appropriate.""",
    "code": """Write a Python function that implements a binary search tree
with insert, search, and delete operations. Include docstrings and type hints.""",
}

# Results directory
RESULTS_DIR = Path("benchmark-results")


@dataclass
class BenchmarkResult:
    """Single benchmark run result."""
    endpoint: str
    prompt_type: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    tokens_per_second: float
    time_to_first_token_ms: float
    success: bool
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    model: str = ""


@dataclass
class BenchmarkSummary:
    """Summary of multiple benchmark runs."""
    endpoint: str
    runs: int
    success_rate: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    avg_tokens_per_second: float
    avg_ttft_ms: float
    total_tokens: int
    duration_seconds: float


def count_tokens(text: str) -> int:
    """Rough token count estimation."""
    # Approximate: ~4 chars per token for English
    return len(text) // 4


def run_single_benchmark(
    endpoint_key: str,
    prompt: str,
    max_tokens: int = 256,
    model: str = "default",
    timeout: float = 120.0,
) -> BenchmarkResult:
    """Run a single inference benchmark."""
    endpoint = ENDPOINTS[endpoint_key]
    prompt_tokens = count_tokens(prompt)

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7,
        "stream": False,
    }

    headers = {"Content-Type": "application/json"}

    # Add API key if needed
    api_key = os.getenv("LITELLM_API_KEY", "")
    if api_key and endpoint_key == "litellm":
        headers["Authorization"] = f"Bearer {api_key}"

    start_time = time.perf_counter()
    ttft = 0

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                endpoint["url"],
                json=payload,
                headers=headers,
            )

        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000

        if response.status_code != 200:
            return BenchmarkResult(
                endpoint=endpoint_key,
                prompt_type="",
                prompt_tokens=prompt_tokens,
                completion_tokens=0,
                total_tokens=prompt_tokens,
                latency_ms=latency_ms,
                tokens_per_second=0,
                time_to_first_token_ms=0,
                success=False,
                error=f"HTTP {response.status_code}: {response.text[:100]}",
            )

        data = response.json()

        # Extract token counts
        usage = data.get("usage", {})
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

        # Calculate metrics
        if completion_tokens > 0:
            # Tokens per second for generation only
            generation_time = latency_ms / 1000  # Convert to seconds
            tokens_per_second = completion_tokens / generation_time
        else:
            tokens_per_second = 0

        return BenchmarkResult(
            endpoint=endpoint_key,
            prompt_type="",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            tokens_per_second=tokens_per_second,
            time_to_first_token_ms=ttft,
            success=True,
            model=data.get("model", model),
        )

    except httpx.TimeoutException:
        return BenchmarkResult(
            endpoint=endpoint_key,
            prompt_type="",
            prompt_tokens=prompt_tokens,
            completion_tokens=0,
            total_tokens=prompt_tokens,
            latency_ms=timeout * 1000,
            tokens_per_second=0,
            time_to_first_token_ms=0,
            success=False,
            error="Timeout",
        )
    except Exception as e:
        return BenchmarkResult(
            endpoint=endpoint_key,
            prompt_type="",
            prompt_tokens=prompt_tokens,
            completion_tokens=0,
            total_tokens=prompt_tokens,
            latency_ms=0,
            tokens_per_second=0,
            time_to_first_token_ms=0,
            success=False,
            error=str(e),
        )


def run_benchmark_suite(
    endpoint_key: str,
    runs_per_prompt: int = 3,
    max_tokens: int = 256,
) -> List[BenchmarkResult]:
    """Run a complete benchmark suite."""
    results = []

    total_runs = len(PROMPTS) * runs_per_prompt
    endpoint = ENDPOINTS[endpoint_key]

    console.print(f"\n[cyan]Benchmarking {endpoint['name']}[/cyan]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("Running benchmarks", total=total_runs)

        for prompt_type, prompt in PROMPTS.items():
            for run in range(runs_per_prompt):
                progress.update(
                    task,
                    description=f"{prompt_type} (run {run + 1}/{runs_per_prompt})"
                )

                result = run_single_benchmark(
                    endpoint_key,
                    prompt,
                    max_tokens=max_tokens,
                )
                result.prompt_type = prompt_type
                results.append(result)

                progress.advance(task)

                # Small delay between runs
                time.sleep(0.5)

    return results


def calculate_summary(results: List[BenchmarkResult], endpoint_key: str) -> BenchmarkSummary:
    """Calculate summary statistics from results."""
    successful = [r for r in results if r.success]

    if not successful:
        return BenchmarkSummary(
            endpoint=endpoint_key,
            runs=len(results),
            success_rate=0,
            avg_latency_ms=0,
            p50_latency_ms=0,
            p95_latency_ms=0,
            p99_latency_ms=0,
            avg_tokens_per_second=0,
            avg_ttft_ms=0,
            total_tokens=0,
            duration_seconds=0,
        )

    latencies = [r.latency_ms for r in successful]
    tps_values = [r.tokens_per_second for r in successful if r.tokens_per_second > 0]

    latencies.sort()
    p50_idx = len(latencies) // 2
    p95_idx = int(len(latencies) * 0.95)
    p99_idx = int(len(latencies) * 0.99)

    return BenchmarkSummary(
        endpoint=endpoint_key,
        runs=len(results),
        success_rate=len(successful) / len(results) * 100,
        avg_latency_ms=statistics.mean(latencies),
        p50_latency_ms=latencies[p50_idx] if latencies else 0,
        p95_latency_ms=latencies[p95_idx] if len(latencies) > p95_idx else latencies[-1],
        p99_latency_ms=latencies[p99_idx] if len(latencies) > p99_idx else latencies[-1],
        avg_tokens_per_second=statistics.mean(tps_values) if tps_values else 0,
        avg_ttft_ms=statistics.mean([r.time_to_first_token_ms for r in successful]),
        total_tokens=sum(r.total_tokens for r in successful),
        duration_seconds=sum(r.latency_ms for r in successful) / 1000,
    )


def print_results(summary: BenchmarkSummary):
    """Print benchmark results."""
    endpoint = ENDPOINTS[summary.endpoint]

    table = Table(
        title=f"Benchmark Results: {endpoint['name']}",
        box=box.ROUNDED,
    )
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Total Runs", str(summary.runs))
    table.add_row("Success Rate", f"{summary.success_rate:.1f}%")
    table.add_row("", "")
    table.add_row("Avg Latency", f"{summary.avg_latency_ms:.1f} ms")
    table.add_row("P50 Latency", f"{summary.p50_latency_ms:.1f} ms")
    table.add_row("P95 Latency", f"{summary.p95_latency_ms:.1f} ms")
    table.add_row("P99 Latency", f"{summary.p99_latency_ms:.1f} ms")
    table.add_row("", "")
    table.add_row("Avg Tokens/sec", f"{summary.avg_tokens_per_second:.1f}")
    table.add_row("Total Tokens", str(summary.total_tokens))
    table.add_row("Total Duration", f"{summary.duration_seconds:.1f} s")

    console.print(table)


def compare_endpoints(runs_per_prompt: int = 3):
    """Compare all endpoints."""
    all_results = {}
    all_summaries = {}

    for endpoint_key in ENDPOINTS:
        try:
            results = run_benchmark_suite(endpoint_key, runs_per_prompt)
            summary = calculate_summary(results, endpoint_key)
            all_results[endpoint_key] = results
            all_summaries[endpoint_key] = summary
        except Exception as e:
            console.print(f"[red]Failed to benchmark {endpoint_key}: {e}[/red]")

    # Comparison table
    console.print("\n")
    table = Table(title="Endpoint Comparison", box=box.ROUNDED)
    table.add_column("Endpoint", style="cyan")
    table.add_column("Success %", justify="right")
    table.add_column("Avg Latency", justify="right")
    table.add_column("P95 Latency", justify="right")
    table.add_column("Tokens/sec", justify="right")

    for key, summary in all_summaries.items():
        endpoint = ENDPOINTS[key]
        table.add_row(
            endpoint["name"],
            f"{summary.success_rate:.0f}%",
            f"{summary.avg_latency_ms:.0f} ms",
            f"{summary.p95_latency_ms:.0f} ms",
            f"{summary.avg_tokens_per_second:.1f}",
        )

    console.print(table)

    return all_results, all_summaries


def stress_test(endpoint_key: str, concurrent: int = 5, duration: int = 60):
    """Run concurrent stress test."""
    console.print(f"\n[cyan]Stress Testing {ENDPOINTS[endpoint_key]['name']}[/cyan]")
    console.print(f"Concurrent requests: {concurrent}")
    console.print(f"Duration: {duration} seconds\n")

    results = []
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=concurrent) as executor:
        with Progress(console=console) as progress:
            task = progress.add_task("Stress testing...", total=duration)

            while time.time() - start_time < duration:
                # Submit batch of requests
                futures = [
                    executor.submit(
                        run_single_benchmark,
                        endpoint_key,
                        PROMPTS["short"],
                        max_tokens=50,
                    )
                    for _ in range(concurrent)
                ]

                for future in as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        console.print(f"[red]Error: {e}[/red]")

                elapsed = time.time() - start_time
                progress.update(task, completed=min(elapsed, duration))

    # Summary
    summary = calculate_summary(results, endpoint_key)
    summary.runs = len(results)
    summary.duration_seconds = time.time() - start_time

    console.print(f"\n[bold]Stress Test Complete[/bold]")
    console.print(f"Total Requests: {len(results)}")
    console.print(f"Requests/second: {len(results) / summary.duration_seconds:.1f}")
    print_results(summary)

    return results


def save_results(results: List[BenchmarkResult], filename: Optional[str] = None):
    """Save results to JSON file."""
    RESULTS_DIR.mkdir(exist_ok=True)

    if not filename:
        filename = f"benchmark-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"

    filepath = RESULTS_DIR / filename

    data = {
        "timestamp": datetime.now().isoformat(),
        "results": [asdict(r) for r in results],
    }

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    console.print(f"\n[green]Results saved to {filepath}[/green]")
    return filepath


def main():
    parser = argparse.ArgumentParser(description="Hydra Inference Benchmark")
    parser.add_argument(
        "--endpoint", "-e",
        choices=list(ENDPOINTS.keys()),
        default="tabby",
        help="Endpoint to benchmark",
    )
    parser.add_argument(
        "--runs", "-n",
        type=int,
        default=3,
        help="Runs per prompt type",
    )
    parser.add_argument(
        "--max-tokens", "-t",
        type=int,
        default=256,
        help="Max tokens to generate",
    )
    parser.add_argument(
        "--compare", "-c",
        action="store_true",
        help="Compare all endpoints",
    )
    parser.add_argument(
        "--stress", "-s",
        action="store_true",
        help="Run stress test",
    )
    parser.add_argument(
        "--concurrent",
        type=int,
        default=5,
        help="Concurrent requests for stress test",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Duration for stress test (seconds)",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save results to file",
    )

    args = parser.parse_args()

    console.print(Panel.fit("[bold blue]Hydra Inference Benchmark[/bold blue]"))

    if args.compare:
        all_results, _ = compare_endpoints(args.runs)
        if args.save:
            for key, results in all_results.items():
                save_results(results, f"benchmark-{key}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")

    elif args.stress:
        results = stress_test(args.endpoint, args.concurrent, args.duration)
        if args.save:
            save_results(results)

    else:
        results = run_benchmark_suite(args.endpoint, args.runs, args.max_tokens)
        summary = calculate_summary(results, args.endpoint)
        print_results(summary)

        if args.save:
            save_results(results)


if __name__ == "__main__":
    main()
