from functools import partial
from datasets import load_dataset, Dataset
from helpers.data import chunk_list, queue, save_json
from helpers.oai import async_gpt_calls
from helpers.progress import Progress
from pipelines.raw import run_raw
import asyncio


async def hotpot_raw():
    dataset = load_dataset("hotpotqa/hotpot_qa", "fullwiki", split="test")

    data = dataset.select_columns(["id", "question", "answer"]).select(range(1500))  # type: ignore

    if not isinstance(data, Dataset):
        raise TypeError("Expected a Dataset object")

    progress = Progress(len(data), "Benchmarking Hotpot Raw")

    results = await queue(
        [
            partial(run_raw, "hotpot_raw", prompt, progress)
            for prompt in data["question"]
        ],
    )
    progress.finish()

    decisions = await async_gpt_calls(
        [
            f"""Please determine if the answer is correct (respond with yes or no).
Accept partial/similar answers (eg. markedly improved = significantly improved)
If the answer is correct in any part of its explanation, it is correct.
Question:
{prompt}

Correct Answer:
{answer}

Provided Answer:
{result["correction"] if "correction" in result else result["response"]}"""
            for prompt, result, answer in zip(data["question"], results, data["answer"])
        ],
        max_tokens=10,
        system="Your answer must be a single word long, either yes or no.",
        progress_bar=True,
    )

    for result, decision in zip(results, decisions):
        result["correct"] = str(decision).lower()[0] == "y"

    correct = sum(1 for r in results if r["correct"])

    print(f"Correct: {correct}/{len(results)} = {correct / len(results) * 100:.2f}%")

    save_json(
        "results/hotpot_raw.json",
        [
            {
                "id": id,
                "is_correct": result["correct"],
                "answer": (
                    result["correction"]
                    if "correction" in result
                    else result["response"]
                ),
                "correct_answer": correct_answer,
            }
            for result, correct_answer, id in zip(results, data["answer"], data["id"])
        ],
    )
