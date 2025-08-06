from utils import calculate_bleu_score, get_rep_wording_hints
from multiprocessing import Pool


def _calculate_one(entry):
    task = entry["task"]
    existing_tasks = entry["existing_tasks"]
    bleu_scores = []
    for existing_task in existing_tasks:
        bleu_score = calculate_bleu_score(task, existing_task)
        bleu_scores.append(bleu_score)
    return {        
        "bleu_scores": bleu_scores
    }


class DiversityHelper:
    def __init__(self, n_workers=32):
        self.n_workers = n_workers
        self.pool = Pool(n_workers)

    def calculate_diversity(self, task, existing_tasks):
        query_entries = []
        BZ = len(existing_tasks) // self.n_workers
        for i in range(self.n_workers):
            start = i * BZ
            end = (i + 1) * BZ if i != self.n_workers - 1 else len(existing_tasks)
            if start >= len(existing_tasks):
                break
            query_entries.append(
                {
                    "task": task,
                    "existing_tasks": existing_tasks[start:end],
                }
            )
        results = self.pool.map(_calculate_one, query_entries)
        all_bleu_scores = []
        for result in results:
            all_bleu_scores.extend(result["bleu_scores"])
        return all_bleu_scores


def get_overlap_wording_hints(query, existing):
    overlap_1_gram, overlap_2_gram, overlap_3_gram, overlap_4_gram = get_rep_wording_hints(
        query, existing
    )
    hints = """
<Overlapped 1-gram>
{one_gram}
</Overlapped 1-gram>
<Overlapped 2-gram>
{two_gram}
</Overlapped 2-gram>
<Overlapped 3-gram>
{three_gram}
</Overlapped 3-gram>
<Overlapped 4-gram>
{four_gram}
</Overlapped 4-gram>
""".strip().format(
                one_gram=overlap_1_gram[:10],
                two_gram=overlap_2_gram[:10],
                three_gram=overlap_3_gram[:10],
                four_gram=overlap_4_gram[:10],
            )
    return hints